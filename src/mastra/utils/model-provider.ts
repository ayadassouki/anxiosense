/**
 * src/mastra/utils/model-provider.ts
 *
 * Shared model factory for all AnxioSense agents.
 *
 * Configuration (set in the Mastra process environment — anxiosense/.env):
 *
 *   MODEL_PROVIDER   groq | openrouter | mistral   (default: groq)
 *   MODEL_ID         model identifier               (default: llama-3.3-70b-versatile)
 *   GROQ_API_KEY     required when MODEL_PROVIDER=groq
 *   OPENROUTER_API_KEY  required when MODEL_PROVIDER=openrouter
 *   MISTRAL_API_KEY  required when MODEL_PROVIDER=mistral
 *
 * To switch models, update MODEL_PROVIDER + MODEL_ID in anxiosense/.env and
 * restart the Mastra dev server (npm run dev from the repo root).
 *
 * Stage C evaluation models — ALL five run through OpenRouter so that the API
 * surface, SDK path, auth, retry logic and error taxonomy are identical across
 * families. Identifiers verified against the OpenRouter catalogue snapshot
 * (338 models, sha256 8950a2285eef034e…, retrieved 2026-08-04):
 *
 *   openrouter  meta-llama/llama-4-scout        pin DeepInfra   (fp8)
 *   openrouter  mistralai/mistral-small-2603    pin Mistral     (Mistral Small 4)
 *   openrouter  google/gemma-4-31b-it           pin DeepInfra   (see fp4/fp8 note below)
 *   openrouter  deepseek/deepseek-v4-flash      pin DeepInfra   (fp4)
 *   openrouter  microsoft/phi-4                 pin DeepInfra   (bf16, sole provider)
 *
 * The `groq` and `mistral` branches remain supported for ad-hoc use but are not
 * part of the Stage C matrix. No separate MISTRAL_API_KEY is required.
 */

import { createGroq }    from '@ai-sdk/groq';
import { createOpenAI }  from '@ai-sdk/openai';
import { createMistral } from '@ai-sdk/mistral';

export type ModelProvider = 'groq' | 'openrouter' | 'mistral';

/**
 * PROVIDER-DEFAULT DECODING — methodology change 2026-08-04.
 *
 * The approved methodology is that each model uses its own default settings. The
 * only faithful implementation is to send NO decoding parameters at all, so each
 * provider applies its own server-side default. Any number we transmit would be
 * our choice, not the provider's.
 *
 * This REPLACES the 2026-08-03 freeze, which injected temperature=0 and
 * max_tokens=4096 into every outgoing body. Data collected under that freeze is
 * preserved unmodified in evaluation/llm-experiments/outputs/stage_c_v2/ and
 * remains valid as a temperature-0 dataset.
 *
 * `stripDecodingParams` actively DELETES these keys rather than merely declining
 * to add them. The Vercel AI SDK does not set them today, but a silent SDK or
 * Mastra upgrade could reintroduce an unrecorded override. Deleting makes the
 * guarantee enforceable, and scripts/verify_provider_routing.ts asserts the keys
 * are absent from the wire.
 *
 * CONSEQUENCE TO RECORD IN THE WRITE-UP: the applied value becomes unobservable.
 * OpenRouter Chat Completions does not echo request parameters. Among the five
 * selected models only Gemma 4 31B publishes a numeric default
 * (temperature 1, top_p 0.95, top_k 64) in the catalogue's `default_parameters`;
 * the other four publish nothing and must be recorded as
 * "unknown / provider default applied".
 */
const OMITTED_DECODING_KEYS = [
    'temperature',
    'max_tokens',
    'max_completion_tokens',   // Responses-API spelling, stripped defensively
    'seed',
] as const;

let stripNoticeShown = false;

/** Removes optional decoding parameters so the provider's own defaults apply. */
function stripDecodingParams(init?: RequestInit): RequestInit | undefined {
    if (!init || typeof init.body !== 'string') return init;
    try {
        const body = JSON.parse(init.body);
        if (!body || typeof body !== 'object') return init;
        const removed: string[] = [];
        for (const key of OMITTED_DECODING_KEYS) {
            if (body[key] !== undefined) {
                delete body[key];
                removed.push(key);
            }
        }
        if (removed.length === 0) return init;
        if (!stripNoticeShown) {
            stripNoticeShown = true;
            console.warn(
                `[model-provider] Stripped decoding parameter(s) [${removed.join(', ')}] from the ` +
                `outgoing request body. Provider defaults are in force by design (methodology ` +
                `2026-08-04). If you did not expect this, something upstream is setting them.`
            );
        }
        return { ...init, body: JSON.stringify(body) };
    } catch {
        // Not a JSON body — leave it exactly as it was.
    }
    return init;
}

/** fetch wrapper for providers that need decoding stripped but not OpenRouter routing. */
async function fetchWithProviderDefaults(
    input: RequestInfo | URL,
    init?: RequestInit,
): Promise<Response> {
    return fetch(input, stripDecodingParams(init));
}

/**
 * PER-MODEL upstream provider pin for OpenRouter.
 *
 * OpenRouter load-balances a model across several upstream inference providers.
 * For meta-llama/llama-4-scout the `Google` upstream returned token-dropped
 * output: measured 2026-08-03 over 200 calls, 21/21 Google responses were
 * corrupted while DeepInfra (87), Groq (70) and Novita (22) were clean — perfect
 * separation. Dropped tokens arrive with finish_reason "stop" and a matching
 * (reduced) output_tokens count, so nothing downstream can detect them.
 *
 * The pin's purpose is to hold ONE upstream fixed PER MODEL, removing the
 * mixed-quantisation / mixed-implementation confound within a model. It is NOT
 * an attempt to standardise on one vendor: no single provider serves all five
 * models, so quantisation still differs BETWEEN models (fp8 / fp4 / bf16). That
 * is a disclosed limitation, not a controlled variable.
 *
 * allow_fallbacks:false means a request errors rather than silently re-routing —
 * the evaluation harness records that as a provider error, which is what we want.
 *
 * Verified against GET /api/v1/models/{id}/endpoints on 2026-08-04:
 *   meta-llama/llama-4-scout      DeepInfra fp8   ctx 327680   uptime 99.8%
 *   mistralai/mistral-small-2603  Mistral         ctx 262144   uptime 100.0%
 *   google/gemma-4-31b-it         DeepInfra fp4   ctx 262144   uptime 99.9%
 *   deepseek/deepseek-v4-flash    DeepInfra fp4   ctx 1048576  uptime 99.7%
 *   microsoft/phi-4               DeepInfra bf16  ctx 16384    uptime 100.0%  (sole provider)
 *
 * QUANTISATION — google/gemma-4-31b-it is served by TWO DeepInfra endpoints,
 * fp4 ($0.09/$0.34) and fp8 ($0.13/$0.38). `order:["DeepInfra"]` alone does not
 * choose between them, and the response's `provider` field reads "DeepInfra"
 * either way, so a switch mid-run would be INVISIBLE in the collected data.
 * Resolved 2026-08-04 by adding `quantizations:['fp4']` for that model. Combined
 * with allow_fallbacks:false, an unavailable precision now ERRORS instead of
 * silently falling through to fp8 — the harness records that as a provider error.
 *
 * The other four each have exactly ONE endpoint at the pinned provider, so a
 * filter is unnecessary today (Llama fp8, DeepSeek fp4, Phi-4 bf16; Mistral
 * publishes no quantisation, so no valid filter value exists). Their observed
 * precision is recorded in experiment_config.yaml for the write-up. If a second
 * endpoint ever appears, add `quantizations` for that model too.
 *
 * NOTE FOR THE WRITE-UP: `quantizations` is a REQUEST DIRECTIVE, not an observed
 * value — OpenRouter's chat response carries `provider` but not `quantization`.
 * What guarantees it is allow_fallbacks:false: a request that cannot be served at
 * fp4 fails loudly rather than being served at another precision. Enforcement is
 * by hard failure, not by measurement.
 */
export interface UpstreamRoute {
    /** OpenRouter upstream provider name, e.g. "DeepInfra". */
    provider: string;
    /** Optional precision filter. Omit when the provider has a single endpoint. */
    quantizations?: string[];
}

export const MODEL_ROUTE: Readonly<Record<string, UpstreamRoute>> = Object.freeze({
    'meta-llama/llama-4-scout':     { provider: 'DeepInfra' },                          // sole endpoint, fp8
    'mistralai/mistral-small-2603': { provider: 'Mistral'   },                          // no published quantisation
    'google/gemma-4-31b-it':        { provider: 'DeepInfra', quantizations: ['fp4'] },  // TWO endpoints — filtered
    'deepseek/deepseek-v4-flash':   { provider: 'DeepInfra' },                          // sole endpoint, fp4
    'microsoft/phi-4':              { provider: 'DeepInfra' },                          // sole endpoint, bf16
});

/**
 * OPENROUTER_PIN_PROVIDER is retained only as an escape hatch and NO LONGER
 * selects the pin. The per-model table above always wins.
 *
 * Accepted values:
 *   'none'                        disable pinning entirely (diagnostics only)
 *   '' or unset                   use the table (normal operation)
 *   anything else (e.g. legacy    IGNORED with a loud warning. A single global
 *   'DeepInfra')                  value cannot be correct once Mistral is pinned
 *                                 to 'Mistral', so honouring it would silently
 *                                 mis-route one model.
 */
const PIN_OVERRIDE = (process.env.OPENROUTER_PIN_PROVIDER ?? '').trim();
let pinOverrideNoticeShown = false;

/** Resolves the full upstream route (provider + optional precision) for a model id. */
export function resolveRoute(modelId: string): UpstreamRoute | null {
    if (PIN_OVERRIDE.toLowerCase() === 'none') return null;

    if (PIN_OVERRIDE && !pinOverrideNoticeShown) {
        pinOverrideNoticeShown = true;
        console.warn(
            `[model-provider] OPENROUTER_PIN_PROVIDER="${PIN_OVERRIDE}" is set but IGNORED. ` +
            `Routes are now per-model (see MODEL_ROUTE). Remove the variable from .env ` +
            `to silence this. Use OPENROUTER_PIN_PROVIDER=none to disable pinning for diagnostics.`
        );
    }

    const route = MODEL_ROUTE[modelId];
    if (!route) {
        console.warn(
            `[model-provider] No upstream route configured for modelId="${modelId}" — OpenRouter ` +
            `will load-balance across every upstream. This reintroduces the mixed-provider ` +
            `confound that corrupted Stage C. Add the model to MODEL_ROUTE before ` +
            `collecting any data with it.`
        );
        return null;
    }
    return route;
}

/** Convenience accessor: just the pinned provider name, or null. */
export function resolvePinProvider(modelId: string): string | null {
    return resolveRoute(modelId)?.provider ?? null;
}

/** Convenience accessor: the enforced precision filter, or null when unfiltered. */
export function resolvePinQuantization(modelId: string): string | null {
    const q = resolveRoute(modelId)?.quantizations;
    return q && q.length ? q.join(',') : null;
}

/**
 * Adds the OpenRouter `provider` routing directive to an outgoing request body.
 * The model id is read from the body itself, so the correct per-model pin is
 * applied even if several models are exercised in one process.
 */
function withProviderRouting(init?: RequestInit): RequestInit | undefined {
    if (!init || typeof init.body !== 'string') return init;
    try {
        const body = JSON.parse(init.body);
        if (!body || typeof body !== 'object' || body.provider !== undefined) return init;
        const modelId = String(body.model ?? getConfiguredModelId());
        const route = resolveRoute(modelId);
        if (!route) return init;
        body.provider = route.quantizations?.length
            ? { order: [route.provider], allow_fallbacks: false, quantizations: route.quantizations }
            : { order: [route.provider], allow_fallbacks: false };
        return { ...init, body: JSON.stringify(body) };
    } catch {
        // Not a JSON body — leave it exactly as it was.
    }
    return init;
}

/**
 * Custom fetch wrapper for OpenRouter that retries on HTTP 429 with
 * exponential backoff.  Free-tier models share an upstream provider
 * pool that can be transiently exhausted; a short wait is usually enough.
 *
 * Caps at 4 retries (total wait up to ~30 s before giving up).
 * Does NOT touch any agent logic — operates purely at the HTTP layer.
 */
async function fetchWithBackoff(
    input: RequestInfo | URL,
    init?: RequestInit,
): Promise<Response> {
    const routedInit = withProviderRouting(stripDecodingParams(init));
    const MAX_RETRIES = 4;
    let delayMs = 2_000; // 2 s → 4 s → 8 s → 16 s
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        const res = await fetch(input, routedInit);
        if (res.status !== 429 || attempt === MAX_RETRIES) return res;
        console.warn(
            `[model-provider] OpenRouter 429 (attempt ${attempt + 1}/${MAX_RETRIES}) — ` +
            `retrying in ${delayMs / 1000}s…`
        );
        await new Promise(resolve => setTimeout(resolve, delayMs));
        delayMs = Math.min(delayMs * 2, 30_000);
    }
    /* istanbul ignore next */
    return fetch(input, routedInit);
}

const VALID_PROVIDERS: ModelProvider[] = ['groq', 'openrouter', 'mistral'];

/** Returns the provider declared in MODEL_PROVIDER, defaulting to 'groq'. */
export function getConfiguredProvider(): ModelProvider {
    const raw = (process.env.MODEL_PROVIDER ?? 'groq').toLowerCase().trim();
    if (VALID_PROVIDERS.includes(raw as ModelProvider)) return raw as ModelProvider;
    console.warn(`[model-provider] Unknown MODEL_PROVIDER="${raw}" — falling back to groq.`);
    return 'groq';
}

/** Returns the model identifier declared in MODEL_ID, defaulting to 'llama-3.3-70b-versatile'. */
export function getConfiguredModelId(): string {
    return (process.env.MODEL_ID ?? 'llama-3.3-70b-versatile').trim();
}

/**
 * Creates and returns a LanguageModel instance for the currently configured
 * provider and model ID.  Called once per agent at Mastra startup.
 *
 * To change the model: update .env → restart Mastra (`npm run dev`).
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function createConfiguredModel(): any {
    const provider = getConfiguredProvider();
    const modelId  = getConfiguredModelId();

    const route = provider === 'openrouter' ? resolveRoute(modelId) : null;
    const quant = route?.quantizations?.length ? route.quantizations.join(',') : 'unfiltered';
    console.log(
        `[model-provider] Initialising agent model: provider=${provider} modelId=${modelId} ` +
        `pin=${route?.provider ?? 'none'} quantization=${quant} ` +
        `decoding=provider-defaults(temperature/max_tokens/seed omitted)`
    );

    switch (provider) {
        case 'openrouter': {
            const openrouter = createOpenAI({
                apiKey:   process.env.OPENROUTER_API_KEY ?? '',
                baseURL:  'https://openrouter.ai/api/v1',
                headers: {
                    'HTTP-Referer': 'https://anxiosense.vercel.app',
                    'X-Title':      'AnxioSense Evaluation',
                },
                fetch: fetchWithBackoff,
            });
            return openrouter.chat(modelId);
        }
        case 'mistral': {
            const mistral = createMistral({
                apiKey: process.env.MISTRAL_API_KEY ?? '',
                fetch: fetchWithProviderDefaults,
            });
            return mistral(modelId);
        }
        case 'groq':
        default: {
            const groq = createGroq({
                apiKey: process.env.GROQ_API_KEY ?? '',
                fetch: fetchWithProviderDefaults,
            });
            return groq(modelId);
        }
    }
}

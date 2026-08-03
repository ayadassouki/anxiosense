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
 * Supported experiment models:
 *   groq        llama-3.3-70b-versatile          (default Groq model)
 *   openrouter  meta-llama/llama-4-scout:free
 *   openrouter  google/gemma-4-31b-it:free
 *   openrouter  nvidia/nemotron-3-ultra-550b-a55b:free
 *   openrouter  deepseek/deepseek-v4-flash
 *   openrouter  microsoft/phi-4:free
 *   mistral     mistral-small-2603
 */

import { createGroq }    from '@ai-sdk/groq';
import { createOpenAI }  from '@ai-sdk/openai';
import { createMistral } from '@ai-sdk/mistral';

export type ModelProvider = 'groq' | 'openrouter' | 'mistral';

/**
 * FROZEN DECODING PARAMETERS — Stage C and later.
 *
 * These MUST match `models[].temperature` and `models[].max_tokens` in
 * evaluation/llm-experiments/config/experiment_config.yaml. The Python harness
 * records the YAML values into every per-cell metadata file, so a mismatch between
 * these constants and that file means the recorded methodology is wrong.
 * Verify with scripts/verify_provider_routing.ts, which prints the outgoing body.
 *
 * temperature 0 — the Vercel AI SDK sends no temperature, so before this the
 *   provider default (1.0) applied and was never recorded. Temperature is also not
 *   comparable across model families, so 0 is the only setting that means the same
 *   thing for all five models.
 * max_tokens 4096 — far above the longest observed output (report step ~100 tokens,
 *   CoT prose ~250), and inside every configured model's limit. A binding cap would
 *   truncate the longest outputs first, which are the CoT strategies — biasing the
 *   exact comparison the study makes.
 *
 * Changing either value is a deliberate methodological change: edit here AND in
 * experiment_config.yaml, and re-run the Stage C collection.
 *
 * NOTE: `max_tokens` is the Chat Completions field name. If the provider is ever
 * switched back to the Responses API the field becomes `max_output_tokens`.
 */
const DECODING_TEMPERATURE = 0;
const DECODING_MAX_TOKENS  = 4096;

/** Adds the frozen decoding parameters to an outgoing request body. */
function withDecodingDefaults(init?: RequestInit): RequestInit | undefined {
    if (!init || typeof init.body !== 'string') return init;
    try {
        const body = JSON.parse(init.body);
        if (!body || typeof body !== 'object') return init;
        let changed = false;
        if (body.temperature === undefined) { body.temperature = DECODING_TEMPERATURE; changed = true; }
        if (body.max_tokens  === undefined) { body.max_tokens  = DECODING_MAX_TOKENS;  changed = true; }
        return changed ? { ...init, body: JSON.stringify(body) } : init;
    } catch {
        // Not a JSON body — leave it exactly as it was.
    }
    return init;
}

/** fetch wrapper for providers that need the decoding defaults but not OpenRouter routing. */
async function fetchWithDecodingDefaults(
    input: RequestInfo | URL,
    init?: RequestInit,
): Promise<Response> {
    return fetch(input, withDecodingDefaults(init));
}

/**
 * Upstream provider pinning for OpenRouter.
 *
 * OpenRouter load-balances a model across several upstream providers. For
 * meta-llama/llama-4-scout the `Google` upstream returns token-dropped output:
 * measured 2026-08-03 over 200 calls, 21/21 Google responses were corrupted while
 * DeepInfra (87), Groq (70) and Novita (22) were clean — perfect separation.
 * Dropped tokens arrive with finish_reason "stop" and a matching (reduced)
 * output_tokens count, so nothing downstream can detect them.
 *
 * Pinning a single upstream also removes the mixed-quantisation confound: without
 * it, one experiment run is served by several different implementations of the
 * "same" model.
 *
 * allow_fallbacks:false means a request errors rather than silently re-routing —
 * the evaluation harness records that as a provider error, which is what we want.
 *
 * Override with OPENROUTER_PIN_PROVIDER; set it to an empty string to disable pinning.
 */
const PINNED_PROVIDER = (process.env.OPENROUTER_PIN_PROVIDER ?? 'DeepInfra').trim();

/** Adds the OpenRouter `provider` routing directive to an outgoing request body. */
function withProviderRouting(init?: RequestInit): RequestInit | undefined {
    if (!init || !PINNED_PROVIDER || typeof init.body !== 'string') return init;
    try {
        const body = JSON.parse(init.body);
        if (body && typeof body === 'object' && body.provider === undefined) {
            body.provider = { order: [PINNED_PROVIDER], allow_fallbacks: false };
            return { ...init, body: JSON.stringify(body) };
        }
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
    const routedInit = withProviderRouting(withDecodingDefaults(init));
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

    console.log(`[model-provider] Initialising agent model: provider=${provider} modelId=${modelId}`);

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
                fetch: fetchWithDecodingDefaults,
            });
            return mistral(modelId);
        }
        case 'groq':
        default: {
            const groq = createGroq({
                apiKey: process.env.GROQ_API_KEY ?? '',
                fetch: fetchWithDecodingDefaults,
            });
            return groq(modelId);
        }
    }
}

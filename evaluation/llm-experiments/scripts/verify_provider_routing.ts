/**
 * verify_provider_routing.ts — offline check that the approved experiment
 * configuration reaches the wire.
 *
 * Asserts, for the currently configured MODEL_ID:
 *   1. the per-model upstream pin is present as {order:[pin], allow_fallbacks:false}
 *   2. temperature, max_tokens, max_completion_tokens and seed are ABSENT
 *      (provider defaults in force — methodology 2026-08-04)
 *   3. the request uses the Chat Completions shape, which returns `provider`
 *
 * Stubs global fetch, calls the real emotion agent, prints the outgoing body.
 * Makes NO network request and spends nothing. Read-only.
 *
 *   cd ~/anxiosense
 *   node --env-file=.env --import=tsx/esm \
 *       evaluation/llm-experiments/scripts/verify_provider_routing.ts
 */
import { emotionAnalysisAgent } from '../../../src/mastra/agents/emotion-analysis-agent';
import {
    MODEL_ROUTE,
    resolveRoute,
    getConfiguredModelId,
    getConfiguredProvider,
} from '../../../src/mastra/utils/model-provider';

let captured: string | null = null;

const stubBody = JSON.stringify({
    id: 'stub', object: 'chat.completion', created: 0,
    model: getConfiguredModelId(), provider: 'StubProvider',
    choices: [{
        index: 0,
        message: { role: 'assistant', content: '{"emotions":[],"emotional_intensity":"low","evidence_from_text":[]}' },
        finish_reason: 'stop',
    }],
    usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
});

const realFetch = globalThis.fetch;
globalThis.fetch = (async (_input: unknown, init: { body?: unknown } | undefined) => {
    captured = typeof init?.body === 'string' ? init.body : null;
    return new Response(stubBody, { status: 200, headers: { 'content-type': 'application/json' } });
}) as typeof fetch;

try {
    await emotionAnalysisAgent.generate('CONTEXT: test\n\nJust got a bit worried about something', {});
} finally {
    globalThis.fetch = realFetch;
}

if (!captured) {
    console.log('FAIL — no request body was captured');
    process.exit(1);
}

const body = JSON.parse(captured);

const provider = getConfiguredProvider();
const modelId  = getConfiguredModelId();
const route    = resolveRoute(modelId);

/** Decoding parameters that MUST NOT appear — provider defaults are in force. */
const MUST_BE_ABSENT = ['temperature', 'max_tokens', 'max_completion_tokens', 'seed'] as const;

console.log('configured provider :', provider);
console.log('configured model id :', modelId);
console.log('expected pin        :', route?.provider ?? '(none)');
console.log('expected quantization:', route?.quantizations?.join(',') ?? '(unfiltered)');
console.log('outgoing body keys  :', Object.keys(body).join(', '));
console.log('endpoint shape      :', 'messages' in body ? 'chat/completions' : 'responses');
console.log('body.model          :', JSON.stringify(body.model));
console.log('provider directive  :', JSON.stringify(body.provider));
for (const k of MUST_BE_ABSENT) {
    console.log(`${k.padEnd(20)}:`, k in body ? JSON.stringify(body[k]) : '(absent)');
}
console.log();

const checks: Array<[string, boolean, string]> = [];

// 1. endpoint shape — Chat Completions is what returns the `provider` field.
checks.push([
    'chat/completions endpoint',
    'messages' in body,
    'the Responses API does not return `provider`, so upstream logging would break',
]);

// 2. the body names the model we think we are running.
checks.push([
    `body.model === "${modelId}"`,
    body.model === modelId,
    `wire says "${body.model}" — .env and the running process disagree; restart Mastra`,
]);

// 3. per-model upstream route, including the precision filter where one is set.
if (route === null) {
    checks.push([
        'upstream route present',
        false,
        `no route resolved for "${modelId}" — add it to MODEL_ROUTE in model-provider.ts`,
    ]);
} else {
    const want = JSON.stringify(
        route.quantizations?.length
            ? { order: [route.provider], allow_fallbacks: false, quantizations: route.quantizations }
            : { order: [route.provider], allow_fallbacks: false }
    );
    checks.push([
        `upstream route === ${route.provider}`
        + (route.quantizations?.length ? ` @ ${route.quantizations.join(',')}` : ' (unfiltered)'),
        JSON.stringify(body.provider) === want,
        `expected ${want}`,
    ]);
    // A model with a precision filter must actually carry it on the wire — this is
    // the only place the fp4/fp8 choice is enforceable, since the response does not
    // report quantization.
    if (route.quantizations?.length) {
        checks.push([
            `quantizations === [${route.quantizations.join(',')}]`,
            JSON.stringify(body.provider?.quantizations) === JSON.stringify(route.quantizations),
            `body.provider.quantizations = ${JSON.stringify(body.provider?.quantizations)} — `
            + `without it OpenRouter may serve a different precision and the response cannot reveal it`,
        ]);
    }
}

// 3b. documented per-model request overrides must be on the wire exactly.
//     (2026-08-09 deviation: qwen reasoning toggle — see MODEL_REQUEST_OVERRIDES.)
if (String(body.model) === 'qwen/qwen3.5-27b') {
    checks.push([
        `reasoning === {"enabled":false} (documented qwen deviation)`,
        JSON.stringify(body.reasoning) === JSON.stringify({ enabled: false }),
        `body.reasoning = ${JSON.stringify(body.reasoning)} — the reasoning-off override is missing/altered`,
    ]);
}

// 4. decoding parameters must be absent.
for (const k of MUST_BE_ABSENT) {
    checks.push([
        `${k} absent`,
        !(k in body),
        `${k}=${JSON.stringify(body[k])} is on the wire — the provider default is being overridden`,
    ]);
}

for (const [label, ok, why] of checks) {
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}${ok ? '' : `\n          ${why}`}`);
}

const pass = checks.every(([, ok]) => ok);
console.log(pass
    ? '\nPASS — per-model route on the wire, decoding parameters omitted'
    : '\nFAIL — configuration does not match the approved methodology');

// Reference table, so a reader of the log can see every route at a glance.
console.log('\nconfigured routes:');
for (const [m, r] of Object.entries(MODEL_ROUTE)) {
    const q = r.quantizations?.length ? r.quantizations.join(',') : 'unfiltered';
    console.log(`  ${m.padEnd(32)} ${r.provider.padEnd(10)} ${q}${m === modelId ? '   <- active' : ''}`);
}

process.exit(pass ? 0 : 1);

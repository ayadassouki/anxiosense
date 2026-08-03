/**
 * verify_provider_routing.ts — offline check that the frozen experiment
 * configuration (provider pin + temperature + max_tokens) reaches the wire.
 *
 * Stubs global fetch, calls the real emotion agent, prints the outgoing body.
 * Makes NO network request and spends nothing. Read-only.
 *
 *   cd ~/anxiosense
 *   node --env-file=.env --import=tsx/esm \
 *       evaluation/llm-experiments/scripts/verify_provider_routing.ts
 */
import { emotionAnalysisAgent } from '../../../src/mastra/agents/emotion-analysis-agent';

let captured: string | null = null;

const stubBody = JSON.stringify({
    id: 'stub', object: 'chat.completion', created: 0,
    model: 'meta-llama/llama-4-scout', provider: 'StubProvider',
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

// Everything the frozen experiment configuration must put on the wire.
const EXPECTED_PROVIDER    = { order: ['DeepInfra'], allow_fallbacks: false };
const EXPECTED_TEMPERATURE = 0;
const EXPECTED_MAX_TOKENS  = 4096;

console.log('outgoing body keys :', Object.keys(body).join(', '));
console.log('endpoint shape     :', 'messages' in body ? 'chat/completions' : 'responses');
console.log('provider directive :', JSON.stringify(body.provider));
console.log('temperature        :', JSON.stringify(body.temperature));
console.log('max_tokens         :', JSON.stringify(body.max_tokens));

const checks: Array<[string, boolean]> = [
    ['provider routing', JSON.stringify(body.provider) === JSON.stringify(EXPECTED_PROVIDER)],
    ['temperature',      body.temperature === EXPECTED_TEMPERATURE],
    ['max_tokens',       body.max_tokens  === EXPECTED_MAX_TOKENS],
];
console.log();
for (const [label, ok] of checks) console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}`);
const pass = checks.every(([, ok]) => ok);
console.log(pass
    ? '\nPASS — frozen configuration is on the wire'
    : `\nFAIL — expected provider=${JSON.stringify(EXPECTED_PROVIDER)} ` +
      `temperature=${EXPECTED_TEMPERATURE} max_tokens=${EXPECTED_MAX_TOKENS}`);
process.exit(pass ? 0 : 1);

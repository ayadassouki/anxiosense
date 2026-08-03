/**
 * probe_concurrency.ts — does corruption appear when the four agents run in parallel?
 *
 * WHY
 * ---
 * The serial agent.generate() probe is clean 200/200 with DeepInfra pinned. The one
 * remaining difference between that probe and a real pipeline call is CONCURRENCY:
 * the assessment workflow fires emotion + symptom + context + referral simultaneously
 * (see the `[usage]` lines and `Timing — parallel …` in the dev-server log).
 *
 * This probe reproduces that fan-out exactly — four concurrent generate() calls per
 * iteration, same agents, same prompts, same mode prefix — while still bypassing the
 * workflow engine, the Express route, extractJson and the CSV writer.
 *
 * It also checks the thing that actually matters in production now: that every single
 * response was served by the pinned upstream provider. A routing leak is reported as
 * PROVIDER_NOT_PINNED even if the text is clean.
 *
 * Reads only. Writes one JSONL file under outputs/probe/. Changes nothing.
 *
 * HOW TO RUN
 * ----------
 *   cd ~/anxiosense
 *   node --env-file=.env --import=tsx/esm \
 *       evaluation/llm-experiments/scripts/probe_concurrency.ts
 *
 * Flags:
 *   --dry-run              print the four prompts and exit, call nothing
 *   --stub                 run the full loop against a canned response — no network,
 *                          no spend; proves the harness works before you pay for it
 *   -n 50                  iterations; each is 4 concurrent calls (default 50 = 200 calls)
 *   --strategy one-shot-cot | zero-shot-cot | zero-shot
 *   --sample-id ge_024113
 *   --parallel-workflows 1 how many 4-agent fan-outs to run at once. 1 matches the real
 *                          workflow. Raise it only to stress-test beyond production load.
 *   --sleep 500            ms between iterations
 *   --expect-provider DeepInfra   provider every response must come from
 *
 * Exit 0 = clean, 1 = corruption or routing leak, 2 = setup failure.
 */

import * as fs from 'fs';
import * as path from 'path';

import { emotionAnalysisAgent }         from '../../../src/mastra/agents/emotion-analysis-agent';
import { anxietySymptomExtractionAgent } from '../../../src/mastra/agents/anxiety-symptom-extraction-agent';
import { contextualStressorAnalysisAgent } from '../../../src/mastra/agents/contextual-stressor-analysis-agent';
import { referralSafetyAssessmentAgent } from '../../../src/mastra/agents/referral-safety-assessment-agent';
import { loadAgentInstructions } from '../../../src/mastra/utils/prompt-strategy-loader';

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const EXP_DIR = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = path.resolve(EXP_DIR, '..', '..');
const DATASET_CSV = path.join(REPO_ROOT, 'evaluation', 'datasets', 'processed',
                              'goemotions_clean.csv');
const OUT_DIR = path.join(EXP_DIR, 'outputs', 'probe');

/** Output contract per agent, taken from the tail of each prompts/<agent>/*.md file. */
const REQUIRED_KEYS: Record<string, string[]> = {
    emotion:  ['emotions', 'emotional_intensity', 'evidence_from_text'],
    symptom:  ['possible_anxiety_indicators', 'evidence_from_text', 'not_enough_information'],
    context:  ['contextual_stressors', 'evidence_from_text', 'life_domains'],
    referral: ['risk_level', 'reasoning', 'recommended_support', 'safety_note'],
};

const AGENTS = [
    { name: 'emotion',  agent: emotionAnalysisAgent },
    { name: 'symptom',  agent: anxietySymptomExtractionAgent },
    { name: 'context',  agent: contextualStressorAnalysisAgent },
    { name: 'referral', agent: referralSafetyAssessmentAgent },
] as const;

// Verbatim from src/mastra/workflows/anxiety-screening-assessment-workflow.ts
const MODE_PREFIX_SOCIAL_MEDIA =
    'CONTEXT: The following text was sourced from social media (e.g. Reddit). ' +
    'Treat it as self-reported content from an unknown author describing their ' +
    'own experiences. Do NOT assume clinical intent or structured disclosure. ' +
    'Be appropriately cautious about any inferences.\n\n';

// Verbatim from the referral step of the same file — only the referral agent gets this.
const REFERRAL_SOCIAL_MEDIA_NOTE =
    'IMPORTANT: This text is from social media, not a direct clinical disclosure. ' +
    'Be conservative — default to "low" or "moderate" unless there are very explicit ' +
    'safety signals in the text itself.\n\n';

// ── CSV ───────────────────────────────────────────────────────────────────────
function parseCsv(text: string): string[][] {
    const rows: string[][] = []; let row: string[] = []; let field = ''; let q = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (q) {
            if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; }
            else field += c;
        } else if (c === '"') q = true;
        else if (c === ',') { row.push(field); field = ''; }
        else if (c === '\n') { row.push(field); field = ''; rows.push(row); row = []; }
        else if (c !== '\r') field += c;
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    return rows;
}

function loadSampleText(sampleId: string): string {
    if (!fs.existsSync(DATASET_CSV)) { console.error(`dataset not found: ${DATASET_CSV}`); process.exit(2); }
    const rows = parseCsv(fs.readFileSync(DATASET_CSV, 'utf-8'));
    const h = rows[0], idI = h.indexOf('sample_id'), txI = h.indexOf('text_redacted');
    for (const r of rows.slice(1)) if (r[idI] === sampleId) return r[txI];
    console.error(`sample_id ${sampleId} not found`); process.exit(2);
}

// ── Detectors ─────────────────────────────────────────────────────────────────
interface Finding { detector: string; detail: string }

/**
 * Unbalanced-key check. A JSON key is always "name": — opening quote, name, closing
 * quote, colon. A dropped token that eats the opening quote leaves name": with nothing
 * in front. Prose cannot produce that shape, so CoT explanations do not trip it.
 */
function findUnbalancedKeys(content: string): string[] {
    const hits = new Set<string>();
    const re = /([A-Za-z_][A-Za-z_0-9]*)"\s*:/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(content)) !== null) {
        if (m.index === 0 || content[m.index - 1] !== '"') hits.add(m[0].trim().slice(0, 48));
    }
    return [...hits].sort();
}

function jsonObjectRecoverable(content: string): boolean {
    for (const c of [content.trim(), ...(content.match(/\{[\s\S]*\}/g) ?? [])]) {
        try { const o = JSON.parse(c); if (o && typeof o === 'object' && !Array.isArray(o)) return true; }
        catch { /* keep looking */ }
    }
    return false;
}

function analyse(agentName: string, content: string | null | undefined): Finding[] {
    if (content == null) return [{ detector: 'NO_CONTENT', detail: 'generate() returned no text' }];
    if (!content.trim()) return [{ detector: 'EMPTY_CONTENT', detail: 'text was empty' }];
    const f: Finding[] = [];
    const missing = (REQUIRED_KEYS[agentName] ?? []).filter(k => !content.includes(`"${k}"`));
    if (missing.length) f.push({ detector: 'MISSING_REQUIRED_KEY', detail: missing.join(', ') });
    const unbal = findUnbalancedKeys(content);
    if (unbal.length) f.push({ detector: 'MID_WORD_CUT', detail: unbal.join(', ') });
    if (!jsonObjectRecoverable(content))
        f.push({ detector: 'NO_JSON_OBJECT', detail: 'no well-formed JSON object in the text' });
    return f;
}

// ── Response introspection ────────────────────────────────────────────────────
function rawBody(res: unknown): Record<string, unknown> | null {
    const b = (res as any)?.response?.body;
    if (!b) return null;
    try { return typeof b === 'string' ? JSON.parse(b) : b; } catch { return null; }
}
function rawBodyText(body: Record<string, unknown> | null): string | null {
    if (!body) return null;
    const ch = (body as any).choices;
    if (Array.isArray(ch) && ch[0]?.message?.content != null) return String(ch[0].message.content);
    const out = (body as any).output;
    if (Array.isArray(out)) {
        const t = out.flatMap((i: any) => (i.content ?? [])).map((c: any) => c?.text)
                     .filter((x: unknown) => typeof x === 'string').join('');
        return t || null;
    }
    return null;
}

function arg(name: string, fallback: string): string {
    const i = process.argv.indexOf(name);
    return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

async function main(): Promise<number> {
    const iterations = parseInt(arg('-n', arg('--iterations', '50')), 10);
    const strategy = arg('--strategy', 'one-shot-cot');
    const sampleId = arg('--sample-id', 'ge_024113');
    const sleepMs = parseInt(arg('--sleep', '500'), 10);
    const lanes = Math.max(1, parseInt(arg('--parallel-workflows', '1'), 10));
    const expectProvider = arg('--expect-provider', 'DeepInfra');
    const dryRun = process.argv.includes('--dry-run');
    const stub = process.argv.includes('--stub');

    const userText = loadSampleText(sampleId);
    const base = MODE_PREFIX_SOCIAL_MEDIA + userText;

    const prompts: Record<string, { instructions: string; message: string }> = {};
    for (const { name } of AGENTS) {
        const instructions = loadAgentInstructions(name as any, strategy);
        if (!instructions) {
            console.error(`prompt for ${name}/${strategy} could not be loaded — the agent would ` +
                          `silently fall back to hardcoded instructions and this probe would not ` +
                          `replay the real request.`);
            return 2;
        }
        prompts[name] = {
            instructions,
            message: name === 'referral' ? REFERRAL_SOCIAL_MEDIA_NOTE + base : base,
        };
    }

    console.log('='.repeat(78));
    console.log('4-agent CONCURRENCY probe — mirrors the workflow parallel step');
    console.log('='.repeat(78));
    console.log(`  provider/model     : ${process.env.MODEL_PROVIDER}/${process.env.MODEL_ID}`);
    console.log(`  pinned provider    : ${process.env.OPENROUTER_PIN_PROVIDER ?? 'DeepInfra (default)'}`);
    console.log(`  expect provider    : ${expectProvider}`);
    console.log(`  strategy           : ${strategy}`);
    console.log(`  sample_id          : ${sampleId}`);
    console.log(`  iterations         : ${iterations}  x 4 agents = ${iterations * 4} calls`);
    console.log(`  parallel workflows : ${lanes}${lanes === 1 ? '  (matches production)' : '  (STRESS — above production load)'}`);
    for (const { name } of AGENTS) console.log(`  prompt ${name.padEnd(9)}  : ${prompts[name].instructions.length} chars`);
    console.log(`  mode               : social-media (as /api/workflow/evaluate)`);
    if (stub) console.log(`  STUB MODE          : fetch is stubbed — no network, no spend`);
    console.log('='.repeat(78));

    if (dryRun) {
        console.log('\n--- DRY RUN — nothing was called ---\n');
        for (const { name } of AGENTS)
            console.log(`[${name}] message:\n${JSON.stringify(prompts[name].message)}\n`);
        return 0;
    }

    if (stub) {
        const canned: Record<string, string> = {
            emotion:  '{"emotions":["anxiety"],"emotional_intensity":"low","evidence_from_text":["worried"]}',
            symptom:  '{"possible_anxiety_indicators":[],"evidence_from_text":[],"not_enough_information":true}',
            context:  '{"contextual_stressors":[],"life_domains":[],"evidence_from_text":[]}',
            referral: '{"risk_level":"low","reasoning":"x","recommended_support":"x","safety_note":"x"}',
        };
        (globalThis as any).fetch = async (_i: unknown, init: any) => {
            const b = JSON.parse(init.body);
            const sys = String(b.messages?.[0]?.content ?? b.input?.[0]?.content ?? '');
            const which = sys.includes('Emotion Analysis') ? 'emotion'
                        : sys.includes('Symptom') ? 'symptom'
                        : sys.includes('Referral') || sys.includes('risk_level') ? 'referral' : 'context';
            return new Response(JSON.stringify({
                id: 'stub', object: 'chat.completion', created: 0,
                model: process.env.MODEL_ID, provider: expectProvider,
                choices: [{ index: 0, message: { role: 'assistant', content: canned[which] }, finish_reason: 'stop' }],
                usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
            }), { status: 200, headers: { 'content-type': 'application/json' } });
        };
    }

    fs.mkdirSync(OUT_DIR, { recursive: true });
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, 'Z');
    const outPath = path.join(OUT_DIR, `concurrency_probe_${strategy}_${stamp}.jsonl`);
    console.log(`\nwriting -> ${outPath}\n`);

    fs.appendFileSync(outPath, JSON.stringify({
        record_type: 'probe_header', started_utc: stamp,
        layer_under_test: '4 concurrent agent.generate() calls (workflow parallel step)',
        bypassed: ['workflow engine', 'express route', 'extractJson', 'csv writer', 'python harness'],
        model: process.env.MODEL_ID, strategy, sample_id: sampleId, user_text: userText,
        expect_provider: expectProvider, parallel_workflows: lanes,
        iterations_planned: iterations, stub,
        prompts: Object.fromEntries(Object.entries(prompts).map(([k, v]) => [k, v.instructions.length])),
    }) + '\n');

    const perAgentDirty: Record<string, number> = { emotion: 0, symptom: 0, context: 0, referral: 0 };
    const providers = new Map<string, number>();
    let dirty = 0, leaks = 0, errors = 0, calls = 0;

    async function oneWorkflow(iter: number, lane: number) {
        const t0 = Date.now();
        // The workflow awaits all four together — same shape here.
        const settled = await Promise.all(AGENTS.map(async ({ name, agent }) => {
            const s = Date.now();
            try {
                const res = await agent.generate(prompts[name].message,
                                                 { instructions: prompts[name].instructions });
                const text = (res as any)?.text ?? null;
                const body = rawBody(res);
                const bText = rawBodyText(body);
                const provider = (body as any)?.provider ?? null;
                const findings = analyse(name, text);
                if (bText !== null && text !== null && bText !== text)
                    findings.push({ detector: 'TEXT_DIFFERS_FROM_RAW_BODY',
                                    detail: `raw ${bText.length} chars vs text ${text.length}` });
                if (provider !== null && provider !== expectProvider)
                    findings.push({ detector: 'PROVIDER_NOT_PINNED',
                                    detail: `served by "${provider}", expected "${expectProvider}"` });
                return { name, text, provider, findings,
                         finish_reason: (res as any)?.finishReason ?? null,
                         usage: (res as any)?.usage ?? null,
                         started_ms: s - t0, latency_ms: Date.now() - s, error: null as string | null };
            } catch (e) {
                return { name, text: null, provider: null,
                         findings: [] as Finding[], finish_reason: null, usage: null,
                         started_ms: s - t0, latency_ms: Date.now() - s,
                         error: `${(e as Error).name}: ${(e as Error).message}` };
            }
        }));

        const wall = Date.now() - t0;
        for (const r of settled) {
            calls++;
            if (r.error) errors++;
            if (r.findings.length) { dirty++; perAgentDirty[r.name]++; }
            if (r.findings.some(f => f.detector === 'PROVIDER_NOT_PINNED')) leaks++;
            providers.set(String(r.provider), (providers.get(String(r.provider)) ?? 0) + 1);
        }

        fs.appendFileSync(outPath, JSON.stringify({
            record_type: 'probe_iteration', iteration: iter, lane,
            timestamp_utc: new Date().toISOString(),
            wall_ms: wall, agents: settled,
        }) + '\n');

        const bad = settled.filter(r => r.findings.length || r.error);
        const flag = bad.length
            ? 'SUSPECT ' + bad.map(r => `${r.name}:${r.error ?? r.findings.map(f => f.detector).join('+')}`).join(' | ')
            : 'CLEAN';
        console.log(`[${String(iter).padStart(3)}/${iterations}]${lanes > 1 ? ` lane${lane}` : ''} ` +
                    `wall=${String(wall).padStart(5)}ms  ` +
                    settled.map(r => `${r.name[0]}=${r.text?.length ?? 'ERR'}`).join(' ') +
                    `  ${flag}`);
        for (const r of bad) if (r.findings.length) console.log(`        ${r.name}: ${JSON.stringify(r.text)}`);
    }

    for (let i = 1; i <= iterations; i += lanes) {
        const batch: Promise<void>[] = [];
        for (let l = 0; l < lanes && i + l <= iterations; l++) batch.push(oneWorkflow(i + l, l + 1));
        await Promise.all(batch);
        if (i + lanes <= iterations && sleepMs > 0) await new Promise(r => setTimeout(r, sleepMs));
    }

    console.log('\n' + '='.repeat(78));
    console.log('SUMMARY');
    console.log('='.repeat(78));
    console.log(`  total agent calls   : ${calls}`);
    console.log(`  clean               : ${calls - dirty - errors}/${calls}`);
    console.log(`  suspect             : ${dirty}`);
    console.log(`  provider leaks      : ${leaks}`);
    console.log(`  errors              : ${errors}`);
    console.log(`  per agent suspect   : ` +
        AGENTS.map(a => `${a.name}=${perAgentDirty[a.name]}`).join('  '));
    console.log(`  providers seen      : ${JSON.stringify(Object.fromEntries(providers))}`);
    console.log(`  output              : ${outPath}`);
    console.log();

    if (dirty || errors) {
        console.log('  VERDICT: NOT clean under concurrency.');
        if (leaks) console.log(`  ${leaks} response(s) were served by an unexpected provider — the pin is leaking.`);
        console.log('  Do not restart Stage C. Investigate the failing agent(s) above.');
        return 1;
    }
    console.log('  VERDICT: clean under the real 4-agent parallel fan-out.');
    console.log(`  All ${calls} responses served by ${expectProvider}, all schemas intact.`);
    return 0;
}

main().then(c => process.exit(c)).catch(e => { console.error(e); process.exit(2); });

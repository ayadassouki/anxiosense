/**
 * probe_agent_generate.ts — does the corruption happen inside agent.generate()?
 *
 * LAYER UNDER TEST
 * ----------------
 * Established so far:
 *   - stage_c_final CSVs contain genuine deletions ('low_from_text', 'otions":', ...)
 *   - the Python harness and CSV writer are cleared (.csv and .jsonl are byte-identical)
 *   - OpenRouter over plain non-streaming HTTP is clean: 0/100 across both CoT strategies
 *
 * The damage therefore happens between the provider's HTTP response and the value
 * the pipeline stores. This probe tests exactly ONE boundary in that gap: the
 * Mastra Agent + Vercel AI SDK call itself.
 *
 * It calls emotionAnalysisAgent.generate() directly — the same agent object the
 * workflow uses — with the same model, the same strategy prompt (loaded through the
 * real prompt-strategy-loader, not a copy) and the same user message. It bypasses:
 *
 *   the assessment workflow      (no steps, no parallel branches, no zod schemas)
 *   the Express /evaluate route  (no HTTP server in the path)
 *   extractJson / the parser     (nothing parses the text)
 *   the CSV / JSONL writer       (nothing reformats the text)
 *   the Python evaluation harness
 *
 * Nothing in the pipeline is modified. This file only reads.
 *
 * HOW TO RUN
 * ----------
 *   cd ~/anxiosense
 *   node --env-file=.env --import=tsx/esm \
 *       evaluation/llm-experiments/scripts/probe_agent_generate.ts
 *
 * Run from the REPO ROOT — the prompt loader walks up from process.cwd() to find
 * prompts/, and --env-file=.env is resolved relative to cwd.
 *
 * Flags:
 *   --dry-run                 build the request, print it, call nothing
 *   -n 50                     iterations (default 50)
 *   --strategy one-shot-cot   one-shot-cot | zero-shot-cot | zero-shot
 *   --sample-id ge_024113     which sample to replay
 *   --sleep 500               ms between calls (default 500)
 *
 * OUTPUT
 * ------
 *   evaluation/llm-experiments/outputs/probe/agent_generate_probe_<strategy>_<UTC>.jsonl
 *
 * Per iteration: iteration number, the complete response.text verbatim, the full
 * response object serialised as far as it is serialisable, finish reason, provider
 * metadata, usage, warnings, latency, and which detectors fired.
 *
 * THE FIELD THAT MATTERS MOST is response.response.body — the raw provider payload as
 * the SDK received it. If .text is damaged while that raw body is intact, the defect is
 * in the SDK's text assembly and this probe has localised it exactly. The script
 * reports that comparison explicitly as TEXT_DIFFERS_FROM_RAW_BODY.
 *
 * Exit code 0 = clean, 1 = corruption reproduced, 2 = setup failure.
 */

import * as fs from 'fs';
import * as path from 'path';
import { createRequire } from 'module';

import { emotionAnalysisAgent } from '../../../src/mastra/agents/emotion-analysis-agent';
import { loadAgentInstructions } from '../../../src/mastra/utils/prompt-strategy-loader';

const require_ = createRequire(import.meta.url);

// ── Paths ─────────────────────────────────────────────────────────────────────
const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const EXP_DIR = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = path.resolve(EXP_DIR, '..', '..');
const DATASET_CSV = path.join(REPO_ROOT, 'evaluation', 'datasets', 'processed',
                              'goemotions_clean.csv');
const OUT_DIR = path.join(EXP_DIR, 'outputs', 'probe');

const REQUIRED_KEYS = ['emotions', 'emotional_intensity', 'evidence_from_text'];

// Literal signatures observed in the corrupted stage_c_final records. Anchored with
// negative lookbehind where the fragment is also a substring of a valid key.
const KNOWN_SIGNATURES: Array<[RegExp, string]> = [
    [/low_from_text/,            `'","evidence' eaten out of the middle`],
    [/emensity/,                 `'otional_int' eaten out of the middle`],
    [/(?<!em)otions"/,           `'"em' eaten off the front of "emotions"`],
    [/(?<!em)otional_intensity/, `'"em' eaten off the front of "emotional_intensity"`],
    [/emotionsxiety/,            `'":["an' eaten out`],
    [/"_text"/,                  `'evidence_from' eaten out`],
    [/evidence_from"/,           `'_text' eaten out`],
    [/"evidence"\s*:/,           `'_from_text' eaten out`],
];

// ── Minimal RFC4180 CSV reader (quoted fields, doubled quotes, embedded newlines) ──
function parseCsv(text: string): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let field = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (inQuotes) {
            if (c === '"') {
                if (text[i + 1] === '"') { field += '"'; i++; }
                else inQuotes = false;
            } else field += c;
        } else if (c === '"') {
            inQuotes = true;
        } else if (c === ',') {
            row.push(field); field = '';
        } else if (c === '\n') {
            row.push(field); field = ''; rows.push(row); row = [];
        } else if (c !== '\r') {
            field += c;
        }
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    return rows;
}

function loadSampleText(sampleId: string): string {
    if (!fs.existsSync(DATASET_CSV)) {
        console.error(`dataset not found: ${DATASET_CSV}`);
        process.exit(2);
    }
    const rows = parseCsv(fs.readFileSync(DATASET_CSV, 'utf-8'));
    const header = rows[0];
    const idIdx = header.indexOf('sample_id');
    const textIdx = header.indexOf('text_redacted');
    for (const r of rows.slice(1)) {
        if (r[idIdx] === sampleId) return r[textIdx];
    }
    console.error(`sample_id ${sampleId} not found in ${DATASET_CSV}`);
    process.exit(2);
}

/**
 * Verbatim copy of modePrefix('social-media') from
 * src/mastra/workflows/anxiety-screening-assessment-workflow.ts.
 * /api/workflow/evaluate always runs in social-media mode, so every stage_c_final
 * record was produced with this prefix.
 */
const MODE_PREFIX_SOCIAL_MEDIA =
    'CONTEXT: The following text was sourced from social media (e.g. Reddit). ' +
    'Treat it as self-reported content from an unknown author describing their ' +
    'own experiences. Do NOT assume clinical intent or structured disclosure. ' +
    'Be appropriately cautious about any inferences.\n\n';

// ── Detectors (read-only; content is never modified) ──────────────────────────
interface Finding { detector: string; detail: string }

/**
 * Mid-word-cut detector, implemented as an UNBALANCED-KEY check.
 * A JSON key is always  "name":  — opening quote, name, closing quote, colon.
 * Corruption that eats the opening quote leaves  name":  with nothing in front.
 * Prose cannot produce that shape, so explanations after the JSON do not trip it.
 */
function findUnbalancedKeys(content: string): string[] {
    const hits = new Set<string>();
    const re = /([A-Za-z_][A-Za-z_0-9]*)"\s*:/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(content)) !== null) {
        const start = m.index;
        if (start === 0 || content[start - 1] !== '"') hits.add(m[0].trim().slice(0, 48));
    }
    return [...hits].sort();
}

function findUnknownKeys(content: string): string[] {
    const keys = new Set<string>();
    const re = /"([A-Za-z_][A-Za-z_0-9]*)"\s*:/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(content)) !== null) {
        if (!REQUIRED_KEYS.includes(m[1])) keys.add(m[1]);
    }
    return [...keys].sort();
}

function jsonObjectRecoverable(content: string): boolean {
    const candidates = [content.trim(), ...(content.match(/\{[\s\S]*\}/g) ?? [])];
    for (const c of candidates) {
        try {
            const o = JSON.parse(c);
            if (o && typeof o === 'object' && !Array.isArray(o)) return true;
        } catch { /* not JSON — keep looking */ }
    }
    return false;
}

function analyse(content: string | null | undefined): Finding[] {
    if (content === null || content === undefined)
        return [{ detector: 'NO_CONTENT', detail: 'generate() returned no text' }];
    if (!content.trim())
        return [{ detector: 'EMPTY_CONTENT', detail: 'text was empty/whitespace' }];

    const findings: Finding[] = [];
    for (const [re, why] of KNOWN_SIGNATURES) {
        const m = content.match(re);
        if (m) findings.push({ detector: 'KNOWN_SIGNATURE', detail: `${JSON.stringify(m[0])} — ${why}` });
    }
    const missing = REQUIRED_KEYS.filter(k => !content.includes(`"${k}"`));
    if (missing.length)
        findings.push({ detector: 'MISSING_REQUIRED_KEY', detail: missing.join(', ') });

    const unbalanced = findUnbalancedKeys(content);
    if (unbalanced.length)
        findings.push({ detector: 'MID_WORD_CUT', detail: unbalanced.join(', ') });

    const unknown = findUnknownKeys(content);
    if (unknown.length)
        findings.push({ detector: 'UNKNOWN_JSON_KEY', detail: unknown.join(', ') });

    if (!jsonObjectRecoverable(content))
        findings.push({ detector: 'NO_JSON_OBJECT', detail: 'no well-formed JSON object in the text' });

    return findings;
}

// ── Safe serialisation of the response object ─────────────────────────────────
/** Strings are preserved in full — nothing is truncated. Cycles and non-serialisable
 *  values are replaced with markers so one bad field cannot lose the whole record. */
function safeSerialize(value: unknown, depth = 0, seen = new Set<object>()): unknown {
    if (depth > 12) return '[max-depth]';
    if (value === null || typeof value === 'string' || typeof value === 'number'
        || typeof value === 'boolean' || value === undefined) return value;
    if (typeof value === 'bigint') return `${value.toString()}n`;
    if (typeof value === 'function') return `[function ${value.name || 'anonymous'}]`;
    if (typeof value === 'symbol') return value.toString();
    if (value instanceof Date) return value.toISOString();
    if (value instanceof Error) return { name: value.name, message: value.message, stack: value.stack };
    if (typeof Headers !== 'undefined' && value instanceof Headers)
        return Object.fromEntries((value as Headers).entries());
    if (value instanceof Map) return Object.fromEntries([...value.entries()]
        .map(([k, v]) => [String(k), safeSerialize(v, depth + 1, seen)]));
    if (value instanceof Set) return [...value].map(v => safeSerialize(v, depth + 1, seen));

    if (typeof value === 'object') {
        // `seen` tracks ANCESTORS on the current path, not everything visited.
        // A shared object reachable from two branches is not a cycle; the first
        // version of this function used a WeakSet of all visited objects and
        // wrongly stamped response.body and providerMetadata as '[circular]',
        // hiding the raw provider payload — the field this probe exists to capture.
        if (seen.has(value as object)) return '[circular]';
        seen.add(value as object);
        try {
            if (Array.isArray(value)) return value.map(v => safeSerialize(v, depth + 1, seen));
            const out: Record<string, unknown> = {};
            for (const key of Object.keys(value as object)) {
                try { out[key] = safeSerialize((value as Record<string, unknown>)[key], depth + 1, seen); }
                catch (e) { out[key] = `[unserialisable: ${(e as Error).message}]`; }
            }
            return out;
        } finally {
            seen.delete(value as object);
        }
    }
    return `[unknown type ${typeof value}]`;
}

/** Pull the assistant text out of the SDK's raw provider body, if it is exposed. */
function rawBodyContent(serialised: unknown): string | null {
    try {
        const body = (serialised as any)?.response?.body;
        if (!body || typeof body === 'string' && body.startsWith('[')) return null;
        const parsed = typeof body === 'string' ? JSON.parse(body) : body;
        const c = parsed?.choices?.[0]?.message?.content;
        return typeof c === 'string' ? c : null;
    } catch { return null; }
}

/** Which upstream provider OpenRouter routed to, from the raw body if exposed. */
function rawBodyProvider(serialised: unknown): string | null {
    try {
        const body = (serialised as any)?.response?.body;
        if (!body || typeof body === 'string' && body.startsWith('[')) return null;
        const parsed = typeof body === 'string' ? JSON.parse(body) : body;
        return parsed?.provider ?? null;
    } catch { return null; }
}

// ── Args ──────────────────────────────────────────────────────────────────────
function arg(name: string, fallback: string): string {
    const i = process.argv.indexOf(name);
    return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

async function main(): Promise<number> {
    const iterations = parseInt(arg('-n', arg('--iterations', '50')), 10);
    const strategy = arg('--strategy', 'one-shot-cot');
    const sampleId = arg('--sample-id', 'ge_024113');
    const sleepMs = parseInt(arg('--sleep', '500'), 10);
    const dryRun = process.argv.includes('--dry-run');

    const pkg = (p: string) => {
        try { return require_(`${p}/package.json`).version; } catch { return 'unknown'; }
    };

    const instructions = loadAgentInstructions('emotion', strategy) ?? undefined;
    if (!instructions) {
        console.error(`prompt for strategy "${strategy}" could not be loaded — the loader ` +
                      `returned null, so the agent would silently fall back to its hardcoded ` +
                      `instructions and this probe would not replay the real request.`);
        return 2;
    }
    const userText = loadSampleText(sampleId);
    const userMessage = MODE_PREFIX_SOCIAL_MEDIA + userText;

    console.log('='.repeat(78));
    console.log('Mastra agent.generate() layer probe');
    console.log('='.repeat(78));
    console.log(`  provider/model : ${process.env.MODEL_PROVIDER}/${process.env.MODEL_ID}`);
    console.log(`  strategy       : ${strategy}  (prompts/emotion/${strategy}.md)`);
    console.log(`  sample_id      : ${sampleId}`);
    console.log(`  user text      : ${JSON.stringify(userText)}`);
    console.log(`  system prompt  : ${instructions.length} chars`);
    console.log(`  iterations     : ${iterations}`);
    console.log(`  versions       : ai=${pkg('ai')} @ai-sdk/openai=${pkg('@ai-sdk/openai')} ` +
                `@mastra/core=${pkg('@mastra/core')} node=${process.version}`);
    console.log('='.repeat(78));

    if (dryRun) {
        console.log('\n--- DRY RUN — nothing was called ---\n');
        console.log(JSON.stringify({ instructions, userMessage }, null, 2));
        return 0;
    }

    fs.mkdirSync(OUT_DIR, { recursive: true });
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, 'Z');
    const outPath = path.join(OUT_DIR, `agent_generate_probe_${strategy}_${stamp}.jsonl`);
    console.log(`\nwriting -> ${outPath}\n`);

    fs.appendFileSync(outPath, JSON.stringify({
        record_type: 'probe_header',
        started_utc: stamp,
        layer_under_test: 'Mastra Agent.generate() + Vercel AI SDK',
        bypassed: ['workflow', 'express route', 'extractJson parser', 'csv/jsonl writer',
                   'python harness'],
        provider: process.env.MODEL_PROVIDER,
        model: process.env.MODEL_ID,
        strategy, sample_id: sampleId,
        user_text: userText,
        system_prompt: instructions,
        user_message: userMessage,
        versions: { ai: pkg('ai'), '@ai-sdk/openai': pkg('@ai-sdk/openai'),
                    '@mastra/core': pkg('@mastra/core'), node: process.version },
        iterations_planned: iterations,
    }) + '\n');

    let dirty = 0, errors = 0, textVsRawMismatch = 0, rawBodySeen = false;
    const distinct = new Map<string, number>();

    for (let i = 1; i <= iterations; i++) {
        const t0 = Date.now();
        let text: string | null = null;
        let serialised: unknown = null;
        let errMsg: string | null = null;
        let findings: Finding[] = [];
        let rawContent: string | null = null;
        let rawProvider: string | null = null;

        try {
            const response = await emotionAnalysisAgent.generate(userMessage, { instructions });
            // verbatim — no trim, no repair, no normalisation
            text = (response as any)?.text ?? null;
            serialised = safeSerialize(response);
            rawContent = rawBodyContent(serialised);
            rawProvider = rawBodyProvider(serialised);
            findings = analyse(text);
            if (rawContent !== null && text !== null && rawContent !== text) {
                textVsRawMismatch++;
                findings.push({
                    detector: 'TEXT_DIFFERS_FROM_RAW_BODY',
                    detail: `raw body content is ${rawContent.length} chars, ` +
                            `response.text is ${text.length} chars`,
                });
            }
        } catch (e) {
            errMsg = `${(e as Error).name}: ${(e as Error).message}`;
            errors++;
        }

        const latency = Date.now() - t0;
        if (rawContent !== null) rawBodySeen = true;
        if (findings.length) dirty++;
        if (text !== null) distinct.set(text, (distinct.get(text) ?? 0) + 1);

        const s = serialised as any;
        fs.appendFileSync(outPath, JSON.stringify({
            record_type: 'probe_response',
            iteration: i,
            timestamp_utc: new Date().toISOString(),
            text,
            text_length: text === null ? null : text.length,
            raw_body_content: rawContent,
            raw_body_content_length: rawContent === null ? null : rawContent.length,
            raw_body_matches_text: rawContent === null ? null : rawContent === text,
            upstream_provider: rawProvider,
            finish_reason: s?.finishReason ?? s?.finish_reason ?? null,
            usage: s?.usage ?? null,
            provider_metadata: s?.providerMetadata ?? s?.experimental_providerMetadata ?? null,
            response_metadata: s?.response ?? null,
            warnings: s?.warnings ?? null,
            full_response: serialised,
            findings,
            latency_ms: latency,
            error: errMsg,
        }) + '\n');

        const flag = errMsg ? `ERROR ${errMsg.slice(0, 60)}`
            : findings.length
                ? 'SUSPECT ' + findings.map(f => `${f.detector}:${f.detail.slice(0, 40)}`).join(' | ')
                : 'CLEAN';
        console.log(`[${String(i).padStart(3)}/${iterations}] len=${String(text?.length ?? 0).padStart(5)} ` +
                    `${String(latency).padStart(6)}ms  ${flag}`);
        if (findings.length) console.log(`        text: ${JSON.stringify(text)}`);

        if (i < iterations && sleepMs > 0) await new Promise(r => setTimeout(r, sleepMs));
    }

    console.log('\n' + '='.repeat(78));
    console.log('SUMMARY');
    console.log('='.repeat(78));
    console.log(`  clean               : ${iterations - dirty - errors}/${iterations}`);
    console.log(`  suspect             : ${dirty}`);
    console.log(`  errors              : ${errors}`);
    console.log(`  text != raw body    : ${textVsRawMismatch}` +
                (rawBodySeen ? '' : '   (raw body NOT exposed by the SDK — comparison unavailable)'));
    console.log(`  distinct texts      : ${distinct.size}`);
    for (const [t, n] of [...distinct.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5)) {
        console.log(`      x${String(n).padStart(3)}  ${JSON.stringify(t.slice(0, 100))}`);
    }
    console.log(`  output              : ${outPath}`);
    console.log();

    if (dirty) {
        console.log('  VERDICT: corruption reproduced through agent.generate().');
        console.log('  The workflow, Express route, parser and CSV writer were NOT in the path,');
        console.log('  so the defect is inside the Mastra Agent / AI SDK call.');
        if (textVsRawMismatch) {
            console.log(`  ${textVsRawMismatch} response(s) had a raw provider body that differs from`);
            console.log('  response.text — the damage is in the SDK\'s text assembly. Compare');
            console.log('  raw_body_content against text in the JSONL.');
        }
        return 1;
    }
    if (errors === iterations) {
        console.log('  VERDICT: inconclusive — every call failed.');
        return 2;
    }
    console.log('  VERDICT: clean through agent.generate() when called serially.');
    console.log('  The remaining untested difference from the real pipeline is CONCURRENCY:');
    console.log('  the workflow fires emotion + symptom + context + referral in parallel.');
    console.log('  Next experiment: this same probe with 4 concurrent generate() calls.');
    return 0;
}

main().then(code => process.exit(code)).catch(e => {
    console.error(e);
    process.exit(2);
});

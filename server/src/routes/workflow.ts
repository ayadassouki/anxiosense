import { Router, Request, Response } from 'express';
import { v4 as uuid } from 'uuid';
import db from '../db.js';
import { validateText } from '../utils/validateText.js';
import { preAssess } from '../utils/preAssess/pipeline.js';
import { evaluateGrounding, calibrateConfidence } from '../utils/preAssess/grounding.js';
import { evaluateSafety, CRISIS_RESPONSE_TEXT } from '../utils/safetyCheck.js';
import { validateFunctionalImpairment } from '../utils/validateFunctionalImpairment.js';
import { insertSubmittedInput } from '../utils/submittedInput.js';
import { buildCrisisReport } from '../utils/crisisReport.js';

const router   = Router();
const MASTRA   = process.env.MASTRA_URL ?? 'http://localhost:4111';
const WF_ID    = 'anxiosense-workflow';
const API      = `${MASTRA}/api`;

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Recursively search for a string value under a specific set of keys.
 * IMPORTANT: only returns strings found under named keys — never returns
 * an arbitrary long string encountered while traversing values.
 */
function findByKey<T>(obj: unknown, keys: string[], depth = 0): T | null {
  if (depth > 10 || obj === null || obj === undefined) return null;
  if (typeof obj !== 'object') return null;
  const rec = obj as Record<string, unknown>;

  for (const key of keys) {
    const val = rec[key];
    if (val !== undefined && val !== null) {
      if (typeof val === 'string' && val.length > 0) return val as T;
      if (typeof val === 'object') return val as T;
    }
  }

  for (const val of Object.values(rec)) {
    if (typeof val === 'object' && val !== null) {
      const found = findByKey<T>(val, keys, depth + 1);
      if (found !== null) return found;
    }
  }
  return null;
}

/**
 * Collect EVERY value stored under `key` anywhere in the run payload, deduplicated.
 *
 * findByKey returns the first match, which is wrong for per-agent fields: one
 * assessment makes five agent calls and we need to know whether they were all served
 * by the same upstream provider. A mixed result is itself the finding.
 */
function collectByKey(obj: unknown, key: string, depth = 0, acc = new Set<string>()): string[] {
  if (depth > 10 || obj === null || typeof obj !== 'object') return [...acc];
  const rec = obj as Record<string, unknown>;
  const val = rec[key];
  if (typeof val === 'string' && val.length > 0) acc.add(val);
  for (const v of Object.values(rec)) {
    if (typeof v === 'object' && v !== null) collectByKey(v, key, depth + 1, acc);
  }
  return [...acc];
}

/** Extract the final report string — only returns it when found under the right key. */
function extractFinalReport(obj: unknown): string | null {
  const val = findByKey<string>(obj, ['finalReport', 'final_report'], 0);
  return typeof val === 'string' && val.length > 50 ? val : null;
}

/**
 * Extract the raw Emotion Agent JSON string from the workflow run result.
 *
 * The Mastra workflow stores emotionAnalysis (a JSON string produced by the
 * emotion agent) in the session store.  The session is cleared before the run
 * result is returned to Express, so we look for it in the exportSession block
 * that is embedded inside the workflow result under various key paths.
 *
 * The value is a raw string like:
 *   '{"emotions":["anxiety","stress"],"emotional_intensity":"high","evidence_from_text":[...]}'
 *
 * Returns null if the field is absent (e.g. safety-override path skips the pipeline).
 */
function extractEmotionAgentRaw(obj: unknown): string | null {
  const val = findByKey<string>(obj, ['emotionAnalysis', 'emotion_analysis'], 0);
  if (typeof val === 'string' && val.length > 2) return val;
  return null;
}

/**
 * Extract the raw pre-fallback Referral Agent output from the workflow result.
 * Persisted so the Dreaddit Mapping A evaluation can always re-derive the
 * referral decision offline, independent of the workflow's fallback handling
 * and of Mastra storage snapshots. Null on the crisis-override path.
 */
function extractReferralAgentRaw(obj: unknown): string | null {
  const val = findByKey<string>(obj, ['referralAnalysis', 'referral_analysis'], 0);
  if (typeof val === 'string' && val.length > 2) return val;
  return null;
}

/** Extract token usage from the workflow result (Mastra v1.42 FullOutput path). */
function extractTokenUsage(obj: unknown): { input_tokens: number; output_tokens: number } | null {
  const tu = findByKey<Record<string, unknown>>(obj, ['tokenUsage', 'token_usage'], 0);
  if (!tu || typeof tu !== 'object') return null;
  const i = tu['inputTokens'];
  const o = tu['outputTokens'];
  if (typeof i === 'number' && typeof o === 'number') return { input_tokens: i, output_tokens: o };
  return null;
}

function extractSummary(report: string): string {
  const match = report.match(
    /(?:#{1,3}\s*(?:\d+\.\s*)?(?:Summary|Overview)[^\n]*\n)([\s\S]{40,600}?)(?=\n#{1,3}|\n\d+\.|$)/i
  );
  if (match) {
    const text = match[1].replace(/\*\*/g, '').trim();
    return (text.match(/[^.!?]+[.!?]+/g) ?? []).slice(0, 3).join(' ').trim() || text.slice(0, 280);
  }
  return report.split('\n')
    .filter(l => l.trim() && !l.match(/^#{1,3}/) && !l.match(/^\d+\./))
    .slice(0, 3).join(' ').replace(/\*\*/g, '').slice(0, 300);
}

async function mastraPost(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${API}/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`Mastra ${path} returned ${res.status}: ${text.slice(0, 200)}`);
  return JSON.parse(text);
}

async function mastraGet(path: string): Promise<unknown> {
  const res = await fetch(`${API}/${path}`);
  const text = await res.text();
  if (!res.ok) throw new Error(`Mastra GET ${path} → ${res.status}`);
  return JSON.parse(text);
}

// ── Poll run until complete ───────────────────────────────────────────────────
async function pollRun(runId: string, intervalMs = 3000, maxMs = 150_000): Promise<unknown> {
  const deadline = Date.now() + maxMs;
  const path     = `workflows/${WF_ID}/runs/${runId}`;

  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, intervalMs));
    let run: Record<string, unknown>;
    try {
      run = await mastraGet(path) as Record<string, unknown>;
    } catch {
      continue; // transient — keep polling
    }

    const status = run.status as string | undefined;
    console.log(`[mastra] poll run ${runId}: status=${status}`);

    if (status === 'completed' || status === 'success') return run;
    if (status === 'failed' || status === 'error') {
      throw new Error(`Workflow failed: ${JSON.stringify(run.error ?? 'unknown')}`);
    }
  }
  throw new Error(`Workflow timed out after ${maxMs / 1000}s`);
}

// ── POST /api/workflow/run ────────────────────────────────────────────────────
router.post('/run', async (req: Request, res: Response): Promise<void> => {
  /** Wall-clock timestamp for total end-to-end request duration measurement. */
  const requestStart = Date.now();

  const {
    mode                = 'journal',
    userText,
    gad7Answers,
    functionalImpairment,
    clinicianMode       = false,
    saveSession         = false,
  } = req.body as {
    mode?:                  'journal' | 'social-media';
    userText?:              string;
    gad7Answers?:           number[];
    functionalImpairment?:  string;
    clinicianMode?:         boolean;
    saveSession?:           boolean;
  };

  const validation = validateText(userText ?? '');
  if (!validation.valid) {
    res.status(400).json({ message: validation.message });
    return;
  }

  // ── Pre-assessment: emoji replacement, language detection, normalisation ──
  const preAssessStart = Date.now();
  const preResult = await preAssess(userText!, mode);
  const preAssessMs = Date.now() - preAssessStart;
  if (preResult.rejected) {
    res.status(400).json({ message: preResult.message });
    return;
  }
  // Use preprocessed text for the Mastra workflow call
  const analysisText = preResult.processedText;

  // ── Safety check — runs BEFORE calling Mastra ────────────────────────────
  // Checks for credible high-risk language (suicidal ideation/intent, self-harm,
  // hopelessness, worthlessness, planning, severe distress).
  // If detected, bypass the AI pipeline entirely and return the crisis response.
  //
  // Evaluates BOTH the raw submission and the pre-processed text the pipeline
  // analyses, in overlapping chunks, returning the highest-severity category
  // found anywhere. The second scan is skipped when the two texts are identical.
  const safety = evaluateSafety(userText!, analysisText);
  if (safety.isCrisis) {
    // Crisis override report. Guidance wording is unchanged and pinned by tests;
    // the Submitted Input section is added for traceability through the SAME
    // helper normal reports use, so sanitisation is identical. Everything else
    // the normal pipeline produces stays bypassed.
    const crisisReport = buildCrisisReport(userText!, mode);

    const crisisReportId = uuid();
    const crisicSummary  = CRISIS_RESPONSE_TEXT.slice(0, 200);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const userId = (req as any).user?.userId as string | undefined;
    if (saveSession && userId) {
      try {
        db.prepare(`
          INSERT INTO reports
            (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode, functional_impairment)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
          crisisReportId, userId, mode,
          'Urgent Safety Notice', 'urgent',
          crisicSummary, crisisReport,
          clinicianMode ? 1 : 0,
          null // safety override — no impairment answer relevant
        );
      } catch (dbErr) {
        console.error('[safety] DB save failed (non-fatal):', dbErr);
      }
    }

    res.json({
      reportId:            crisisReportId,
      finalReport:         crisisReport,
      concernPattern:      'Urgent Safety Notice',
      referralLevel:       'urgent',
      summary:             crisicSummary,
      functionalImpairment: null,
      _meta: {
        safetyOverride: true,
        safetyCategory: safety.category,
        // Counts only — never chunk text or matched substrings.
        safetyCategories:   safety.categories,
        safetyMatchCount:   safety.matchCount,
        safetyChunkCount:   safety.chunkCount,
        safetyScannedTexts: safety.scannedTexts,
      },
    });
    return;
  }

  // ── Functional impairment validation ──────────────────────────────────────
  // Runs AFTER the safety check so crisis submissions (which return early above)
  // bypass this validation — they always store null.
  const impairmentResult = validateFunctionalImpairment(mode, functionalImpairment);
  if (!impairmentResult.ok) {
    res.status(400).json({ message: impairmentResult.message });
    return;
  }
  const validatedImpairment = impairmentResult.value;

  // ── 1. Create run ─────────────────────────────────────────────────────
  const mastraStart = Date.now();
  let runId: string;
  try {
    const createBody = await mastraPost(`workflows/${WF_ID}/create-run`, {}) as Record<string, unknown>;
    runId = (createBody.runId as string | undefined) ?? uuid();
    console.log(`[mastra] created run ${runId}`);
  } catch (err) {
    res.status(502).json({
      message: 'Could not create Mastra run. Is Mastra running on port 4111?',
    });
    return;
  }

  // ── 2. Start run (synchronous endpoint — may return result directly) ──
  let startResult: unknown;
  try {
    startResult = await mastraPost(
      `workflows/${WF_ID}/start?runId=${runId}`,
      { inputData: { mode, userText: analysisText, gad7Answers, functionalImpairment, clinicianMode } }
    );
    console.log('[mastra] start result keys:', Object.keys(startResult as object ?? {}));
  } catch (err) {
    res.status(502).json({
      message: err instanceof Error ? err.message : 'Mastra workflow start failed.',
    });
    return;
  }

  // ── 3. Try to extract report from start response ───────────────────
  let workflowData: unknown = startResult;
  let finalReport = extractFinalReport(startResult);

  // ── 4. If not in start response, poll /runs/:runId ─────────────────
  if (!finalReport) {
    console.log('[mastra] report not in start response — polling /runs/:runId');
    try {
      workflowData = await pollRun(runId);
      finalReport  = extractFinalReport(workflowData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Workflow polling failed.';
      console.error('[mastra] polling failed:', err);
      res.status(504).json({ message: msg });
      return;
    }
  }

  if (!finalReport) {
    console.error('[mastra] extractFinalReport returned null. Data:', JSON.stringify(workflowData).slice(0, 800));
    res.status(502).json({
      message: 'Workflow completed but finalReport not found in response.',
      debug:   JSON.stringify(workflowData).slice(0, 800),
    });
    return;
  }

  const mastraMs = Date.now() - mastraStart;

  // ── 5. Determine authoritative concernPattern + referralLevel ─────────────
  //
  // The Mastra workflow outputs ONLY { finalReport } — concernPattern is never
  // in its output object, so findByKey always returned null and defaulted to
  // 'Mild Concern Pattern'. Fix: derive from data we already have in the request.
  //
  //   a) Urgent safety path  → detect by report body header string
  //   b) Journal + GAD-7     → compute from score (same thresholds as gad7-assessment-scorer.ts)
  //   c) Text-only / social  → proxy from riskLevel the pipeline produced
  //
  const isUrgentReport =
    finalReport.includes('## Important — Urgent Safety Notice') ||
    finalReport.includes('## Important — Safety Alert');

  let concernPattern: string;
  let referralLevel: 'low' | 'moderate' | 'urgent';

  if (isUrgentReport) {
    concernPattern = 'Urgent Safety Notice';
    referralLevel  = 'urgent';

  } else if (mode === 'journal' && Array.isArray(gad7Answers) && gad7Answers.length === 7) {
    // Canonical: deterministic from submitted answers — cannot be wrong.
    // referralLevel is capped at 'moderate' for all GAD-7 severity bands.
    // 'urgent' is reserved exclusively for the safety-agent crisis path above
    // (isUrgentReport), which is triggered by explicit crisis / safety indicators
    // in the user's text — not by a high GAD-7 score alone.
    const gad7Score = (gad7Answers as number[]).reduce((a: number, b: number) => a + b, 0);
    if      (gad7Score <= 4)  { concernPattern = 'Minimal Concern Pattern';  referralLevel = 'low';      }
    else if (gad7Score <= 9)  { concernPattern = 'Mild Concern Pattern';     referralLevel = 'moderate'; }
    else if (gad7Score <= 14) { concernPattern = 'Elevated Concern Pattern'; referralLevel = 'moderate'; }
    else                      { concernPattern = 'High Concern Pattern';      referralLevel = 'moderate'; }

  } else {
    // Text-only (no GAD-7) or social-media mode:
    // Use the riskLevel the referral agent produced as the best available proxy.
    const riskHint =
      findByKey<string>(workflowData, ['riskLevel']) ??
      findByKey<string>(workflowData, ['risk_level']);

    if      (riskHint === 'urgent')   { concernPattern = 'High Concern Pattern';      referralLevel = 'urgent';   }
    else if (riskHint === 'moderate') { concernPattern = 'Elevated Concern Pattern';  referralLevel = 'moderate'; }
    else                              { concernPattern = 'Minimal Concern Pattern';    referralLevel = 'low';      }
  }

  console.log(`[workflow] concernPattern="${concernPattern}" referralLevel="${referralLevel}"`);

  // ── Post-workflow grounding evaluation (research metadata only) ──────
  // Lexical grounding check: measures how many user key-terms appear in the
  // report. This is distinct from the Mastra workflow's in-process evidence
  // validation step (claim validation against the knowledge base).
  const groundingStart = Date.now();
  const grounding = evaluateGrounding(userText!, finalReport);
  const groundingMs = Date.now() - groundingStart;
  const confidence = calibrateConfidence(grounding.score);

  const totalRequestMs = Date.now() - requestStart;

  console.log(
    `[groundingEval] score=${grounding.score.toFixed(3)} refs=${grounding.specificReferences} ` +
    `generic=${grounding.genericPhraseCount} passed=${grounding.passed} confidence=${confidence}`
  );
  console.log(
    `[timing] preAssess=${preAssessMs}ms mastra=${mastraMs}ms groundingEval=${groundingMs}ms ` +
    `total=${totalRequestMs}ms`
  );

  const summary  = extractSummary(finalReport);
  const reportId = uuid();

  // ── 5b. Submitted Input section ───────────────────────────────────
  // Added LAST, after concern-pattern/referral derivation, the grounding
  // evaluation and summary extraction have all read the report. Order matters:
  // inserting earlier would put the user's own words inside the text the
  // grounding evaluator scores, driving lexical overlap towards 1.0 and
  // invalidating that research metric. Nothing below reads the report again,
  // so no assessment output can be affected by this.
  //
  // Uses the RAW submission (userText), not the pre-processed analysisText, so
  // the reader sees exactly what they typed. The crisis path returns earlier and
  // deliberately does not include this section.
  finalReport = insertSubmittedInput(finalReport, userText!, mode);

  // ── 6. Persist if authenticated ───────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const userId = (req as any).user?.userId as string | undefined;
  if (saveSession && userId) {
    try {
      db.prepare(`
        INSERT INTO reports
          (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode, functional_impairment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(reportId, userId, mode, concernPattern, referralLevel, summary, finalReport, clinicianMode ? 1 : 0,
        validatedImpairment);
      console.log(`[mastra] saved report ${reportId} for user ${userId}`);
    } catch (dbErr) {
      console.error('[mastra] DB save failed (non-fatal):', dbErr);
    }
  }

  res.json({
    reportId,
    finalReport,
    concernPattern,
    referralLevel,
    summary,
    functionalImpairment: validatedImpairment,
    // Research metadata — not displayed in the UI, inspectable via network tools.
    // timings covers the three server-measured phases; the Mastra workflow's
    // internal agent timings are logged separately to the console and eval exports.
    _meta: {
      language: preResult.detectedLanguage,
      languageConfidence: preResult.languageConfidence,
      emojiProcessed: preResult.emojiProcessed,
      normalized: preResult.normalized,
      groundingScore: grounding.score,
      groundingLexical: grounding.lexicalScore,
      groundingTfidf: grounding.tfidfSimilarity,
      groundingConfidence: confidence,
      timings: {
        preAssessMs,
        mastraMs,
        groundingMs,
        totalRequestMs,
      },
    },
  });
});

// ── POST /api/workflow/evaluate ───────────────────────────────────────────────
// Evaluation endpoint for the AnxioSense LLM experiment pipeline.
//
// Accepts a raw text string plus optional model/strategy fields. Calls the same
// Mastra workflow as /run using "social-media" mode (datasets have no GAD-7).
//
// Model switching: set MODEL_PROVIDER + MODEL_ID in the Mastra .env and restart
// the Mastra dev server. The endpoint reflects what is ACTUALLY running via
// model_actual/provider_actual in the metadata response, and logs a warning when
// the caller-requested model differs from the active one.
//
// Strategy switching: the `strategy` field is forwarded directly into the
// workflow inputData, where each agent step loads the matching prompt file from
// prompts/{agentName}/{strategy}.md at generate() time — no restart required.
//
// No workflow order, RAG retrieval, safety logic, concern patterns, validation,
// clinician mode, or agent output schemas are modified by this endpoint.
router.post('/evaluate', async (req: Request, res: Response): Promise<void> => {
  const requestStart = Date.now();

  const {
    text,
    model    = `${process.env.MODEL_PROVIDER ?? 'groq'}/${process.env.MODEL_ID ?? 'llama-3.3-70b-versatile'}`,
    strategy = process.env.ANXIOSENSE_STRATEGY  ?? 'one-shot-cot',
    evaluation_mode = true,
  } = req.body as {
    text?:            string;
    model?:           string;
    strategy?:        string;
    evaluation_mode?: boolean;
  };

  // Reflect what is ACTUALLY running in Mastra — set at startup via MODEL_PROVIDER + MODEL_ID.
  const provider_actual = process.env.MODEL_PROVIDER ?? 'groq';
  const model_id_actual = process.env.MODEL_ID       ?? 'llama-3.3-70b-versatile';
  const model_actual    = `${provider_actual}/${model_id_actual}`;

  if (model !== model_actual) {
    console.warn(
      `[evaluate] model mismatch — requested="${model}" actual="${model_actual}". ` +
      `To switch models, update MODEL_PROVIDER + MODEL_ID in .env and restart Mastra.`
    );
  }
  console.log(`[evaluate] model_actual="${model_actual}" strategy="${strategy}"`);

  if (typeof text !== 'string' || text.trim().length < 10) {
    res.status(400).json({
      error: 'Field "text" must be a non-empty string of at least 10 characters.',
    });
    return;
  }

  const userText = text.trim();

  // Safety check — crisis texts return referralLevel:"urgent" which maps to
  // binary label 1 in Dreaddit evaluation (stressed). Kept identical to /run.
  const safety = evaluateSafety(userText, userText);
  if (safety.isCrisis) {
    const crisisReport = buildCrisisReport(userText, 'social-media');
    res.json({
      report: {
        finalReport:    crisisReport,
        concernPattern: 'Urgent Safety Notice',
        referralLevel:  'urgent',
        summary:        CRISIS_RESPONSE_TEXT.slice(0, 200),
      },
      metadata: {
        model_requested: model,
        model_actual,
        provider_actual,
        // Crisis override short-circuits before any LLM call, so no upstream was used.
        upstream_provider:  null,
        upstream_providers: [],
        strategy_used:   strategy,
        evaluation_mode,
        latency_ms:      Date.now() - requestStart,
        token_usage:     { prompt_tokens: 0, completion_tokens: 0 },
        safety_override: true,
        safety_category: safety.category,
      },
    });
    return;
  }

  // ── Create Mastra run ─────────────────────────────────────────────────────
  let runId: string;
  try {
    const createBody = await mastraPost(
      `workflows/${WF_ID}/create-run`, {}
    ) as Record<string, unknown>;
    runId = (createBody.runId as string | undefined) ?? uuid();
    console.log(`[evaluate] created run ${runId}`);
  } catch {
    res.status(502).json({
      error: 'Could not reach Mastra (port 4111). Is the Mastra dev server running?',
    });
    return;
  }

  // ── Start run with social-media mode + resolved strategy ────────────────
  let startResult: unknown;
  try {
    startResult = await mastraPost(
      `workflows/${WF_ID}/start?runId=${runId}`,
      { inputData: { mode: 'social-media', userText, strategy } }
    );
    console.log('[evaluate] start result keys:', Object.keys(startResult as object ?? {}));
  } catch (err) {
    res.status(502).json({
      error: err instanceof Error ? err.message : 'Mastra workflow start failed.',
    });
    return;
  }

  // ── Extract report (try start response first, then poll) ──────────────────
  let workflowData: unknown = startResult;
  let finalReport: string | null = extractFinalReport(startResult);

  if (!finalReport) {
    console.log('[evaluate] report not in start response — polling /runs/:runId');
    try {
      workflowData = await pollRun(runId);
      finalReport  = extractFinalReport(workflowData);
    } catch (err) {
      res.status(504).json({
        error: err instanceof Error ? err.message : 'Workflow polling timed out.',
      });
      return;
    }
  }

  if (!finalReport) {
    console.error('[evaluate] extractFinalReport returned null. Data:', JSON.stringify(workflowData).slice(0, 600));
    res.status(502).json({
      error: 'Workflow completed but finalReport was not found in response.',
    });
    return;
  }

  // ── Determine concernPattern + referralLevel ──────────────────────────────
  // Mirrors the logic in /run (text-only / social-media path, no GAD-7).
  let concernPattern: string;
  let referralLevel: 'low' | 'moderate' | 'urgent';

  const isUrgentReport = finalReport.includes('## Important — Urgent Safety Notice');
  if (isUrgentReport) {
    concernPattern = 'Urgent Safety Notice';
    referralLevel  = 'urgent';
  } else {
    const riskHint =
      findByKey<string>(workflowData, ['riskLevel']) ??
      findByKey<string>(workflowData, ['risk_level']);

    if      (riskHint === 'urgent')   { concernPattern = 'High Concern Pattern';      referralLevel = 'urgent';   }
    else if (riskHint === 'moderate') { concernPattern = 'Elevated Concern Pattern';  referralLevel = 'moderate'; }
    else                              { concernPattern = 'Minimal Concern Pattern';    referralLevel = 'low';      }
  }

  console.log(`[evaluate] concernPattern="${concernPattern}" referralLevel="${referralLevel}"`);

  const latency_ms        = Date.now() - requestStart;
  const token_usage       = extractTokenUsage(workflowData);
  const emotion_agent_raw = extractEmotionAgentRaw(workflowData);
  const referral_agent_raw = extractReferralAgentRaw(workflowData);

  // Upstream provider(s) that actually served this assessment's agent calls.
  // Pinned in model-provider.ts; recorded here so every result row proves the pin held.
  // More than one value means routing changed mid-assessment — treat the row as suspect.
  const upstream_providers = collectByKey(workflowData, 'upstreamProvider');
  const upstream_provider =
    upstream_providers.length === 1 ? upstream_providers[0]
    : upstream_providers.length === 0 ? null
    : 'MIXED';

  // Extract internal quality flags from the workflow output.
  // These are set by the workflow's claim-construction step, Map 2, and report step.
  // All default to false so the field is always present even on older workflow versions.
  const rawQf = findByKey<Record<string, unknown>>(workflowData, ['qualityFlags'], 0);
  const quality_flags = {
    agent_json_parse_failed:     Boolean(rawQf?.agent_json_parse_failed     ?? false),
    fallback_claim_injected:     Boolean(rawQf?.fallback_claim_injected     ?? false),
    referral_risk_fallback_used: Boolean(rawQf?.referral_risk_fallback_used ?? false),
    recommendation_rejected:     Boolean(rawQf?.recommendation_rejected     ?? false),
  };

  res.json({
    report: {
      finalReport,
      concernPattern,
      referralLevel,
      summary: extractSummary(finalReport),
    },
    /**
     * emotion_agent_raw: the raw JSON string produced by the Emotion Analysis Agent.
     * Shape: {"emotions": [...], "emotional_intensity": "...", "evidence_from_text": [...]}
     *
     * Used by the GoEmotions evaluation (RQ2) to compare the Emotion Agent's output
     * directly against GoEmotions ground-truth labels, independent of the final report.
     * This is the PRIMARY prediction source for GoEmotions evaluation.
     * The finalReport markdown is a SECONDARY end-to-end measure.
     *
     * Null on the crisis-override path (no LLM agents are called).
     * Null if the workflow result does not include the exportSession block.
     */
    emotion_agent_raw,
    /**
     * referral_agent_raw: the verbatim Referral Agent output BEFORE fallback
     * handling. Primary offline source for Dreaddit Mapping A re-derivation.
     * Null on the crisis-override path (no LLM agents are called).
     */
    referral_agent_raw,
    metadata: {
      model_requested: model,
      model_actual,
      provider_actual,
      // Upstream provider behind `provider_actual` (OpenRouter routes to DeepInfra /
      // Groq / Novita / Google). "MIXED" if one assessment hit more than one.
      upstream_provider,
      upstream_providers,
      strategy_used:   strategy,
      evaluation_mode,
      latency_ms,
      // inputTokens + outputTokens from LanguageModelV2Usage (all 5 agents summed).
      // Null when the provider does not return usage (some OpenRouter free-tier models).
      token_usage,
      safety_override: false,
      // Internal quality flags — observable side-effects that occurred during the run.
      // Recorded in result CSVs so non-clean runs are not silently treated as clean.
      quality_flags,
    },
  });
});

export default router;

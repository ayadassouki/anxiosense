import { Router, Request, Response } from 'express';
import { v4 as uuid } from 'uuid';
import db from '../db.js';
import { validateText } from '../utils/validateText.js';
import { preAssess } from '../utils/preAssess/pipeline.js';
import { evaluateGrounding, calibrateConfidence } from '../utils/preAssess/grounding.js';

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

/** Extract the final report string — only returns it when found under the right key. */
function extractFinalReport(obj: unknown): string | null {
  const val = findByKey<string>(obj, ['finalReport', 'final_report'], 0);
  return typeof val === 'string' && val.length > 50 ? val : null;
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
    mode          = 'journal',
    userText,
    gad7Answers,
    clinicianMode = false,
    saveSession   = false,
  } = req.body as {
    mode?:          'journal' | 'social-media';
    userText?:      string;
    gad7Answers?:   number[];
    clinicianMode?: boolean;
    saveSession?:   boolean;
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
      { inputData: { mode, userText: analysisText, gad7Answers, clinicianMode } }
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
  //   b) Journal + GAD-7     → compute from score (same thresholds as gad7-scorer.ts)
  //   c) Text-only / social  → proxy from riskLevel the pipeline produced
  //
  const isUrgentReport = finalReport.includes('## Important — Urgent Safety Notice');

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

  // ── 6. Persist if authenticated ───────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const userId = (req as any).user?.userId as string | undefined;
  if (saveSession && userId) {
    try {
      db.prepare(`
        INSERT INTO reports
          (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(reportId, userId, mode, concernPattern, referralLevel, summary, finalReport, clinicianMode ? 1 : 0);
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

export default router;

/**
 * Lightweight in-memory session store.
 *
 * Each workflow run writes its intermediate outputs here keyed by sessionId.
 * The report step reads the full snapshot and passes it to exportWorkflowRun,
 * then clears the entry so memory doesn't grow unbounded across runs.
 *
 * This avoids schema changes to existing step I/O contracts.
 */

export interface SessionData {
    /** Input mode selected by the user. */
    mode: 'journal' | 'social-media';
    /** Whether clinician-only details should be included in the report. */
    clinicianMode: boolean;
    userText: string;
    emotionAnalysis: string;
    symptomAnalysis: string;
    contextAnalysis: string;
    referralAnalysis: string;
    buildClaimsOutput: unknown;
    retrievalOutput: unknown;
    /** Formatted GAD-7 concern-pattern block for user-facing report (null in social-media mode). */
    gad7Block: string | null;
    /** Raw GAD-7 total score (0–21). Clinician-only. Null in social-media mode. */
    gad7Score: number | null;
    /** Clinical severity band (minimal/mild/moderate/severe). Clinician-only. Null in social-media mode. */
    gad7Severity: string | null;
    /** Individual item scores [0–3] × 7. Clinician-only. */
    gad7ItemScores: number[] | null;
    /** User-facing concern pattern label derived from GAD-7 score (null if no GAD-7). */
    gad7ConcernPattern: string | null;
    /**
     * Functional impairment response from the GAD-7 follow-up question.
     * Only present in journal mode when the user answered the question.
     * Does NOT affect the GAD-7 score — used only for recommendation lookup.
     */
    functionalImpairment: string | null;
    /**
     * Flags cases where GAD-7 and text-based claims disagree markedly.
     * high_gad7_low_text: GAD-7 ≥15 but text claims ≤1 (minimal text signal)
     * low_gad7_high_text: GAD-7 ≤4 but text has ≥4 real claims
     */
    discordanceNote: 'high_gad7_low_text' | 'low_gad7_high_text' | null;
    /**
     * Prompting strategy active for this workflow run.
     * Written by Map 2 (which has access to getInitData) so that the report
     * step can read it from the session without requiring getInitData.
     */
    promptStrategy?: 'zero-shot' | 'zero-shot-cot' | 'one-shot-cot';
    /**
     * Accumulated token usage across all agent.generate() calls in this run.
     * Written incrementally by parallel steps and the report step.
     * Fields mirror LanguageModelV2Usage: inputTokens / outputTokens.
     */
    tokenUsage?: {
        inputTokens:  number;
        outputTokens: number;
    };

    // ── Timing scratch fields (internal — written by workflow map steps) ─────
    /** Wall-clock ms for each parallel agent's generate() call. */
    agentTimingsMs?: { emotion: number; symptom: number; context: number; referral: number };
    /** Timestamp (Date.now()) recorded just before the retrieval step starts. */
    retrievalStartMs?: number;
    /** Elapsed retrieval time in ms — written by Map 3 after retrieval completes. */
    retrievalElapsedMs?: number;
    /** Timestamp (Date.now()) recorded just before the evidence validation step starts. */
    validationStartMs?: number;
    /** Elapsed validation time in ms — written by Map 4 after validation completes. */
    validationElapsedMs?: number;
    /** Timestamp (Date.now()) recorded just before the report generation step starts. */
    reportStartMs?: number;

    // ── Final assembled timing summary (written by report step) ──────────────
    timings?: {
        /** Wall-clock time for the parallel agent phase (= max of the four agents, since they run concurrently). */
        parallelMs: number;
        emotionMs:  number;
        symptomMs:  number;
        contextMs:  number;
        referralMs: number;
        retrievalMs:   number;
        validationMs:  number;
        reportMs:      number;
        totalMs:       number;
    };

    /**
     * Internal quality flags — observable side-effects that occurred during the run.
     * Written incrementally by workflow steps; read by the report step and included in
     * the workflow output so the evaluation runner can record them without re-running.
     * These flags do NOT change any pipeline behaviour — they are pure observability.
     */
    qualityFlags?: {
        /** True if any agent's text output could not be parsed as JSON by extractJson(). */
        agent_json_parse_failed: boolean;
        /** True if GEN-1 fallback claim was injected because all agents returned empty arrays. */
        fallback_claim_injected: boolean;
        /** True if the Referral Agent JSON parse failed and risk_level was defaulted to "moderate". */
        referral_risk_fallback_used: boolean;
        /** True if the Report step's recommendation was rejected and reset to the deterministic anchor. */
        recommendation_rejected: boolean;
    };
}

const store = new Map<string, Partial<SessionData>>();

export function writeSession(sessionId: string, data: Partial<SessionData>): void {
    const existing = store.get(sessionId) ?? {};
    store.set(sessionId, { ...existing, ...data });
}

/**
 * Atomically adds `inputTokens` and `outputTokens` to the running token-usage
 * accumulator for the session.  Safe to call from concurrent parallel steps
 * because JavaScript is single-threaded; no await between read and write.
 */
export function accumulateTokenUsage(
    sessionId: string,
    inputTokens:  number | undefined,
    outputTokens: number | undefined,
): void {
    const existing = store.get(sessionId) ?? {};
    const prev     = existing.tokenUsage ?? { inputTokens: 0, outputTokens: 0 };
    store.set(sessionId, {
        ...existing,
        tokenUsage: {
            inputTokens:  prev.inputTokens  + (inputTokens  ?? 0),
            outputTokens: prev.outputTokens + (outputTokens ?? 0),
        },
    });
}

export function readSession(sessionId: string): Partial<SessionData> | undefined {
    return store.get(sessionId);
}

export function clearSession(sessionId: string): void {
    store.delete(sessionId);
}

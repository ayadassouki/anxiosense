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
     * Flags cases where GAD-7 and text-based claims disagree markedly.
     * high_gad7_low_text: GAD-7 ≥15 but text claims ≤1 (minimal text signal)
     * low_gad7_high_text: GAD-7 ≤4 but text has ≥4 real claims
     */
    discordanceNote: 'high_gad7_low_text' | 'low_gad7_high_text' | null;

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
}

const store = new Map<string, Partial<SessionData>>();

export function writeSession(sessionId: string, data: Partial<SessionData>): void {
    const existing = store.get(sessionId) ?? {};
    store.set(sessionId, { ...existing, ...data });
}

export function readSession(sessionId: string): Partial<SessionData> | undefined {
    return store.get(sessionId);
}

export function clearSession(sessionId: string): void {
    store.delete(sessionId);
}

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

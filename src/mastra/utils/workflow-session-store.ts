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
    userText: string;
    emotionAnalysis: string;
    symptomAnalysis: string;
    contextAnalysis: string;
    referralAnalysis: string;
    buildClaimsOutput: unknown;
    retrievalOutput: unknown;
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

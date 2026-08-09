/**
 * AnxioSense — model-independent referral risk-level extraction.
 *
 * Replaces the strict JSON.parse previously used in the assessment workflow's
 * Map 2. Validated offline against 4,410 stored Dreaddit referral outputs from
 * Llama 4 Scout, Mistral Small 4 and Phi-4 (2026-08-08 validation): models
 * frequently wrap a complete, valid JSON object in Markdown code fences and/or
 * chain-of-thought prose, which strict parsing rejected and silently replaced
 * with the 'moderate' fallback.
 *
 * Extraction ladder (label-blind, identical for every model — "recover, never
 * invent"; mirrors src/emotion_payload.py used for the Emotion Agent):
 *   1. strict JSON.parse on the raw string;
 *   2. strip Markdown code fences and retry;
 *   3. extract the first balanced {...} object (string-aware) and retry;
 *   4. read ONLY the exact key `risk_level`;
 *   5. lowercase/trim; accept ONLY 'low' | 'moderate' | 'urgent';
 *   6. otherwise return null — the caller applies the existing fallback and
 *      sets referral_risk_fallback_used, exactly as before.
 *
 * No synonyms, no key aliases, no semantic inference, no model-specific paths.
 */

export type ReferralRiskLevel = 'low' | 'moderate' | 'urgent';

const VALID: readonly string[] = ['low', 'moderate', 'urgent'];

/** Strip a leading ```lang fence and a trailing ``` fence, if present. */
function stripFences(text: string): string {
    return text.trim().replace(/^```[a-zA-Z]*\s*/, '').replace(/\s*```$/, '');
}

/**
 * Return the first balanced top-level {...} span in `text`, respecting JSON
 * string literals and escapes, or null when no balanced object exists
 * (e.g. truncated output). Never repairs or invents closing braces.
 */
export function firstBalancedObject(text: string): string | null {
    let start = text.indexOf('{');
    while (start !== -1) {
        let depth = 0;
        let inString = false;
        let escaped = false;
        for (let i = start; i < text.length; i++) {
            const ch = text[i];
            if (escaped) { escaped = false; continue; }
            if (ch === '\\') { escaped = true; continue; }
            if (ch === '"') { inString = !inString; continue; }
            if (inString) continue;
            if (ch === '{') depth++;
            else if (ch === '}') {
                depth--;
                if (depth === 0) return text.slice(start, i + 1);
            }
        }
        start = text.indexOf('{', start + 1);
    }
    return null;
}

function tryParseObject(text: string): Record<string, unknown> | null {
    try {
        const obj = JSON.parse(text);
        return obj !== null && typeof obj === 'object' && !Array.isArray(obj)
            ? (obj as Record<string, unknown>)
            : null;
    } catch {
        return null;
    }
}

/**
 * Extract an explicit, valid risk_level from a raw Referral Agent response.
 * Returns null when no explicit valid value exists — never infers a label.
 */
export function extractRiskLevel(raw: unknown): ReferralRiskLevel | null {
    if (typeof raw !== 'string' || raw.length === 0) return null;

    // 1. strict parse
    let obj = tryParseObject(raw);
    // 2. fence-stripped retry
    if (!obj) obj = tryParseObject(stripFences(raw));
    // 3. first balanced embedded object
    if (!obj) {
        const candidate = firstBalancedObject(raw);
        if (candidate) obj = tryParseObject(candidate);
    }
    if (!obj) return null;

    // 4./5. exact key, closed vocabulary
    const value = obj['risk_level'];
    if (typeof value !== 'string') return null;
    const normalized = value.trim().toLowerCase();
    return VALID.includes(normalized) ? (normalized as ReferralRiskLevel) : null;
}

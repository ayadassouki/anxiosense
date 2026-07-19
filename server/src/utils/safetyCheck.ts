/**
 * AnxioSense Safety Check — Deterministic High-Risk Language Detector
 *
 * Runs BEFORE the Mastra AI pipeline. If credible high-risk language is detected,
 * the normal workflow is bypassed and a crisis response is returned immediately.
 *
 * Design rationale: deterministic pattern matching (not AI) is used here because:
 *   - Safety decisions must be predictable and testable
 *   - Speed: no API call required for the check itself
 *   - AI models can miss patterns or produce inconsistent results on safety signals
 *
 * Source: AnxioSense supervisory guidance (July 2026). Risk categories and example
 * phrases are derived from the clinical specification document.
 */

export type SafetyRiskCategory =
    | 'suicidal_intent'
    | 'suicidal_ideation'
    | 'planning'
    | 'self_harm'
    | 'hopelessness'
    | 'worthlessness'
    | 'severe_distress';

export interface SafetyCheckResult {
    /** True if credible high-risk language was identified. */
    isCrisis: boolean;
    /** Which risk category triggered the check, if any. */
    category?: SafetyRiskCategory;
}

/**
 * Crisis guidance text shown to the user when high-risk language is detected.
 * Source: AnxioSense supervisory guidance (July 2026).
 */
export const CRISIS_RESPONSE_TEXT =
    'Your responses suggest that you may be experiencing a mental health crisis. ' +
    'This screening cannot provide emergency care. ' +
    'Please contact your local emergency services, go to the nearest emergency department, ' +
    'or reach out to a trusted crisis service or healthcare professional immediately. ' +
    'If you are in immediate danger, call your local emergency number now.';

// ── Risk pattern registry ─────────────────────────────────────────────────────
// Patterns are ordered from most-specific (intent/planning) to least-specific
// so that the category logged reflects the highest-severity signal detected.

const RISK_PATTERNS: Array<{ category: SafetyRiskCategory; patterns: RegExp[] }> = [
    {
        // Explicit statements of intent to die by suicide
        category: 'suicidal_intent',
        patterns: [
            /\bi('ve| have) decided to (kill|end|take)\b.*\b(myself|my life)\b/i,
            /\bi (will|am going to|plan to|intend to) (kill|end|take)\b.*\b(myself|my life)\b/i,
            /\bkill myself\b/i,
            /\bend my (own )?life\b/i,
            /\btake my (own )?life\b/i,
            /\bsuicide (attempt|plan|note)\b/i,
        ],
    },
    {
        // Thoughts about suicide without explicit stated intent
        category: 'suicidal_ideation',
        patterns: [
            /\b(thinking about|thoughts? of|considered|contemplat(ing|ed)) (suicide|killing myself|ending (my life|it all|everything))\b/i,
            /\bwant(ed|s)? to (die|not (be here|exist|live anymore))\b/i,
            /\bwish(ed|es)? (i was|i were|to be) dead\b/i,
            /\bbetter off dead\b/i,
            /\bno reason (left )?to (live|keep going|continue)\b/i,
            /\bending (it|it all|everything) (feels?|seems?|would be)\b/i,
            /\b(there is|there's) no point (anymore|in (going on|living|continuing))\b/i,
            /\bno point (in|to) (living|going on|being here|existing)\b/i,
        ],
    },
    {
        // Evidence of a specific plan or method
        category: 'planning',
        patterns: [
            /\b(know|figured out|decided) how (i would|i('d| would)|to) do it\b/i,
            /\b(have|got) (a )?(plan|method|means|way) (to end|for ending|to kill|for killing)\b/i,
            /\b(stockpil|collect|gather)(ing|ed)? .{0,30}(pill|medication|weapon|knife|gun|rope|belt)\b/i,
        ],
    },
    {
        // Active self-harm behaviour
        category: 'self_harm',
        patterns: [
            /\b(hurting|cutting|harming|injuring|burning|scratching|hitting) (myself|my (skin|arms?|wrists?|legs?|body|thighs?))\b/i,
            /\bself[- ]harm(ing|ed)?\b/i,
            /\bi (have been|have|am|was|keep) (hurting|cutting|harming|burning|injuring) myself\b/i,
            /\bcut(ting)? (myself|my (arms?|wrists?|skin|thighs?))\b/i,
        ],
    },
    {
        // Expressions of hopelessness (no future / no way out)
        category: 'hopelessness',
        patterns: [
            /\b(there is|there's|it's|it is) no (hope|point|use|way out|future) (left|anymore|for me)\b/i,
            /\bnothing (will|can|is going to|ever gets?) (get )?better\b/i,
            /\bno (hope|future|way out|reason) (left|anymore|for me)\b/i,
            /\bcan('t| not) (go on|keep going|continue|do this) (anymore|any longer|like this)\b/i,
        ],
    },
    {
        // Statements of worthlessness / being a burden
        category: 'worthlessness',
        patterns: [
            /\beveryone (would be|will be|is|would) better off without me\b/i,
            /\b(i am|i'm|i feel|feel(ing|s)?) (worthless|useless|like a burden|a burden to (everyone|my family|others))\b/i,
            /\bno[- ]?one (would|will) (miss|notice|care( about)?) (if i (was|were|am) gone|me( being gone)?)\b/i,
            /\b(nobody|no[- ]?one) (needs|wants|cares( about)?) me\b/i,
        ],
    },
    {
        // Expressions of severe emotional distress / inability to cope
        category: 'severe_distress',
        patterns: [
            /\b(i can'?t|i cannot|can no longer) cope (anymore|any longer|with (this|everything|life))?\b/i,
            /\b(i can'?t|i cannot) (take|handle|bear|stand|go through) this (anymore|any (more|longer))\b/i,
            /\b(completely|totally|absolutely|utterly) (overwhelmed|hopeless|desperate|broken|lost)\b/i,
            /\b(don'?t|do not) want to (be here|exist|go on) (anymore|any longer)\b/i,
        ],
    },
];

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Checks free-text input for credible high-risk language.
 *
 * @param text  The raw or pre-processed user submission.
 * @returns     SafetyCheckResult — { isCrisis: false } if no risk signals found,
 *              or { isCrisis: true, category } if a risk pattern was matched.
 */
export function checkSafety(text: string): SafetyCheckResult {
    for (const { category, patterns } of RISK_PATTERNS) {
        for (const pattern of patterns) {
            if (pattern.test(text)) {
                console.log(`[safety] High-risk language detected — category: ${category}`);
                return { isCrisis: true, category };
            }
        }
    }
    return { isCrisis: false };
}

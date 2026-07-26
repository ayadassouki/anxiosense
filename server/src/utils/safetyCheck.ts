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
 *
 * ── Long-input handling ──────────────────────────────────────────────────────
 * Submissions are capped at 5,000 characters by validateText. A single regex pass
 * over the whole string already finds risk language regardless of where it sits,
 * so position was never the problem. Two structural issues were, both measured:
 *
 *   1. `.` does not match a newline, so a risk phrase broken across a line break
 *      was missed ("stockpiling my\nmedication" was not detected, the same phrase
 *      on one line was). Longer entries contain more line breaks, so the miss rate
 *      rose with length. Gaps that may legitimately span lines now use [\s\S].
 *
 *   2. Two intent patterns used an unbounded `.*`, which bridges an entire line.
 *      The same benign sentence was safe at 227 characters and classified as
 *      `suicidal_intent` at 274, purely because a later clause containing
 *      "myself" joined the same line. Those gaps are now bounded, and the verb
 *      "take" was removed from both (see INTENT_GAP below).
 *
 * Text is additionally evaluated in overlapping chunks so that per-chunk evidence
 * is available and no pattern can be severed at a boundary. Chunking is evidence
 * gathering — the sensitivity fixes come from the pattern changes above.
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
 * Result of a chunked evaluation. Carries counts only — never chunk text,
 * matched substrings, or any part of the submission.
 */
export interface DeepSafetyResult extends SafetyCheckResult {
    /** Distinct categories found, ordered most severe first. */
    categories: SafetyRiskCategory[];
    /** Number of (chunk × category) hits across the whole evaluation. */
    matchCount: number;
    /** Number of chunks evaluated across the whole evaluation. */
    chunkCount: number;
    /** How many distinct texts were scanned (1 when raw and processed are identical). */
    scannedTexts: number;
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

// ── Severity ranking ──────────────────────────────────────────────────────────

/**
 * Explicit clinical severity ranking, 1 = most severe.
 *
 * Previously the returned category was whichever appeared first in the pattern
 * registry, which is an array-ordering accident rather than a clinical decision:
 * text containing both ideation and a stated plan returned `suicidal_ideation`,
 * under-reporting the presence of a method. Ranking is now declared here so it
 * can be reviewed and changed on clinical grounds, and is covered by tests.
 *
 * `planning` outranks `suicidal_ideation` because evidence of a method or means
 * is a higher acute-risk indicator than ideation alone. Adjust deliberately.
 */
export const SEVERITY_RANK: Record<SafetyRiskCategory, number> = {
    suicidal_intent:   1,
    planning:          2,
    suicidal_ideation: 3,
    self_harm:         4,
    hopelessness:      5,
    worthlessness:     6,
    severe_distress:   7,
};

/** Rank of the most severe category — used to short-circuit further scanning. */
const TOP_RANK = 1;

// ── Chunking configuration ────────────────────────────────────────────────────

/** Target maximum chunk length in characters. */
export const CHUNK_SIZE = 800;

/**
 * Overlap between consecutive chunks. Must exceed MAX_PATTERN_SPAN so that no
 * risk phrase can be severed by a chunk boundary.
 */
export const CHUNK_OVERLAP = 200;

/**
 * Longest span any single pattern can match, used to justify CHUNK_OVERLAP.
 * The widest patterns are the bounded intent gap (~50 chars including the
 * surrounding words) and the planning gap (~50). 120 is a deliberate margin.
 */
export const MAX_PATTERN_SPAN = 120;

// ── Risk pattern registry ─────────────────────────────────────────────────────
//
// Registry order is preserved from the original implementation for readability.
// It no longer determines which category is returned — SEVERITY_RANK does.
//
// Whitespace convention: separators between words use \s+ so that a phrase
// broken across a line break is still detected. Gaps that may contain
// intervening words use [\s\S]{0,N} — never `.` (which stops at a newline) and
// never unbounded `.*`.

/**
 * Maximum characters permitted between the verb and its object in the two
 * "stated intent" patterns.
 *
 * Was `.*` (unbounded within a line), which produced measured false positives on
 * ordinary self-care language. 20 characters admits the genuine constructions
 * ("decided to end my life" = 1, "decided to end it all myself" = 8) while
 * excluding clause-length bridges.
 *
 * The verb "take" was also removed from both alternations. Bounding alone was
 * insufficient: "I am going to take a long walk by myself" has a 16-character
 * gap and "I am going to take care of myself" has 9, so both survived any bound
 * loose enough to be useful. No coverage is lost — "take my life" and "take my
 * own life" are matched by their own dedicated pattern below.
 */
const INTENT_GAP = '[\\s\\S]{0,20}';

const RISK_PATTERNS: Array<{ category: SafetyRiskCategory; patterns: RegExp[] }> = [
    {
        // Explicit statements of intent to die by suicide
        category: 'suicidal_intent',
        patterns: [
            new RegExp(`\\bi('ve|\\s+have)\\s+decided\\s+to\\s+(kill|end)\\b${INTENT_GAP}\\b(myself|my\\s+(own\\s+)?life)\\b`, 'i'),
            new RegExp(`\\bi\\s+(will|am\\s+going\\s+to|plan\\s+to|intend\\s+to)\\s+(kill|end)\\b${INTENT_GAP}\\b(myself|my\\s+(own\\s+)?life)\\b`, 'i'),
            /\bkill\s+myself\b/i,
            /\bend\s+my\s+(own\s+)?life\b/i,
            /\btake\s+my\s+(own\s+)?life\b/i,
            /\bsuicide\s+(attempt|plan|note)\b/i,
        ],
    },
    {
        // Thoughts about suicide without explicit stated intent
        category: 'suicidal_ideation',
        patterns: [
            /\b(thinking\s+about|thoughts?\s+of|considered|contemplat(ing|ed))\s+(suicide|killing\s+myself|ending\s+(my\s+life|it\s+all|everything))\b/i,
            /\bwant(ed|s)?\s+to\s+(die|not\s+(be\s+here|exist|live\s+anymore))\b/i,
            /\bwish(ed|es)?\s+(i\s+was|i\s+were|to\s+be)\s+dead\b/i,
            /\bbetter\s+off\s+dead\b/i,
            /\bno\s+reason\s+(left\s+)?to\s+(live|keep\s+going|continue)\b/i,
            /\bending\s+(it|it\s+all|everything)\s+(feels?|seems?|would\s+be)\b/i,
            /\b(there\s+is|there's)\s+no\s+point\s+(anymore|in\s+(going\s+on|living|continuing))\b/i,
            /\bno\s+point\s+(in|to)\s+(living|going\s+on|being\s+here|existing)\b/i,
        ],
    },
    {
        // Evidence of a specific plan or method
        category: 'planning',
        patterns: [
            /\b(know|figured\s+out|decided)\s+how\s+(i\s+would|i('d|\s+would)|to)\s+do\s+it\b/i,
            /\b(have|got)\s+(a\s+)?(plan|method|means|way)\s+(to\s+end|for\s+ending|to\s+kill|for\s+killing)\b/i,
            // [\s\S] so the phrase survives a line break between verb and object.
            /\b(stockpil|collect|gather)(ing|ed)?\s+[\s\S]{0,30}(pill|medication|weapon|knife|gun|rope|belt)\b/i,
        ],
    },
    {
        // Active self-harm behaviour
        category: 'self_harm',
        patterns: [
            /\b(hurting|cutting|harming|injuring|burning|scratching|hitting)\s+(myself|my\s+(skin|arms?|wrists?|legs?|body|thighs?))\b/i,
            /\bself[-\s]harm(ing|ed)?\b/i,
            /\bi\s+(have\s+been|have|am|was|keep)\s+(hurting|cutting|harming|burning|injuring)\s+myself\b/i,
            /\bcut(ting)?\s+(myself|my\s+(arms?|wrists?|skin|thighs?))\b/i,
        ],
    },
    {
        // Expressions of hopelessness (no future / no way out)
        category: 'hopelessness',
        patterns: [
            /\b(there\s+is|there's|it's|it\s+is)\s+no\s+(hope|point|use|way\s+out|future)\s+(left|anymore|for\s+me)\b/i,
            /\bnothing\s+(will|can|is\s+going\s+to|ever\s+gets?)\s+(get\s+)?better\b/i,
            /\bno\s+(hope|future|way\s+out|reason)\s+(left|anymore|for\s+me)\b/i,
            /\bcan('t|\s+not)\s+(go\s+on|keep\s+going|continue|do\s+this)\s+(anymore|any\s+longer|like\s+this)\b/i,
        ],
    },
    {
        // Statements of worthlessness / being a burden
        category: 'worthlessness',
        patterns: [
            /\beveryone\s+(would\s+be|will\s+be|is|would)\s+better\s+off\s+without\s+me\b/i,
            /\b(i\s+am|i'm|i\s+feel|feel(ing|s)?)\s+(worthless|useless|like\s+a\s+burden|a\s+burden\s+to\s+(everyone|my\s+family|others))\b/i,
            /\bno[-\s]?one\s+(would|will)\s+(miss|notice|care(\s+about)?)\s+(if\s+i\s+(was|were|am)\s+gone|me(\s+being\s+gone)?)\b/i,
            /\b(nobody|no[-\s]?one)\s+(needs|wants|cares(\s+about)?)\s+me\b/i,
        ],
    },
    {
        // Expressions of severe emotional distress / inability to cope
        category: 'severe_distress',
        patterns: [
            /\b(i\s+can'?t|i\s+cannot|can\s+no\s+longer)\s+cope\s+(anymore|any\s+longer|with\s+(this|everything|life))?\b/i,
            /\b(i\s+can'?t|i\s+cannot)\s+(take|handle|bear|stand|go\s+through)\s+this\s+(anymore|any\s+(more|longer))\b/i,
            /\b(completely|totally|absolutely|utterly)\s+(overwhelmed|hopeless|desperate|broken|lost)\b/i,
            /\b(don'?t|do\s+not)\s+want\s+to\s+(be\s+here|exist|go\s+on)\s+(anymore|any\s+longer)\b/i,
        ],
    },
];

// ── Internal helpers ──────────────────────────────────────────────────────────

/**
 * Evaluates every category against a single span of text.
 * Returns the categories found — never the matched text.
 */
function scanSpan(text: string): SafetyRiskCategory[] {
    const found: SafetyRiskCategory[] = [];
    for (const { category, patterns } of RISK_PATTERNS) {
        for (const pattern of patterns) {
            if (pattern.test(text)) {
                found.push(category);
                break; // one hit per category is enough
            }
        }
    }
    return found;
}

/** Returns the most severe category from a list, or undefined when empty. */
function mostSevere(categories: SafetyRiskCategory[]): SafetyRiskCategory | undefined {
    if (categories.length === 0) return undefined;
    return categories.reduce((worst, current) =>
        SEVERITY_RANK[current] < SEVERITY_RANK[worst] ? current : worst
    );
}

/** Sorts categories most severe first. */
function bySeverity(categories: SafetyRiskCategory[]): SafetyRiskCategory[] {
    return [...categories].sort((a, b) => SEVERITY_RANK[a] - SEVERITY_RANK[b]);
}

// ── Chunking ──────────────────────────────────────────────────────────────────

/**
 * Splits text into overlapping, paragraph-aware chunks.
 *
 * Boundaries prefer a paragraph break, then a line break, in the latter part of
 * each window, so chunks align with the narrative structure of a journal entry.
 * Consecutive chunks always overlap by at least `overlap` characters, which
 * exceeds MAX_PATTERN_SPAN — so no risk phrase can be split across a boundary
 * and thereby escape detection.
 *
 * Text at or below `size` is returned as a single chunk, so short submissions
 * take exactly one scan and behave identically to the pre-chunking implementation.
 */
export function chunkText(
    text: string,
    size: number = CHUNK_SIZE,
    overlap: number = CHUNK_OVERLAP
): string[] {
    if (text.length <= size) return [text];

    const chunks: string[] = [];
    // Only consider a break in the latter 40% of the window, so chunks stay
    // reasonably full rather than collapsing to one short paragraph each.
    const earliestBreak = Math.floor(size * 0.6);
    let start = 0;

    while (start < text.length) {
        let end = Math.min(start + size, text.length);

        if (end < text.length) {
            const window = text.slice(start, end);
            const paragraphBreak = window.lastIndexOf('\n\n');
            const lineBreak = window.lastIndexOf('\n');
            const cut =
                paragraphBreak >= earliestBreak ? paragraphBreak + 2 :
                lineBreak      >= earliestBreak ? lineBreak + 1 :
                -1;
            if (cut > 0) end = start + cut;
        }

        chunks.push(text.slice(start, end));
        if (end >= text.length) break;

        // Step forward, always retaining `overlap` characters of context.
        // Math.max guarantees forward progress and so terminates.
        start = Math.max(start + 1, end - overlap);
    }

    return chunks;
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Checks free-text input for credible high-risk language.
 *
 * Retained with its original signature and semantics for existing callers and
 * tests. Every category is evaluated and the most severe is returned; for
 * single-category text — which is every existing test case — this is identical
 * to the previous first-match behaviour.
 *
 * @param text  The raw or pre-processed user submission.
 * @returns     SafetyCheckResult — { isCrisis: false } if no risk signals found,
 *              or { isCrisis: true, category } if a risk pattern was matched.
 */
export function checkSafety(text: string): SafetyCheckResult {
    const found = scanSpan(text);
    const category = mostSevere(found);
    if (!category) return { isCrisis: false };

    console.log(`[safety] High-risk language detected — category: ${category}`);
    return { isCrisis: true, category };
}

/**
 * Chunked evaluation of a single text.
 *
 * Every chunk is evaluated — scanning does not stop at the first hit — except
 * when the most severe category has already been found, at which point no
 * further chunk can raise the result.
 *
 * Emits no log line: callers log once via evaluateSafety so a long entry does
 * not produce one line per chunk. Returns counts only, never chunk content.
 */
export function checkSafetyChunked(
    text: string,
    options?: { size?: number; overlap?: number }
): DeepSafetyResult {
    const chunks = chunkText(text, options?.size ?? CHUNK_SIZE, options?.overlap ?? CHUNK_OVERLAP);

    const categories = new Set<SafetyRiskCategory>();
    let matchCount = 0;
    let evaluated = 0;

    for (const chunk of chunks) {
        evaluated++;
        const found = scanSpan(chunk);
        matchCount += found.length;
        for (const category of found) categories.add(category);

        // Nothing more severe can be found — stop early.
        const worst = mostSevere([...categories]);
        if (worst && SEVERITY_RANK[worst] === TOP_RANK) break;
    }

    const ordered = bySeverity([...categories]);
    return {
        isCrisis:     ordered.length > 0,
        category:     ordered[0],
        categories:   ordered,
        matchCount,
        chunkCount:   evaluated,
        scannedTexts: 1,
    };
}

/** Merges two chunked results, keeping the most severe category across both. */
function mergeSafetyResults(a: DeepSafetyResult, b: DeepSafetyResult): DeepSafetyResult {
    const ordered = bySeverity([...new Set([...a.categories, ...b.categories])]);
    return {
        isCrisis:     ordered.length > 0,
        category:     ordered[0],
        categories:   ordered,
        matchCount:   a.matchCount + b.matchCount,
        chunkCount:   a.chunkCount + b.chunkCount,
        scannedTexts: a.scannedTexts + b.scannedTexts,
    };
}

/**
 * Production entry point: evaluates both the raw submission and the
 * pre-processed text used by the analysis pipeline, and returns the union.
 *
 * The two differ when preAssess changed something — emoji replacement in either
 * mode, plus social-media normalisation. Scanning both closes the gap where a
 * risk signal is only expressible in one of the two forms. When the texts are
 * identical — the common journal-mode case — the second scan is skipped
 * entirely rather than repeated.
 *
 * Logs the category and counts only. Never logs chunk text, matched substrings,
 * or any part of the submission.
 */
export function evaluateSafety(rawText: string, processedText?: string): DeepSafetyResult {
    const rawResult = checkSafetyChunked(rawText);

    const needsSecondScan =
        processedText !== undefined && processedText !== rawText;

    const result = needsSecondScan
        ? mergeSafetyResults(rawResult, checkSafetyChunked(processedText))
        : rawResult;

    if (result.isCrisis) {
        console.log(
            `[safety] High-risk language detected — category: ${result.category} ` +
            `(categories: ${result.categories.length}, matches: ${result.matchCount}, ` +
            `chunks: ${result.chunkCount}, texts: ${result.scannedTexts})`
        );
    }

    return result;
}

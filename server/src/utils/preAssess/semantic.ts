/**
 * Semantic sufficiency checker for AnxioSense.
 *
 * After emoji replacement and social-media normalisation, checks whether the
 * text still contains enough meaningful content to warrant analysis. This
 * catches the residual gap cases that pass the rule-based validateText checks
 * (e.g. very short stopword-only phrases that happen to be ≥20 chars after
 * whitespace expansion).
 *
 * This is intentionally conservative: the threshold is low (2 content words)
 * to avoid false positives.  A caller may log a warning when
 * `semanticallySufficient === false` but it is up to the caller whether to
 * hard-reject the submission.
 *
 * A SemanticChecker interface is provided so the default implementation can be
 * swapped out in tests or future research iterations.
 */

// ── Stop-word list ─────────────────────────────────────────────────────────────

/** Common English function words that carry little standalone semantic weight. */
const STOPWORDS = new Set([
  'a', 'an', 'the', 'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it',
  'they', 'them', 'their', 'this', 'that', 'these', 'those', 'is', 'am', 'are', 'was',
  'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
  'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'on',
  'at', 'by', 'for', 'with', 'as', 'from', 'up', 'or', 'and', 'but', 'not', 'no',
  'nor', 'so', 'yet', 'both', 'either', 'neither', 'if', 'then', 'than', 'when',
  'where', 'who', 'which', 'how', 'what', 'why', 'all', 'any', 'each', 'few', 'more',
  'most', 'other', 'some', 'such', 'own', 'same', 'just', 'very', 'too', 'also',
  'here', 'there', 'now', 'then', 'again', 'once', 'about', 'into', 'through',
  'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
  'under', 'again', 'further', 'while', 'ok', 'okay', 'yes', 'yeah', 'no', 'nah',
  'oh', 'ah', 'um', 'uh', 'hmm', 'hey', 'hi', 'hello', 'bye', 'thanks', 'thank',
]);

// ── Semantic checker interface ─────────────────────────────────────────────────

export interface SemanticCheckResult {
  sufficient: boolean;
  /** Number of non-stopword content words found. */
  contentWordCount: number;
}

export interface SemanticChecker {
  check(text: string): SemanticCheckResult;
}

// ── Default implementation ────────────────────────────────────────────────────

/** Minimum content words required to consider text semantically sufficient. */
const MIN_CONTENT_WORDS = 2;

/**
 * Default semantic checker.
 *
 * Extracts tokens of ≥3 alpha characters (strips apostrophes so contractions
 * contribute their root), filters out stopwords, and counts what remains.
 */
export const defaultSemanticChecker: SemanticChecker = {
  check(text: string): SemanticCheckResult {
    // Normalise: strip apostrophes so "I'm" → "Im" (not counted) vs
    // "feeling" stays "feeling"; strip bracket labels from emoji replacement.
    const cleaned = text
      .replace(/\[[^\]]+\]/g, ' ')    // remove [emoji label] replacements
      .replace(/'/g, '')               // strip apostrophes
      .toLowerCase();

    const tokens = cleaned.match(/\b[a-z]{3,}\b/g) ?? [];
    const contentWords = tokens.filter(w => !STOPWORDS.has(w));

    return {
      sufficient: contentWords.length >= MIN_CONTENT_WORDS,
      contentWordCount: contentWords.length,
    };
  },
};

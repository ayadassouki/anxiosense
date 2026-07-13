/**
 * Post-report Grounding Evaluation for AnxioSense.
 *
 * IMPORTANT — what this module does and does NOT do:
 *
 *   ┌─ Inside the Mastra workflow (not this file) ────────────────────────────┐
 *   │  Evidence Validation Step: claim-level validation against the knowledge │
 *   │  base. Each agent claim is checked for KB support. Unsupported claims   │
 *   │  are filtered out before the report is generated. This is the primary   │
 *   │  quality gate on factual accuracy inside the AI pipeline.               │
 *   └─────────────────────────────────────────────────────────────────────────┘
 *
 *   ┌─ This file (server-side, post-workflow) ────────────────────────────────┐
 *   │  Grounding Evaluation: after the Mastra workflow returns a final report, │
 *   │  evaluateGrounding measures two complementary scores:                   │
 *   │                                                                         │
 *   │  1. Lexical score — 4-char root prefix matching of the user's key terms │
 *   │     against the report. Fast, interpretable, language-agnostic.         │
 *   │                                                                         │
 *   │  2. TF-IDF cosine similarity — weighted bag-of-words overlap between    │
 *   │     user text and report. Down-weights very common terms so rare,       │
 *   │     content-specific terms contribute more. Computed in pure JS with    │
 *   │     no additional dependencies.                                         │
 *   │                                                                         │
 *   │  A low score on either metric suggests the report may be too generic.  │
 *   │  Neither score guarantees hallucination detection or factual accuracy.  │
 *   │                                                                         │
 *   │  This is a RESEARCH METADATA utility. It does not prevent any report   │
 *   │  from reaching the user and does not modify report content.             │
 *   └─────────────────────────────────────────────────────────────────────────┘
 *
 * Output destinations:
 *   - Server console  ([groundingEval] log line)
 *   - _meta field of the HTTP response (inspectable via network dev tools)
 *
 * calibrateConfidence maps the numeric score to HIGH / MODERATE / LOW for
 * inclusion in evaluation export metadata.
 */

import type { GroundingReport } from './types.js';

// ── Stopwords ──────────────────────────────────────────────────────────────────

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
  'under', 'while',
]);

// ── Generic phrase list ────────────────────────────────────────────────────────

/**
 * Phrases that frequently appear in non-grounded / generic mental health text.
 * Their presence slightly lowers the lexical grounding score.
 */
const GENERIC_PHRASES: string[] = [
  'various feelings',
  'general wellbeing',
  'overall wellness',
  'holistic approach',
  'mental health journey',
  'feelings and experiences',
  'emotional wellbeing',
  'wide range of emotions',
  'variety of emotions',
  'general patterns',
  'emotional health',
  'mental wellbeing',
  'positive outlook',
  'self-care strategies',
  'coping mechanisms in general',
];

// ── Grounding score threshold ──────────────────────────────────────────────────

/** Minimum lexical score for a report to be considered grounded. */
const GROUNDING_THRESHOLD = 0.25;

// ── Key-term extraction ────────────────────────────────────────────────────────

/** Extract up to 20 deduplicated content-word key terms from text. */
function extractKeyTerms(text: string): string[] {
  const tokens = text
    .toLowerCase()
    .replace(/'/g, '')
    .match(/\b[a-z]{4,}\b/g) ?? [];
  const seen = new Set<string>();
  return tokens
    .filter(w => !STOPWORDS.has(w) && !seen.has(w) && seen.add(w))
    .slice(0, 20);
}

// ── TF-IDF cosine similarity ──────────────────────────────────────────────────

/**
 * Computes TF-IDF cosine similarity between two short texts.
 *
 * Down-weights terms that appear in both documents (common terms) and
 * up-weights terms unique to one document (specific/rare terms).
 * Operates entirely in memory with no external dependencies.
 *
 * Returns a value in [0, 1]: 1 = identical content, 0 = no overlap.
 */
function tfidfCosineSimilarity(textA: string, textB: string): number {
  // Tokenise: lowercase words ≥3 chars, stopwords removed
  const tokenize = (text: string): string[] =>
    (text.toLowerCase().replace(/'/g, '').match(/\b[a-z]{3,}\b/g) ?? [])
      .filter(w => !STOPWORDS.has(w));

  const tokensA = tokenize(textA);
  const tokensB = tokenize(textB);

  if (tokensA.length === 0 || tokensB.length === 0) return 0;

  // Term-frequency maps (raw counts)
  const tfA = new Map<string, number>();
  const tfB = new Map<string, number>();
  for (const t of tokensA) tfA.set(t, (tfA.get(t) ?? 0) + 1);
  for (const t of tokensB) tfB.set(t, (tfB.get(t) ?? 0) + 1);

  // Build vocabulary (union of both docs)
  const vocab = new Set([...tfA.keys(), ...tfB.keys()]);

  // N = 2 documents; IDF = ln(1 + N / df) — smooth to avoid log(0)
  const N = 2;

  let dot = 0, magA = 0, magB = 0;

  for (const term of vocab) {
    const df = (tfA.has(term) ? 1 : 0) + (tfB.has(term) ? 1 : 0);
    const idf = Math.log(1 + N / df);

    const tfidfA = ((tfA.get(term) ?? 0) / tokensA.length) * idf;
    const tfidfB = ((tfB.get(term) ?? 0) / tokensB.length) * idf;

    dot  += tfidfA * tfidfB;
    magA += tfidfA * tfidfA;
    magB += tfidfB * tfidfB;
  }

  if (magA === 0 || magB === 0) return 0;
  return Math.min(1, dot / (Math.sqrt(magA) * Math.sqrt(magB)));
}

// ── Public API ─────────────────────────────────────────────────────────────────

/**
 * Grounding Evaluation — measures how well the report references the user's
 * own content, using two complementary approaches:
 *
 * A. Lexical score (existing, unchanged):
 *    1. Extract up to 20 content-word key terms from userText.
 *    2. For each term, check for an exact match or a 4-char root prefix match
 *       in the report (e.g. "anxious" matches "anxiety" via shared prefix "anxi").
 *    3. Count generic filler phrases and apply a small penalty per phrase.
 *    4. lexicalScore = specificReferences / max(1, keyTermCount) − penalties
 *    5. passed = lexicalScore >= GROUNDING_THRESHOLD (0.25)
 *
 * B. TF-IDF cosine similarity (new):
 *    Weighted bag-of-words similarity between user text and report.
 *    Rare content terms contribute more than common terms.
 *    Provides a complementary signal when the model paraphrases rather than
 *    repeating the user's exact vocabulary.
 *
 * Neither score is semantic (synonym-aware) — they are both surface-level
 * approximations exposed as research metadata only.
 *
 * `score` (= lexicalScore) is unchanged from prior versions and drives `passed`.
 * `tfidfSimilarity` is a new supplementary field.
 */
export function evaluateGrounding(userText: string, report: string): GroundingReport {
  const keyTerms    = extractKeyTerms(userText);
  const reportLower = report.toLowerCase();

  // ── Lexical score (4-char prefix matching) ─────────────────────────────────
  // anxious  → anxiety  (shared prefix "anxi")
  // sleeping → sleep    (shared prefix "slee")
  // feeling  → felt     (shared prefix "feel")
  const specificReferences = keyTerms.filter(term => {
    if (reportLower.includes(term)) return true;
    if (term.length >= 5) {
      const prefix = term.slice(0, 4);
      return reportLower.includes(prefix);
    }
    return false;
  }).length;

  const genericPhraseCount = GENERIC_PHRASES.filter(phrase =>
    reportLower.includes(phrase.toLowerCase())
  ).length;

  const rawLexical    = specificReferences / Math.max(1, keyTerms.length);
  const penaltyPerPhrase = 0.05;
  const lexicalScore  = Math.max(0, Math.min(1, rawLexical - genericPhraseCount * penaltyPerPhrase));

  // ── TF-IDF cosine similarity ───────────────────────────────────────────────
  const tfidfSimilarity = tfidfCosineSimilarity(userText, report);

  return {
    // `score` keeps its original meaning (lexical) so existing callers and
    // tests are unaffected.
    score: lexicalScore,
    lexicalScore,
    tfidfSimilarity,
    specificReferences,
    genericPhraseCount,
    passed: lexicalScore >= GROUNDING_THRESHOLD,
  };
}

/**
 * Map a grounding evaluation score to a human-readable confidence label.
 *
 * Used in eval export metadata and the _meta HTTP response field.
 * Does NOT influence or modify the user-facing report.
 */
export function calibrateConfidence(groundingScore: number): 'HIGH' | 'MODERATE' | 'LOW' {
  if (groundingScore >= 0.6) return 'HIGH';
  if (groundingScore >= 0.3) return 'MODERATE';
  return 'LOW';
}

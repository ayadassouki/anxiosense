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
 *   │  Lexical Grounding Evaluation: after the Mastra workflow returns a      │
 *   │  final report, evaluateGrounding measures how many of the user's own    │
 *   │  key terms appear in the report. A low score suggests the report may    │
 *   │  be too generic — it does NOT guarantee hallucination or error.         │
 *   │                                                                         │
 *   │  This is a RESEARCH METADATA utility. It does not prevent any report    │
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

// ── Stopwords (reused from semantic.ts to avoid duplication) ──────────────────

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
 * When found in a report their presence slightly lowers the grounding score,
 * because they indicate the report may not be referencing the user's specific content.
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

/** Minimum score for a report to be considered lexically grounded. */
const GROUNDING_THRESHOLD = 0.25;

// ── Key-term extraction ────────────────────────────────────────────────────────

/** Extract up to 20 deduplicated content-word key terms from the user's text. */
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

// ── Public API ─────────────────────────────────────────────────────────────────

/**
 * Lexical Grounding Evaluation — measures how well the report references
 * the user's own content.
 *
 * Algorithm:
 * 1. Extract up to 20 content-word key terms from userText.
 * 2. For each term, check for an exact match or a 4-char root prefix match
 *    in the report (e.g. "anxious" matches "anxiety" via shared prefix "anxi").
 * 3. Count generic filler phrases and apply a small score penalty per phrase.
 * 4. score = specificReferences / max(1, keyTermCount) − penalties
 * 5. passed = score >= GROUNDING_THRESHOLD (0.25)
 *
 * Limitation: this is a lexical heuristic, not semantic similarity or
 * hallucination detection. A report that paraphrases the user's content
 * without repeating their exact vocabulary will score lower than its true
 * grounding warrants. Future work could use embedding similarity instead.
 */
export function evaluateGrounding(userText: string, report: string): GroundingReport {
  const keyTerms = extractKeyTerms(userText);
  const reportLower = report.toLowerCase();

  // 4-char prefix matching captures common inflections across roots:
  //   anxious  → anxiety  (shared prefix "anxi")
  //   sleeping → sleep    (shared prefix "slee")
  //   feeling  → felt     (shared prefix "feel")
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

  const rawScore = specificReferences / Math.max(1, keyTerms.length);
  const penaltyPerPhrase = 0.05;
  const score = Math.max(0, Math.min(1, rawScore - genericPhraseCount * penaltyPerPhrase));

  return {
    score,
    specificReferences,
    genericPhraseCount,
    passed: score >= GROUNDING_THRESHOLD,
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

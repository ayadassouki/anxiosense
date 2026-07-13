/**
 * Shared types for the AnxioSense pre-assessment pipeline.
 */

export type InputMode = 'journal' | 'social-media';

/**
 * Machine-readable reason codes for pre-assessment rejections.
 * Rule-based rejections (spam, length, etc.) are handled upstream by validateText.
 * This module adds only semantic-level reason codes.
 */
export type ReasonCode = 'INSUFFICIENT_SEMANTIC_CONTENT';

/** Output from the pre-assessment pipeline. */
export interface PreAssessOutput {
  /**
   * Text to pass to the Mastra workflow.
   * Semantically equivalent to the original but may have emoji replaced with
   * descriptions and social media artefacts normalised.
   */
  processedText: string;

  /**
   * True only when the pipeline itself decides to reject the submission.
   * Note: basic rule checks (spam, length…) have already run via validateText
   * before preAssess is called.
   */
  rejected: boolean;

  /** Machine-readable reason code, present only when rejected === true. */
  reasonCode?: ReasonCode;

  /** User-facing rejection message, present only when rejected === true. */
  message?: string;

  /** ISO 639-1 language code inferred from script / word analysis. */
  detectedLanguage: string;

  /** Confidence in the language detection, 0–1. */
  languageConfidence: number;

  /** True if at least one emoji was replaced with a semantic label. */
  emojiProcessed: boolean;

  /** True if social-media normalisation was applied (social-media mode only). */
  normalized: boolean;

  /** True if the text has sufficient semantic content for analysis. */
  semanticallySufficient: boolean;
}

/**
 * Result of the post-report Grounding Evaluation.
 *
 * This is research metadata — it does not affect what the user sees.
 * See grounding.ts for the distinction between this evaluation and the
 * Mastra workflow's in-process evidence validation step.
 *
 * Two complementary scores are provided:
 *   - lexicalScore: 4-char root-prefix matching (fast, language-agnostic)
 *   - tfidfSimilarity: TF-IDF weighted cosine similarity (content-aware)
 *
 * `score` equals `lexicalScore` for backwards compatibility.
 * `passed` is derived from `lexicalScore` >= 0.25.
 */
export interface GroundingReport {
  /**
   * Primary grounding score in [0, 1]. Equals lexicalScore.
   * Kept for backwards compatibility with existing callers and tests.
   */
  score: number;
  /** Fraction of user key-terms found in the report via 4-char root prefix matching. */
  lexicalScore: number;
  /** TF-IDF cosine similarity between user text and report in [0, 1]. */
  tfidfSimilarity: number;
  /** Number of user key-terms found in the report (exact or root-prefix match). */
  specificReferences: number;
  /** Number of generic/filler phrases detected in the report. */
  genericPhraseCount: number;
  /** True when lexicalScore >= GROUNDING_THRESHOLD (0.25). */
  passed: boolean;
}

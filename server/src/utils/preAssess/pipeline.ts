/**
 * Pre-assessment pipeline orchestrator for AnxioSense.
 *
 * Sits between input validation (validateText) and the Mastra workflow call.
 * It does NOT replace validateText — it receives text that has already passed
 * all rule-based checks.
 *
 * Steps (in order):
 *  1. Emoji replacement      (emoji.ts)
 *  2. Language detection     (language.ts)
 *  3. Social-media normalisation  (normalize.ts)
 *  4. Semantic sufficiency check  (semantic.ts)
 *  5. PII-safe logging       (logger.ts)
 *
 * Returns a PreAssessOutput whose `processedText` field replaces the raw
 * userText in the Mastra workflow call.
 *
 * Semantic rejection applies only to English submissions — the sufficiency checker
 * is English-only (ASCII regex). Non-English text passes through to the Mastra
 * workflow regardless of the semantic check result. Set REJECT_INSUFFICIENT=false
 * to disable rejection even for English (development / A/B evaluation).
 */

import { replaceEmoji } from './emoji.js';
import { detectLanguage } from './language.js';
import { normalizeSocialMedia } from './normalize.js';
import { defaultSemanticChecker } from './semantic.js';
import { hashText, logPreAssess } from './logger.js';
import type { InputMode, PreAssessOutput } from './types.js';

/**
 * Run the pre-assessment pipeline on validated user text.
 *
 * @param text  Raw (already validated) user text
 * @param mode  'journal' | 'social-media'
 * @returns     PreAssessOutput with processedText and quality metadata
 */
export async function preAssess(text: string, mode: InputMode): Promise<PreAssessOutput> {
  // ── Step 1: Emoji replacement ──────────────────────────────────────────
  const { result: emojiText, changed: emojiProcessed } = replaceEmoji(text);

  // ── Step 2: Language detection (on emoji-replaced text, before normalisation) ──
  const { language: detectedLanguage, confidence: languageConfidence } = detectLanguage(emojiText);

  // ── Step 3: Social-media normalisation ────────────────────────────────
  const { result: processedText, changed: normalized } = normalizeSocialMedia(emojiText, mode);

  // ── Step 4: Semantic sufficiency ──────────────────────────────────────
  const { sufficient: semanticallySufficient, contentWordCount } =
    defaultSemanticChecker.check(processedText);

  // Log a warning when semantic content is borderline but not rejected
  if (!semanticallySufficient) {
    console.warn(
      `[preAssess] Low semantic content: contentWordCount=${contentWordCount}, mode=${mode}, lang=${detectedLanguage}`
    );
  }

  // ── Step 5: Determine rejection ───────────────────────────────────────
  // The semantic sufficiency checker uses an ASCII [a-z] regex and cannot
  // evaluate non-Latin scripts (Arabic, CJK, Cyrillic, etc.).  Applying the
  // English-only check to those submissions would always produce
  // contentWordCount = 0 and incorrectly reject valid non-English input.
  //
  // Policy: hard semantic rejection only applies when the detected language is
  // English.  For all other languages the check result is logged for
  // observability but the submission is allowed through to the Mastra workflow.
  //
  // Set REJECT_INSUFFICIENT=false to disable rejection even for English
  // (useful during development or A/B evaluation).
  const isEnglish = detectedLanguage === 'en';
  const hardRejectInsufficient = isEnglish && process.env.REJECT_INSUFFICIENT !== 'false';
  const rejected = hardRejectInsufficient && !semanticallySufficient;

  // ── Step 6: PII-safe logging ──────────────────────────────────────────
  logPreAssess({
    ts: new Date().toISOString(),
    hash: hashText(text),
    len: text.length,
    mode,
    lang: detectedLanguage,
    langConf: parseFloat(languageConfidence.toFixed(3)),
    emoji: emojiProcessed,
    normalized,
    semantic: semanticallySufficient,
    rejected,
    ...(rejected ? { reasonCode: 'INSUFFICIENT_SEMANTIC_CONTENT' } : {}),
  });

  if (rejected) {
    return {
      processedText: text, // return original — caller will reject anyway
      rejected: true,
      reasonCode: 'INSUFFICIENT_SEMANTIC_CONTENT',
      message:
        'Your submission does not appear to contain enough descriptive content. ' +
        'Please describe how you have been feeling in your own words.',
      detectedLanguage,
      languageConfidence,
      emojiProcessed,
      normalized,
      semanticallySufficient,
    };
  }

  return {
    processedText,
    rejected: false,
    detectedLanguage,
    languageConfidence,
    emojiProcessed,
    normalized,
    semanticallySufficient,
  };
}

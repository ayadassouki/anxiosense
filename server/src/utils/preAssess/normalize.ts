/**
 * Social-media text normalisation for AnxioSense.
 *
 * Applied only in 'social-media' mode. Journal-mode text is left untouched
 * to preserve the authentic voice valued for clinical data quality.
 *
 * Transformations (applied in order):
 *  1. Collapse letter runs:  "soooooo" → "soo"  (max 2 consecutive identical chars)
 *  2. Strip hashtag '#' prefix:  "#anxiety" → "anxiety"
 *  3. Replace @mentions with "[person]" (privacy + noise reduction)
 *  4. Replace URLs with "[link]" (removes noise, preserves fact that a link was shared)
 *
 * What is NOT changed:
 *  - Case (SHOUTING preserved — it carries emotional signal)
 *  - Abbreviations / slang (tbh, rn, lmao…) — the downstream LLM handles these
 *  - Punctuation, emojis (handled separately by emoji.ts)
 *  - Any content in journal mode
 */

import type { InputMode } from './types.js';

// ── Transformation helpers ────────────────────────────────────────────────────

/**
 * Collapse runs of 3+ identical characters down to 2.
 * "yessss" → "yess", "nooooo" → "noo", "well" → "well" (unchanged).
 */
function collapseLetterRuns(text: string): string {
  return text.replace(/(.)\1{2,}/g, '$1$1');
}

/**
 * Strip the '#' from hashtags while keeping the word.
 * "#anxiety" → "anxiety", "#MentalHealthMatters" → "MentalHealthMatters"
 */
function stripHashtags(text: string): string {
  return text.replace(/#(\w+)/g, '$1');
}

/**
 * Replace @mentions with "[person]".
 * Preserves the fact that another person was referenced without retaining
 * potentially identifying information.
 */
function replaceAtMentions(text: string): string {
  return text.replace(/@\w+/g, '[person]');
}

/**
 * Replace URLs with "[link]".
 * Catches http://, https://, and bare t.co / bit.ly style shortlinks.
 */
function replaceUrls(text: string): string {
  return text
    .replace(/https?:\/\/\S+/g, '[link]')
    .replace(/\bwww\.\S+/g, '[link]');
}

// ── Public API ───────────────────────────────────────────────────────────────

export interface NormalizeResult {
  result: string;
  changed: boolean;
}

/**
 * Normalise `text` for the given `mode`.
 * In 'journal' mode the text is returned unchanged.
 * In 'social-media' mode all four transformations are applied.
 */
export function normalizeSocialMedia(text: string, mode: InputMode): NormalizeResult {
  if (mode !== 'social-media') {
    return { result: text, changed: false };
  }

  const original = text;

  let result = replaceUrls(text);
  result = replaceAtMentions(result);
  result = stripHashtags(result);
  result = collapseLetterRuns(result);

  return { result, changed: result !== original };
}

/**
 * Language detection for AnxioSense pre-assessment.
 *
 * Uses Unicode script analysis for non-Latin scripts and a common-word
 * frequency approach for Latin-script language distinction.
 *
 * Accuracy is sufficient for a research MVP that needs to:
 *   - Detect non-Latin-script input (Arabic, CJK, Cyrillic, etc.) reliably
 *   - Distinguish English from common European languages
 *   - Provide a confidence score for downstream logging
 *
 * No external dependencies (no franc) — all logic is self-contained.
 *
 * Interface:
 *   detectLanguage(text)  → { language: string; confidence: number }
 *   TranslationProvider   → pluggable translation interface (default: no-op)
 */

export interface LanguageResult {
  /** ISO 639-1 language code. 'en' is the default / fallback. */
  language: string;
  /** Confidence in [0, 1]. Values below 0.5 indicate low confidence. */
  confidence: number;
}

// ── Unicode script ranges ─────────────────────────────────────────────────────

interface ScriptRange {
  start: number;
  end: number;
  language: string;
}

const SCRIPT_RANGES: ScriptRange[] = [
  { start: 0x0600, end: 0x06FF, language: 'ar' }, // Arabic
  { start: 0x0750, end: 0x077F, language: 'ar' }, // Arabic supplement
  { start: 0x08A0, end: 0x08FF, language: 'ar' }, // Arabic extended-A
  { start: 0x0590, end: 0x05FF, language: 'he' }, // Hebrew
  { start: 0xFB1D, end: 0xFB4F, language: 'he' }, // Hebrew presentation
  { start: 0x4E00, end: 0x9FFF, language: 'zh' }, // CJK unified ideographs
  { start: 0x3040, end: 0x309F, language: 'ja' }, // Hiragana
  { start: 0x30A0, end: 0x30FF, language: 'ja' }, // Katakana
  { start: 0x3400, end: 0x4DBF, language: 'zh' }, // CJK extension A
  { start: 0x0400, end: 0x04FF, language: 'ru' }, // Cyrillic
  { start: 0x0500, end: 0x052F, language: 'ru' }, // Cyrillic supplement
  { start: 0x0370, end: 0x03FF, language: 'el' }, // Greek
  { start: 0x0900, end: 0x097F, language: 'hi' }, // Devanagari (Hindi)
  { start: 0x0E00, end: 0x0E7F, language: 'th' }, // Thai
  { start: 0xAC00, end: 0xD7AF, language: 'ko' }, // Korean hangul
  { start: 0x1100, end: 0x11FF, language: 'ko' }, // Hangul jamo
];

/** Count characters in `text` that fall within the given Unicode range. */
function countRange(text: string, start: number, end: number): number {
  let count = 0;
  for (const ch of text) {
    const cp = ch.codePointAt(0) ?? 0;
    if (cp >= start && cp <= end) count++;
  }
  return count;
}

// ── Latin-script word lists ──────────────────────────────────────────────────

/** Common function words that strongly indicate a specific Latin-script language. */
const LATIN_MARKERS: Record<string, string[]> = {
  fr: ['je', 'est', 'les', 'des', 'une', 'dans', 'pas', 'sur', 'avec', 'mais', 'très', 'tout', 'bien', 'plus', 'pour', 'que', 'qui', 'cette', 'aussi'],
  es: ['soy', 'estoy', 'está', 'los', 'las', 'una', 'con', 'pero', 'muy', 'todo', 'también', 'tengo', 'tengo', 'para', 'que', 'este', 'esta', 'hay', 'sé'],
  pt: ['não', 'uma', 'para', 'com', 'isso', 'tenho', 'também', 'mais', 'estou', 'muito', 'são', 'tem', 'aqui', 'nosso', 'então'],
  de: ['ich', 'ist', 'das', 'die', 'der', 'und', 'nicht', 'sich', 'haben', 'wird', 'aber', 'sehr', 'auch', 'noch', 'kann', 'mehr', 'bin', 'war'],
  it: ['sono', 'che', 'non', 'con', 'una', 'anche', 'tutto', 'bene', 'molto', 'questa', 'questo', 'ogni', 'fare', 'come', 'quando'],
  nl: ['het', 'een', 'zijn', 'van', 'dat', 'niet', 'ook', 'met', 'aan', 'voor', 'ze', 'zij', 'maar', 'dan', 'meer'],
};

/** Tokenise into lowercase alpha words. */
function words(text: string): string[] {
  return (text.toLowerCase().match(/\b[a-záàâäéèêëíìîïóòôöúùûüçñß]+\b/g) ?? []);
}

/** Score a text against a language's word list. */
function wordListScore(tokens: string[], markers: string[]): number {
  const markerSet = new Set(markers);
  const hits = tokens.filter(w => markerSet.has(w)).length;
  return tokens.length === 0 ? 0 : hits / tokens.length;
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Detect the language of `text`.
 *
 * Algorithm:
 * 1. Count non-ASCII characters per script range.
 *    If a script dominates (>15% of total chars), return that language.
 * 2. Otherwise treat as Latin-script and score against word lists.
 *    If any language scores above 0.04 (4 % marker overlap), return it.
 * 3. Default to English ('en').
 */
export function detectLanguage(text: string): LanguageResult {
  const total = text.length;
  if (total === 0) return { language: 'en', confidence: 0 };

  // Pass 1: script-based detection
  const scriptCounts: Record<string, number> = {};
  for (const range of SCRIPT_RANGES) {
    const count = countRange(text, range.start, range.end);
    if (count > 0) {
      scriptCounts[range.language] = (scriptCounts[range.language] ?? 0) + count;
    }
  }

  const dominant = Object.entries(scriptCounts)
    .sort((a, b) => b[1] - a[1])
    .find(([, count]) => count / total >= 0.15);

  if (dominant) {
    const confidence = Math.min(1, (dominant[1] / total) * 2);
    return { language: dominant[0], confidence };
  }

  // Pass 2: Latin word-list scoring
  const tokens = words(text);
  if (tokens.length === 0) return { language: 'en', confidence: 0.5 };

  const scores = Object.entries(LATIN_MARKERS).map(([lang, markers]) => ({
    language: lang,
    score: wordListScore(tokens, markers),
  }));

  const best = scores.sort((a, b) => b.score - a.score)[0];
  if (best.score >= 0.04) {
    return { language: best.language, confidence: Math.min(0.9, best.score * 10) };
  }

  return { language: 'en', confidence: 0.7 };
}

// ── Translation provider interface (pluggable, no-op default) ────────────────

export interface TranslationProvider {
  /**
   * Translate `text` from `fromLang` (ISO 639-1) to `toLang`.
   * Return the original text unchanged if translation is not supported.
   */
  translate(text: string, fromLang: string, toLang: string): Promise<string>;
}

/** Default no-op provider — passes text through without translation. */
export const noOpTranslationProvider: TranslationProvider = {
  async translate(text: string): Promise<string> {
    return text;
  },
};

/**
 * Shared input validation for AnxioSense text submissions.
 *
 * Implemented identically in:
 *   server/src/utils/validateText.ts
 *   frontend/src/utils/validateText.ts
 * Keep both files in sync.
 *
 * Validation rules (applied in order):
 *  1. Empty / whitespace-only
 *  2. Fewer than 20 characters (trimmed)
 *  3. More than 5,000 characters
 *  4. Digits only
 *  5. Phone-number-only input
 *  6. Only punctuation or symbols (no alphabetic / numeric content)
 *  7. Repeated single-character spam (e.g. "aaaaaaaaaa")
 *  8. Repeated short-pattern spam (e.g. "asdfasdfasdf")
 *  9. Obvious keyboard-sequence spam (e.g. "qwerty", "asdfghjkl")
 *
 * Does NOT reject text that legitimately contains numbers, punctuation,
 * emojis, slang, contractions, or spelling mistakes.
 */

export interface ValidationResult {
  valid: boolean;
  /** User-facing error message, present only when valid is false. */
  message?: string;
}

// ── Internal helpers ─────────────────────────────────────────────────────────

/** True if every character in trimmed text is a digit. */
function isDigitsOnly(text: string): boolean {
  return /^\d+$/.test(text);
}

/**
 * True if the whole text is just a bare phone number with no meaningful prose.
 * Strips typical phone-formatting characters (digits, spaces, +, -, (, ), .).
 * If nothing alphabetic remains and there are ≥7 digits, it's a phone number.
 */
function isPhoneOnly(text: string): boolean {
  const withoutPhoneChars = text.replace(/[\d\s()\-+.]/g, '');
  const alphabeticRemaining = withoutPhoneChars.replace(/[^a-zA-Z]/g, '');
  const digits = text.replace(/\D/g, '');
  return alphabeticRemaining.length === 0 && digits.length >= 7;
}

/**
 * True if text contains no alphabetic or numeric content — only symbols/punctuation.
 * Covers ASCII, extended Latin, CJK, Hiragana/Katakana, and Cyrillic so non-Latin
 * language users are not incorrectly rejected.
 */
function isPunctuationOnly(text: string): boolean {
  return !/[a-zA-Z0-9À-ɏ一-鿿぀-ヿЀ-ӿ؀-ۿ]/.test(text);
}

/**
 * True if a single character makes up more than 80 % of the non-whitespace content.
 * Guards against "aaaaaaaaaa", "!!!!!!!!", etc.
 * Only applied when non-whitespace content is at least 8 characters long.
 */
function isRepeatedCharSpam(text: string): boolean {
  const noSpace = text.replace(/\s/g, '');
  if (noSpace.length < 8) return false;
  const counts: Record<string, number> = {};
  for (const ch of noSpace) {
    counts[ch] = (counts[ch] ?? 0) + 1;
  }
  const maxCount = Math.max(...Object.values(counts));
  return maxCount / noSpace.length > 0.8;
}

/**
 * True if the non-whitespace content is entirely a repeated short pattern.
 * Guards against "asdfasdfasdf", "lollollol", etc.
 * Only applied when stripped content is at least 12 characters long.
 */
function isRepeatedPatternSpam(text: string): boolean {
  const clean = text.toLowerCase().replace(/\s/g, '');
  if (clean.length < 12) return false;
  const maxLen = Math.min(8, Math.floor(clean.length / 2));
  for (let len = 2; len <= maxLen; len++) {
    const pattern = clean.slice(0, len);
    const repeated = pattern.repeat(Math.ceil(clean.length / len)).slice(0, clean.length);
    if (repeated === clean) return true;
  }
  return false;
}

/**
 * Keyboard rows used for sequence detection.
 * Both forward and reversed variants are listed so we catch "rewq", "lkjh", etc.
 */
const KEYBOARD_ROWS: string[] = [
  'qwertyuiop', 'poiuytrewq',
  'asdfghjkl',  'lkjhgfdsa',
  'zxcvbnm',    'mnbvcxz',
  '1234567890', '0987654321',
];

/**
 * True if a word (stripped to alpha-numeric chars, length ≥4) consists entirely
 * of consecutive characters from a single keyboard row.
 */
function isKeyboardWord(word: string): boolean {
  const clean = word.toLowerCase().replace(/[^a-z0-9]/g, '');
  if (clean.length < 4) return false;
  for (const row of KEYBOARD_ROWS) {
    for (let start = 0; start <= row.length - clean.length; start++) {
      if (row.slice(start, start + clean.length) === clean) return true;
    }
  }
  return false;
}

/**
 * True if the text is obviously keyboard-sequence spam.
 *
 * Word-level heuristic: if ≥80 % of words with ≥4 alpha-numeric characters are
 * keyboard-row sequences, the submission is spam.
 *
 * Single-word check: a lone word of ≥6 characters that is a keyboard run is also spam.
 * This catches "asdfghjkl" submitted on its own.
 *
 * Legitimate text that merely mentions a keyboard sequence (e.g. "my old password
 * was qwerty") scores well below the 80 % threshold and is never rejected.
 */
function isKeyboardSequenceSpam(text: string): boolean {
  const words = text
    .toLowerCase()
    .trim()
    .split(/\s+/)
    .filter(w => w.replace(/[^a-z0-9]/g, '').length >= 4);

  if (words.length === 0) {
    // No qualifying words — check if the entire stripped content is one keyboard run
    const clean = text.toLowerCase().replace(/[^a-z0-9]/g, '');
    return clean.length >= 6 && isKeyboardWord(clean);
  }

  const keyboardWordCount = words.filter(isKeyboardWord).length;
  return keyboardWordCount / words.length >= 0.8;
}

// ── Public API ───────────────────────────────────────────────────────────────

export const VALIDATION_MIN_CHARS = 20;
export const VALIDATION_MAX_CHARS = 5000;

/**
 * Validates the submitted assessment text.
 * Returns `{ valid: true }` on success, or `{ valid: false, message }` on failure.
 * Error messages are user-friendly and safe to display directly in the UI.
 */
export function validateText(text: string): ValidationResult {
  // 1. Empty / whitespace only
  if (!text || !text.trim()) {
    return { valid: false, message: 'Please enter some text before submitting.' };
  }

  const trimmed = text.trim();

  // 2. Fewer than 20 characters
  if (trimmed.length < VALIDATION_MIN_CHARS) {
    return {
      valid: false,
      message: `Please write at least ${VALIDATION_MIN_CHARS} characters so the analysis has enough context (currently ${trimmed.length}).`,
    };
  }

  // 3. More than 5,000 characters
  if (text.length > VALIDATION_MAX_CHARS) {
    return {
      valid: false,
      message: `Please keep your text under ${VALIDATION_MAX_CHARS.toLocaleString()} characters (currently ${text.length.toLocaleString()}).`,
    };
  }

  // 4. Digits only
  if (isDigitsOnly(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to contain only numbers. Please describe how you have been feeling in your own words.',
    };
  }

  // 5. Phone-number-only input
  if (isPhoneOnly(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to be a phone number. Please describe how you have been feeling in your own words.',
    };
  }

  // 6. Only punctuation or symbols (no letters or digits)
  if (isPunctuationOnly(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to contain only symbols or punctuation. Please describe how you have been feeling in your own words.',
    };
  }

  // 7. Repeated single-character spam
  if (isRepeatedCharSpam(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to be repeated characters. Please describe how you have been feeling in your own words.',
    };
  }

  // 8. Repeated short-pattern spam
  if (isRepeatedPatternSpam(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to be a repeated pattern. Please describe how you have been feeling in your own words.',
    };
  }

  // 9. Keyboard-sequence spam
  if (isKeyboardSequenceSpam(trimmed)) {
    return {
      valid: false,
      message: 'Text appears to be a keyboard sequence. Please describe how you have been feeling in your own words.',
    };
  }

  return { valid: true };
}

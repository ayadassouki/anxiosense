/**
 * Emoji preprocessing for AnxioSense.
 *
 * Replaces emoji characters in user text with bracketed semantic descriptions
 * so that the downstream LLM receives explicit, unambiguous emotional signal.
 *
 * Known emotional emoji → "[description]"
 * Unknown / decorative emoji → "[emoji]"
 *
 * Text between emoji is preserved exactly; whitespace is not collapsed.
 */

/** Map of emoji codepoint strings to semantic descriptions. */
const EMOJI_SEMANTIC: Readonly<Record<string, string>> = {
  // ── Sadness / Distress ──────────────────────────────────────────────────
  '😢': 'feeling sad',
  '😭': 'crying intensely',
  '😞': 'feeling disappointed',
  '😔': 'feeling downcast',
  '😟': 'feeling worried',
  '😩': 'feeling overwhelmed and exhausted',
  '😫': 'feeling worn out',
  '😖': 'feeling distressed',
  '😣': 'feeling strained',
  '🥺': 'feeling vulnerable',
  // ── Anxiety / Fear ──────────────────────────────────────────────────────
  '😰': 'feeling anxious',
  '😨': 'feeling fearful',
  '😱': 'feeling terrified',
  '😬': 'feeling nervous',
  '😓': 'feeling stressed',
  '🫨': 'feeling shaken',
  '😧': 'feeling anguished',
  '😦': 'feeling dismayed',
  // ── Anger / Frustration ─────────────────────────────────────────────────
  '😠': 'feeling angry',
  '😡': 'feeling very angry',
  '🤬': 'feeling furious',
  '😤': 'feeling frustrated',
  '🙄': 'feeling exasperated',
  // ── Numbness / Blankness ────────────────────────────────────────────────
  '😶': 'feeling speechless',
  '😑': 'feeling blank or numb',
  '😐': 'feeling flat or neutral',
  '🫥': 'feeling disconnected or invisible',
  '🙃': 'feeling ironically overwhelmed',
  '😒': 'feeling indifferent',
  // ── Confusion / Uncertainty ─────────────────────────────────────────────
  '🤔': 'thinking or reflecting',
  '😕': 'feeling confused',
  '🫤': 'feeling uncertain',
  '😅': 'feeling awkward or nervous',
  // ── Tiredness / Fatigue ─────────────────────────────────────────────────
  '😴': 'feeling exhausted',
  '🥱': 'feeling very tired',
  '😪': 'feeling drowsy',
  // ── Physical Illness ────────────────────────────────────────────────────
  '🤒': 'feeling physically unwell',
  '🤕': 'feeling hurt',
  '🤢': 'feeling nauseous',
  '🤮': 'feeling sick',
  '🥴': 'feeling confused or dizzy',
  '🤧': 'feeling ill',
  // ── Positive ────────────────────────────────────────────────────────────
  '😊': 'feeling happy',
  '😀': 'feeling joyful',
  '😁': 'grinning',
  '🙂': 'feeling okay',
  '😄': 'feeling cheerful',
  '😃': 'feeling very happy',
  '🥰': 'feeling loved',
  '😍': 'feeling great',
  '🤗': 'feeling warmly supported',
  '😌': 'feeling at peace',
  '☺️': 'feeling content',
  // ── Heart / Connection ──────────────────────────────────────────────────
  '💔': 'heartbroken',
  '❤️': 'feeling love or care',
  '🖤': 'dark feelings',
  '💜': 'gentle caring feelings',
  '💙': 'feeling calm sadness',
  '💚': 'feeling hopeful',
  '🤍': 'feeling pure or empty',
  '💛': 'feeling warm',
  '🧡': 'feeling passionate',
  // ── Crying / Tears ──────────────────────────────────────────────────────
  '🥲': 'crying while trying to smile',
  '😂': 'laughing while crying',
  // ── Other emotional signals ──────────────────────────────────────────────
  '🙏': 'pleading or grateful',
  '👍': 'feeling positive',
  '👎': 'feeling negative',
  '💪': 'feeling strong',
  '🤞': 'hoping',
  '✨': 'feeling hopeful or positive',
  '🌊': 'feeling overwhelmed like a wave',
  '🌧️': 'feeling low like rainy weather',
  '⚡': 'feeling intense or shocked',
  '🔥': 'feeling intense passion or burnout',
  '💭': 'having many thoughts',
  '😶‍🌫️': 'feeling foggy or unclear',
};

/**
 * Regex that matches Extended Pictographic characters (covers all emoji) plus
 * optional variation selector (FE0F) or skin-tone modifiers.
 */
const EMOJI_RE = /\p{Extended_Pictographic}[️︎]?/gu;

/**
 * Replace emoji in `text` with semantic descriptions.
 *
 * @returns `{ result, changed }` — `changed` is true if any replacement was made.
 */
export function replaceEmoji(text: string): { result: string; changed: boolean } {
  let changed = false;

  const result = text.replace(EMOJI_RE, (match) => {
    // Normalise by stripping variation selector for lookup
    const base = match.replace(/[️︎]/g, '');
    const description = EMOJI_SEMANTIC[match] ?? EMOJI_SEMANTIC[base];
    changed = true;
    return description ? `[${description}]` : '[emoji]';
  });

  return { result, changed };
}

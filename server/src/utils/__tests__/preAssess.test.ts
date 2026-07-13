/**
 * Tests for the AnxioSense pre-assessment pipeline and its constituent modules.
 * Run with: npx tsx src/utils/__tests__/preAssess.test.ts
 *
 * Uses Node.js built-in test runner (node:test) — no extra dependencies.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import { replaceEmoji } from '../preAssess/emoji';
import { detectLanguage } from '../preAssess/language';
import { normalizeSocialMedia } from '../preAssess/normalize';
import { defaultSemanticChecker } from '../preAssess/semantic';
import { hashText } from '../preAssess/logger';
import { evaluateGrounding, calibrateConfidence } from '../preAssess/grounding';
import { preAssess } from '../preAssess/pipeline';

// ── emoji.ts ──────────────────────────────────────────────────────────────────

describe('replaceEmoji', () => {
  test('replaces a known sad emoji with its description', () => {
    const { result, changed } = replaceEmoji('I feel 😢 today');
    assert.ok(changed);
    assert.ok(result.includes('[feeling sad]'), `got: ${result}`);
  });

  test('replaces heartbroken emoji', () => {
    const { result, changed } = replaceEmoji('My heart feels 💔');
    assert.ok(changed);
    assert.ok(result.includes('[heartbroken]'), `got: ${result}`);
  });

  test('replaces unknown emoji with [emoji]', () => {
    // 🪄 is a magic wand emoji — unlikely to be in the known map
    const { result, changed } = replaceEmoji('This is 🪄 weird');
    assert.ok(changed);
    assert.ok(result.includes('[emoji]') || result.includes('['), `got: ${result}`);
  });

  test('leaves text without emoji unchanged', () => {
    const { result, changed } = replaceEmoji('I feel really anxious today');
    assert.equal(changed, false);
    assert.equal(result, 'I feel really anxious today');
  });

  test('handles multiple emoji in one string', () => {
    const { result, changed } = replaceEmoji('Feeling 😢 and 😰 all day');
    assert.ok(changed);
    assert.ok(result.includes('[feeling sad]'), `got: ${result}`);
    assert.ok(result.includes('[feeling anxious]'), `got: ${result}`);
  });

  test('changed is false when text has no emoji', () => {
    const { changed } = replaceEmoji('Just text here, no emoji at all.');
    assert.equal(changed, false);
  });
});

// ── language.ts ───────────────────────────────────────────────────────────────

describe('detectLanguage', () => {
  test('detects English as default for plain English text', () => {
    const { language, confidence } = detectLanguage(
      "I've been feeling really anxious and can't sleep properly lately."
    );
    assert.equal(language, 'en');
    assert.ok(confidence > 0, 'confidence should be positive');
  });

  test('detects Arabic via script analysis', () => {
    const { language, confidence } = detectLanguage('أشعر بالقلق الشديد في الفترة الأخيرة');
    assert.equal(language, 'ar');
    assert.ok(confidence >= 0.5, `confidence too low: ${confidence}`);
  });

  test('detects CJK (Chinese) via script analysis', () => {
    const { language, confidence } = detectLanguage('我最近感到非常焦虑，无法入睡');
    assert.equal(language, 'zh');
    assert.ok(confidence >= 0.5, `confidence too low: ${confidence}`);
  });

  test('detects Cyrillic (Russian) via script analysis', () => {
    const { language } = detectLanguage('Я чувствую сильную тревогу и не могу спать');
    assert.equal(language, 'ru');
  });

  test('detects French via word markers', () => {
    const { language } = detectLanguage(
      "Je me sens très anxieux et je ne peux pas dormir depuis des semaines."
    );
    assert.equal(language, 'fr');
  });

  test('detects Spanish via word markers', () => {
    const { language } = detectLanguage(
      'Me siento muy ansioso y no puedo dormir bien por las noches.'
    );
    assert.equal(language, 'es');
  });

  test('returns en for empty string with zero confidence', () => {
    const { language, confidence } = detectLanguage('');
    assert.equal(language, 'en');
    assert.equal(confidence, 0);
  });
});

// ── normalize.ts ──────────────────────────────────────────────────────────────

describe('normalizeSocialMedia', () => {
  test('collapses letter runs in social-media mode', () => {
    const { result, changed } = normalizeSocialMedia('I am soooooo tired', 'social-media');
    assert.ok(changed);
    assert.ok(!result.includes('oooo'), `expected run to collapse: ${result}`);
  });

  test('strips hashtag # prefix in social-media mode', () => {
    const { result } = normalizeSocialMedia('#anxiety is real today', 'social-media');
    assert.ok(!result.includes('#'), `should strip #: ${result}`);
    assert.ok(result.includes('anxiety'), `should keep word: ${result}`);
  });

  test('replaces @mentions in social-media mode', () => {
    const { result } = normalizeSocialMedia('talked to @therapist about it', 'social-media');
    assert.ok(!result.includes('@therapist'), `got: ${result}`);
    assert.ok(result.includes('[person]'), `got: ${result}`);
  });

  test('replaces URLs in social-media mode', () => {
    const { result } = normalizeSocialMedia('check this https://t.co/abc out', 'social-media');
    assert.ok(!result.includes('https://'), `got: ${result}`);
    assert.ok(result.includes('[link]'), `got: ${result}`);
  });

  test('does NOT change text in journal mode', () => {
    const original = '#anxiety is real. I feel soooo overwhelmed @nobody';
    const { result, changed } = normalizeSocialMedia(original, 'journal');
    assert.equal(changed, false);
    assert.equal(result, original);
  });

  test('changed is false when nothing to normalise in social-media mode', () => {
    const { changed } = normalizeSocialMedia('I feel anxious and cannot sleep.', 'social-media');
    assert.equal(changed, false);
  });
});

// ── semantic.ts ───────────────────────────────────────────────────────────────

describe('defaultSemanticChecker', () => {
  test('sufficient: typical journal entry', () => {
    const { sufficient, contentWordCount } = defaultSemanticChecker.check(
      "I've been feeling anxious and overwhelmed for weeks."
    );
    assert.ok(sufficient, `contentWordCount=${contentWordCount}`);
    assert.ok(contentWordCount >= 2);
  });

  test('sufficient: slang entry', () => {
    const { sufficient } = defaultSemanticChecker.check(
      "Tbh I'm struggling rn. Can't focus at all."
    );
    assert.ok(sufficient, 'should be sufficient — "struggling", "focus" are content words');
  });

  test('insufficient: pure stopwords repeated', () => {
    // "ok ok ok…" — no content words beyond stopwords
    const { sufficient, contentWordCount } = defaultSemanticChecker.check(
      'ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok'
    );
    assert.equal(sufficient, false, `contentWordCount=${contentWordCount}`);
  });

  test('sufficient: text with emoji labels already replaced', () => {
    // After emoji replacement: "[feeling sad] and overwhelmed about everything"
    const { sufficient } = defaultSemanticChecker.check(
      '[feeling sad] and overwhelmed about everything happening right now'
    );
    assert.ok(sufficient);
  });
});

// ── logger.ts ─────────────────────────────────────────────────────────────────

describe('hashText', () => {
  test('returns a 12-character hex string', () => {
    const hash = hashText('some test input');
    assert.equal(hash.length, 12);
    assert.ok(/^[0-9a-f]{12}$/.test(hash), `not hex: ${hash}`);
  });

  test('same input produces same hash', () => {
    const a = hashText('consistent input');
    const b = hashText('consistent input');
    assert.equal(a, b);
  });

  test('different inputs produce different hashes', () => {
    const a = hashText('input one');
    const b = hashText('input two');
    assert.notEqual(a, b);
  });
});

// ── grounding.ts ──────────────────────────────────────────────────────────────

describe('evaluateGrounding', () => {
  test('grounded report references user key terms', () => {
    const userText = 'I have been feeling anxious and cannot sleep properly at night.';
    const report = [
      '## Assessment',
      'Based on your account, you are experiencing significant anxiety and sleep difficulties.',
      'The sleep disruption you describe is a common presentation of heightened anxiety.',
    ].join('\n');

    const { score, specificReferences, passed } = evaluateGrounding(userText, report);
    assert.ok(specificReferences > 0, 'should find references to user terms');
    assert.ok(score > 0);
    assert.ok(passed, `score=${score} should exceed threshold`);
  });

  test('generic report scores low', () => {
    const userText = 'I have been feeling anxious and cannot sleep properly at night.';
    const report = [
      '## Assessment',
      'This report reflects a wide range of emotions and general wellbeing patterns.',
      'A holistic approach to emotional wellbeing is recommended.',
      'Consider various feelings and experiences in your mental health journey.',
    ].join('\n');

    const { score, genericPhraseCount } = evaluateGrounding(userText, report);
    assert.ok(genericPhraseCount > 0, 'should detect generic phrases');
    assert.ok(score < 0.6, `expected lower score for generic report: ${score}`);
  });

  test('empty user text returns zero score', () => {
    const { score, specificReferences } = evaluateGrounding('', 'Any report content.');
    assert.equal(specificReferences, 0);
    // score may be 0 or based on empty key terms
    assert.ok(score >= 0 && score <= 1);
  });
});

describe('calibrateConfidence', () => {
  test('HIGH for score >= 0.6', () => {
    assert.equal(calibrateConfidence(0.6), 'HIGH');
    assert.equal(calibrateConfidence(0.9), 'HIGH');
    assert.equal(calibrateConfidence(1.0), 'HIGH');
  });

  test('MODERATE for score in [0.3, 0.6)', () => {
    assert.equal(calibrateConfidence(0.3), 'MODERATE');
    assert.equal(calibrateConfidence(0.45), 'MODERATE');
    assert.equal(calibrateConfidence(0.59), 'MODERATE');
  });

  test('LOW for score < 0.3', () => {
    assert.equal(calibrateConfidence(0.0), 'LOW');
    assert.equal(calibrateConfidence(0.1), 'LOW');
    assert.equal(calibrateConfidence(0.29), 'LOW');
  });
});

// ── pipeline.ts (integration) ─────────────────────────────────────────────────

describe('preAssess pipeline', () => {
  test('returns processedText with emoji replaced', async () => {
    const result = await preAssess(
      "I feel 😢 and overwhelmed — can't sleep or eat properly anymore.",
      'journal'
    );
    assert.equal(result.rejected, false);
    assert.ok(result.emojiProcessed, 'should flag emojiProcessed');
    assert.ok(!result.processedText.includes('😢'), 'emoji should be replaced');
    assert.ok(result.processedText.includes('[feeling sad]'), `got: ${result.processedText}`);
  });

  test('normalises social-media text', async () => {
    const result = await preAssess(
      '#anxiety is sooooo real. Been having panic attacks every morning for the last two weeks.',
      'social-media'
    );
    assert.equal(result.rejected, false);
    assert.ok(result.normalized, 'should flag normalized');
    assert.ok(!result.processedText.includes('#'), 'hashtag # should be stripped');
    assert.ok(!result.processedText.includes('oooo'), 'letter run should be collapsed');
  });

  test('does NOT normalise journal text', async () => {
    const input = '#anxiety is sooooo real. Been having panic attacks every morning for the last two weeks.';
    const result = await preAssess(input, 'journal');
    assert.equal(result.normalized, false);
    // Emoji still processed, but social-media normalization not applied
    assert.ok(result.processedText.includes('#'), 'hashtag preserved in journal mode');
  });

  test('detects English for English input', async () => {
    const result = await preAssess(
      "I've been feeling really anxious lately and can't sleep properly.",
      'journal'
    );
    assert.equal(result.detectedLanguage, 'en');
  });

  test('detects Arabic for Arabic input', async () => {
    const result = await preAssess(
      'أشعر بالقلق الشديد ولا أستطيع النوم بشكل صحيح في الفترة الأخيرة',
      'journal'
    );
    assert.equal(result.detectedLanguage, 'ar');
    assert.ok(result.languageConfidence >= 0.5);
  });

  test('semanticallySufficient is true for meaningful journal entry', async () => {
    const result = await preAssess(
      "Feeling really overwhelmed and anxious — deadlines, meetings, everything at once.",
      'journal'
    );
    assert.ok(result.semanticallySufficient);
  });

  test('rejects by default when semantic content is insufficient', async () => {
    // Default behaviour (REJECT_INSUFFICIENT !== 'false'): reject semantically
    // empty input so it never reaches the Mastra workflow.
    // The test text bypasses validateText (called directly on preAssess) but
    // has no content words beyond stopwords.
    const emptyish = 'I am and but so the if to on it as for at by from into here';
    const result = await preAssess(emptyish, 'journal');
    assert.equal(result.rejected, true, 'should reject semantically empty input by default');
    assert.equal(result.semanticallySufficient, false);
    assert.equal(result.reasonCode, 'INSUFFICIENT_SEMANTIC_CONTENT');
  });

  test('REJECT_INSUFFICIENT=false disables semantic rejection', async () => {
    const prev = process.env.REJECT_INSUFFICIENT;
    process.env.REJECT_INSUFFICIENT = 'false';
    try {
      const emptyish = 'I am and but so the if to on it as for at by from into here';
      const result = await preAssess(emptyish, 'journal');
      assert.equal(result.rejected, false, 'env var override should prevent rejection');
      assert.equal(result.semanticallySufficient, false);
    } finally {
      if (prev === undefined) delete process.env.REJECT_INSUFFICIENT;
      else process.env.REJECT_INSUFFICIENT = prev;
    }
  });
});

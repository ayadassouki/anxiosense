/**
 * Tests for the shared AnxioSense text validation helper.
 * Run with: npm test (server package)
 *
 * Uses Node.js built-in test runner (node:test) — no extra dependencies.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { validateText } from '../validateText';

// ── Valid submissions (must pass) ─────────────────────────────────────────────

describe('valid submissions', () => {
  test('accepts a normal journal entry', () => {
    const r = validateText("I've been feeling really anxious lately and can't sleep properly.");
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text that contains numbers in context', () => {
    const r = validateText('I slept maybe 3 hours last night and woke up 4 times feeling panicked.');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text with punctuation and dashes', () => {
    const r = validateText('Work is really stressful — deadlines, meetings, and emails... it never stops.');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts slang and contractions', () => {
    const r = validateText("Tbh I'm struggling rn. Can't focus, feeling meh about everything.");
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text that mentions a phone number inline', () => {
    const r = validateText("My doctor is 555-1234 and I'm calling them — I've been so anxious and overwhelmed.");
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text that mentions a keyboard sequence inline', () => {
    const r = validateText('I find typing on my qwerty keyboard stressful lately because of all the deadlines.');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text with emojis', () => {
    const r = validateText("Feeling really overwhelmed 😢 and don't know what to do anymore about my anxiety.");
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text with spelling mistakes', () => {
    const r = validateText('I hav ben feleing relly tierd and anxous for the past too weeks now and cant slep.');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts text with repeated words in a natural sentence', () => {
    const r = validateText('I feel sad sad sad all the time and nothing seems to help me feel better anymore.');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts exactly 20-character text', () => {
    // 20 chars: "I feel very anxious!" = 20
    const r = validateText('I feel very anxious!');
    assert.equal(r.valid, true, r.message);
  });

  test('accepts a social-media-style post with hashtags', () => {
    const r = validateText('#anxiety is real. Been having panic attacks every morning for the last two weeks.');
    assert.equal(r.valid, true, r.message);
  });
});

// ── Invalid submissions (must reject) ─────────────────────────────────────────

describe('empty / whitespace', () => {
  test('rejects empty string', () => {
    const r = validateText('');
    assert.equal(r.valid, false);
    assert.ok(r.message, 'should provide a message');
  });

  test('rejects whitespace only', () => {
    const r = validateText('   \t\n   ');
    assert.equal(r.valid, false);
  });
});

describe('length violations', () => {
  test('rejects text shorter than 20 chars (trimmed)', () => {
    const r = validateText('I feel bad');
    assert.equal(r.valid, false);
    assert.match(r.message!, /20/, 'message should mention 20');
  });

  test('rejects text of exactly 19 chars', () => {
    const r = validateText('I feel very anxious'); // 19 chars
    assert.equal(r.valid, false);
  });

  test('rejects text longer than 5000 chars', () => {
    const r = validateText('I feel anxious. '.repeat(313)); // > 5000
    assert.equal(r.valid, false);
    assert.match(r.message!, /5,000/);
  });
});

describe('digits only', () => {
  test('rejects a string of only digits', () => {
    const r = validateText('123456789012345678901234');
    assert.equal(r.valid, false);
    assert.match(r.message!, /numbers/i);
  });

  test('rejects exactly 20 digits', () => {
    const r = validateText('12345678901234567890');
    assert.equal(r.valid, false);
  });
});

describe('phone numbers', () => {
  test('rejects a UK-style phone number (≥20 chars)', () => {
    // Long enough to pass the length check and reach the phone check
    const r = validateText('+44 (0)20 7946 0123 4567');  // 24 chars, no letters
    assert.equal(r.valid, false);
    assert.match(r.message!, /phone/i);
  });

  test('rejects a US phone number with formatting', () => {
    const r = validateText('+1 (800) 555-1234');
    assert.equal(r.valid, false);
  });

  test('rejects a plain digit string of 10 digits (looks like phone)', () => {
    const r = validateText('8005551234');
    // Caught by digits-only rule before phone rule
    assert.equal(r.valid, false);
  });
});

describe('punctuation / symbols only', () => {
  test('rejects a string of only punctuation', () => {
    const r = validateText('!!! ??? ... !!! ??? ... !!! ???');
    assert.equal(r.valid, false);
    assert.match(r.message!, /symbols|punctuation/i);
  });

  test('rejects a string of only symbols', () => {
    const r = validateText('*** @@@ ### $$$ %%% ^^^');
    assert.equal(r.valid, false);
  });
});

describe('repeated-character spam', () => {
  test('rejects a single character repeated many times', () => {
    const r = validateText('aaaaaaaaaaaaaaaaaaaaaaaa');
    assert.equal(r.valid, false);
    assert.match(r.message!, /repeated/i);
  });

  test('rejects exclamation marks repeated many times', () => {
    const r = validateText('!!!!!!!!!!!!!!!!!!!!!!!!!!!!');
    // Caught by punctuation-only before repeated-char
    assert.equal(r.valid, false);
  });

  test('rejects "x" repeated 50 times', () => {
    const r = validateText('x'.repeat(50));
    assert.equal(r.valid, false);
  });
});

describe('repeated-pattern spam', () => {
  test('rejects "asdf" repeated pattern', () => {
    const r = validateText('asdfasdfasdfasdfasdfasdf');
    assert.equal(r.valid, false);
    assert.match(r.message!, /repeated|keyboard/i);
  });

  test('rejects "ab" repeated many times', () => {
    const r = validateText('abababababababababababab');
    assert.equal(r.valid, false);
  });

  test('rejects "lol" repeated pattern', () => {
    const r = validateText('lollollollollollollol');
    assert.equal(r.valid, false);
  });
});

describe('keyboard-sequence spam', () => {
  test('rejects qwertyuiop repeated', () => {
    const r = validateText('qwertyuiop qwertyuiop qwertyuiop');
    assert.equal(r.valid, false);
    assert.match(r.message!, /keyboard/i);
  });

  test('rejects asdfghjkl repeated', () => {
    const r = validateText('asdfghjkl asdfghjkl asdfghjkl');
    assert.equal(r.valid, false);
  });

  test('rejects a mix of keyboard-row words', () => {
    const r = validateText('qwert asdfg zxcvb qwerty asdf zxcv');
    assert.equal(r.valid, false);
  });

  test('rejects multiple full keyboard rows without spaces', () => {
    // Each row-chunk is a qualifying keyboard word when split on caps/delimiter;
    // use spaces so isKeyboardWord can evaluate each run individually.
    const r = validateText('qwertyuiop asdfghjkl zxcvbnm qwertyuiop');
    assert.equal(r.valid, false);
  });

  test('does NOT reject text that merely mentions qwerty', () => {
    const r = validateText('I find typing on my qwerty keyboard stressful lately because of all the deadlines.');
    assert.equal(r.valid, true, r.message);
  });
});

/**
 * Implementation-level tests for functional impairment validation and UUID uniqueness.
 *
 * Tests here run against the REAL validateFunctionalImpairment utility and the REAL
 * uuid library — not fake helpers. This catches regressions in the actual validation
 * logic and ensures the UUID contract is enforced by the installed library.
 *
 * Run with: npm test (server package)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { v4 as uuid } from 'uuid';
import {
  validateFunctionalImpairment,
  VALID_IMPAIRMENTS,
  type FunctionalImpairmentValue,
} from '../validateFunctionalImpairment.js';

// ── Valid self-assessment values — all four must be accepted ─────────────────

describe('validateFunctionalImpairment — valid self-assessment values', () => {
  const VALID: FunctionalImpairmentValue[] = [
    'not_difficult_at_all',
    'somewhat_difficult',
    'very_difficult',
    'extremely_difficult',
  ];

  for (const value of VALID) {
    test(`accepts "${value}" for journal mode`, () => {
      const result = validateFunctionalImpairment('journal', value);
      assert.equal(result.ok, true);
      if (result.ok) {
        assert.equal(result.value, value);
      }
    });
  }
});

// ── VALID_IMPAIRMENTS set contains exactly the four expected values ───────────

describe('VALID_IMPAIRMENTS set', () => {
  test('contains exactly four values', () => {
    assert.equal(VALID_IMPAIRMENTS.size, 4);
  });

  test('contains all four impairment enum values', () => {
    assert.ok(VALID_IMPAIRMENTS.has('not_difficult_at_all'));
    assert.ok(VALID_IMPAIRMENTS.has('somewhat_difficult'));
    assert.ok(VALID_IMPAIRMENTS.has('very_difficult'));
    assert.ok(VALID_IMPAIRMENTS.has('extremely_difficult'));
  });
});

// ── Missing self-assessment impairment must return HTTP 400 ──────────────────

describe('validateFunctionalImpairment — missing value in journal mode (→ 400)', () => {
  test('undefined → not ok', () => {
    const result = validateFunctionalImpairment('journal', undefined);
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.ok(result.message.length > 0);
    }
  });

  test('null → not ok', () => {
    const result = validateFunctionalImpairment('journal', null);
    assert.equal(result.ok, false);
  });

  test('empty string → not ok', () => {
    const result = validateFunctionalImpairment('journal', '');
    assert.equal(result.ok, false);
  });
});

// ── Invalid string values must return HTTP 400 ───────────────────────────────

describe('validateFunctionalImpairment — invalid string values in journal mode (→ 400)', () => {
  test('"not_difficult" (missing _at_all) → not ok', () => {
    // A common truncation error — must be rejected
    const result = validateFunctionalImpairment('journal', 'not_difficult');
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.ok(result.message.includes('"not_difficult"'));
    }
  });

  test('arbitrary invalid string → not ok', () => {
    const result = validateFunctionalImpairment('journal', 'yes_very_hard');
    assert.equal(result.ok, false);
  });

  test('numeric value → not ok', () => {
    const result = validateFunctionalImpairment('journal', 42);
    assert.equal(result.ok, false);
  });

  test('object → not ok', () => {
    const result = validateFunctionalImpairment('journal', { level: 2 });
    assert.equal(result.ok, false);
  });
});

// ── Social-media mode: value is always forced to null ────────────────────────

describe('validateFunctionalImpairment — social-media mode forces null', () => {
  test('undefined → ok with null (social-media path)', () => {
    const result = validateFunctionalImpairment('social-media', undefined);
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.value, null);
    }
  });

  test('valid string → ok with null (client value discarded)', () => {
    // Client must not be able to spoof an impairment value in social-media mode
    const result = validateFunctionalImpairment('social-media', 'somewhat_difficult');
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.value, null, 'social-media must force null regardless of client value');
    }
  });

  test('invalid string → ok with null (social-media ignores content)', () => {
    const result = validateFunctionalImpairment('social-media', 'bad_value');
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.value, null);
    }
  });

  test('null → ok with null', () => {
    const result = validateFunctionalImpairment('social-media', null);
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.value, null);
    }
  });
});

// ── POST response includes functionalImpairment (contract) ───────────────────
// validateFunctionalImpairment returns { ok: true, value } which the route
// then includes in its JSON response as `functionalImpairment: validatedImpairment`.
// This test encodes that shape contract.

describe('validateFunctionalImpairment — return shape contract', () => {
  test('ok result has { ok: true, value }', () => {
    const result = validateFunctionalImpairment('journal', 'very_difficult');
    assert.equal(result.ok, true);
    assert.ok('value' in result);
    if (result.ok) {
      assert.equal(result.value, 'very_difficult');
    }
  });

  test('fail result has { ok: false, message }', () => {
    const result = validateFunctionalImpairment('journal', undefined);
    assert.equal(result.ok, false);
    assert.ok('message' in result);
    if (!result.ok) {
      assert.ok(typeof result.message === 'string' && result.message.length > 0);
    }
  });
});

// ── UUID uniqueness — tests real uuid library, not a handwritten reimplementation

describe('uuid v4 — same-day report ID uniqueness', () => {
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  test('uuid() produces a valid RFC 4122 v4 string', () => {
    const id = uuid();
    assert.match(id, UUID_RE, `uuid() produced "${id}" which is not valid UUID v4`);
  });

  test('two uuid() calls on the same tick produce distinct IDs', () => {
    const a = uuid();
    const b = uuid();
    assert.notEqual(a, b, 'Two consecutive uuid() calls must return distinct IDs');
  });

  test('ten uuid() calls all produce distinct IDs', () => {
    const ids = Array.from({ length: 10 }, () => uuid());
    const unique = new Set(ids);
    assert.equal(unique.size, 10, 'All 10 uuid() calls must produce distinct IDs');
    for (const id of ids) {
      assert.match(id, UUID_RE, `"${id}" is not a valid UUID v4`);
    }
  });

  test('journal and social-media report IDs are drawn from the same UUID space', () => {
    // Both modes call uuid() independently — there is no namespace separation
    // that could cause collisions
    const journalId     = uuid();
    const socialMediaId = uuid();
    assert.notEqual(journalId, socialMediaId);
    assert.match(journalId,     UUID_RE);
    assert.match(socialMediaId, UUID_RE);
  });
});

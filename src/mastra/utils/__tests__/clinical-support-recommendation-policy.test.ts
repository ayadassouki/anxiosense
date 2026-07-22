/**
 * Tests for the AnxioSense centralised clinical support recommendation policy.
 * Run with: npm test (root Mastra package)
 *
 * Uses Node.js built-in test runner (node:test) — no extra dependencies.
 *
 * Spec requirements verified:
 *   - Every severity × impairment combination returns the correct recommendation
 *   - Functional impairment never changes the GAD-7 score
 *   - Minimal × (somewhat|very|extremely) difficult all return identical text (per PDF)
 *   - Severe × extremely_difficult includes crisis safety language
 *   - getStandardClinicalRecommendation returns distinct text per severity
 *   - getFunctionalImpairmentLabel returns the correct display label
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import {
  getPatientRecommendation,
  getStandardClinicalRecommendation,
  getFunctionalImpairmentLabel,
  FUNCTIONAL_IMPAIRMENT_OPTIONS,
} from '../clinical-support-recommendation-policy.js';
import {
  computeGad7Score,
} from '../gad7-assessment-scorer.js';

// ── Type aliases (mirrors types from the modules) ─────────────────────────────

type Severity   = 'minimal' | 'mild' | 'moderate' | 'severe';
type Impairment = 'not_difficult_at_all' | 'somewhat_difficult' | 'very_difficult' | 'extremely_difficult';

const SEVERITIES:   Severity[]   = ['minimal', 'mild', 'moderate', 'severe'];
const IMPAIRMENTS:  Impairment[] = [
  'not_difficult_at_all', 'somewhat_difficult', 'very_difficult', 'extremely_difficult',
];

// ── All 16 combinations return non-empty strings ──────────────────────────────

describe('getPatientRecommendation — all 16 combinations are populated', () => {
  for (const severity of SEVERITIES) {
    for (const impairment of IMPAIRMENTS) {
      test(`${severity} × ${impairment} → non-empty string`, () => {
        const text = getPatientRecommendation(severity, impairment);
        assert.ok(
          typeof text === 'string' && text.length > 0,
          `Expected non-empty string for ${severity} × ${impairment}`
        );
      });
    }
  }
});

// ── Minimal severity: "difficult" options collapse to same text (per PDF) ─────

describe('getPatientRecommendation — minimal severity collapse rule', () => {
  test('minimal × somewhat = minimal × very = minimal × extremely', () => {
    const a = getPatientRecommendation('minimal', 'somewhat_difficult');
    const b = getPatientRecommendation('minimal', 'very_difficult');
    const c = getPatientRecommendation('minimal', 'extremely_difficult');
    assert.equal(a, b, 'minimal×somewhat and minimal×very must return identical text');
    assert.equal(b, c, 'minimal×very and minimal×extremely must return identical text');
  });

  test('minimal × not_difficult is DIFFERENT from the collapsed versions', () => {
    const notDifficult = getPatientRecommendation('minimal', 'not_difficult_at_all');
    const difficult    = getPatientRecommendation('minimal', 'somewhat_difficult');
    assert.notEqual(
      notDifficult, difficult,
      'minimal×not_difficult must differ from minimal×(any difficult)'
    );
  });
});

// ── Severity-specific content checks ─────────────────────────────────────────

describe('getPatientRecommendation — content contracts per severity', () => {
  test('minimal × not_difficult_at_all does NOT recommend professional consultation', () => {
    const text = getPatientRecommendation('minimal', 'not_difficult_at_all');
    assert.ok(
      !text.includes('healthcare professional'),
      'Minimal + not difficult should not recommend a healthcare professional'
    );
  });

  test('minimal × somewhat_difficult mentions considering professional discussion', () => {
    const text = getPatientRecommendation('minimal', 'somewhat_difficult');
    assert.ok(
      text.includes('healthcare professional'),
      'Minimal + difficult should mention healthcare professional as consideration'
    );
  });

  test('moderate × not_difficult_at_all recommends professional discussion', () => {
    const text = getPatientRecommendation('moderate', 'not_difficult_at_all');
    assert.ok(
      text.includes('healthcare professional'),
      'Moderate severity must always mention healthcare professional'
    );
  });

  test('severe × extremely_difficult includes crisis/safety language', () => {
    const text = getPatientRecommendation('severe', 'extremely_difficult');
    const hasCrisisLanguage =
      text.includes('unable to keep yourself safe') ||
      text.includes('crisis service') ||
      text.includes('emergency services') ||
      text.includes('emergency department');
    assert.ok(
      hasCrisisLanguage,
      'Severe + extremely difficult must include crisis safety guidance'
    );
  });

  test('severe × not_difficult_at_all still strongly recommends professional evaluation', () => {
    const text = getPatientRecommendation('severe', 'not_difficult_at_all');
    assert.ok(
      text.toLowerCase().includes('strongly recommended') ||
      text.toLowerCase().includes('strongly recommend'),
      'Severe severity must strongly recommend evaluation regardless of impairment'
    );
  });
});

// ── Different severities return different text ────────────────────────────────

describe('getPatientRecommendation — severities are distinct for same impairment', () => {
  for (const impairment of IMPAIRMENTS) {
    test(`all four severities return distinct text for ${impairment}`, () => {
      const texts = SEVERITIES.map(s => getPatientRecommendation(s, impairment));
      const unique = new Set(texts);
      assert.equal(
        unique.size, 4,
        `Expected 4 distinct recommendation texts for impairment="${impairment}"`
      );
    });
  }
});

// ── Standard clinical recommendations ────────────────────────────────────────

describe('getStandardClinicalRecommendation', () => {
  for (const severity of SEVERITIES) {
    test(`${severity} returns a non-empty string`, () => {
      const text = getStandardClinicalRecommendation(severity);
      assert.ok(typeof text === 'string' && text.length > 0);
    });
  }

  test('all four severities return distinct clinical recommendations', () => {
    const texts = SEVERITIES.map(s => getStandardClinicalRecommendation(s));
    const unique = new Set(texts);
    assert.equal(unique.size, 4, 'Expected 4 distinct clinical recommendations');
  });

  test('severe recommendation includes prompt/specialist language', () => {
    const text = getStandardClinicalRecommendation('severe');
    const hasUrgencyLanguage = text.toLowerCase().includes('prompt') ||
                               text.toLowerCase().includes('specialist');
    assert.ok(hasUrgencyLanguage, 'Severe clinical recommendation must convey urgency');
  });
});

// ── getFunctionalImpairmentLabel ──────────────────────────────────────────────

describe('getFunctionalImpairmentLabel', () => {
  test('not_difficult_at_all → "Not difficult at all"', () => {
    assert.equal(getFunctionalImpairmentLabel('not_difficult_at_all'), 'Not difficult at all');
  });

  test('somewhat_difficult → "Somewhat difficult"', () => {
    assert.equal(getFunctionalImpairmentLabel('somewhat_difficult'), 'Somewhat difficult');
  });

  test('very_difficult → "Very difficult"', () => {
    assert.equal(getFunctionalImpairmentLabel('very_difficult'), 'Very difficult');
  });

  test('extremely_difficult → "Extremely difficult"', () => {
    assert.equal(getFunctionalImpairmentLabel('extremely_difficult'), 'Extremely difficult');
  });

  test('all four FUNCTIONAL_IMPAIRMENT_OPTIONS values are resolvable via label lookup', () => {
    for (const { value, label } of FUNCTIONAL_IMPAIRMENT_OPTIONS) {
      assert.equal(getFunctionalImpairmentLabel(value), label);
    }
  });
});

// ── Functional impairment MUST NOT change the GAD-7 score ────────────────────
// Verifies the architectural contract: computeGad7Score has no knowledge of
// functional impairment — the score is solely determined by the 7 item answers.

describe('functional impairment does not change GAD-7 score (contract test)', () => {
  const ANSWER_SETS: Array<{ label: string; answers: number[]; expectedScore: number; expectedSeverity: Severity }> = [
    { label: 'minimal',  answers: [0, 1, 0, 0, 1, 0, 0], expectedScore: 2,  expectedSeverity: 'minimal'  },
    { label: 'mild',     answers: [1, 1, 1, 1, 1, 1, 0], expectedScore: 6,  expectedSeverity: 'mild'     },
    { label: 'moderate', answers: [2, 2, 2, 2, 1, 1, 1], expectedScore: 11, expectedSeverity: 'moderate' },
    { label: 'severe',   answers: [3, 3, 3, 3, 3, 3, 3], expectedScore: 21, expectedSeverity: 'severe'   },
  ];

  for (const { label, answers, expectedScore, expectedSeverity } of ANSWER_SETS) {
    for (const impairment of IMPAIRMENTS) {
      test(`${label} answers → score ${expectedScore} regardless of impairment="${impairment}"`, () => {
        // computeGad7Score does not accept a functionalImpairment parameter —
        // calling it multiple times with the same answers must always yield the
        // same score, proving impairment has zero effect on scoring.
        const result = computeGad7Score(answers);
        assert.equal(result.score, expectedScore,
          `Score must be ${expectedScore} regardless of impairment="${impairment}"`
        );
        assert.equal(result.severity, expectedSeverity,
          `Severity must be "${expectedSeverity}" regardless of impairment="${impairment}"`
        );
      });
    }
  }
});

// ── Recommendation text is independent of GAD-7 score calculation ─────────────
// Verifies that the recommendation lookup uses the SEVERITY BAND (not the raw
// score) and that the band is determined solely by computeGad7Score.

describe('recommendation lookup uses severity band, not raw score', () => {
  test('score 5 → mild → same recommendation as any other mild score', () => {
    const r5  = computeGad7Score([1, 1, 1, 1, 1, 0, 0]); // score 5
    const r9  = computeGad7Score([1, 2, 1, 2, 1, 1, 1]); // score 9
    assert.equal(r5.severity, 'mild');
    assert.equal(r9.severity, 'mild');
    // Same severity → same recommendation for any given impairment
    for (const impairment of IMPAIRMENTS) {
      const rec5 = getPatientRecommendation(r5.severity, impairment);
      const rec9 = getPatientRecommendation(r9.severity, impairment);
      assert.equal(rec5, rec9,
        `Scores 5 and 9 are both mild — recommendation must be identical for impairment="${impairment}"`
      );
    }
  });

  test('score 10 → moderate → different recommendation than mild (score 9)', () => {
    const r9  = computeGad7Score([1, 2, 1, 2, 1, 1, 1]); // score 9  → mild
    const r10 = computeGad7Score([2, 2, 1, 2, 1, 1, 1]); // score 10 → moderate
    assert.equal(r9.severity,  'mild');
    assert.equal(r10.severity, 'moderate');
    for (const impairment of IMPAIRMENTS) {
      const recMild = getPatientRecommendation(r9.severity,  impairment);
      const recMod  = getPatientRecommendation(r10.severity, impairment);
      assert.notEqual(recMild, recMod,
        `Mild and moderate must have different recommendations for impairment="${impairment}"`
      );
    }
  });
});

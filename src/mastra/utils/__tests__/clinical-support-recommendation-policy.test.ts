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
  CONCERN_PATTERN_ANCHORS,
  buildRecommendationDirective,
  renderRecommendationPrompt,
  validateRecommendationSection,
  enforceRecommendation,
  isSafeLabel,
  toSafeLabels,
  type RecommendationDirective,
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

// ═════════════════════════════════════════════════════════════════════════════
// P3 — Recommendation personalisation
//
// The clinical classification is decided before generation. These tests assert
// that personalisation cannot move it, and that no user sentence can reach the
// prompt. They are pure and synchronous — no model is invoked.
// ═════════════════════════════════════════════════════════════════════════════

const ALL_SEVERITIES = ['minimal', 'mild', 'moderate', 'severe'] as const;
const ALL_IMPAIRMENTS = [
  'not_difficult_at_all', 'somewhat_difficult', 'very_difficult', 'extremely_difficult',
] as const;

/** Builds a directive with sensible defaults for tests. */
function directive(overrides: Partial<Parameters<typeof buildRecommendationDirective>[0]> = {}) {
  return buildRecommendationDirective({
    mode: 'journal',
    severity: 'moderate',
    impairment: 'somewhat_difficult',
    referralLevel: 'moderate',
    concernPattern: 'Elevated Concern Pattern',
    symptomClaims: [{ claimId: 'SYM-1', claimText: 'Sleep disruption' }],
    stressorClaims: [{ claimId: 'CTX-1', claimText: 'Academic stress' }],
    ...overrides,
  });
}

/** Wraps a recommendation body in a minimal report shell. */
function report(recommendationBody: string): string {
  return [
    '## Supporting Findings',
    '',
    '- Persistent worry',
    '',
    '## Recommendation',
    '',
    recommendationBody,
    '',
    '## Limitations',
    '',
    'This report is based only on the information provided.',
  ].join('\n');
}

// ── All 16 anchors preserved ─────────────────────────────────────────────────

describe('P3 — all 16 severity × impairment anchors are preserved', () => {
  for (const severity of ALL_SEVERITIES) {
    for (const impairment of ALL_IMPAIRMENTS) {
      test(`${severity} × ${impairment} anchor is byte-identical to the lookup table`, () => {
        const d = directive({ severity, impairment, mode: 'journal' });
        assert.equal(d.anchorText, getPatientRecommendation(severity, impairment));
        assert.equal(d.anchorSource, 'severity_impairment_lookup');
      });
    }
  }

  test('minimal row still collapses the three "difficult" levels to one text', () => {
    const texts = ['somewhat_difficult', 'very_difficult', 'extremely_difficult'].map(
      i => directive({ severity: 'minimal', impairment: i as typeof ALL_IMPAIRMENTS[number] }).anchorText
    );
    assert.equal(new Set(texts).size, 1);
  });

  test('severe × extremely_difficult retains its crisis safety language', () => {
    const d = directive({ severity: 'severe', impairment: 'extremely_difficult' });
    assert.match(d.anchorText, /emergency services|crisis service/i);
  });

  test('the 16 cells still yield exactly 14 distinct anchor strings', () => {
    const all = new Set<string>();
    for (const s of ALL_SEVERITIES) for (const i of ALL_IMPAIRMENTS) {
      all.add(directive({ severity: s, impairment: i }).anchorText);
    }
    assert.equal(all.size, 14);
  });
});

// ── Fallback anchors ─────────────────────────────────────────────────────────

describe('P3 — concern-pattern fallback anchors', () => {
  test('social-media mode uses the concern-pattern anchor, not the lookup', () => {
    const d = directive({ mode: 'social-media', severity: null, impairment: null });
    assert.equal(d.anchorSource, 'concern_pattern_fallback');
    assert.equal(d.anchorText, CONCERN_PATTERN_ANCHORS['Elevated Concern Pattern']);
  });

  test('journal mode without a GAD-7 score uses the concern-pattern anchor', () => {
    const d = directive({ severity: null, impairment: null });
    assert.equal(d.anchorSource, 'concern_pattern_fallback');
  });

  test('journal mode without an impairment answer uses the concern-pattern anchor', () => {
    const d = directive({ impairment: null });
    assert.equal(d.anchorSource, 'concern_pattern_fallback');
  });

  test('the Mild anchor preserves the mandated verbatim sentence', () => {
    assert.match(
      CONCERN_PATTERN_ANCHORS['Mild Concern Pattern'],
      /Monitoring how these experiences change over time may be helpful\./
    );
  });

  test('every concern pattern has a distinct anchor', () => {
    const values = Object.values(CONCERN_PATTERN_ANCHORS);
    assert.equal(new Set(values).size, values.length);
  });
});

// ── Personalisation varies with inputs ───────────────────────────────────────

describe('P3 — personalisation differs across symptoms and stressors', () => {
  test('different symptom sets produce different prompts', () => {
    const a = renderRecommendationPrompt(directive({
      symptomClaims: [{ claimId: 'SYM-1', claimText: 'Sleep disruption' }],
    }));
    const b = renderRecommendationPrompt(directive({
      symptomClaims: [{ claimId: 'SYM-1', claimText: 'Excessive worry' }],
    }));
    assert.notEqual(a, b);
    assert.match(a, /Sleep disruption/);
    assert.match(b, /Excessive worry/);
  });

  test('different stressor sets produce different prompts', () => {
    const a = renderRecommendationPrompt(directive({
      stressorClaims: [{ claimId: 'CTX-1', claimText: 'Academic stress' }],
    }));
    const b = renderRecommendationPrompt(directive({
      stressorClaims: [{ claimId: 'CTX-1', claimText: 'Financial stress' }],
    }));
    assert.notEqual(a, b);
  });

  test('mode changes the assessment basis line', () => {
    const journal = renderRecommendationPrompt(directive({ mode: 'journal' }));
    const social = renderRecommendationPrompt(directive({
      mode: 'social-media', severity: null, impairment: null,
    }));
    assert.match(journal, /Journal \/ Self-Report/);
    assert.match(social, /Social Media Analysis/);
  });

  test('identical inputs produce identical prompts (deterministic)', () => {
    assert.equal(renderRecommendationPrompt(directive()), renderRecommendationPrompt(directive()));
  });

  test('the anchor is identical across all those variations', () => {
    const variants = [
      directive({ symptomClaims: [{ claimId: 'SYM-1', claimText: 'Sleep disruption' }] }),
      directive({ symptomClaims: [{ claimId: 'SYM-1', claimText: 'Restlessness' }] }),
      directive({ stressorClaims: [{ claimId: 'CTX-1', claimText: 'Family stress' }] }),
    ];
    const anchors = new Set(variants.map(v => v.anchorText));
    assert.equal(anchors.size, 1, 'personalisation must never change the anchor');
  });

  test('no labels available disables personalisation entirely', () => {
    const d = directive({ symptomClaims: [], stressorClaims: [] });
    assert.equal(d.personalisationAvailable, false);
    assert.match(renderRecommendationPrompt(d), /Do not add any further paragraph/);
  });
});

// ── No raw user text in prompts ──────────────────────────────────────────────

describe('P3 — raw user text never reaches the personalisation prompt', () => {
  const RAW_SENTENCE =
    "I keep worrying about everything and I can't sleep because my mind won't stop racing at night";

  test('the GEN-1 fallback claim is excluded by claim id', () => {
    const d = directive({ symptomClaims: [{ claimId: 'GEN-1', claimText: RAW_SENTENCE }] });
    assert.deepEqual(d.symptomLabels, []);
    assert.ok(!renderRecommendationPrompt(d).includes('worrying about everything'));
  });

  test('sentence-shaped claim text is rejected even under a normal claim id', () => {
    const d = directive({ symptomClaims: [{ claimId: 'SYM-1', claimText: RAW_SENTENCE }] });
    assert.deepEqual(d.symptomLabels, []);
  });

  test('isSafeLabel accepts genuine labels', () => {
    for (const label of ['Excessive worry', 'Sleep disruption', 'Academic stress', 'Panic-like experiences']) {
      assert.equal(isSafeLabel(label), true, label);
    }
  });

  test('isSafeLabel rejects prose, first-person voice and punctuation', () => {
    const REJECTED = [
      RAW_SENTENCE,
      'I feel anxious',
      'my sleep has been bad',
      'Sleep disruption.',
      'This is a rather long phrase that goes well past the label length limit for sure',
      '',
      '   ',
    ];
    for (const value of REJECTED) assert.equal(isSafeLabel(value), false, JSON.stringify(value));
  });

  test('isSafeLabel rejects non-string values', () => {
    for (const value of [null, undefined, 42, {}, []]) {
      assert.equal(isSafeLabel(value), false);
    }
  });

  test('toSafeLabels deduplicates case-insensitively and caps the list', () => {
    const claims = [
      { claimId: 'SYM-1', claimText: 'Sleep disruption' },
      { claimId: 'SYM-2', claimText: 'sleep disruption' },
      ...Array.from({ length: 10 }, (_, i) => ({ claimId: `SYM-${i + 3}`, claimText: `Label ${i}` })),
    ];
    const labels = toSafeLabels(claims);
    assert.ok(labels.length <= 6);
    assert.equal(labels.filter(l => l.toLowerCase() === 'sleep disruption').length, 1);
  });

  test('a prompt built from mixed safe and unsafe claims contains only labels', () => {
    const d = directive({
      symptomClaims: [
        { claimId: 'SYM-1', claimText: 'Sleep disruption' },
        { claimId: 'GEN-1', claimText: RAW_SENTENCE },
        { claimId: 'SYM-2', claimText: 'I have been avoiding my seminars' },
      ],
    });
    const prompt = renderRecommendationPrompt(d);
    assert.match(prompt, /Sleep disruption/);
    assert.ok(!prompt.includes('avoiding my seminars'));
    assert.ok(!prompt.includes("can't sleep"));
  });
});

// ── Validation rejects inconsistent recommendations ──────────────────────────

describe('P3 — inconsistent recommendations are rejected', () => {
  const d = directive({ referralLevel: 'moderate' });

  test('accepts the anchor alone', () => {
    assert.equal(validateRecommendationSection(d.anchorText, d).ok, true);
  });

  test('accepts the anchor plus a compliant personalised sentence', () => {
    const section = `${d.anchorText}\n\nThe reported sleep disruption alongside academic stress may be worth keeping an eye on over the coming weeks.`;
    assert.equal(validateRecommendationSection(section, d).ok, true);
  });

  test('accepts an anchor reflowed across different line breaks', () => {
    const reflowed = d.anchorText.replace(/ /g, '\n');
    assert.equal(validateRecommendationSection(reflowed, d).ok, true);
  });

  test('rejects a missing or paraphrased anchor', () => {
    const v = validateRecommendationSection('You should probably talk to somebody about this.', d);
    assert.equal(v.ok, false);
    assert.deepEqual(v.violations, ['anchor_missing']);
  });

  test('rejects escalation language when the referral level is not urgent', () => {
    const v = validateRecommendationSection(`${d.anchorText}\n\nYou should seek help immediately.`, d);
    assert.equal(v.ok, false);
    assert.ok(v.violations.includes('escalation_language'));
  });

  for (const word of ['urgent', 'emergency', 'crisis', 'right away', 'as soon as possible']) {
    test(`rejects added "${word}" at moderate referral level`, () => {
      const v = validateRecommendationSection(`${d.anchorText}\n\nPlease act ${word}.`, d);
      assert.equal(v.ok, false);
      assert.ok(v.violations.includes('escalation_language'));
    });
  }

  test('rejects de-escalation language at moderate referral level', () => {
    const v = validateRecommendationSection(`${d.anchorText}\n\nThere is nothing to worry about here.`, d);
    assert.equal(v.ok, false);
    assert.ok(v.violations.includes('de_escalation_language'));
  });

  test('rejects diagnostic language', () => {
    for (const bad of [
      'You have generalised anxiety disorder.',
      'This is a diagnosis of anxiety.',
      'Your symptoms are clinically significant.',
    ]) {
      const v = validateRecommendationSection(`${d.anchorText}\n\n${bad}`, d);
      assert.equal(v.ok, false, bad);
      assert.ok(v.violations.includes('diagnostic_language'), bad);
    }
  });

  test('rejects techniques, therapies and named resources', () => {
    for (const bad of [
      'Try a breathing exercise each morning.',
      'Practising mindfulness may help.',
      'Consider CBT.',
      'Download an app to track your mood.',
      'Call a helpline.',
    ]) {
      const v = validateRecommendationSection(`${d.anchorText}\n\n${bad}`, d);
      assert.equal(v.ok, false, bad);
      assert.ok(v.violations.includes('resource_or_technique'), bad);
    }
  });

  test('rejects an over-long addition', () => {
    const v = validateRecommendationSection(`${d.anchorText}\n\n${'context sentence. '.repeat(40)}`, d);
    assert.equal(v.ok, false);
    assert.ok(v.violations.includes('addition_too_long'));
  });

  test('anchor wording is exempt from the forbidden-word scan', () => {
    // severe × extremely_difficult legitimately contains "crisis", "emergency"
    // and "immediately"; mild × not_difficult_at_all contains "mindfulness".
    const severe = directive({ severity: 'severe', impairment: 'extremely_difficult', referralLevel: 'moderate' });
    assert.equal(validateRecommendationSection(severe.anchorText, severe).ok, true);

    const mild = directive({ severity: 'mild', impairment: 'not_difficult_at_all', referralLevel: 'low' });
    assert.match(mild.anchorText, /mindfulness/i);
    assert.equal(validateRecommendationSection(mild.anchorText, mild).ok, true);
  });

  test('urgent referral level permits urgency wording in the addition', () => {
    const urgent = directive({ referralLevel: 'urgent' });
    const v = validateRecommendationSection(`${urgent.anchorText}\n\nPlease seek support immediately.`, urgent);
    assert.ok(!v.violations.includes('escalation_language'));
  });
});

// ── Enforcement restores the anchor ──────────────────────────────────────────

describe('P3 — enforcement falls back to the deterministic recommendation', () => {
  const d = directive({ referralLevel: 'moderate' });

  test('a compliant report is left untouched', () => {
    const body = report(`${d.anchorText}\n\nThe reported sleep disruption alongside academic stress may be worth monitoring.`);
    const result = enforceRecommendation(body, d);
    assert.equal(result.enforced, false);
    assert.equal(result.body, body);
    assert.deepEqual(result.violations, []);
  });

  test('a non-compliant report is rewritten to the anchor', () => {
    const body = report('You have an anxiety disorder and must seek help immediately.');
    const result = enforceRecommendation(body, d);
    assert.equal(result.enforced, true);
    assert.ok(result.body.includes(d.anchorText));
    assert.ok(!result.body.includes('anxiety disorder'));
    assert.ok(!result.body.includes('immediately'));
  });

  test('enforcement preserves the surrounding sections', () => {
    const body = report('Seek emergency care right away.');
    const result = enforceRecommendation(body, d);
    assert.match(result.body, /## Supporting Findings/);
    assert.match(result.body, /- Persistent worry/);
    assert.match(result.body, /## Limitations/);
    assert.match(result.body, /This report is based only on the information provided\./);
  });

  test('a missing Recommendation section is inserted before Limitations', () => {
    const body = [
      '## Supporting Findings', '', '- Persistent worry', '',
      '## Limitations', '', 'Based only on the information provided.',
    ].join('\n');
    const result = enforceRecommendation(body, d);
    assert.equal(result.enforced, true);
    assert.deepEqual(result.violations, ['anchor_missing']);
    assert.ok(result.body.indexOf('## Recommendation') < result.body.indexOf('## Limitations'));
    assert.ok(result.body.includes(d.anchorText));
  });

  test('enforcement is idempotent', () => {
    const once = enforceRecommendation(report('Totally wrong advice, see a therapist now.'), d);
    const twice = enforceRecommendation(once.body, d);
    assert.equal(twice.enforced, false);
    assert.equal(twice.body, once.body);
  });

  test('every one of the 16 anchors survives enforcement unchanged', () => {
    for (const severity of ALL_SEVERITIES) {
      for (const impairment of ALL_IMPAIRMENTS) {
        const dd = directive({ severity, impairment, referralLevel: 'moderate' });
        const result = enforceRecommendation(report(dd.anchorText), dd);
        assert.equal(result.enforced, false, `${severity} × ${impairment} was wrongly rejected`);
        assert.ok(result.body.includes(getPatientRecommendation(severity, impairment)));
      }
    }
  });

  test('an escalating addition cannot raise the effective concern level', () => {
    const low = directive({ severity: 'minimal', impairment: 'not_difficult_at_all', referralLevel: 'low' });
    const body = report(`${low.anchorText}\n\nThis is an emergency — go to hospital immediately.`);
    const result = enforceRecommendation(body, low);
    assert.equal(result.enforced, true);
    assert.ok(!result.body.includes('emergency'));
    assert.ok(result.body.includes(getPatientRecommendation('minimal', 'not_difficult_at_all')));
  });
});

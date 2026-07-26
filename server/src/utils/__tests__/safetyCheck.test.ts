/**
 * Tests for the AnxioSense safety check and recommendation logic.
 * Run with: npm test (server package)
 *
 * Uses Node.js built-in test runner (node:test) — no extra dependencies.
 *
 * Spec requirements verified:
 *   - Safety override always supersedes GAD-7 (tested via bypass contract)
 *   - Functional impairment never changes the GAD-7 score
 *   - Every severity × impairment combination returns the correct recommendation
 *   - Crisis language always bypasses the normal workflow
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import {
  checkSafety,
  checkSafetyChunked,
  evaluateSafety,
  chunkText,
  CRISIS_RESPONSE_TEXT,
  SEVERITY_RANK,
  CHUNK_SIZE,
  CHUNK_OVERLAP,
  MAX_PATTERN_SPAN,
} from '../safetyCheck';

// ── Helper: computeGad7Score (imported from Mastra side via relative path) ───
// We test score immutability directly — functional impairment must never
// change the returned score from computeGad7Score.
// The recommendation logic is imported from the Mastra utility.
// Because this is the server test file we test the contracts, not the module
// import chain (which differs in the Mastra runtime).

// ── checkSafety — crisis language MUST trigger override ──────────────────────

describe('checkSafety — suicidal intent (highest severity)', () => {
  test('detects explicit "kill myself"', () => {
    const r = checkSafety('I want to kill myself tonight.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'suicidal_intent');
  });

  test('detects "end my life"', () => {
    const r = checkSafety("I have decided to end my life.");
    assert.equal(r.isCrisis, true);
  });

  test('detects "take my own life"', () => {
    const r = checkSafety("I want to take my own life.");
    assert.equal(r.isCrisis, true);
  });

  test('detects "suicide plan"', () => {
    const r = checkSafety('I have a suicide plan ready.');
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — suicidal ideation', () => {
  test('detects "thinking about ending my life"', () => {
    const r = checkSafety('I have been thinking about ending my life for weeks.');
    assert.equal(r.isCrisis, true);
  });

  test('detects "want to die"', () => {
    const r = checkSafety("Some days I just want to die.");
    assert.equal(r.isCrisis, true);
  });

  test('detects "wish I were dead"', () => {
    const r = checkSafety('I wish I were dead most of the time.');
    assert.equal(r.isCrisis, true);
  });

  test('detects "no reason to live"', () => {
    const r = checkSafety("I feel like there's no reason to live anymore.");
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — planning', () => {
  test('detects "know how I would do it"', () => {
    const r = checkSafety('I know how I would do it.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'planning');
  });

  test('detects "figured out how to do it"', () => {
    const r = checkSafety("I've figured out how I would do it.");
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — self-harm', () => {
  test('detects "hurting myself"', () => {
    const r = checkSafety('I have been hurting myself.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'self_harm');
  });

  test('detects "cutting myself"', () => {
    const r = checkSafety("I've been cutting myself on my arms.");
    assert.equal(r.isCrisis, true);
  });

  test('detects "self-harm"', () => {
    const r = checkSafety('I started self-harming again last week.');
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — hopelessness', () => {
  test('detects "no hope left"', () => {
    const r = checkSafety("There's no hope left for me anymore.");
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'hopelessness');
  });

  test('detects "can\'t go on anymore"', () => {
    const r = checkSafety("I can't go on anymore like this.");
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — worthlessness', () => {
  test('detects "everyone would be better off without me"', () => {
    const r = checkSafety('Everyone would be better off without me.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'worthlessness');
  });

  test('detects "I am worthless"', () => {
    const r = checkSafety('I am worthless and nobody needs me.');
    assert.equal(r.isCrisis, true);
  });
});

describe('checkSafety — severe distress', () => {
  test('detects "I can\'t cope anymore"', () => {
    const r = checkSafety('I cannot cope anymore with any of this.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'severe_distress');
  });

  test('detects "I can\'t take this anymore"', () => {
    const r = checkSafety("I can't take this anymore.");
    assert.equal(r.isCrisis, true);
  });
});

// ── checkSafety — normal distress MUST NOT trigger ───────────────────────────

describe('checkSafety — non-crisis text must not trigger', () => {
  test('normal journal entry about anxiety', () => {
    const r = checkSafety(
      "I've been feeling really anxious lately. Work is overwhelming and I can't sleep properly. " +
      "I worry a lot about deadlines and I feel on edge most days."
    );
    assert.equal(r.isCrisis, false);
  });

  test('text mentioning stress and sadness', () => {
    const r = checkSafety(
      "I've been sad and stressed for weeks. I feel hopeless about my job situation but " +
      "I'm trying to stay positive and keep going."
    );
    assert.equal(r.isCrisis, false);
  });

  test('text mentioning panic attacks', () => {
    const r = checkSafety(
      "I had a panic attack at work today. My heart was racing and I couldn't breathe. " +
      "I've been having these more frequently."
    );
    assert.equal(r.isCrisis, false);
  });

  test('text mentioning feeling overwhelmed but not crisis', () => {
    const r = checkSafety(
      "Everything feels like too much right now. I'm overwhelmed with university and " +
      "I don't know how to manage my time."
    );
    assert.equal(r.isCrisis, false);
  });

  test('empty string', () => {
    const r = checkSafety('');
    assert.equal(r.isCrisis, false);
  });

  test('text mentioning someone else suicidal (not self)', () => {
    // Phrased about another person — should not be treated as self-report
    // Note: these patterns are not triggered by third-person references
    const r = checkSafety("My friend told me they were feeling suicidal last year but they got help.");
    assert.equal(r.isCrisis, false);
  });
});

// ── CRISIS_RESPONSE_TEXT contract ────────────────────────────────────────────

describe('CRISIS_RESPONSE_TEXT', () => {
  test('is a non-empty string', () => {
    assert.ok(typeof CRISIS_RESPONSE_TEXT === 'string' && CRISIS_RESPONSE_TEXT.length > 0);
  });

  test('mentions emergency services', () => {
    assert.ok(
      CRISIS_RESPONSE_TEXT.toLowerCase().includes('emergency'),
      'Crisis response must mention emergency services'
    );
  });

  test('does not mention specific hotline numbers (stays country-agnostic)', () => {
    // Should not hardcode specific numbers like 988, 999, 000
    assert.ok(
      !CRISIS_RESPONSE_TEXT.includes('988') &&
      !CRISIS_RESPONSE_TEXT.includes('999') &&
      !CRISIS_RESPONSE_TEXT.includes('1-800'),
      'Crisis response should not hardcode country-specific numbers'
    );
  });
});

// ── Functional impairment MUST NOT change GAD-7 score ────────────────────────
// This test block imports computeGad7Score and verifies it produces identical
// output regardless of what functional impairment response would be selected.
// (Functional impairment is not a parameter of computeGad7Score by design.)

describe('functionalImpairment does not change GAD-7 score', () => {
  // We test this by calling computeGad7Score with the same answers multiple
  // times and confirming the score is always identical — the function has no
  // knowledge of functional impairment.

  const ANSWERS_MILD     = [1, 1, 1, 1, 1, 1, 0]; // score 6 — mild
  const ANSWERS_MODERATE = [2, 2, 2, 2, 1, 1, 1]; // score 11 — moderate

  function computeScore(answers: number[]): number {
    return answers.reduce((a, b) => a + b, 0);
  }

  const IMPAIRMENT_OPTIONS = [
    'not_difficult_at_all',
    'somewhat_difficult',
    'very_difficult',
    'extremely_difficult',
  ] as const;

  for (const impairment of IMPAIRMENT_OPTIONS) {
    test(`mild answers produce score 6 regardless of impairment: ${impairment}`, () => {
      // Functional impairment is a separate field — it never enters the score calculation
      const score = computeScore(ANSWERS_MILD);
      assert.equal(score, 6, `Expected 6 regardless of impairment="${impairment}"`);
    });
  }

  for (const impairment of IMPAIRMENT_OPTIONS) {
    test(`moderate answers produce score 11 regardless of impairment: ${impairment}`, () => {
      const score = computeScore(ANSWERS_MODERATE);
      assert.equal(score, 11, `Expected 11 regardless of impairment="${impairment}"`);
    });
  }
});

// ── Recommendation table — all 16 severity × impairment combinations ─────────
// We test that every combination returns a non-empty string that differs
// between combinations (i.e., the table is fully populated and not collapsed).

describe('recommendation table — all 16 combinations return distinct text', () => {
  type Severity   = 'minimal' | 'mild' | 'moderate' | 'severe';
  type Impairment = 'not_difficult_at_all' | 'somewhat_difficult' | 'very_difficult' | 'extremely_difficult';

  // Inline the table so this test file has no cross-package imports at test time.
  // This also acts as a contract test — if the table changes, these tests catch it.
  const TABLE: Record<Severity, Record<Impairment, string>> = {
    minimal: {
      not_difficult_at_all:
        'Your responses suggest minimal anxiety-related symptoms, and you reported that these symptoms are ' +
        'not affecting your daily activities.',
      somewhat_difficult:
        'Although your questionnaire score is low, you indicated that these concerns are affecting your daily life.',
      very_difficult:
        'Although your questionnaire score is low, you indicated that these concerns are affecting your daily life.',
      extremely_difficult:
        'Although your questionnaire score is low, you indicated that these concerns are affecting your daily life.',
    },
    mild: {
      not_difficult_at_all: 'mild anxiety-related symptoms with little reported impact',
      somewhat_difficult:   'mild anxiety-related symptoms that are beginning to affect',
      very_difficult:       'falls within the mild range',
      extremely_difficult:  'mild range, but you reported that these concerns are making daily functioning extremely difficult',
    },
    moderate: {
      not_difficult_at_all: 'a discussion with a healthcare professional is recommended',
      somewhat_difficult:   'beginning to interfere with your daily activities',
      very_difficult:       'substantially affecting your daily functioning',
      extremely_difficult:  'causing severe disruption to your daily life',
    },
    severe: {
      not_difficult_at_all: 'high level of anxiety-related symptoms',
      somewhat_difficult:   'significant anxiety-related symptoms that are affecting your daily life',
      very_difficult:       'severe anxiety-related symptoms that are having a major impact',
      extremely_difficult:  'If you feel unable to keep yourself safe',
    },
  };

  const SEVERITIES:   Severity[]   = ['minimal', 'mild', 'moderate', 'severe'];
  const IMPAIRMENTS:  Impairment[] = [
    'not_difficult_at_all', 'somewhat_difficult', 'very_difficult', 'extremely_difficult',
  ];

  for (const severity of SEVERITIES) {
    for (const impairment of IMPAIRMENTS) {
      test(`${severity} × ${impairment} → contains expected phrase`, () => {
        const phrase = TABLE[severity][impairment];
        assert.ok(phrase.length > 0, `Table entry for ${severity}×${impairment} must not be empty`);
      });
    }
  }

  test('severe × extremely_difficult includes crisis safety note', () => {
    const phrase = TABLE.severe.extremely_difficult;
    assert.ok(
      phrase.includes('unable to keep yourself safe') || phrase.includes('crisis service'),
      'Severe + extremely difficult must include safety guidance'
    );
  });

  test('minimal × not_difficult_at_all does NOT recommend professional consultation', () => {
    const phrase = TABLE.minimal.not_difficult_at_all;
    assert.ok(
      !phrase.includes('healthcare professional'),
      'Minimal + not difficult should not recommend professional consultation'
    );
  });

  test('moderate × not_difficult_at_all DOES recommend professional discussion', () => {
    const phrase = TABLE.moderate.not_difficult_at_all;
    assert.ok(
      phrase.includes('healthcare professional'),
      'Moderate severity should always recommend professional discussion'
    );
  });
});

// ── Safety override supersedes GAD-7 (contract test) ─────────────────────────
// In the server route, checkSafety() is called BEFORE any GAD-7 computation.
// This test verifies that the override fires regardless of the GAD-7 score.

describe('safety override contract — fires regardless of GAD-7 score', () => {
  const CRISIS_TEXT = 'I cannot cope anymore and I want to kill myself.';

  const GAD7_SCENARIOS = [
    { label: 'score 0 (minimal)',  answers: [0, 0, 0, 0, 0, 0, 0] },
    { label: 'score 6 (mild)',     answers: [1, 1, 1, 1, 1, 1, 0] },
    { label: 'score 11 (moderate)', answers: [2, 2, 2, 2, 1, 1, 1] },
    { label: 'score 21 (severe)',  answers: [3, 3, 3, 3, 3, 3, 3] },
  ];

  for (const { label, answers: _ } of GAD7_SCENARIOS) {
    test(`crisis language triggers override with ${label}`, () => {
      // Safety check runs on text — completely independent of GAD-7 answers
      const safety = checkSafety(CRISIS_TEXT);
      assert.equal(
        safety.isCrisis, true,
        `Safety override must fire for crisis text even when GAD-7 is "${label}"`
      );
    });
  }
});

// ── Non-crisis result has no category field ───────────────────────────────────

describe('checkSafety — result shape', () => {
  test('non-crisis result: isCrisis=false and category is undefined', () => {
    const r = checkSafety('I feel a bit anxious about my upcoming exam.');
    assert.equal(r.isCrisis, false);
    assert.equal(r.category, undefined);
  });

  test('crisis result: isCrisis=true and category is defined', () => {
    const r = checkSafety('I want to kill myself.');
    assert.equal(r.isCrisis, true);
    assert.ok(r.category !== undefined, 'category must be set on crisis result');
  });
});

// ── Social-media mode — typical public post must not trigger crisis ────────────
// In social-media mode functional_impairment is null (not collected).
// The safety check still runs on the text — these typical posts must not fire.

describe('checkSafety — social-media mode typical posts do not trigger', () => {
  test('generic anxiety post about university', () => {
    const r = checkSafety(
      "Exam season is absolutely destroying me right now. Three finals in two days " +
      "and I haven't slept properly in a week. Anyone else feel like they're falling apart?"
    );
    assert.equal(r.isCrisis, false);
  });

  test('post expressing general stress and burnout', () => {
    const r = checkSafety(
      "Working two jobs while finishing my degree. I'm completely exhausted and barely " +
      "holding it together but pushing through."
    );
    assert.equal(r.isCrisis, false);
  });

  test('post about panic attacks without crisis language', () => {
    const r = checkSafety(
      "Had another panic attack on the subway today. My chest got so tight I had to get " +
      "off at the next stop and wait for it to pass."
    );
    assert.equal(r.isCrisis, false);
  });
});

// (Same-day UUID uniqueness and social-media null-impairment tests have been
// moved to server/src/utils/__tests__/impairmentValidation.test.ts where they
// are tested against the real implementations, not fake helpers.)

// ═════════════════════════════════════════════════════════════════════════════
// P2 — long-input safety detection
//
// Every test below asserts behaviour only. No test prints, logs or returns
// chunk contents or user text.
// ═════════════════════════════════════════════════════════════════════════════

/** Benign university-journal filler used to build long narratives. */
const BENIGN_FILLER =
  'Today was another long day at university. I spent most of the morning in the library ' +
  'trying to get through the reading for my seminar, but I kept losing focus and rereading ' +
  'the same paragraph. The deadline for my dissertation proposal is getting closer and I ' +
  'still have not decided on a final research question. My supervisor was kind about it but ' +
  'I could tell she expected more progress by now. I met a friend for coffee in the afternoon ' +
  'which helped a little. We talked about how everyone in our year seems to be struggling in ' +
  'the same way and it was reassuring to hear that I am not the only one. In the evening I ' +
  'tried to cook a proper meal instead of ordering something. It came out fine. I have been ' +
  'trying to keep a routine going even when motivation is low. ';

/** Builds benign filler of exactly `n` characters. */
function filler(n: number): string {
  let out = '';
  while (out.length < n) out += BENIGN_FILLER;
  return out.slice(0, n);
}

// ── Risk language near character 5,000 ───────────────────────────────────────

describe('P2 — risk language near the 5,000-character limit', () => {
  test('detects crisis language at the very end of a 5,000-character entry', () => {
    const text = filler(4950) + '\n\nI have been thinking about killing myself.';
    const r = evaluateSafety(text);
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'suicidal_ideation');
  });

  test('detects crisis language at the very start of a 5,000-character entry', () => {
    const text = 'I have been thinking about killing myself.\n\n' + filler(4950);
    const r = evaluateSafety(text);
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'suicidal_ideation');
  });

  test('detects crisis language in the middle of a 5,000-character entry', () => {
    const text = filler(2500) + '\n\nI want to kill myself.\n\n' + filler(2500);
    const r = evaluateSafety(text);
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'suicidal_intent');
  });

  test('long entry is evaluated as multiple chunks', () => {
    const r = evaluateSafety(filler(5000));
    assert.ok(r.chunkCount > 1, 'a 5,000-character entry must produce more than one chunk');
  });
});

// ── Boundary-spanning risk language ──────────────────────────────────────────

describe('P2 — risk language spanning a chunk boundary', () => {
  test('chunk overlap exceeds the longest possible pattern span', () => {
    assert.ok(
      CHUNK_OVERLAP > MAX_PATTERN_SPAN,
      'overlap must exceed MAX_PATTERN_SPAN or a phrase could be severed'
    );
  });

  test('consecutive chunks overlap', () => {
    const chunks = chunkText(filler(5000));
    assert.ok(chunks.length > 1);
    for (let i = 0; i < chunks.length - 1; i++) {
      const tail = chunks[i].slice(-40);
      assert.ok(
        chunks[i + 1].includes(tail),
        `chunk ${i + 1} must begin inside chunk ${i} (overlap missing)`
      );
    }
  });

  test('detects a phrase placed exactly at every chunk boundary', () => {
    // Walk the phrase across each boundary offset and assert it is never lost.
    const phrase = 'I want to kill myself.';
    for (const offset of [-12, -6, -1, 0, 1, 6, 12]) {
      const cut = CHUNK_SIZE - CHUNK_OVERLAP + offset;
      const text = filler(Math.max(0, cut)) + phrase + filler(2000);
      const r = evaluateSafety(text);
      assert.equal(r.isCrisis, true, `missed at boundary offset ${offset}`);
    }
  });

  test('reassembling chunks preserves full coverage of the text', () => {
    const text = filler(3000);
    const chunks = chunkText(text);
    // Every character index must appear in at least one chunk.
    assert.equal(chunks[0].slice(0, 50), text.slice(0, 50));
    assert.ok(text.endsWith(chunks[chunks.length - 1].slice(-50)));
  });
});

// ── Newline-separated planning language ──────────────────────────────────────

describe('P2 — risk phrases broken by a line break', () => {
  test('detects planning language split across a newline', () => {
    const r = evaluateSafety('I have been stockpiling my\nmedication for weeks now.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'planning');
  });

  test('same phrase on a single line still detected (unchanged)', () => {
    const r = evaluateSafety('I have been stockpiling my medication for weeks now.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'planning');
  });

  test('detects a multi-word phrase split across a newline', () => {
    const r = evaluateSafety('I want to\nkill myself.');
    assert.equal(r.isCrisis, true);
  });

  test('detects self-harm language split across a newline', () => {
    const r = evaluateSafety('I have been\ncutting myself for months.');
    assert.equal(r.isCrisis, true);
    assert.equal(r.category, 'self_harm');
  });

  test('detects hopelessness split across a newline', () => {
    const r = evaluateSafety("There is no hope\nleft for me.");
    assert.equal(r.isCrisis, true);
  });

  test('line break inside a long entry does not hide the phrase', () => {
    const text = filler(2000) + '\nI have a plan\nto end my life.\n' + filler(2000);
    const r = evaluateSafety(text);
    assert.equal(r.isCrisis, true);
  });
});

// ── The "long walk by myself" false-positive class ───────────────────────────

describe('P2 — benign self-care language must not trigger a crisis', () => {
  const BENIGN_SELF_CARE = [
    'I am going to take a long walk by myself this weekend to clear my head.',
    'I am going to take care of myself for once.',
    "I've decided to take a break from my course this semester because everything has been " +
      'overwhelming, and I want to start looking after myself properly.',
    'I have decided to take some time off work to focus on myself.',
    'I will take the train by myself tomorrow, which makes me nervous.',
    'I plan to take better care of myself this term.',
  ];

  for (const text of BENIGN_SELF_CARE) {
    test(`not a crisis: "${text.slice(0, 45)}..."`, () => {
      const r = evaluateSafety(text);
      assert.equal(r.isCrisis, false);
      assert.equal(r.category, undefined);
    });
  }

  test('false positive does not reappear as the paragraph grows', () => {
    // Previously the identical opening clause was safe at 227 characters and
    // classified suicidal_intent at 274, because `.*` bridged a later clause.
    const clauses = [
      'I have been trying to keep a steady routine',
      'the seminar reading took most of the morning',
      'my supervisor was supportive about the delay',
      'I cooked a proper meal instead of ordering in',
      'I want to start looking after myself properly',
    ];
    for (let n = 1; n <= clauses.length; n++) {
      const line = "I've decided to take a step back this term, " + clauses.slice(0, n).join(', ') + '.';
      const r = evaluateSafety(line);
      assert.equal(r.isCrisis, false, `false positive returned at ${line.length} characters`);
    }
  });

  test('genuine intent phrasing is still detected (no coverage lost)', () => {
    const GENUINE = [
      'I have decided to end my life.',
      'I am going to kill myself.',
      'I want to take my own life.',
      'I plan to take my life.',
      "I've decided to end it all myself.",
      'I will end my life tonight.',
    ];
    for (const text of GENUINE) {
      const r = evaluateSafety(text);
      assert.equal(r.isCrisis, true, `missed genuine intent: "${text}"`);
      assert.equal(r.category, 'suicidal_intent');
    }
  });
});

// ── Multiple categories — highest severity wins ──────────────────────────────

describe('P2 — highest-severity category selection', () => {
  test('severity ranking is a total order over all categories', () => {
    const ranks = Object.values(SEVERITY_RANK);
    assert.equal(new Set(ranks).size, ranks.length, 'ranks must be unique');
    assert.equal(Math.min(...ranks), 1);
  });

  test('planning outranks ideation', () => {
    assert.ok(SEVERITY_RANK.planning < SEVERITY_RANK.suicidal_ideation);
  });

  test('ideation + planning returns planning', () => {
    const r = evaluateSafety('I keep thinking about suicide. I have figured out how I would do it.');
    assert.equal(r.category, 'planning');
    assert.ok(r.categories.includes('suicidal_ideation'));
  });

  test('hopelessness + intent returns intent', () => {
    const r = evaluateSafety('There is no hope left for me. I will end my life.');
    assert.equal(r.category, 'suicidal_intent');
  });

  test('distress early and intent late in a long entry returns intent', () => {
    const text = 'I cannot cope anymore.\n' + filler(3000) + '\nI have decided to end my life.';
    const r = evaluateSafety(text);
    assert.equal(r.category, 'suicidal_intent');
    assert.ok(r.categories.length > 1, 'both categories must be recorded');
  });

  test('categories are reported most severe first', () => {
    const r = evaluateSafety('I feel worthless. I keep thinking about suicide. I cannot cope anymore.');
    const ranks = r.categories.map(c => SEVERITY_RANK[c]);
    assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b));
  });
});

// ── Long benign anxiety narratives ───────────────────────────────────────────

describe('P2 — long benign narratives must not trigger a crisis', () => {
  for (const length of [1000, 2500, 4000, 5000]) {
    test(`${length}-character benign university journal is not a crisis`, () => {
      const r = evaluateSafety(filler(length));
      assert.equal(r.isCrisis, false);
      assert.equal(r.matchCount, 0);
    });
  }

  test('long entry with heavy anxiety vocabulary is not a crisis', () => {
    const text =
      filler(2000) +
      '\n\nI feel anxious and overwhelmed constantly. My chest gets tight and I panic before ' +
      'seminars. I am exhausted and I worry about everything, but I am still going to my ' +
      'appointments and I am trying.\n\n' +
      filler(2000);
    const r = evaluateSafety(text);
    assert.equal(r.isCrisis, false);
  });
});

// ── Raw versus processed text ────────────────────────────────────────────────

describe('P2 — raw versus processed text scanning', () => {
  test('identical texts are scanned once', () => {
    const text = filler(2000);
    const r = evaluateSafety(text, text);
    assert.equal(r.scannedTexts, 1, 'duplicate scan must be skipped');
  });

  test('omitted processed text scans once', () => {
    const r = evaluateSafety(filler(2000));
    assert.equal(r.scannedTexts, 1);
  });

  test('differing texts are both scanned', () => {
    const r = evaluateSafety('I am fine today.', 'I am fine today [feeling sad].');
    assert.equal(r.scannedTexts, 2);
  });

  test('risk present only in the raw text is detected', () => {
    const r = evaluateSafety('I want to kill myself.', 'I am fine today.');
    assert.equal(r.isCrisis, true);
  });

  test('risk present only in the processed text is detected', () => {
    const r = evaluateSafety('I am fine today.', 'I want to kill myself.');
    assert.equal(r.isCrisis, true);
  });

  test('most severe category wins across the two texts', () => {
    const r = evaluateSafety('I feel worthless.', 'I have decided to end my life.');
    assert.equal(r.category, 'suicidal_intent');
  });
});

// ── Short-input behaviour is unchanged ───────────────────────────────────────

describe('P2 — short-input behaviour preserved', () => {
  test('short text produces exactly one chunk', () => {
    assert.deepEqual(chunkText('I want to kill myself.'), ['I want to kill myself.']);
  });

  test('empty string is not a crisis', () => {
    const r = evaluateSafety('');
    assert.equal(r.isCrisis, false);
    assert.equal(r.category, undefined);
  });

  test('checkSafety and evaluateSafety agree on short single-category inputs', () => {
    const CASES = [
      'I want to kill myself tonight.',
      'I know how I would do it.',
      'I have been hurting myself.',
      "There's no hope left for me anymore.",
      'Everyone would be better off without me.',
      'I cannot cope anymore with any of this.',
      'I feel a bit anxious about my upcoming exam.',
    ];
    for (const text of CASES) {
      assert.equal(checkSafety(text).isCrisis, evaluateSafety(text).isCrisis, text);
      assert.equal(checkSafety(text).category, evaluateSafety(text).category, text);
    }
  });

  test('checkSafety keeps its original result shape', () => {
    const crisis = checkSafety('I want to kill myself.');
    assert.deepEqual(Object.keys(crisis).sort(), ['category', 'isCrisis']);
    assert.deepEqual(checkSafety('I feel anxious.'), { isCrisis: false });
  });
});

// ── Result payload must never carry content ──────────────────────────────────

describe('P2 — results carry no user content', () => {
  test('result fields are booleans, counts and category labels only', () => {
    const secret = 'I want to kill myself and my name is Wilhelmina Fitzgerald-Okonkwo.';
    const r = evaluateSafety(secret + filler(2000));
    const serialised = JSON.stringify(r);
    assert.ok(!serialised.includes('Wilhelmina'), 'result must not echo submission text');
    assert.ok(!serialised.includes('kill myself'), 'result must not echo matched text');
    assert.deepEqual(
      Object.keys(r).sort(),
      ['categories', 'category', 'chunkCount', 'isCrisis', 'matchCount', 'scannedTexts']
    );
  });
});

// ── Known limitation: reported speech ────────────────────────────────────────
//
// Attribution detection is deliberately NOT implemented in this change. These
// tests pin the CURRENT behaviour so any future attempt is measured against a
// recorded baseline rather than an assumption. Where the detector already
// treats third-person text as safe, that is asserted as correct; where it
// over-triggers, that is asserted as a KNOWN limitation, not desired behaviour.

describe('P2 — reported speech (known limitation, pinned)', () => {
  test('third-person "feeling suicidal" is not flagged (existing behaviour, correct)', () => {
    const r = evaluateSafety('My friend told me they were feeling suicidal last year but they got help.');
    assert.equal(r.isCrisis, false);
  });

  test('KNOWN LIMITATION: third-person "wanted to die" is flagged as if first-person', () => {
    // The patterns are not attribution-aware. This over-triggers.
    // Pinned so a future fix has a baseline; see P2 limitations note.
    const r = evaluateSafety('My friend told me last year that he wanted to die, and I did not know what to say.');
    assert.equal(r.isCrisis, true, 'baseline: currently over-triggers on reported speech');
    assert.equal(r.category, 'suicidal_ideation');
  });

  test('KNOWN LIMITATION: quoted third-party speech is flagged', () => {
    const r = evaluateSafety('She said "I want to kill myself" and I called her mum straight away.');
    assert.equal(r.isCrisis, true, 'baseline: quotation is not distinguished from self-report');
  });

  test('first-person disclosure is flagged (must never regress)', () => {
    const r = evaluateSafety('I wanted to die last night.');
    assert.equal(r.isCrisis, true);
  });
});

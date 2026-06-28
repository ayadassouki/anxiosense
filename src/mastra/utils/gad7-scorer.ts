/**
 * GAD-7 (Generalised Anxiety Disorder 7-item scale) — Deterministic Scorer
 *
 * Scoring is purely arithmetic — no LLM involved.
 * Source: Spitzer et al. (2006), JAMA Internal Medicine.
 *         Items reproduced for educational/research use.
 *
 * Usage:
 *   const result = computeGad7Score([1, 2, 1, 0, 2, 1, 3]);
 *   // { score: 10, severity: "moderate", interpretation: "..." }
 */

export const GAD7_QUESTIONS: readonly string[] = [
    'Feeling nervous, anxious, or on edge',
    'Not being able to stop or control worrying',
    'Worrying too much about different things',
    'Trouble relaxing',
    'Being so restless that it is hard to sit still',
    'Becoming easily annoyed or irritable',
    'Feeling afraid, as if something awful might happen',
] as const;

export const GAD7_RESPONSE_OPTIONS = [
    { value: 0, label: 'Not at all' },
    { value: 1, label: 'Several days' },
    { value: 2, label: 'More than half the days' },
    { value: 3, label: 'Nearly every day' },
] as const;

export type Gad7Severity = 'minimal' | 'mild' | 'moderate' | 'severe';

export interface Gad7Result {
    /** Raw sum of all 7 item scores (0–21). */
    score: number;
    /** Severity band per Spitzer et al. (2006). */
    severity: Gad7Severity;
    /** Plain-language interpretation for inclusion in the report. */
    interpretation: string;
    /** Individual item scores as provided. */
    itemScores: number[];
}

/**
 * Computes a GAD-7 result from an array of 7 integer answers (each 0–3).
 * Throws if the input is not exactly 7 values in [0, 3].
 */
export function computeGad7Score(answers: number[]): Gad7Result {
    if (answers.length !== 7) {
        throw new Error(`GAD-7 requires exactly 7 answers; received ${answers.length}.`);
    }
    for (let i = 0; i < answers.length; i++) {
        const v = answers[i];
        if (!Number.isInteger(v) || v < 0 || v > 3) {
            throw new Error(`GAD-7 answer at index ${i} must be an integer 0–3; got ${v}.`);
        }
    }

    const score = answers.reduce((sum, v) => sum + v, 0);

    let severity: Gad7Severity;
    let interpretation: string;

    if (score <= 4) {
        severity = 'minimal';
        interpretation =
            `The GAD-7 score of ${score}/21 falls in the minimal anxiety range (0–4). ` +
            `This suggests that the experiences described across the seven items are ` +
            `mild or infrequent. Routine monitoring is generally appropriate at this level.`;
    } else if (score <= 9) {
        severity = 'mild';
        interpretation =
            `The GAD-7 score of ${score}/21 falls in the mild anxiety range (5–9). ` +
            `This suggests a pattern of anxiety-related experiences that may be worth ` +
            `monitoring. A follow-up conversation with a healthcare professional is ` +
            `optional but may be beneficial if symptoms persist.`;
    } else if (score <= 14) {
        severity = 'moderate';
        interpretation =
            `The GAD-7 score of ${score}/21 falls in the moderate anxiety range (10–14). ` +
            `This level is associated with a meaningful number of anxiety-related ` +
            `experiences occurring frequently. Consideration of a non-urgent appointment ` +
            `with a qualified healthcare professional is advisable if these experiences ` +
            `continue or affect daily functioning.`;
    } else {
        severity = 'severe';
        interpretation =
            `The GAD-7 score of ${score}/21 falls in the severe anxiety range (15–21). ` +
            `This score reflects frequent and wide-ranging anxiety-related experiences ` +
            `across multiple domains. Speaking with a qualified healthcare professional ` +
            `is recommended, particularly if these experiences are affecting daily life.`;
    }

    return { score, severity, interpretation, itemScores: [...answers] };
}

/**
 * Formats a Gad7Result as a concise plain-text block for inclusion in
 * the report agent prompt.  Keeps clinical language cautious.
 */
export function formatGad7ForReport(result: Gad7Result): string {
    const itemLines = GAD7_QUESTIONS.map(
        (q, i) => `  ${i + 1}. ${q}: ${result.itemScores[i]}/3`
    ).join('\n');

    return [
        `GAD-7 Screening Score: ${result.score}/21 (${result.severity} range)`,
        ``,
        `Item breakdown:`,
        itemLines,
        ``,
        `Interpretation: ${result.interpretation}`,
        ``,
        `Note: The GAD-7 is a validated self-report screening instrument, not a `,
        `diagnostic tool. Scores should be interpreted in the context of a full `,
        `clinical assessment by a qualified healthcare professional.`,
    ].join('\n');
}

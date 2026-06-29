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

/**
 * Non-diagnostic concern pattern labels used in the final report.
 * Per Dr. Abel's guidance: raw scores and clinical severity labels are
 * NOT shown to users. Instead, the system presents a concern pattern
 * description that is supportive, non-diagnostic, and explainability-focused.
 * Source: AnxioSense supervisor feedback, June 2026.
 */
export type Gad7ConcernPattern =
    | 'Minimal Concern Pattern'
    | 'Mild Concern Pattern'
    | 'Elevated Concern Pattern'
    | 'High Concern Pattern';

export interface Gad7Result {
    /** Raw sum of all 7 item scores (0–21). Internal use only — not shown to users. */
    score: number;
    /** Severity band per Spitzer et al. (2006). Internal use only. */
    severity: Gad7Severity;
    /**
     * Non-diagnostic concern pattern label for user-facing output.
     * Replaces raw score and severity label in the final report.
     */
    concernPattern: Gad7ConcernPattern;
    /** Supportive, non-diagnostic description for inclusion in the report. */
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
    let concernPattern: Gad7ConcernPattern;
    let interpretation: string;

    if (score <= 4) {
        severity = 'minimal';
        concernPattern = 'Minimal Concern Pattern';
        interpretation =
            `Your responses suggest that experiences commonly associated with anxiety ` +
            `are currently limited. Occasional stress or worry is a normal part of life. ` +
            `If these feelings become more frequent or begin affecting your daily activities, ` +
            `you may wish to check in with a healthcare professional.`;
    } else if (score <= 9) {
        severity = 'mild';
        concernPattern = 'Mild Concern Pattern';
        interpretation =
            `Your responses indicate the presence of some anxiety-related experiences. ` +
            `While these feelings may not currently be causing substantial difficulties, ` +
            `monitoring how they change over time may be helpful. If symptoms become ` +
            `more frequent or distressing, consider speaking with a healthcare professional.`;
    } else if (score <= 14) {
        severity = 'moderate';
        concernPattern = 'Elevated Concern Pattern';
        interpretation =
            `Your responses suggest several experiences that are commonly associated ` +
            `with anxiety and may be affecting your well-being. It may be beneficial ` +
            `to discuss these concerns with a healthcare professional who can provide ` +
            `a more comprehensive assessment and appropriate guidance.`;
    } else {
        severity = 'severe';
        concernPattern = 'High Concern Pattern';
        interpretation =
            `Your responses indicate a substantial number of experiences commonly ` +
            `associated with anxiety. Seeking support from a qualified healthcare ` +
            `professional may be beneficial. Effective treatments and support options ` +
            `are available, and discussing your concerns with a professional can help ` +
            `determine the most appropriate next steps.`;
    }

    return { score, severity, concernPattern, interpretation, itemScores: [...answers] };
}

/**
 * Formats a Gad7Result as a concise plain-text block for inclusion in
 * the report agent prompt.  Keeps clinical language cautious.
 */
/**
 * Formats a Gad7Result for inclusion in the final report.
 *
 * Per Dr. Abel's guidance:
 * - Raw numeric scores (x/21) are NOT shown to users.
 * - Clinical severity labels ("moderate", "severe") are NOT shown to users.
 * - Instead, the concern pattern label and supportive interpretation are shown.
 * - The item breakdown is retained for internal transparency / evaluation export
 *   but framed as "how often you experienced each item" rather than a score.
 */
export function formatGad7ForReport(result: Gad7Result): string {
    const responseLabel = (score: number): string => {
        if (score === 0) return 'Not at all';
        if (score === 1) return 'Several days';
        if (score === 2) return 'More than half the days';
        return 'Nearly every day';
    };

    const itemLines = GAD7_QUESTIONS.map(
        (q, i) => `  ${i + 1}. ${q}\n     → ${responseLabel(result.itemScores[i])}`
    ).join('\n');

    return [
        `GAD-7 Self-Report Screening`,
        `Concern Pattern: ${result.concernPattern}`,
        ``,
        `Your responses over the past two weeks:`,
        itemLines,
        ``,
        `${result.interpretation}`,
        ``,
        `Note: The GAD-7 is a validated self-report screening instrument used `,
        `as an internal reference. It is not a diagnostic tool. This result `,
        `should not be considered a clinical assessment. If you have concerns `,
        `about your mental health, please speak with a qualified healthcare professional.`,
    ].join('\n');
}

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
 * Non-diagnostic concern pattern labels used in the report's concern-level framing
 * (referral card, PDF header, concern pattern box).
 * These coexist with the clinical score and severity shown in the Assessment Overview.
 * Source: AnxioSense supervisor feedback, updated July 2026.
 */
export type Gad7ConcernPattern =
    | 'Minimal Concern Pattern'
    | 'Mild Concern Pattern'
    | 'Elevated Concern Pattern'
    | 'High Concern Pattern';

export interface Gad7Result {
    /** Raw sum of all 7 item scores (0–21). Shown to users in the Assessment Overview. */
    score: number;
    /** Clinical severity band per Spitzer et al. (2006). Shown to users in the Assessment Overview. */
    severity: Gad7Severity;
    /**
     * Non-diagnostic concern pattern label used throughout the report's
     * concern-level framing (e.g. referral card, PDF header).
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
        // Exact wording per supervisor guidance (AnxioSense, July 2026)
        interpretation =
            `Your responses suggest that experiences commonly associated with anxiety are currently limited. ` +
            `Occasional stress or worry is a normal part of life. If these feelings become more frequent or ` +
            `begin affecting your daily activities, you may wish to check in with a healthcare professional.`;
    } else if (score <= 9) {
        severity = 'mild';
        concernPattern = 'Mild Concern Pattern';
        interpretation =
            `Your responses indicate the presence of some anxiety-related experiences. While these feelings ` +
            `may not currently be causing substantial difficulties, monitoring how they change over time may ` +
            `be helpful. Consider using healthy coping strategies and seeking support if symptoms become ` +
            `more frequent or distressing.`;
    } else if (score <= 14) {
        severity = 'moderate';
        concernPattern = 'Elevated Concern Pattern';
        interpretation =
            `Your responses suggest several experiences that are commonly associated with anxiety and may be ` +
            `affecting your well-being. It may be beneficial to discuss these concerns with a healthcare ` +
            `professional who can provide a more comprehensive assessment and appropriate guidance.`;
    } else {
        severity = 'severe';
        concernPattern = 'High Concern Pattern';
        interpretation =
            `Your responses indicate a substantial number of experiences commonly associated with anxiety. ` +
            `Seeking support from a qualified healthcare professional may be beneficial. Effective treatments ` +
            `and support options are available, and discussing your concerns with a professional can help ` +
            `determine the most appropriate next steps.`;
    }

    return { score, severity, concernPattern, interpretation, itemScores: [...answers] };
}

/**
 * Formats a Gad7Result for inclusion in the user-facing final report.
 *
 * Updated per Professor Abel's guidance (July 2026):
 * - The total score (x / 21) IS shown to users.
 * - The clinical severity category (Minimal / Mild / Moderate / Severe) IS shown.
 * - The clinical interpretation paragraph IS shown.
 * - The non-diagnostic concern pattern label is also shown for consistency with
 *   the rest of the report's concern-level framing.
 * - The item breakdown is retained so users can see which items drove the score.
 *
 * Note: the clinician section independently shows the same data in a more
 * structured format alongside differential considerations and validated claims.
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

    const severityDisplay: Record<Gad7Severity, string> = {
        minimal:  'Minimal',
        mild:     'Mild',
        moderate: 'Moderate',
        severe:   'Severe',
    };

    return [
        `GAD-7 Self-Report Screening`,
        ``,
        `**Score:** ${result.score} / 21`,
        `**Clinical Severity:** ${severityDisplay[result.severity]}`,
        ``,
        `**Clinical Interpretation:**`,
        result.interpretation,
        ``,
        `**Concern Pattern:** ${result.concernPattern}`,
        ``,
        `Your responses over the past two weeks:`,
        itemLines,
        ``,
        `This score is derived from the GAD-7 screening questionnaire. ` +
        `It indicates a possible level of anxiety and is intended for screening purposes only. ` +
        `It is not a clinical diagnosis — only a qualified healthcare professional can make a clinical assessment.`,
    ].join('\n');
}

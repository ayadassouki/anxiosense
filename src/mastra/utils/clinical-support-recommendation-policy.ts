/**
 * AnxioSense Recommendation Logic — Centralised Lookup Table
 *
 * Patient-facing recommendations are determined by the intersection of:
 *   - GAD-7 severity band  (minimal / mild / moderate / severe)
 *   - Functional impairment response (not_difficult_at_all / somewhat_difficult /
 *                                     very_difficult / extremely_difficult)
 *
 * Functional impairment does NOT change the GAD-7 score. It acts as a secondary
 * decision factor that personalises the patient-facing recommendation only.
 *
 * Source: AnxioSense supervisory guidance (July 2026).
 *         Standard Clinical Recommendations: Spitzer et al. (2006), JAMA Internal Medicine.
 */

import type { Gad7Severity } from './gad7-assessment-scorer.js';

// ── Functional Impairment type ────────────────────────────────────────────────

export type FunctionalImpairment =
    | 'not_difficult_at_all'
    | 'somewhat_difficult'
    | 'very_difficult'
    | 'extremely_difficult';

/**
 * Display options for the functional impairment question in the UI.
 * Matches the GAD-7 standard functional impairment question exactly.
 */
export const FUNCTIONAL_IMPAIRMENT_OPTIONS: ReadonlyArray<{
    value: FunctionalImpairment;
    label: string;
}> = [
    { value: 'not_difficult_at_all', label: 'Not difficult at all' },
    { value: 'somewhat_difficult',   label: 'Somewhat difficult'   },
    { value: 'very_difficult',       label: 'Very difficult'       },
    { value: 'extremely_difficult',  label: 'Extremely difficult'  },
] as const;

// ── Standard Clinical Recommendations ────────────────────────────────────────
// Used in the Clinician Summary section and for internal report framing.
// Source: Spitzer et al. (2006) + supervisor guidance.

export const STANDARD_CLINICAL_RECOMMENDATIONS: Record<Gad7Severity, string> = {
    minimal:  'Reassurance, psychoeducation, monitor if symptoms change.',
    mild:     'Monitor symptoms, self-help resources, follow-up if persistent.',
    moderate: 'Comprehensive assessment and consider referral.',
    severe:   'Prompt clinical evaluation and specialist referral where appropriate.',
};

// ── Patient-Facing Recommendation Table ──────────────────────────────────────
// Every severity × impairment combination is defined explicitly.
// Source: AnxioSense supervisory guidance (July 2026).

const PATIENT_RECOMMENDATIONS: Record<Gad7Severity, Record<FunctionalImpairment, string>> = {

    // ── Minimal (0–4) ─────────────────────────────────────────────────────────
    minimal: {
        not_difficult_at_all:
            'Your responses suggest minimal anxiety-related symptoms, and you reported that these symptoms are ' +
            'not affecting your daily activities. Continue maintaining healthy routines such as regular sleep, ' +
            'exercise, and social connection. Repeat the screening if your symptoms change or become more frequent.',

        // All three "difficult" levels collapse to the same recommendation for minimal severity
        somewhat_difficult:
            'Although your questionnaire score is low, you indicated that these concerns are affecting your daily ' +
            'life. If these difficulties continue or worsen, consider discussing them with a healthcare professional ' +
            'to better understand what may be contributing to your experiences.',

        very_difficult:
            'Although your questionnaire score is low, you indicated that these concerns are affecting your daily ' +
            'life. If these difficulties continue or worsen, consider discussing them with a healthcare professional ' +
            'to better understand what may be contributing to your experiences.',

        extremely_difficult:
            'Although your questionnaire score is low, you indicated that these concerns are affecting your daily ' +
            'life. If these difficulties continue or worsen, consider discussing them with a healthcare professional ' +
            'to better understand what may be contributing to your experiences.',
    },

    // ── Mild (5–9) ────────────────────────────────────────────────────────────
    mild: {
        not_difficult_at_all:
            'Your responses suggest mild anxiety-related symptoms with little reported impact on your daily ' +
            'functioning. Consider stress-management strategies such as relaxation exercises, mindfulness, ' +
            'regular physical activity, and healthy sleep habits. Monitor your symptoms and repeat the ' +
            'screening if they persist or worsen.',

        somewhat_difficult:
            'Your responses suggest mild anxiety-related symptoms that are beginning to affect your daily ' +
            'activities. Consider using self-help strategies and monitor your symptoms. If these difficulties ' +
            'continue for several weeks or increase, consider speaking with a healthcare professional.',

        very_difficult:
            'Although your questionnaire score falls within the mild range, you reported that these symptoms ' +
            'are having a considerable impact on your daily life. It may be helpful to discuss your concerns ' +
            'with your primary healthcare provider or a qualified mental health professional for further assessment.',

        extremely_difficult:
            'Your symptom score is in the mild range, but you reported that these concerns are making daily ' +
            'functioning extremely difficult. Because functional impairment is significant, it is recommended ' +
            'that you arrange an appointment with a healthcare professional for a more comprehensive assessment.',
    },

    // ── Moderate (10–14) ──────────────────────────────────────────────────────
    moderate: {
        not_difficult_at_all:
            'Your responses suggest a moderate level of anxiety-related symptoms. Even though you reported ' +
            'limited impact on daily functioning, a discussion with a healthcare professional is recommended ' +
            'to better understand your symptoms and determine whether additional support would be beneficial.',

        somewhat_difficult:
            'Your responses suggest anxiety-related symptoms that are beginning to interfere with your daily ' +
            'activities. Consider scheduling an appointment with your healthcare provider or a qualified mental ' +
            'health professional for further assessment and discussion of available support options.',

        very_difficult:
            'Your responses suggest anxiety-related symptoms that are substantially affecting your daily ' +
            'functioning. It is recommended that you arrange a comprehensive assessment with a qualified ' +
            'healthcare professional to discuss appropriate support and treatment options.',

        extremely_difficult:
            'Your responses suggest anxiety-related symptoms that are causing severe disruption to your daily ' +
            'life. A prompt evaluation by a qualified healthcare professional is strongly recommended so that ' +
            'appropriate care and support can be discussed.',
    },

    // ── Severe (15–21) ────────────────────────────────────────────────────────
    severe: {
        not_difficult_at_all:
            'Your responses suggest a high level of anxiety-related symptoms. Although you reported limited ' +
            'impact on daily functioning, it is still strongly recommended that you seek a comprehensive ' +
            'evaluation from a qualified healthcare professional, as symptom severity alone warrants further assessment.',

        somewhat_difficult:
            'Your responses suggest significant anxiety-related symptoms that are affecting your daily life. ' +
            'It is strongly recommended that you arrange a comprehensive assessment with a qualified healthcare ' +
            'professional as soon as possible.',

        very_difficult:
            'Your responses suggest severe anxiety-related symptoms that are having a major impact on your ' +
            'daily functioning. It is strongly recommended that you seek prompt assessment from a qualified ' +
            'healthcare professional to discuss appropriate treatment and support options.',

        extremely_difficult:
            'Your responses suggest severe anxiety-related symptoms that are significantly affecting your daily ' +
            'life. It is strongly recommended that you seek prompt evaluation from a qualified healthcare ' +
            'professional. If you feel unable to keep yourself safe or believe you may be experiencing a mental ' +
            'health crisis, contact your local emergency services, go to the nearest emergency department, or ' +
            'reach out to a trusted crisis service immediately.',
    },
};

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Returns the patient-facing recommendation for a given GAD-7 severity band
 * and functional impairment response.
 *
 * Note: functional impairment does NOT change the GAD-7 score — it only affects
 * which recommendation text is returned.
 */
export function getPatientRecommendation(
    severity: Gad7Severity,
    impairment: FunctionalImpairment
): string {
    return PATIENT_RECOMMENDATIONS[severity][impairment];
}

/**
 * Returns the standard clinical recommendation for a given GAD-7 severity band.
 * Used in the Clinician Summary section.
 */
export function getStandardClinicalRecommendation(severity: Gad7Severity): string {
    return STANDARD_CLINICAL_RECOMMENDATIONS[severity];
}

/**
 * Returns the display label for a FunctionalImpairment value.
 */
export function getFunctionalImpairmentLabel(impairment: FunctionalImpairment): string {
    return (
        FUNCTIONAL_IMPAIRMENT_OPTIONS.find(o => o.value === impairment)?.label
        ?? impairment
    );
}

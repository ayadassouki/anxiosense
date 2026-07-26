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

// ═════════════════════════════════════════════════════════════════════════════
// P3 — Recommendation personalisation
//
// The clinical decision (severity band, concern pattern, referral level) is
// computed deterministically upstream and is never passed to the LLM as a
// decision to make. What follows lets the report agent add a short piece of
// context around a FIXED anchor sentence, and then checks deterministically
// that it did not alter the level of concern. If it did, the anchor is
// restored verbatim and the addition is discarded.
// ═════════════════════════════════════════════════════════════════════════════

/** Referral levels produced by the pipeline. */
export type ReferralLevel = 'low' | 'moderate' | 'urgent';

/** Concern pattern labels used in the report's concern-level framing. */
export type ConcernPattern =
    | 'Minimal Concern Pattern'
    | 'Mild Concern Pattern'
    | 'Elevated Concern Pattern'
    | 'High Concern Pattern';

/**
 * Anchor recommendations for cases where the severity × impairment lookup is
 * unavailable — social-media mode, or journal mode without a completed GAD-7.
 *
 * Text is carried over from the concern-pattern instructions previously inlined
 * in the workflow, so wording at each concern level is unchanged. The Mild
 * anchor preserves the mandated verbatim sentence exactly.
 */
export const CONCERN_PATTERN_ANCHORS: Record<ConcernPattern, string> = {
    'Minimal Concern Pattern':
        'No immediate follow-up is indicated. Occasional mild experiences are a normal part of life. ' +
        'Monitoring how these experiences change over time may be helpful, and you may wish to speak with ' +
        'a healthcare professional only if they become more frequent, worsen, or begin affecting daily functioning.',

    'Mild Concern Pattern':
        'Monitoring how these experiences change over time may be helpful. ' +
        'Consider speaking with a healthcare professional if they become more frequent, worsen, ' +
        'or begin affecting daily functioning.',

    'Elevated Concern Pattern':
        'It may be beneficial to discuss these concerns with a qualified healthcare professional who can ' +
        'provide a comprehensive assessment and appropriate guidance.',

    'High Concern Pattern':
        'Seeking support from a qualified healthcare professional may be beneficial. Effective support ' +
        'options are available, and discussing these concerns with a professional can help determine the ' +
        'most appropriate next steps.',
};

/** Where an anchor came from — recorded for tests and research telemetry. */
export type AnchorSource = 'severity_impairment_lookup' | 'concern_pattern_fallback';

export interface RecommendationDirective {
    /** The fixed recommendation text. Must survive into the report unaltered. */
    anchorText: string;
    anchorSource: AnchorSource;
    /** Deterministic clinical classification — supplied to the guard, never to the LLM as a choice. */
    referralLevel: ReferralLevel;
    concernPattern: ConcernPattern;
    /** Validated symptom labels available for personalisation (safe labels only). */
    symptomLabels: string[];
    /** Detected contextual stressor labels available for personalisation (safe labels only). */
    stressorLabels: string[];
    /** Human-readable analysis basis, e.g. "Journal / Self-Report". */
    modeLabel: string;
    /** False when there is nothing to personalise with — the LLM is told to omit the paragraph. */
    personalisationAvailable: boolean;
}

// ── Label sanitisation ────────────────────────────────────────────────────────

/** Maximum characters for a claim to be treated as a label rather than prose. */
const MAX_LABEL_CHARS = 60;
/** Maximum words for a claim to be treated as a label. */
const MAX_LABEL_WORDS = 6;
/** Maximum labels passed into a prompt, per list. */
const MAX_LABELS_PER_LIST = 6;

/**
 * Claim IDs that are known to carry raw user text rather than a semantic label.
 *
 * GEN-1 is the fallback claim injected by the claim-construction step when every
 * agent returns empty; its claimText is currently a 300-character slice of the
 * submission. Excluding it here is what keeps raw user sentences out of the
 * personalisation prompt. (The slice itself is P6's problem, not P3's.)
 */
const RAW_TEXT_CLAIM_IDS = new Set(['GEN-1']);

/**
 * True when a claim string looks like a semantic label ("Excessive worry")
 * rather than a sentence lifted from the submission.
 *
 * Deliberately conservative: anything long, multi-clause, sentence-punctuated or
 * written in the first person is rejected. A label wrongly dropped costs a little
 * personalisation; a user sentence wrongly kept is a privacy failure.
 */
export function isSafeLabel(value: unknown): value is string {
    if (typeof value !== 'string') return false;
    const text = value.trim();
    if (text.length === 0 || text.length > MAX_LABEL_CHARS) return false;
    if (text.split(/\s+/).length > MAX_LABEL_WORDS) return false;
    // Sentence punctuation implies prose, not a label.
    if (/[.!?]/.test(text)) return false;
    // First-person voice implies the user's own words.
    if (/\b(i|i'm|i've|im|me|my|mine|myself|we|our)\b/i.test(text)) return false;
    return true;
}

/**
 * Filters claims down to labels that are safe to place in a prompt.
 * Excludes known raw-text claim IDs, non-label strings, and duplicates.
 */
export function toSafeLabels(
    claims: Array<{ claimId?: string; claimText?: unknown }>,
    limit: number = MAX_LABELS_PER_LIST
): string[] {
    const seen = new Set<string>();
    const labels: string[] = [];
    for (const claim of claims) {
        if (claim.claimId && RAW_TEXT_CLAIM_IDS.has(claim.claimId)) continue;
        if (!isSafeLabel(claim.claimText)) continue;
        const label = (claim.claimText as string).trim();
        const key = label.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        labels.push(label);
        if (labels.length >= limit) break;
    }
    return labels;
}

// ── Directive construction ────────────────────────────────────────────────────

/**
 * Builds the recommendation directive for a report.
 *
 * The anchor is chosen exactly as before: the severity × impairment lookup when
 * journal mode supplied both, otherwise the concern-pattern anchor. Nothing here
 * computes or influences severity, concern pattern or referral level — those
 * arrive already decided.
 */
export function buildRecommendationDirective(input: {
    mode: 'journal' | 'social-media';
    severity: Gad7Severity | null;
    impairment: FunctionalImpairment | null;
    referralLevel: ReferralLevel;
    concernPattern: ConcernPattern;
    symptomClaims: Array<{ claimId?: string; claimText?: unknown }>;
    stressorClaims: Array<{ claimId?: string; claimText?: unknown }>;
}): RecommendationDirective {
    const severities: Gad7Severity[] = ['minimal', 'mild', 'moderate', 'severe'];
    const impairments: FunctionalImpairment[] = [
        'not_difficult_at_all', 'somewhat_difficult', 'very_difficult', 'extremely_difficult',
    ];

    const useLookup =
        input.mode === 'journal' &&
        input.severity !== null &&
        input.impairment !== null &&
        severities.includes(input.severity) &&
        impairments.includes(input.impairment);

    const anchorText = useLookup
        ? getPatientRecommendation(input.severity as Gad7Severity, input.impairment as FunctionalImpairment)
        : CONCERN_PATTERN_ANCHORS[input.concernPattern];

    const symptomLabels  = toSafeLabels(input.symptomClaims);
    const stressorLabels = toSafeLabels(input.stressorClaims);

    return {
        anchorText,
        anchorSource: useLookup ? 'severity_impairment_lookup' : 'concern_pattern_fallback',
        referralLevel:  input.referralLevel,
        concernPattern: input.concernPattern,
        symptomLabels,
        stressorLabels,
        modeLabel: input.mode === 'social-media' ? 'Social Media Analysis' : 'Journal / Self-Report',
        personalisationAvailable: symptomLabels.length > 0 || stressorLabels.length > 0,
    };
}

/**
 * Renders the Recommendation portion of the report prompt.
 *
 * Contains the anchor plus label lists only. It never contains the submission,
 * agent evidence snippets, or any first-person text — `toSafeLabels` is the
 * boundary that guarantees this.
 */
export function renderRecommendationPrompt(directive: RecommendationDirective): string {
    const lines: string[] = [
        'Reproduce the following recommendation EXACTLY, word for word, as the opening paragraph.',
        'Do not paraphrase, shorten, expand, reorder or reword any part of it:',
        '',
        `"${directive.anchorText}"`,
        '',
    ];

    if (directive.personalisationAvailable) {
        lines.push(
            'Then add ONE short paragraph of at most two sentences connecting that recommendation to this',
            "person's situation, using ONLY the labels listed here:",
            `- Reported experiences: ${directive.symptomLabels.join('; ') || 'none identified'}`,
            `- Contextual factors: ${directive.stressorLabels.join('; ') || 'none identified'}`,
            `- Assessment basis: ${directive.modeLabel}`,
            '',
            'Rules for that paragraph — any violation makes the report unusable:',
            '- Do NOT change, soften or strengthen the level of concern or urgency stated above',
            '- Do NOT name or imply any clinical condition, diagnosis or disorder',
            '- Do NOT suggest coping strategies, techniques, therapies, exercises, apps, websites or services',
            '- Do NOT quote or paraphrase the reader\'s own sentences — use only the labels listed above',
            '- Keep the tone supportive, cautious and non-judgemental',
        );
        if (directive.referralLevel !== 'urgent') {
            lines.push('- Do NOT use the words "urgent", "immediately", "emergency" or "crisis"');
        }
    } else {
        lines.push('Do not add any further paragraph — reproduce only the recommendation above.');
    }

    return lines.join('\n');
}

// ── Deterministic validation ──────────────────────────────────────────────────

/** Reasons a generated recommendation can be rejected. */
export type RecommendationViolation =
    | 'anchor_missing'
    | 'escalation_language'
    | 'de_escalation_language'
    | 'diagnostic_language'
    | 'resource_or_technique'
    | 'addition_too_long';

/** Maximum characters the LLM may add beyond the anchor. */
const MAX_ADDITION_CHARS = 400;

/** Escalation wording, rejected unless the referral level is already urgent. */
const ESCALATION_PATTERNS: RegExp[] = [
    /\burgent(ly)?\b/i,
    /\bimmediate(ly)?\b/i,
    /\bemergency\b/i,
    /\bcrisis\b/i,
    /\bright\s+away\b/i,
    /\bas\s+soon\s+as\s+possible\b/i,
    /\bwithout\s+delay\b/i,
    /\b(a\s*&\s*e|999|911|112)\b/i,
];

/** Wording that would understate a moderate or urgent referral. */
const DE_ESCALATION_PATTERNS: RegExp[] = [
    /\bno\s+need\s+to\s+(seek|see|contact|speak|worry)\b/i,
    /\bnothing\s+to\s+worry\s+about\b/i,
    /\bnot\s+necessary\s+to\s+(seek|see|contact|speak)\b/i,
    /\bdoes\s+not\s+require\s+(any\s+)?(follow[-\s]?up|assessment|attention)\b/i,
];

/** Diagnostic wording, rejected at every level. */
const DIAGNOSTIC_PATTERNS: RegExp[] = [
    /\bdiagnos(is|es|ed|e|tic)\b/i,
    /\byou\s+(have|are\s+suffering\s+from|suffer\s+from)\s+[^.]*\b(anxiety|depression|disorder|gad)\b/i,
    /\bgenerali[sz]ed\s+anxiety\s+disorder\b/i,
    /\b(anxiety|depressive|panic)\s+disorder\b/i,
    /\bclinically\s+significant\b/i,
];

/** Techniques, services and named resources, rejected at every level. */
const RESOURCE_PATTERNS: RegExp[] = [
    /\bbreathing\s+(exercise|technique)/i,
    /\bmindfulness\b/i,
    /\bmeditat(e|ion|ing)\b/i,
    /\bjournal(l)?ing\b/i,
    /\bhotline\b/i,
    /\bhelpline\b/i,
    /\bhelpline\b/i,
    /\b(therapy|therapist|counsell?ing|counsell?or|cbt)\b/i,
    /\b(app|website|helpline|support\s+group)s?\b/i,
];

export interface RecommendationValidation {
    ok: boolean;
    violations: RecommendationViolation[];
}

/** Collapses whitespace so anchor comparison ignores wrapping differences. */
function normaliseForComparison(text: string): string {
    return text.replace(/\s+/g, ' ').replace(/[“”]/g, '"').trim();
}

/**
 * Checks a generated Recommendation section against its directive.
 *
 * The anchor must appear intact. Forbidden wording is scanned only in the text
 * the LLM ADDED — the anchors themselves legitimately contain words such as
 * "crisis", "immediately" and "mindfulness", and must not be flagged.
 */
export function validateRecommendationSection(
    sectionText: string,
    directive: RecommendationDirective
): RecommendationValidation {
    const violations: RecommendationViolation[] = [];

    const normalisedSection = normaliseForComparison(sectionText);
    const normalisedAnchor  = normaliseForComparison(directive.anchorText);

    const anchorIndex = normalisedSection.indexOf(normalisedAnchor);
    if (anchorIndex === -1) {
        // Without the anchor there is nothing to trust — reject immediately.
        return { ok: false, violations: ['anchor_missing'] };
    }

    // Everything the LLM added, either side of the anchor.
    const addition = (
        normalisedSection.slice(0, anchorIndex) +
        ' ' +
        normalisedSection.slice(anchorIndex + normalisedAnchor.length)
    ).replace(/^["'\s]+|["'\s]+$/g, '').trim();

    if (addition.length > MAX_ADDITION_CHARS) violations.push('addition_too_long');

    if (directive.referralLevel !== 'urgent' && ESCALATION_PATTERNS.some(p => p.test(addition))) {
        violations.push('escalation_language');
    }
    if (directive.referralLevel !== 'low' && DE_ESCALATION_PATTERNS.some(p => p.test(addition))) {
        violations.push('de_escalation_language');
    }
    if (DIAGNOSTIC_PATTERNS.some(p => p.test(addition))) violations.push('diagnostic_language');
    if (RESOURCE_PATTERNS.some(p => p.test(addition))) violations.push('resource_or_technique');

    return { ok: violations.length === 0, violations };
}

// ── Enforcement ───────────────────────────────────────────────────────────────

export interface RecommendationEnforcement {
    /** The report body, with the Recommendation section replaced if it failed validation. */
    body: string;
    /** True when the section was rejected and the anchor restored. */
    enforced: boolean;
    violations: RecommendationViolation[];
}

/**
 * Extracts the Recommendation section from a generated report body, validates
 * it, and — if it fails — replaces its content with the anchor verbatim.
 *
 * Pure and synchronous, so the safety property is testable without invoking a
 * model. A missing section is also repaired, since a report without a
 * recommendation is not usable.
 */
export function enforceRecommendation(
    body: string,
    directive: RecommendationDirective
): RecommendationEnforcement {
    const headingMatch = body.match(/^#{1,3}\s*Recommendation\b[^\n]*$/im);

    if (!headingMatch || headingMatch.index === undefined) {
        // No Recommendation section at all — insert one before Limitations,
        // or append it if there is no Limitations section either.
        const anchorSection = `## Recommendation\n\n${directive.anchorText}`;
        const limitationsMatch = body.match(/^#{1,3}\s*Limitations?\b/im);
        const repaired = limitationsMatch && limitationsMatch.index !== undefined
            ? body.slice(0, limitationsMatch.index).trimEnd() + '\n\n' + anchorSection + '\n\n' + body.slice(limitationsMatch.index)
            : body.trimEnd() + '\n\n' + anchorSection;
        return { body: repaired, enforced: true, violations: ['anchor_missing'] };
    }

    const headingLine  = headingMatch[0];
    const sectionStart = headingMatch.index;
    const afterHeading = sectionStart + headingLine.length;

    // The section runs until the next heading of the same or higher level.
    const rest = body.slice(afterHeading);
    const nextHeading = rest.match(/^#{1,3}\s+\S/m);
    const sectionEnd = nextHeading && nextHeading.index !== undefined
        ? afterHeading + nextHeading.index
        : body.length;

    const sectionBody = body.slice(afterHeading, sectionEnd);
    const validation  = validateRecommendationSection(sectionBody, directive);

    if (validation.ok) {
        return { body, enforced: false, violations: [] };
    }

    const replaced =
        body.slice(0, afterHeading) +
        `\n\n${directive.anchorText}\n\n` +
        body.slice(sectionEnd);

    return { body: replaced, enforced: true, violations: validation.violations };
}

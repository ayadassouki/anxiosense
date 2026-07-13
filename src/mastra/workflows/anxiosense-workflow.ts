import { evidenceValidationStep } from './evidence-validation-step';
import { buildClaimsStep } from './build-claims-step';
import { retrievalStep } from '../agents/retrieval-agent';
import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';
import { ValidationAgentOutputSchema } from '../../kb/types';
import { writeSession, readSession, clearSession, type SessionData } from '../utils/workflow-session-store';
import { exportWorkflowRun } from '../utils/export-workflow-run';
import { computeGad7Score, formatGad7ForReport } from '../utils/gad7-scorer';

// ── Input schema ─────────────────────────────────────────────────────────────

const inputSchema = z.object({
    /**
     * Selects the analysis pipeline:
     *   - "journal"       → personal journal entry; GAD-7 supported; full referral.
     *   - "social-media"  → pasted Reddit/social posts; GAD-7 bypassed; extra disclaimer.
     */
    mode: z.enum(['journal', 'social-media']).default('journal'),

    /** The free-text content to analyse. */
    userText: z.string(),

    /**
     * Optional GAD-7 answers — exactly 7 integers, each 0–3.
     * Only used in "journal" mode. Ignored in "social-media" mode.
     */
    gad7Answers: z
        .array(z.number().int().min(0).max(3))
        .length(7)
        .optional(),

    /**
     * When true, the report includes a Clinician Details section with the raw
     * GAD-7 score, clinical severity label, and per-item breakdown.
     * Hidden from standard user-facing output.
     */
    clinicianMode: z.boolean().optional().default(false),
});

// ── Shared step schemas ───────────────────────────────────────────────────────

const agentOutputSchema = z.object({
    result: z.string(),
    /** Wall-clock duration of agent.generate() in milliseconds. */
    durationMs: z.number(),
});

const combinedAnalysisSchema = z.object({
    mode: z.enum(['journal', 'social-media']),
    userText: z.string(),
    emotionAnalysis: z.string(),
    symptomAnalysis: z.string(),
    contextAnalysis: z.string(),
    referralAnalysis: z.string(),
    /** Per-agent generate() durations for session timing instrumentation. */
    agentTimingsMs: z.object({
        emotion: z.number(),
        symptom: z.number(),
        context: z.number(),
        referral: z.number(),
    }),
});

const validatedAnalysisSchema = combinedAnalysisSchema.extend({
    validationAnalysis: z.string(),
});

const finalReportSchema = z.object({
    finalReport: z.string(),
});

// ── Mode context helpers ──────────────────────────────────────────────────────

function modePrefix(mode: 'journal' | 'social-media'): string {
    if (mode === 'social-media') {
        return (
            'CONTEXT: The following text was sourced from social media (e.g. Reddit). ' +
            'Treat it as self-reported content from an unknown author describing their ' +
            'own experiences. Do NOT assume clinical intent or structured disclosure. ' +
            'Be appropriately cautious about any inferences.\n\n'
        );
    }
    return (
        'CONTEXT: The following text is a personal journal entry written by the user ' +
        'to describe how they have been feeling recently.\n\n'
    );
}

// ── Parallel extraction steps ─────────────────────────────────────────────────

const emotionStep = createStep({
    id: 'emotion-analysis-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('emotionAgent');
        if (!agent) throw new Error('Emotion agent not found');
        const t0 = Date.now();
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text, durationMs: Date.now() - t0 };
    },
});

const symptomStep = createStep({
    id: 'symptom-extraction-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('symptomAgent');
        if (!agent) throw new Error('Symptom agent not found');
        const t0 = Date.now();
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text, durationMs: Date.now() - t0 };
    },
});

const contextStep = createStep({
    id: 'context-reasoning-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('contextAgent');
        if (!agent) throw new Error('Context agent not found');
        const t0 = Date.now();
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text, durationMs: Date.now() - t0 };
    },
});

const referralStep = createStep({
    id: 'referral-safety-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('referralAgent');
        if (!agent) throw new Error('Referral agent not found');

        // Social-media mode: prepend extra conservatism instruction to the referral agent.
        const socialMediaNote =
            inputData.mode === 'social-media'
                ? 'IMPORTANT: This text is from social media, not a direct clinical disclosure. ' +
                  'Be conservative — default to "low" or "moderate" unless there are very explicit ' +
                  'safety signals in the text itself.\n\n'
                : '';

        const t0 = Date.now();
        const response = await agent.generate(
            socialMediaNote + modePrefix(inputData.mode) + inputData.userText
        );
        return { result: response.text, durationMs: Date.now() - t0 };
    },
});

// ── Validation step ───────────────────────────────────────────────────────────

const validationStep = createStep({
    id: 'validation-step',
    inputSchema: combinedAnalysisSchema,
    outputSchema: validatedAnalysisSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('validationAgent');
        if (!agent) throw new Error('Validation agent not found');

        const prompt = `
Original User Text:
${inputData.userText}

Emotion Analysis Agent Output:
${inputData.emotionAnalysis}

Symptom Extraction Agent Output:
${inputData.symptomAnalysis}

Context Reasoning Agent Output:
${inputData.contextAnalysis}

Referral and Safety Agent Output:
${inputData.referralAnalysis}

Validate the agent outputs. Remove or flag unsupported claims. Return only the validation JSON.
`;

        const response = await agent.generate(prompt);
        return { ...inputData, validationAnalysis: response.text };
    },
});

// ── Report step ───────────────────────────────────────────────────────────────

const reportStep = createStep({
    id: 'assessment-report-step',
    inputSchema: ValidationAgentOutputSchema,
    outputSchema: finalReportSchema,
    execute: async ({ inputData, mastra }) => {
        let finalReport: string;

        if (inputData.riskLevel === 'urgent') {
            finalReport = `# AnxioSense Screening Support Report

## Important — Urgent Safety Notice

Based on what you shared, there may be an immediate safety concern that requires urgent attention.

**This screening tool is not able to provide crisis support.** Please reach out for help right now:

- Contact a crisis line in your country or region
- Go to your nearest emergency department, or call emergency services (911 / 999 / 112)
- Reach out immediately to a trusted person who can be with you

---

*This report has not been generated. When an immediate safety concern is present, your wellbeing takes priority over a screening summary. Please seek support now.*

*This tool is intended for screening support only and is not a clinical service.*`;

            // Clear session data — urgent path short-circuits before the export block.
            // Timing data is unavailable on this path; just clean up memory.
            try { clearSession(inputData.sessionId); } catch { /* non-fatal */ }

        } else {
            const agent = mastra?.getAgent('reportAgent');
            if (!agent) throw new Error('Report agent not found');

            // Read session data — includes mode, clinicianMode, gad7 fields, retrieval output
            const session = readSession(inputData.sessionId);
            const mode              = session?.mode              ?? 'journal';
            const clinicianMode     = session?.clinicianMode     ?? false;
            const gad7Block         = session?.gad7Block         ?? null;
            const gad7ConcernPattern = session?.gad7ConcernPattern ?? null;
            const discordanceNote   = session?.discordanceNote   ?? null;

            // ── Mode label ────────────────────────────────────────────────────
            const modeLabel =
                mode === 'social-media' ? 'Social Media Analysis' : 'Journal / Self-Report';

            // ── Group validated claims by agent for structured LLM input ──────
            // Claims are passed as semantic labels, not raw user sentences,
            // so the LLM can rewrite them as clinical findings.
            const emotionClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'emotion')
                .map(v => v.claimText);
            const symptomClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'symptom')
                .map(v => v.claimText);
            const contextClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'context')
                .map(v => v.claimText);

            const claimsForPrompt = [
                `Emotional signals: ${emotionClaims.length  > 0 ? emotionClaims.join('; ')  : 'none identified'}`,
                `Anxiety indicators: ${symptomClaims.length > 0 ? symptomClaims.join('; ')  : 'none identified'}`,
                `Contextual factors: ${contextClaims.length > 0 ? contextClaims.join('; ')  : 'none identified'}`,
            ].join('\n');

            // ── Evidence Agreement — based on concern-level comparison ─────────
            // Compares validated text signal strength (symptom claim count) against
            // the GAD-7 concern band, or falls back to KB support ratio for social-media.
            const validatedSymptomClaims = inputData.claimValidations.filter(
                v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'symptom'
            );

            let evidenceAgreement: 'High' | 'Moderate' | 'Low';
            let agreementText: string;

            if (discordanceNote === 'high_gad7_low_text') {
                evidenceAgreement = 'Low';
                agreementText     = 'The questionnaire responses indicated more concern than the written text alone suggested.';
            } else if (discordanceNote === 'low_gad7_high_text') {
                evidenceAgreement = 'Low';
                agreementText     = 'The written text reflected more concern indicators than the questionnaire responses.';
            } else if (gad7ConcernPattern) {
                // Journal mode with GAD-7: compare concern bands numerically
                const levelToNum: Record<string, number> = {
                    'Minimal Concern Pattern':  0,
                    'Mild Concern Pattern':     1,
                    'Elevated Concern Pattern': 2,
                    'High Concern Pattern':     3,
                };
                const gad7Num = levelToNum[gad7ConcernPattern] ?? 1;
                // Text level: derived from validated symptom claim count
                const textNum = validatedSymptomClaims.length === 0 ? 0
                    : validatedSymptomClaims.length <= 2              ? 1
                    : validatedSymptomClaims.length <= 4              ? 2
                    :                                                    3;
                const diff = Math.abs(gad7Num - textNum);
                if (diff === 0) {
                    evidenceAgreement = 'High';
                    agreementText     = 'The questionnaire responses and written text were generally consistent.';
                } else if (diff === 1) {
                    evidenceAgreement = 'Moderate';
                    agreementText     = 'Some indicators were present, but the available text provided limited detail.';
                } else {
                    evidenceAgreement = 'Low';
                    agreementText     = 'The questionnaire responses and written text did not fully align.';
                }
            } else {
                // Social media or journal without GAD-7: compare text against KB
                const totalClaims    = inputData.claimValidations.length;
                const supportedCount = inputData.claimValidations.filter(v => v.supportStatus === 'supported').length;
                const partialCount   = inputData.claimValidations.filter(v => v.supportStatus === 'partially_supported').length;
                if (totalClaims === 0) {
                    evidenceAgreement = 'Low';
                    agreementText     = 'Insufficient information was available to assess agreement across sources.';
                } else {
                    const supportRatio = (supportedCount + partialCount * 0.5) / totalClaims;
                    evidenceAgreement  = supportRatio >= 0.6 ? 'High' : 'Moderate';
                    agreementText      = supportRatio >= 0.6
                        ? 'The identified indicators were broadly consistent with the clinical guidance used.'
                        : 'Some indicators were present, but the available text provided limited detail.';
                }
            }

            // ── Recommendation instruction (concern-pattern-specific) ──────────
            const concernPatternForReport = gad7ConcernPattern
                ?? (inputData.riskLevel === 'urgent'   ? 'High Concern Pattern'
                  : inputData.riskLevel === 'moderate' ? 'Elevated Concern Pattern'
                  :                                      'Minimal Concern Pattern');

            let recommendationInstruction: string;
            if (concernPatternForReport === 'Minimal Concern Pattern') {
                recommendationInstruction =
                    'State that no immediate follow-up is indicated. Note that occasional mild experiences are a normal part of life. ' +
                    'Suggest monitoring how these experiences change over time and considering speaking with a healthcare professional ' +
                    'only if they become more frequent, worsen, or begin affecting daily functioning.';
            } else if (concernPatternForReport === 'Mild Concern Pattern') {
                recommendationInstruction =
                    'Use monitoring language only — do NOT recommend professional consultation as the default outcome. ' +
                    'Include this wording verbatim: "Monitoring how these experiences change over time may be helpful. ' +
                    'Consider speaking with a healthcare professional if they become more frequent, worsen, or begin affecting daily functioning." ' +
                    'Do not add language implying referral is necessary or urgent.';
            } else if (concernPatternForReport === 'Elevated Concern Pattern') {
                recommendationInstruction =
                    'State that it may be beneficial to discuss these concerns with a qualified healthcare professional who can ' +
                    'provide a comprehensive assessment and appropriate guidance. Keep tone helpful and non-urgent.';
            } else {
                // High Concern Pattern
                recommendationInstruction =
                    'State that seeking support from a qualified healthcare professional may be beneficial. Note that effective support ' +
                    'options are available and that discussing these concerns with a professional can help determine the most appropriate next steps.';
            }

            // ── LLM generates Supporting Findings + Recommendation + Limitations ─
            // Supporting Findings are generated by the LLM (not TypeScript) so it can
            // rewrite the raw claim text into concise clinical language without copying
            // user sentences. Assessment Overview and Evidence Agreement remain TypeScript.
            const prompt = `
Input Mode: ${modeLabel}
Concern Pattern: ${concernPatternForReport}

VALIDATED FINDINGS (summarise as clinical plain-language findings — do NOT reproduce user text):
${claimsForPrompt}

Generate THREE sections. Do NOT include a document title. Do NOT include Assessment Overview — it is generated automatically.
Start your response directly with "## Supporting Findings".

## Supporting Findings
Rewrite the validated findings above as concise clinical plain-language bullet points.
Rules:
- NEVER copy the user's original words or sentences
- Use clinical terminology: "persistent worry", "sleep disruption", "positive emotional tone", "stable functioning", "social withdrawal"
- Keep each bullet 2–5 words (a label, not a sentence)
- If anxiety indicators are "none identified" AND emotional signals are positive/neutral: write only "No significant anxiety-related indicators were identified in the provided text."
- If anxiety indicators are present: write "The report identified the following experiences in the provided text:" then 3–6 bullets, then end with "These findings were checked against the clinical guidance and screening knowledge base used by AnxioSense."
- Include any contextual factors at the end of the bullets (e.g., "Academic stress", "Social pressures")

## Recommendation
${recommendationInstruction}

## Limitations
State that: (a) the report is based only on the information provided; (b) missing context may affect interpretation; (c) this is not a clinical diagnosis; (d) a qualified healthcare professional is needed for a clinical assessment.${mode === 'social-media' ? ' Also note that social media text adds additional uncertainty to the analysis.' : ''}
End with exactly: "This report is intended for screening support only and should not be considered a clinical diagnosis."

CRITICAL RULES — any violation makes the report unusable:
- Do NOT include a document title, Assessment Overview, or Evidence Agreement
- Do NOT reproduce user text in Supporting Findings — summarise clinically
- Do NOT include chunk IDs, claim IDs, file names, similarity scores
- Do NOT diagnose the user or name any clinical condition
- Do NOT suggest coping strategies, breathing exercises, mindfulness, or therapy techniques
- Do NOT mention hotlines, apps, websites, specific clinic types, or named resources
- Keep tone supportive, cautious, and non-judgmental
`;

            const response = await agent.generate(prompt);

            // ── Post-process LLM output ───────────────────────────────────────
            let llmBody = response.text.trim()
                .replace(/^#+\s*AnxioSense\b[^\n]*\n\n?/im, '')
                .trim();

            // Ensure output starts at Supporting Findings; strip any LLM preamble
            const sfIdx = llmBody.search(/^#{1,3}\s*Supporting\s+Findings\b/im);
            if (sfIdx > 10) {
                llmBody = llmBody.slice(sfIdx).trim();
            } else if (sfIdx === -1) {
                // LLM skipped the section — inject fallback
                const recIdx = llmBody.search(/^#{1,3}\s*Recommendation\b/im);
                const fallback = symptomClaims.length === 0
                    ? '## Supporting Findings\n\nNo significant anxiety-related indicators were identified in the provided text.'
                    : '## Supporting Findings\n\nThe report identified the following experiences in the provided text:\n\n' +
                      symptomClaims.map(c => `- ${c}`).join('\n') +
                      '\n\nThese findings were checked against the clinical guidance and screening knowledge base used by AnxioSense.';
                llmBody = recIdx !== -1
                    ? fallback + '\n\n' + llmBody.slice(recIdx)
                    : fallback + '\n\n' + llmBody;
            }

            // ── Build Assessment Overview (deterministic TypeScript) ──────────
            const overviewParts: string[] = [];
            if (mode === 'social-media') {
                overviewParts.push(
                    '**Analysis Type:** Social Media Analysis\n\n' +
                    'No structured questionnaire was available because this analysis was performed using secondary ' +
                    'social media text. Results therefore rely only on linguistic, emotional, symptomatic, and ' +
                    'contextual indicators identified in the written text.'
                );
            } else {
                overviewParts.push('**Analysis Type:** Journal / Self-Report');
                if (gad7Block) {
                    overviewParts.push('\n' + gad7Block);
                } else {
                    overviewParts.push(
                        '\nNo structured questionnaire was completed for this assessment. ' +
                        'The analysis relies on linguistic and contextual indicators identified in the written text.'
                    );
                }
                if (discordanceNote === 'high_gad7_low_text') {
                    overviewParts.push(
                        '\n**Note on Evidence Sources:** The structured questionnaire indicates a higher level of ' +
                        'concern than was reflected in the written text. Written expression may not fully capture ' +
                        'all of an individual\'s internal experiences. Both sources were considered in generating this report.'
                    );
                } else if (discordanceNote === 'low_gad7_high_text') {
                    overviewParts.push(
                        '\n**Note on Evidence Sources:** The written text reflects more indicators of concern than ' +
                        'the structured questionnaire score alone suggests. Both sources were considered in generating this report.'
                    );
                }
            }
            const assessmentOverview = `## Assessment Overview\n\n${overviewParts.join('\n')}`;

            // ── Evidence Agreement section ────────────────────────────────────
            const evidenceAgreementSection =
                `## Evidence Agreement\n\n**${evidenceAgreement}** — ${agreementText}`;

            // Insert Evidence Agreement before Limitations
            const limitIdx = llmBody.search(/^#{1,3}\s*Limitations?\b/im);
            let mainBody: string;
            if (limitIdx !== -1) {
                mainBody =
                    llmBody.slice(0, limitIdx).trimEnd() +
                    '\n\n' + evidenceAgreementSection +
                    '\n\n' + llmBody.slice(limitIdx);
            } else {
                mainBody = llmBody + '\n\n' + evidenceAgreementSection;
            }

            finalReport =
                `# AnxioSense Screening Support Report\n\n` +
                `${assessmentOverview}\n\n` +
                mainBody;

            // ── Clinician Summary block ───────────────────────────────────────
            // Clinically meaningful details only — no chunk IDs, no cosine thresholds.
            if (clinicianMode) {
                const severityLabel: Record<string, string> = {
                    minimal:  'Minimal — 0–4',
                    mild:     'Mild — 5–9',
                    moderate: 'Moderate — 10–14',
                    severe:   'Severe — 15–21',
                };
                const itemLabels = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'];
                const questions  = [
                    'Feeling nervous, anxious, or on edge',
                    'Not being able to stop or control worrying',
                    'Worrying too much about different things',
                    'Trouble relaxing',
                    'Being so restless that it is hard to sit still',
                    'Becoming easily annoyed or irritable',
                    'Feeling afraid, as if something awful might happen',
                ];

                // GAD-7 section
                let gad7ClinicianSection = '';
                if (session?.gad7Score !== null && session?.gad7Score !== undefined) {
                    const itemBreakdown = (session.gad7ItemScores ?? [])
                        .map((score, i) => `  ${i + 1}. ${questions[i]}\n     → ${itemLabels[score]}`)
                        .join('\n');
                    gad7ClinicianSection =
                        `**GAD-7:** ${session.gad7Score}/21 ` +
                        `(${severityLabel[session.gad7Severity ?? ''] ?? session.gad7Severity ?? 'Unknown'})\n\n` +
                        `**Per-Item Responses:**\n${itemBreakdown}\n\n`;
                }

                // Validated indicators — clinician-friendly labels, no raw user text
                const allValidated = inputData.claimValidations.filter(v => v.supportStatus !== 'unsupported');
                const indicatorLines = allValidated.length > 0
                    ? allValidated
                        .map(v => {
                            const supportLabel = v.supportStatus === 'supported' ? 'Supported' : 'Partially Supported';
                            return `  - ${v.claimText} (${supportLabel})`;
                        })
                        .join('\n')
                    : '  No anxiety-related indicators validated.';

                // Differential considerations — always natural clinical language
                const diffLean = inputData.differentiationAssessment.primaryLean;
                const differentialText = (!diffLean || diffLean === 'unclear')
                    ? 'Available information was insufficient to confidently distinguish anxiety-related symptoms from ' +
                      'other possible conditions such as depression. Further clinical assessment would be required.'
                    : `Assessment leans toward ${diffLean}. ${inputData.differentiationAssessment.reasoning}`;

                // Assessment notes — only if discordance was detected
                const assessmentNotes = discordanceNote === 'high_gad7_low_text'
                    ? 'The questionnaire responses indicated greater concern than was reflected in the written text. ' +
                      'This may suggest that written expression did not fully capture the respondent\'s internal experience.'
                    : discordanceNote === 'low_gad7_high_text'
                    ? 'The written text reflected more indicators of concern than the questionnaire responses alone suggested. ' +
                      'Clinical attention to both sources would be warranted.'
                    : '';

                const clinicianBlock = `

---

## Clinician Summary *(restricted — do not share with patient)*

${gad7ClinicianSection}**Validated Indicators:**
${indicatorLines}

**Evidence Confidence:** ${evidenceAgreement}

**Differential Considerations:**
${differentialText}
${assessmentNotes ? `\n**Assessment Notes:**\n${assessmentNotes}\n` : ''}
*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*`;

                finalReport += clinicianBlock;
            }
        }

        // ── Pipeline Performance timing ────────────────────────────────────────
        // Timing is written to session store and logged to console ONLY.
        // It is NOT appended to finalReport (kept out of user-facing content).
        // It IS passed to the evaluation export for research analysis.
        let assembledTimings: SessionData['timings'] | undefined;
        try {
            const timingSession = readSession(inputData.sessionId);
            const agentMs       = timingSession?.agentTimingsMs;
            const retrievalMs   = timingSession?.retrievalElapsedMs  ?? 0;
            const validationMs  = timingSession?.validationElapsedMs ?? 0;
            const reportMs      = timingSession?.reportStartMs != null
                ? Date.now() - timingSession.reportStartMs
                : 0;

            if (agentMs) {
                const parallelMs = Math.max(agentMs.emotion, agentMs.symptom, agentMs.context, agentMs.referral);
                const totalMs    = parallelMs + retrievalMs + validationMs + reportMs;
                const fmt = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;

                assembledTimings = {
                    parallelMs,
                    emotionMs:   agentMs.emotion,
                    symptomMs:   agentMs.symptom,
                    contextMs:   agentMs.context,
                    referralMs:  agentMs.referral,
                    retrievalMs,
                    validationMs,
                    reportMs,
                    totalMs,
                };

                writeSession(inputData.sessionId, { timings: assembledTimings });

                // Console-only timing summary (not written to user report)
                console.log(
                    `[AnxioSense] Timing — ` +
                    `parallel: ${fmt(parallelMs)} ` +
                    `(emotion: ${fmt(agentMs.emotion)}, symptom: ${fmt(agentMs.symptom)}, ` +
                    `context: ${fmt(agentMs.context)}, referral: ${fmt(agentMs.referral)}), ` +
                    `retrieval: ${fmt(retrievalMs)}, validation: ${fmt(validationMs)}, ` +
                    `report: ${fmt(reportMs)}, total: ${fmt(totalMs)}`
                );
            }
        } catch (timingErr) {
            console.warn('[AnxioSense] Timing block failed (non-fatal):', timingErr);
        }

        // ── Evaluation export ─────────────────────────────────────────────────
        try {
            const exportSession = readSession(inputData.sessionId);
            const filePath = exportWorkflowRun({
                testCaseName:      process.env.ANXIOSENSE_TEST_CASE     ?? 'manual-run',
                promptVersion:     process.env.ANXIOSENSE_PROMPT_VERSION ?? 'cot-oneshot-v1',
                userText:          exportSession?.userText          ?? '',
                gad7Block:         exportSession?.gad7Block         ?? null,
                emotionAnalysis:   exportSession?.emotionAnalysis   ?? '{}',
                symptomAnalysis:   exportSession?.symptomAnalysis   ?? '{}',
                contextAnalysis:   exportSession?.contextAnalysis   ?? '{}',
                referralAnalysis:  exportSession?.referralAnalysis  ?? '{}',
                buildClaimsOutput: exportSession?.buildClaimsOutput ?? {},
                retrievalOutput:   exportSession?.retrievalOutput   ?? {},
                validationOutput:  inputData,
                finalReport,
                timings:           assembledTimings,
            });
            clearSession(inputData.sessionId);
            console.log(`[AnxioSense] Evaluation run saved → ${filePath}`);
        } catch (e) {
            console.warn('[AnxioSense] Export failed (non-fatal):', e);
        }

        return { finalReport };
    },
});

// ── Workflow definition ───────────────────────────────────────────────────────

export const anxiosenseWorkflow = createWorkflow({
    id: 'anxiosense-workflow',
    inputSchema,
    outputSchema: finalReportSchema,
})
    .parallel([emotionStep, symptomStep, contextStep, referralStep])

    // ── Map 1: merge parallel outputs → combinedAnalysisSchema ───────────────
    .map(async ({ inputData, getInitData }) => {
        const originalInput = getInitData() as z.infer<typeof inputSchema>;
        return {
            mode:             originalInput.mode ?? 'journal',
            userText:         originalInput.userText,
            emotionAnalysis:  inputData['emotion-analysis-step'].result,
            symptomAnalysis:  inputData['symptom-extraction-step'].result,
            contextAnalysis:  inputData['context-reasoning-step'].result,
            referralAnalysis: inputData['referral-safety-step'].result,
            agentTimingsMs: {
                emotion:  inputData['emotion-analysis-step'].durationMs,
                symptom:  inputData['symptom-extraction-step'].durationMs,
                context:  inputData['context-reasoning-step'].durationMs,
                referral: inputData['referral-safety-step'].durationMs,
            },
        };
    })
    .then(buildClaimsStep)

    // ── Map 2: risk level + GAD-7 computation + session write ────────────────
    .map(async ({ inputData, getInitData }) => {
        // ── Risk level ────────────────────────────────────────────────────────
        const VALID_RISK_LEVELS = ['low', 'moderate', 'urgent'] as const;
        type RiskLevel = typeof VALID_RISK_LEVELS[number];
        let riskLevel: RiskLevel = 'moderate';
        try {
            const referral = JSON.parse(inputData.referralAnalysis);
            const raw = referral.risk_level;
            if (typeof raw === 'string' && (VALID_RISK_LEVELS as readonly string[]).includes(raw)) {
                riskLevel = raw as RiskLevel;
            } else if (typeof raw === 'string') {
                console.warn(
                    `[AnxioSense] Invalid risk_level "${raw}" from referral agent — defaulting to "moderate".`
                );
            }
        } catch {
            console.warn('[AnxioSense] Referral JSON parse failed — defaulting risk_level to "moderate".');
        }

        // ── GAD-7 (journal mode only) ─────────────────────────────────────────
        const originalInput = getInitData() as z.infer<typeof inputSchema>;
        const mode          = originalInput.mode          ?? 'journal';
        const clinicianMode = originalInput.clinicianMode ?? false;

        let gad7Block:      string | null   = null;
        let gad7Score:      number | null   = null;
        let gad7Severity:   string | null   = null;
        let gad7ItemScores: number[] | null = null;

        if (mode === 'journal' && Array.isArray(originalInput.gad7Answers) && originalInput.gad7Answers.length === 7) {
            try {
                const gad7Result = computeGad7Score(originalInput.gad7Answers);
                gad7Block      = formatGad7ForReport(gad7Result);
                gad7Score      = gad7Result.score;
                gad7Severity   = gad7Result.severity;
                gad7ItemScores = [...gad7Result.itemScores];
                console.log(`[AnxioSense] GAD-7 scored: ${gad7Score}/21 (${gad7Severity})`);
            } catch (e) {
                console.warn('[AnxioSense] GAD-7 scoring failed (non-fatal):', e);
            }
        } else if (mode === 'social-media') {
            console.log('[AnxioSense] Social-media mode — GAD-7 bypassed.');
        }

        // ── Concern pattern label (from GAD-7 score) ──────────────────────────
        let gad7ConcernPattern: string | null = null;
        if (mode === 'journal' && gad7Score !== null) {
            if      (gad7Score <= 4)  gad7ConcernPattern = 'Minimal Concern Pattern';
            else if (gad7Score <= 9)  gad7ConcernPattern = 'Mild Concern Pattern';
            else if (gad7Score <= 14) gad7ConcernPattern = 'Elevated Concern Pattern';
            else                      gad7ConcernPattern = 'High Concern Pattern';
        }

        // ── Discordance detection ─────────────────────────────────────────────
        // Flags when GAD-7 and text-based signal disagree markedly.
        // GEN-1 is the fallback claim injected when agents return nothing —
        // treat it as "no real text signal" for discordance purposes.
        let discordanceNote: 'high_gad7_low_text' | 'low_gad7_high_text' | null = null;
        if (mode === 'journal' && gad7Score !== null) {
            const isFallbackOnly =
                inputData.claims.length === 1 && inputData.claims[0].claimId === 'GEN-1';
            const realClaimCount = isFallbackOnly ? 0 : inputData.claims.length;

            if (gad7Score >= 15 && realClaimCount <= 1) {
                // High questionnaire score but minimal text signal
                discordanceNote = 'high_gad7_low_text';
                console.log('[AnxioSense] Discordance detected: high_gad7_low_text');
            } else if (gad7Score <= 4 && realClaimCount >= 4) {
                // Minimal questionnaire score but rich text signal
                discordanceNote = 'low_gad7_high_text';
                console.log('[AnxioSense] Discordance detected: low_gad7_high_text');
            }
        }

        // ── Session write ─────────────────────────────────────────────────────
        writeSession(inputData.sessionId, {
            mode,
            clinicianMode,
            userText:          inputData.userText,
            emotionAnalysis:   inputData.emotionAnalysis,
            symptomAnalysis:   inputData.symptomAnalysis,
            contextAnalysis:   inputData.contextAnalysis,
            referralAnalysis:  inputData.referralAnalysis,
            buildClaimsOutput: { sessionId: inputData.sessionId, claims: inputData.claims },
            gad7Block,
            gad7Score,
            gad7Severity,
            gad7ItemScores,
            gad7ConcernPattern,
            discordanceNote,
            // Timing: parallel agent durations + start mark for retrieval
            agentTimingsMs:    inputData.agentTimingsMs,
            retrievalStartMs:  Date.now(),
        });

        return {
            sessionId:    inputData.sessionId,
            originalText: inputData.userText,
            claims:       inputData.claims,
            riskLevel,
        };
    })
    .then(retrievalStep)

    // ── Pass-through: write retrieval output + timing to session ─────────────
    .map(async ({ inputData }) => {
        const session = readSession(inputData.sessionId);
        const retrievalElapsedMs = session?.retrievalStartMs != null
            ? Date.now() - session.retrievalStartMs
            : 0;
        writeSession(inputData.sessionId, {
            retrievalOutput:    inputData,
            retrievalElapsedMs,
            validationStartMs:  Date.now(),
        });
        return inputData;
    })
    .then(evidenceValidationStep)

    // ── Map 4: record evidence validation elapsed time ────────────────────────
    .map(async ({ inputData }) => {
        const session = readSession(inputData.sessionId);
        const validationElapsedMs = session?.validationStartMs != null
            ? Date.now() - session.validationStartMs
            : 0;
        writeSession(inputData.sessionId, {
            validationElapsedMs,
            reportStartMs: Date.now(),
        });
        return inputData;
    })
    .then(reportStep);

anxiosenseWorkflow.commit();

import { evidenceValidationStep } from './evidence-validation-step';
import { buildClaimsStep } from './build-claims-step';
import { retrievalStep } from '../agents/retrieval-agent';
import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';
import { ValidationAgentOutputSchema } from '../../kb/types';
import { writeSession, readSession, clearSession } from '../utils/workflow-session-store';
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
});

const combinedAnalysisSchema = z.object({
    mode: z.enum(['journal', 'social-media']),
    userText: z.string(),
    emotionAnalysis: z.string(),
    symptomAnalysis: z.string(),
    contextAnalysis: z.string(),
    referralAnalysis: z.string(),
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
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text };
    },
});

const symptomStep = createStep({
    id: 'symptom-extraction-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('symptomAgent');
        if (!agent) throw new Error('Symptom agent not found');
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text };
    },
});

const contextStep = createStep({
    id: 'context-reasoning-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('contextAgent');
        if (!agent) throw new Error('Context agent not found');
        const response = await agent.generate(modePrefix(inputData.mode) + inputData.userText);
        return { result: response.text };
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

        const response = await agent.generate(
            socialMediaNote + modePrefix(inputData.mode) + inputData.userText
        );
        return { result: response.text };
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

        } else {
            const agent = mastra?.getAgent('reportAgent');
            if (!agent) throw new Error('Report agent not found');

            // Read session data — includes mode, clinicianMode, gad7 fields, retrieval output
            const session = readSession(inputData.sessionId);
            const mode          = session?.mode          ?? 'journal';
            const clinicianMode = session?.clinicianMode ?? false;
            const gad7Block     = session?.gad7Block     ?? null;

            // ── Format validated claims by agent ──────────────────────────────
            const confidenceLabel = (status: string) =>
                status === 'supported' ? 'strong evidence' : 'partial evidence';

            const filterAndFormat = (agentName: string) =>
                inputData.claimValidations
                    .filter((v) => v.supportStatus !== 'unsupported' && v.sourceAgent === agentName)
                    .map((v) => `- ${v.claimText} [${confidenceLabel(v.supportStatus)}]`)
                    .join('\n') || 'None';

            const emotionClaimsText  = filterAndFormat('emotion');
            const symptomClaimsText  = filterAndFormat('symptom');
            const contextClaimsText  = filterAndFormat('context');

            const unsupportedCount = inputData.claimValidations
                .filter((v) => v.supportStatus === 'unsupported').length;

            // ── Extract top evidence snippets from retrieval output ────────────
            // Pull the top 4 KB chunks across all supported claims for the
            // Evidence section — gives the user a transparent view of what the
            // KB contributed.
            let evidenceSnippets = 'None available.';
            try {
                const retrieval = session?.retrievalOutput as {
                    results?: Array<{
                        claimText: string;
                        retrievedChunks: Array<{ text: string; source?: string; similarityScore: number }>;
                    }>;
                } | undefined;

                if (retrieval?.results) {
                    const chunks: Array<{ text: string; source?: string; score: number }> = [];
                    for (const r of retrieval.results) {
                        for (const c of r.retrievedChunks ?? []) {
                            chunks.push({ text: c.text, source: c.source, score: c.similarityScore });
                        }
                    }
                    // Deduplicate by first 60 chars, keep top 4 by score
                    const seen = new Set<string>();
                    const top = chunks
                        .sort((a, b) => b.score - a.score)
                        .filter((c) => {
                            const key = c.text.slice(0, 60);
                            if (seen.has(key)) return false;
                            seen.add(key);
                            return true;
                        })
                        .slice(0, 4);

                    if (top.length > 0) {
                        evidenceSnippets = top
                            .map((c, i) => {
                                const excerpt = c.text.length > 200
                                    ? c.text.slice(0, 200).trimEnd() + '...'
                                    : c.text;
                                const src = c.source ? ` (${c.source})` : '';
                                return `${i + 1}. "${excerpt}"${src}`;
                            })
                            .join('\n\n');
                    }
                }
            } catch {
                // Non-fatal — evidence section will show "None available."
            }

            // ── Mode-specific framing ─────────────────────────────────────────
            const modeLabel =
                mode === 'social-media'
                    ? 'Social Media Analysis'
                    : 'Journal / Self-Report';

            // Per supervisor guidance: social-media mode must NEVER assign or infer a GAD-7 score.
            // The GAD-7 is a structured self-report instrument — it can only be computed from
            // the user's own responses to its 7 items. For secondary text data (Reddit, social
            // media), the GAD-7 serves only as a conceptual reference for symptom domains.
            const socialMediaDisclaimer =
                mode === 'social-media'
                    ? '\nNOTE TO REPORT AGENT: This analysis is based on social media text written by an unknown author, ' +
                      'not a structured clinical self-report. ' +
                      'CRITICAL: Do NOT assign, infer, estimate, or reference any GAD-7 score for this content. ' +
                      'The system identifies anxiety-related linguistic and contextual indicators only. ' +
                      'In Section 1, add a clear statement that: (a) no GAD-7 was administered, ' +
                      '(b) results carry additional uncertainty due to the indirect nature of the text, ' +
                      'and (c) this is a non-diagnostic screening summary based on linguistic indicators.'
                    : '';

            const prompt = `
Input Mode: ${modeLabel}
${socialMediaDisclaimer}

Evidence-Based Validation Summary (pre-categorised — use ONLY what is listed here):

EMOTIONAL INDICATORS (for Section 2):
${emotionClaimsText}

ANXIETY-RELATED INDICATORS (for Section 3):
${symptomClaimsText}

CONTEXTUAL FACTORS (for Section 5):
${contextClaimsText}

SUPPORTING EVIDENCE FROM KNOWLEDGE BASE (for Section 4 — quote these verbatim):
${evidenceSnippets}

Unsupported claims dropped: ${unsupportedCount}
Differentiation assessment: ${inputData.differentiationAssessment.primaryLean}

Generate the final AnxioSense Screening Support Report using this EXACT section structure:

# AnxioSense Screening Support Report

## 1. Input Mode
State the mode used (${modeLabel}) in one sentence.${mode === 'social-media' ? ' Add one sentence noting that results carry additional uncertainty because the text is from social media.' : ''}

## 2. Summary of Concern
2–3 sentence overview of the validated findings. Use cautious language. Do not diagnose.

## 3. Emotional Indicators
Use ONLY the emotional indicators listed above. If none: "No emotional indicators were identified in the available information."

## 4. Anxiety-Related Indicators
Use ONLY the anxiety-related indicators listed above. If none: "No anxiety-related indicators were identified in the available information."

## 5. Supporting Evidence
Present the knowledge-base evidence snippets provided above. Introduce them with: "The following excerpts from the clinical knowledge base supported the validated findings:" then list them. Do not paraphrase — present them as provided.

## 6. Contextual Factors
Use ONLY the contextual factors listed above. If none: "No contextual factors were identified in the available information."

## 7. Referral and Safety Recommendation
State the appropriate follow-up level based on validated findings. Do not add coping strategies or specific resources.

## 8. Limitations
State that: (a) the report is based only on the information provided; (b) missing context may affect interpretation; (c) this is not a clinical diagnosis; (d) a qualified healthcare professional is needed for a clinical assessment.${mode === 'social-media' ? ' Also note that social media text adds additional uncertainty to the analysis.' : ''}

CRITICAL RULES — any violation makes the report unusable:
- Do NOT include a Section 0 — it will be added automatically if applicable.
- Do NOT include claim IDs (EMO-1, SYM-1, CTX-1, etc.), chunk IDs, file names, or similarity scores.
- Do NOT diagnose the user or say they "have anxiety" or any clinical condition.
- Do NOT introduce findings not in the lists above.
- Do NOT suggest coping strategies, breathing exercises, mindfulness, journaling, or therapy techniques.
- Do NOT mention hotlines, apps, websites, specific clinic types, or named resources.
- Keep tone supportive, cautious, and non-judgmental.
- End with exactly: "This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment."
`;

            const response = await agent.generate(prompt);

            // ── Inject GAD-7 concern-pattern block (Section 0) ────────────────
            // Inserted directly in TypeScript after generation so Mistral cannot
            // condense or drop the item-by-item breakdown.
            if (gad7Block) {
                const reportBody = response.text
                    .replace(/^#\s+AnxioSense Screening Support Report\s*/i, '')
                    .trimStart();
                // Section 0 heading uses supervisor-approved label.
                // Numerical score and clinical severity label are never shown here —
                // those appear only in the Clinician Details section (if clinicianMode).
                finalReport =
                    `# AnxioSense Screening Support Report\n\n` +
                    `## 0. GAD-7 Screening Result\n\n${gad7Block}\n\n` +
                    reportBody;
            } else {
                finalReport = response.text;
            }

            // ── Inject Clinician Details block ────────────────────────────────
            // Appended after the user-facing report. Raw GAD-7 score and clinical
            // severity are never shown to standard users.
            if (clinicianMode && session?.gad7Score !== null && session?.gad7Score !== undefined) {
                // Per Spitzer et al. (2006) as cited in supervisor guidance
                const severityLabel: Record<string, string> = {
                    minimal:  'Minimal Anxiety — 0–4',
                    mild:     'Mild Anxiety — 5–9',
                    moderate: 'Moderate Anxiety — 10–14',
                    severe:   'Severe Anxiety — 15–21',
                };
                const itemLabels = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'];
                const questions = [
                    'Feeling nervous, anxious, or on edge',
                    'Not being able to stop or control worrying',
                    'Worrying too much about different things',
                    'Trouble relaxing',
                    'Being so restless that it is hard to sit still',
                    'Becoming easily annoyed or irritable',
                    'Feeling afraid, as if something awful might happen',
                ];
                const itemBreakdown = (session.gad7ItemScores ?? [])
                    .map((score, i) => `  ${i + 1}. ${questions[i]}\n     → ${itemLabels[score]} (${score})`)
                    .join('\n');

                const clinicianBlock = `

---

## Clinician Details *(restricted — do not share with patient)*

**GAD-7 Raw Score:** ${session.gad7Score}/21
**Clinical Severity:** ${severityLabel[session.gad7Severity ?? ''] ?? session.gad7Severity ?? 'Unknown'}

**Per-Item Breakdown:**
${itemBreakdown}

**Differentiation Assessment:** ${inputData.differentiationAssessment.primaryLean}
**Differentiation Reasoning:** ${inputData.differentiationAssessment.reasoning}
**Validation Notes:** ${inputData.overallConsistencyNotes}

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*`;

                finalReport += clinicianBlock;
            }
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
        });

        return {
            sessionId:    inputData.sessionId,
            originalText: inputData.userText,
            claims:       inputData.claims,
            riskLevel,
        };
    })
    .then(retrievalStep)

    // ── Pass-through: write retrieval output to session ───────────────────────
    .map(async ({ inputData }) => {
        writeSession(inputData.sessionId, { retrievalOutput: inputData });
        return inputData;
    })
    .then(evidenceValidationStep)
    .then(reportStep);

anxiosenseWorkflow.commit();

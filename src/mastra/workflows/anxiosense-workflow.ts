import { evidenceValidationStep } from './evidence-validation-step';
import { buildClaimsStep } from './build-claims-step';
import { retrievalStep } from '../agents/retrieval-agent';
import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';
import { ValidationAgentOutputSchema } from '../../kb/types';
import { writeSession, readSession, clearSession } from '../utils/workflow-session-store';
import { exportWorkflowRun } from '../utils/export-workflow-run';

const inputSchema = z.object({
    userText: z.string(),
});

const agentOutputSchema = z.object({
    result: z.string(),
});

const combinedAnalysisSchema = z.object({
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

const emotionStep = createStep({
    id: 'emotion-analysis-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('emotionAgent');
        if (!agent) throw new Error('Emotion agent not found');

        const response = await agent.generate(inputData.userText);
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

        const response = await agent.generate(inputData.userText);
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

        const response = await agent.generate(inputData.userText);
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

        const response = await agent.generate(inputData.userText);
        return { result: response.text };
    },
});

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

        return {
            ...inputData,
            validationAnalysis: response.text,
        };
    },
});

const reportStep = createStep({
    id: 'assessment-report-step',
    inputSchema: ValidationAgentOutputSchema,
    outputSchema: finalReportSchema,
    execute: async ({ inputData, mastra }) => {
        let finalReport: string;

        if (inputData.riskLevel === 'urgent') {
            // Safety override: bypass the LLM entirely and return a hardcoded crisis
            // response.  This prevents the report agent from generating a routine
            // screening report when the user has described an immediate safety concern.
            finalReport = `# AnxioSense Screening Support — Urgent Safety Notice

## Important

Based on what you shared, there may be an immediate safety concern that requires urgent attention.

**This screening tool is not able to provide crisis support.** Please reach out for help right now:

- Contact a crisis line in your country or region (e.g. a mental health crisis line or helpline)
- Go to your nearest emergency department, or call emergency services (e.g. 911 / 999 / 112)
- Reach out immediately to a trusted person who can be with you

---

*This report has not been generated. When an immediate safety concern is present, your wellbeing takes priority over a screening summary. Please seek support now.*

*This tool is intended for screening support only and is not a clinical service.*`;
        } else {
            const agent = mastra?.getAgent('reportAgent');
            if (!agent) throw new Error('Report agent not found');

            // Split validated claims by source agent so the LLM knows exactly which
            // claims belong in each section (Section 2 = emotion, 3 = symptom, 4 = context).
            // This prevents the model from misassigning or inventing section content.
            const confidenceLabel = (status: string) =>
                status === 'supported' ? 'strong evidence' : 'partial evidence';

            const filterAndFormat = (agentName: string) =>
                inputData.claimValidations
                    .filter((v) => v.supportStatus !== 'unsupported' && v.sourceAgent === agentName)
                    .map((v) => `- ${v.claimText} [${confidenceLabel(v.supportStatus)}]`)
                    .join('\n') || 'None';

            const emotionClaimsText   = filterAndFormat('emotion');
            const symptomClaimsText   = filterAndFormat('symptom');
            const contextClaimsText   = filterAndFormat('context');

            const unsupportedCount = inputData.claimValidations
                .filter((v) => v.supportStatus === 'unsupported').length;

            const prompt = `
Evidence-Based Validation Summary (pre-categorised — use ONLY what is listed here):

EMOTIONAL INDICATORS (for Section 2):
${emotionClaimsText}

ANXIETY-RELATED INDICATORS (for Section 3):
${symptomClaimsText}

CONTEXTUAL FACTORS (for Section 4):
${contextClaimsText}

Unsupported claims: ${unsupportedCount} (do not name them — mention only the count in Section 6)
Differentiation assessment: ${inputData.differentiationAssessment.primaryLean}

Generate the final AnxioSense Screening Support Report.

CRITICAL RULES — violation of any rule makes the report unusable:
- Do NOT include any internal identifiers (e.g. EMO-1, SYM-1, CTX-1, ANX-001, or any code of letters-hyphen-number).
- Do NOT mention chunk IDs, claim IDs, file names, similarity scores, or threshold values.
- Do NOT diagnose the user or say they have anxiety or depression.
- Do NOT introduce findings that are not in the lists above. Write exactly what is in the list.
- Do NOT suggest coping strategies, breathing exercises, mindfulness, journaling, or treatment techniques.
- Section 2 must use ONLY the emotional indicators listed above.
- Section 3 must use ONLY the anxiety-related indicators listed above.
- Section 4 must use ONLY the contextual factors listed above.
- If a section's list says "None", write: "No [indicator type] were identified in the available information."
- Keep the tone cautious, supportive, and professional.
- End with exactly this sentence: "This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment."
`;

            const response = await agent.generate(prompt);
            finalReport = response.text;
        }

        // ── Evaluation export ─────────────────────────────────────────────────
        // Write the full run snapshot to evaluation/prompt-experiments/runs/.
        // Wrapped in try/catch so a write error never breaks the workflow output.
        // Set ANXIOSENSE_TEST_CASE and ANXIOSENSE_PROMPT_VERSION in your env
        // before running to label the file (defaults are provided below).
        try {
            const session = readSession(inputData.sessionId);
            const filePath = exportWorkflowRun({
                testCaseName:     process.env.ANXIOSENSE_TEST_CASE    ?? 'manual-run',
                promptVersion:    process.env.ANXIOSENSE_PROMPT_VERSION ?? 'cot-oneshot-v1',
                userText:         session?.userText          ?? '',
                emotionAnalysis:  session?.emotionAnalysis   ?? '{}',
                symptomAnalysis:  session?.symptomAnalysis   ?? '{}',
                contextAnalysis:  session?.contextAnalysis   ?? '{}',
                referralAnalysis: session?.referralAnalysis  ?? '{}',
                buildClaimsOutput: session?.buildClaimsOutput ?? {},
                retrievalOutput:  session?.retrievalOutput   ?? {},
                validationOutput: inputData,
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

export const anxiosenseWorkflow = createWorkflow({
    id: 'anxiosense-workflow',
    inputSchema,
    outputSchema: finalReportSchema,
})
    .parallel([emotionStep, symptomStep, contextStep, referralStep])
    .map(async ({ inputData, getInitData }) => {
        const originalInput = getInitData() as { userText: string };

        return {
            userText: originalInput.userText,
            emotionAnalysis: inputData['emotion-analysis-step'].result,
            symptomAnalysis: inputData['symptom-extraction-step'].result,
            contextAnalysis: inputData['context-reasoning-step'].result,
            referralAnalysis: inputData['referral-safety-step'].result,
        };
        })
    .then(buildClaimsStep)
    .map(async ({ inputData }) => {
        // Extract risk_level from referral agent output so it can be forwarded
        // to the report step for the urgent safety override.
        let riskLevel = 'low';
        try {
            const referral = JSON.parse(inputData.referralAnalysis);
            if (typeof referral.risk_level === 'string') {
                riskLevel = referral.risk_level;
            }
        } catch {
            // referral JSON parse failed — default to 'low' (safe fallback)
        }

        // Deposit intermediate outputs into the session store so the report step
        // can include them in the evaluation export without schema changes.
        writeSession(inputData.sessionId, {
            userText:          inputData.userText,
            emotionAnalysis:   inputData.emotionAnalysis,
            symptomAnalysis:   inputData.symptomAnalysis,
            contextAnalysis:   inputData.contextAnalysis,
            referralAnalysis:  inputData.referralAnalysis,
            buildClaimsOutput: { sessionId: inputData.sessionId, claims: inputData.claims },
        });

        return {
            sessionId:    inputData.sessionId,
            originalText: inputData.userText,
            claims:       inputData.claims,
            riskLevel,
        };
    })
    .then(retrievalStep)
    // Pass-through map: write retrieval output to the session store.
    // Returns inputData unchanged so evidenceValidationStep sees its expected input.
    .map(async ({ inputData }) => {
        writeSession(inputData.sessionId, { retrievalOutput: inputData });
        return inputData;
    })
    .then(evidenceValidationStep)
    .then(reportStep);
anxiosenseWorkflow.commit();

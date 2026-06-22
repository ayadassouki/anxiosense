import { evidenceValidationStep } from './evidence-validation-step';
import { buildClaimsStep } from './build-claims-step';
import { retrievalStep } from '../agents/retrieval-agent';
import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';

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
    inputSchema: validatedAnalysisSchema,
    outputSchema: finalReportSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('reportAgent');
        if (!agent) throw new Error('Report agent not found');

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

Validation Agent Output:
${inputData.validationAnalysis}

Generate the final AnxioSense Screening Support Report using the validation output as the source of truth. Do not include unsupported claims.
`;

        const response = await agent.generate(prompt);
        return { finalReport: response.text };
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
        return {
            sessionId: inputData.sessionId,
            originalText: inputData.userText,
            claims: inputData.claims,
        };
    })
    .then(retrievalStep)
    .then(evidenceValidationStep)
    .then(reportStep);
anxiosenseWorkflow.commit();

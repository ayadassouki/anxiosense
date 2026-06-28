import { createStep } from '@mastra/core/workflows';
import { z } from 'zod';
import { ClaimSchema } from '../../kb/types';

const combinedAnalysisSchema = z.object({
  userText: z.string(),
  emotionAnalysis: z.string(),
  symptomAnalysis: z.string(),
  contextAnalysis: z.string(),
  referralAnalysis: z.string(),
});

export const claimsBuildOutputSchema = combinedAnalysisSchema.extend({
  sessionId: z.string(),
  claims: z.array(ClaimSchema),
});

function safeParseJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

export const buildClaimsStep = createStep({
  id: 'build-claims-step',
  inputSchema: combinedAnalysisSchema,
  outputSchema: claimsBuildOutputSchema,
  execute: async ({ inputData }) => {
    const emotion = safeParseJson(inputData.emotionAnalysis);
    const symptom = safeParseJson(inputData.symptomAnalysis);
    const context = safeParseJson(inputData.contextAnalysis);

    const claims: z.infer<typeof ClaimSchema>[] = [];

    (emotion.emotions ?? []).forEach((item: string, index: number) => {
      claims.push({
        claimId: `EMO-${index + 1}`,
        sourceAgent: 'emotion',
        claimText: item,
        category: 'emotional_state',
      });
    });

    (symptom.possible_anxiety_indicators ?? []).forEach((item: string, index: number) => {
      const lower = item.toLowerCase();
      const category =
        lower.includes('sleep') ||
          lower.includes('fatigue') ||
          lower.includes('concentration') ||
          lower.includes('irritability')
          ? 'shared_symptom'
          : 'anxiety_indicator';

      claims.push({
        claimId: `SYM-${index + 1}`,
        sourceAgent: 'symptom',
        claimText: item,
        category,
      });
    });

    (context.contextual_stressors ?? []).forEach((item: string, index: number) => {
      claims.push({
        claimId: `CTX-${index + 1}`,
        sourceAgent: 'context',
        claimText: item,
        category: 'contextual_stressor',
      });
    });
    return {
      ...inputData,
      sessionId: `session-${Date.now()}`,
      claims,
    };
  },
});

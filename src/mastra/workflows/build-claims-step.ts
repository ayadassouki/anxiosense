import { createStep } from '@mastra/core/workflows';
import { z } from 'zod';
import { ClaimSchema } from '../../kb/types';

const combinedAnalysisSchema = z.object({
  userText: z.string(),
  emotionAnalysis: z.string(),
  symptomAnalysis: z.string(),
  contextAnalysis: z.string(),
  referralAnalysis: z.string(),
  /** Per-agent generate() durations collected in Map 1; passed through for session write in Map 2. */
  agentTimingsMs: z.object({
    emotion: z.number(),
    symptom: z.number(),
    context: z.number(),
    referral: z.number(),
  }),
});

export const claimsBuildOutputSchema = combinedAnalysisSchema.extend({
  sessionId: z.string(),
  claims: z.array(ClaimSchema),
});

/**
 * Robust JSON extractor.
 * Handles:
 *   1. Raw valid JSON
 *   2. JSON wrapped in markdown code fences (```json ... ```)
 *   3. JSON embedded after explanatory text
 * Returns {} on total failure so callers never throw.
 */
function extractJson(raw: string): Record<string, unknown> {
  const text = raw.trim();

  // 1. Direct parse
  try { return JSON.parse(text); } catch {}

  // 2. Markdown code fence  ```json { ... } ```
  const fence = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/i);
  if (fence) {
    try { return JSON.parse(fence[1]); } catch {}
  }

  // 3. First {...} block anywhere in the text
  const firstBrace = text.indexOf('{');
  const lastBrace  = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try { return JSON.parse(text.slice(firstBrace, lastBrace + 1)); } catch {}
  }

  console.warn('[buildClaimsStep] Could not extract JSON from agent output:', text.slice(0, 200));
  return {};
}

export const buildClaimsStep = createStep({
  id: 'build-claims-step',
  inputSchema: combinedAnalysisSchema,
  outputSchema: claimsBuildOutputSchema,
  execute: async ({ inputData }) => {
    const emotion = extractJson(inputData.emotionAnalysis);
    const symptom = extractJson(inputData.symptomAnalysis);
    const context = extractJson(inputData.contextAnalysis);

    const claims: z.infer<typeof ClaimSchema>[] = [];

    (Array.isArray(emotion.emotions) ? emotion.emotions : []).forEach((item: unknown, index: number) => {
      if (typeof item !== 'string' || !item.trim()) return;
      claims.push({
        claimId:     `EMO-${index + 1}`,
        sourceAgent: 'emotion',
        claimText:   item.trim(),
        category:    'emotional_state',
      });
    });

    (Array.isArray(symptom.possible_anxiety_indicators) ? symptom.possible_anxiety_indicators : []).forEach((item: unknown, index: number) => {
      if (typeof item !== 'string' || !item.trim()) return;
      const lower = item.toLowerCase();
      const category =
        lower.includes('sleep') ||
        lower.includes('fatigue') ||
        lower.includes('concentration') ||
        lower.includes('irritability')
          ? 'shared_symptom'
          : 'anxiety_indicator';

      claims.push({
        claimId:     `SYM-${index + 1}`,
        sourceAgent: 'symptom',
        claimText:   item.trim(),
        category,
      });
    });

    (Array.isArray(context.contextual_stressors) ? context.contextual_stressors : []).forEach((item: unknown, index: number) => {
      if (typeof item !== 'string' || !item.trim()) return;
      claims.push({
        claimId:     `CTX-${index + 1}`,
        sourceAgent: 'context',
        claimText:   item.trim(),
        category:    'contextual_stressor',
      });
    });

    // ── Fallback: retrieval step requires ≥1 claim ────────────────────────────
    // When all agents return empty arrays (typical for minimal-concern text),
    // inject a generic emotional-state claim derived from the user's own text so
    // the pipeline can still produce a report.  The resulting retrieval will pull
    // general wellness/screening KB chunks rather than specific symptom chunks,
    // which is appropriate for a minimal-concern profile.
    if (claims.length === 0) {
      console.log('[buildClaimsStep] All agents returned empty — injecting fallback claim.');
      claims.push({
        claimId:     'GEN-1',
        sourceAgent: 'emotion',
        claimText:   inputData.userText.slice(0, 300).trim() || 'general emotional state',
        category:    'anxiety_indicator',
      });
    }

    console.log(`[buildClaimsStep] Built ${claims.length} claim(s):`, claims.map(c => c.claimId).join(', '));

    return {
      ...inputData,
      sessionId: `session-${Date.now()}`,
      claims,
    };
  },
});

import { createStep } from '@mastra/core/workflows';
import { z } from 'zod';
import { ClaimSchema } from '../../kb/types';
import { writeSession } from '../utils/anxiety-assessment-session-store';

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
  /**
   * Summed token usage from the four parallel agents (emotion + symptom + context + referral).
   * Must pass through this step's schema or Zod strips it; Map 2 writes it to the session store
   * so the report step can accumulate its own usage on top and return the full workflow total.
   */
  parallelTokenUsage: z.object({
    inputTokens:  z.number(),
    outputTokens: z.number(),
  }).optional(),
});

export const claimsBuildOutputSchema = combinedAnalysisSchema.extend({
  sessionId: z.string(),
  claims: z.array(ClaimSchema),
  /** True if any agent's text output could not be parsed as JSON. */
  agent_json_parse_failed: z.boolean(),
  /** True if GEN-1 fallback claim was injected (all agents returned empty arrays). */
  fallback_claim_injected: z.boolean(),
});

/**
 * Robust JSON extractor.
 * Handles:
 *   1. Raw valid JSON
 *   2. JSON wrapped in markdown code fences (```json ... ```)
 *   3. JSON embedded after explanatory text
 * Returns { data: {}, failed: true } on total failure so callers never throw.
 */
function extractJson(raw: string): { data: Record<string, unknown>; failed: boolean } {
  const text = raw.trim();

  // 1. Direct parse
  try { return { data: JSON.parse(text), failed: false }; } catch {}

  // 2. Markdown code fence  ```json { ... } ```
  const fence = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/i);
  if (fence) {
    try { return { data: JSON.parse(fence[1]), failed: false }; } catch {}
  }

  // 3. First {...} block anywhere in the text
  const firstBrace = text.indexOf('{');
  const lastBrace  = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try { return { data: JSON.parse(text.slice(firstBrace, lastBrace + 1)), failed: false }; } catch {}
  }

  console.warn('[buildClaimsStep] Could not extract JSON from agent output:', text.slice(0, 200));
  return { data: {}, failed: true };
}

export const assessmentClaimConstructionStep = createStep({
  id: 'build-claims-step',
  inputSchema: combinedAnalysisSchema,
  outputSchema: claimsBuildOutputSchema,
  execute: async ({ inputData }) => {
    const emotionResult = extractJson(inputData.emotionAnalysis);
    const symptomResult = extractJson(inputData.symptomAnalysis);
    const contextResult = extractJson(inputData.contextAnalysis);

    // Quality flag: any agent output that could not be parsed as JSON
    const agent_json_parse_failed =
      emotionResult.failed || symptomResult.failed || contextResult.failed;

    const emotion = emotionResult.data;
    const symptom = symptomResult.data;
    const context = contextResult.data;

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
    let fallback_claim_injected = false;
    if (claims.length === 0) {
      console.log('[buildClaimsStep] All agents returned empty — injecting fallback claim.');
      claims.push({
        claimId:     'GEN-1',
        sourceAgent: 'emotion',
        claimText:   inputData.userText.slice(0, 300).trim() || 'general emotional state',
        category:    'anxiety_indicator',
      });
      fallback_claim_injected = true;
    }

    console.log(`[buildClaimsStep] Built ${claims.length} claim(s):`, claims.map(c => c.claimId).join(', '));

    const sessionId = `session-${Date.now()}`;

    // Seed the quality flags in the session store so downstream steps can augment them.
    writeSession(sessionId, {
      qualityFlags: {
        agent_json_parse_failed,
        fallback_claim_injected,
        referral_risk_fallback_used: false,  // updated in Map 2
        recommendation_rejected:     false,  // updated in report step
      },
    });

    return {
      ...inputData,
      sessionId,
      claims,
      agent_json_parse_failed,
      fallback_claim_injected,
    };
  },
});

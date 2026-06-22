import { Agent } from "@mastra/core/agent";
import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import {
  RetrievalAgentOutputSchema,
  ValidationAgentOutputSchema,
  ClaimValidation,
  ClaimValidationSchema,
  DifferentiationAssessmentSchema,
} from "../../kb/types";

/**
 * The Validation Agent itself. Model choice and instructions can be swapped
 * for whatever free/local-tier model AnxioSense already uses elsewhere
 * (e.g. Mistral via free tier, or an Ollama-served local model) — nothing
 * here is provider-specific.
 */
export const validationAgent = new Agent({
  id: "validation-agent",
  name: "AnxioSense Validation Agent",
  instructions: `
You are a claim-evidence validator for a non-diagnostic anxiety/depression
screening-support tool. You are given ONE claim and a small set of
retrieved knowledge-base passages. Your job is narrow:

1. Decide whether the retrieved passages SUPPORT the claim:
   - "supported": at least one passage directly substantiates the claim's
     content.
   - "partially_supported": a passage is topically related but doesn't
     directly substantiate the specific claim as stated.
   - "unsupported": none of the passages substantiate the claim.
2. List the chunkId(s) of any passage you relied on. Never cite a chunk you
   did not actually use.
3. Write a one-sentence validationNote explaining the classification.

Do not add clinical judgment beyond what the passages support. Do not
upgrade a claim's certainty. Do not diagnose. If the passages don't
mention something the claim asserts, say so plainly rather than assuming
it's implied.
`.trim(),
  model: "openai/gpt-4.1-mini", // swap for your project's actual model
});

const ClaimValidationLlmOutputSchema = z.object({
  supportStatus: ClaimValidationSchema.shape.supportStatus,
  citedChunkIds: z.array(z.string()),
  validationNote: z.string(),
});

/**
 * Validates a single claim against its retrieved chunks. Run once per
 * claim (not batched into one giant prompt) so each LLM call stays focused
 * and per-claim accuracy can be evaluated independently later.
 */
async function validateClaim(
  claimId: string,
  claimText: string,
  sourceAgent: string,
  retrievedChunks: { chunkId: string; text: string }[]
): Promise<ClaimValidation> {
  if (retrievedChunks.length === 0) {
    return {
      claimId,
      claimText,
      sourceAgent,
      supportStatus: "unsupported",
      citedChunkIds: [],
      validationNote: "No knowledge-base passages were retrieved for this claim.",
    };
  }

  const passagesBlock = retrievedChunks
    .map((c) => `[${c.chunkId}]\n${c.text}`)
    .join("\n\n");

  const result = await validationAgent.generate(
    `CLAIM: "${claimText}"\n\nRETRIEVED PASSAGES:\n${passagesBlock}`,
    { structuredOutput: { schema: ClaimValidationLlmOutputSchema } }
  );

  return {
    claimId,
    claimText,
    sourceAgent,
    supportStatus: result.object.supportStatus,
    citedChunkIds: result.object.citedChunkIds,
    validationNote: result.object.validationNote,
  };
}

const DifferentiationLlmOutputSchema = DifferentiationAssessmentSchema;

/**
 * Session-level differentiation pass. Runs once, after all per-claim
 * validations are complete, using the aggregated claim list plus the
 * session-level anxiety_vs_depression.txt chunks retrieved by the
 * Retrieval Agent.
 */
async function assessDifferentiation(
  claimValidations: ClaimValidation[],
  differentiationChunks: { chunkId: string; text: string }[]
): Promise<z.infer<typeof DifferentiationAssessmentSchema>> {
  if (differentiationChunks.length === 0) {
    return {
      primaryLean: "unclear",
      supportingChunkIds: [],
      reasoning:
        "No differentiation evidence was retrieved for this session (claims did not span both anxiety and depression categories).",
    };
  }

  const supportedClaims = claimValidations.filter(
    (v) => v.supportStatus !== "unsupported"
  );
  const claimsBlock = supportedClaims
    .map((v) => `- ${v.claimText}`)
    .join("\n");
  const passagesBlock = differentiationChunks
    .map((c: { chunkId: string; text: string }) => `[${c.chunkId}]\n${c.text}`)
    .join("\n\n");

  const result = await validationAgent.generate(
    `SUPPORTED CLAIMS THIS SESSION:\n${claimsBlock}\n\nDIFFERENTIATION GUIDANCE PASSAGES:\n${passagesBlock}\n\nBased only on the supported claims and the differentiation guidance above, classify the session's primaryLean as "anxiety", "depression", "mixed", or "unclear". Use "mixed" when clear signals from both categories are present per the guidance. Use "unclear" when claims are dominated by low-specificity shared symptoms. Cite the chunkIds you relied on.`,
    { structuredOutput: { schema: DifferentiationLlmOutputSchema } }
  );

  return result.object;
}

export const validationStep = createStep({
  id: "validation-agent",
  description:
    "Performs per-claim evidence matching against retrieved knowledge-base chunks, then a session-level anxiety-vs-depression differentiation assessment.",
  inputSchema: RetrievalAgentOutputSchema,
  outputSchema: ValidationAgentOutputSchema,
  execute: async ({
    inputData,
  }: {
    inputData: z.infer<typeof RetrievalAgentOutputSchema>;
  }) => {
    const { sessionId, results, sessionDifferentiationChunks } = inputData;

    // Pass 1: validate each claim independently.
    const claimValidations: ClaimValidation[] = [];
    for (const r of results) {
      const validation = await validateClaim(
        r.claimId,
        r.claimText,
        r.sourceAgent,
        r.retrievedChunks
      );
      claimValidations.push(validation);
    }

    // Pass 2: session-level differentiation, using only supported claims.
    const differentiationAssessment = await assessDifferentiation(
      claimValidations,
      sessionDifferentiationChunks
    );

    const unsupportedCount = claimValidations.filter(
      (v) => v.supportStatus === "unsupported"
    ).length;
    const overallConsistencyNotes =
      unsupportedCount > 0
        ? `${unsupportedCount} of ${claimValidations.length} claim(s) had no supporting knowledge-base evidence and should be flagged in the report rather than presented as established.`
        : `All ${claimValidations.length} claim(s) had at least partial knowledge-base support.`;

    return {
      sessionId,
      claimValidations,
      differentiationAssessment,
      overallConsistencyNotes,
    };
  },
});

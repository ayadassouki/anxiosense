import { createWorkflow, createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { ClaimSchema, RetrievalAgentInputSchema } from "../../kb/types";
import { retrievalStep } from "../agents/retrieval-agent";
import { validationStep } from "../agents/validation-agent";
// import { emotionStep } from "../agents/emotion-agent";       // existing
// import { symptomStep } from "../agents/symptom-agent";       // existing
// import { contextStep } from "../agents/context-agent";       // existing
// import { reportStep } from "../agents/report-agent";         // existing
// import { safetyCheckStep } from "../agents/safety-check-agent"; // see note below

/**
 * Workflow-level input: the raw user submission.
 */
const WorkflowInputSchema = z.object({
  sessionId: z.string(),
  originalText: z.string(),
});

/**
 * Safety/Crisis Check step. This is a deliberately simple gate per the
 * architecture decision: it should NOT depend on vector retrieval, and
 * should run before any RAG-dependent agent. Implementation can start as
 * keyword/rule-based for the MVP and be upgraded to a lightweight
 * classifier later — the workflow shape below does not change either way.
 *
 * Replace the body with your actual safety-check logic; this stub shows
 * the contract the rest of the workflow expects.
 */
const safetyCheckStep = createStep({
  id: "safety-crisis-check",
  description:
    "Fast, retrieval-independent check for urgent risk indicators. Bypasses the standard pipeline if triggered.",
  inputSchema: WorkflowInputSchema,
  outputSchema: z.object({
    sessionId: z.string(),
    originalText: z.string(),
    urgentRiskDetected: z.boolean(),
  }),
  execute: async ({ inputData }: { inputData: z.infer<typeof WorkflowInputSchema> }) => {
    // Placeholder logic — replace with your actual rule-based/classifier
    // check. Keep this fast and independent of the vector store.
    const urgentRiskDetected = false;
    return { ...inputData, urgentRiskDetected };
  },
});

/**
 * Crisis response step — used only on the bypass branch. Pulls its
 * explanation text from safety_boundary.txt / referral_guidelines.txt at
 * report-render time (not via vector search), per SAFE-004.
 */
const crisisResponseStep = createStep({
  id: "crisis-response",
  description: "Renders crisis resources, bypassing the standard report pipeline.",
  inputSchema: z.object({
    sessionId: z.string(),
    originalText: z.string(),
    urgentRiskDetected: z.boolean(),
  }),
  outputSchema: z.object({
    sessionId: z.string(),
    reportType: z.literal("crisis"),
    message: z.string(),
  }),
  execute: async ({ inputData }: { inputData: { sessionId: string } }) => {
    return {
      sessionId: inputData.sessionId,
      reportType: "crisis" as const,
      message:
        "If you are in immediate danger or having thoughts of harming yourself, please contact a crisis line or emergency services right away.",
    };
  },
});

/**
 * Placeholder type for what your real Emotion/Symptom/Context agents
 * should each produce: a partial claims array. Replace these stand-ins
 * with imports of your actual existing agent steps once they're updated
 * to emit the Claim[] contract from kb/types.ts.
 */
const emotionStepStub = createStep({
  id: "emotion-agent",
  inputSchema: z.object({ sessionId: z.string(), originalText: z.string() }),
  outputSchema: z.object({ claims: z.array(ClaimSchema) }),
  execute: async () => ({ claims: [] }), // replace with real Emotion Agent
});

const symptomStepStub = createStep({
  id: "symptom-agent",
  inputSchema: z.object({ sessionId: z.string(), originalText: z.string() }),
  outputSchema: z.object({ claims: z.array(ClaimSchema) }),
  execute: async () => ({ claims: [] }), // replace with real Symptom Agent
});

const contextStepStub = createStep({
  id: "context-agent",
  inputSchema: z.object({ sessionId: z.string(), originalText: z.string() }),
  outputSchema: z.object({ claims: z.array(ClaimSchema) }),
  execute: async () => ({ claims: [] }), // replace with real Context Agent
});

/**
 * Merges the three parallel agents' claims into a single
 * RetrievalAgentInputSchema-shaped object for the Retrieval Agent.
 */
const mergeClaimsStep = createStep({
  id: "merge-claims",
  inputSchema: z.object({
    sessionId: z.string(),
    originalText: z.string(),
    "emotion-agent": z.object({ claims: z.array(ClaimSchema) }),
    "symptom-agent": z.object({ claims: z.array(ClaimSchema) }),
    "context-agent": z.object({ claims: z.array(ClaimSchema) }),
  }),
  outputSchema: RetrievalAgentInputSchema,
  execute: async ({
    inputData,
  }: {
    inputData: {
      sessionId: string;
      originalText: string;
      "emotion-agent": { claims: z.infer<typeof ClaimSchema>[] };
      "symptom-agent": { claims: z.infer<typeof ClaimSchema>[] };
      "context-agent": { claims: z.infer<typeof ClaimSchema>[] };
    };
  }) => {
    const claims = [
      ...inputData["emotion-agent"].claims,
      ...inputData["symptom-agent"].claims,
      ...inputData["context-agent"].claims,
    ];
    return {
      sessionId: inputData.sessionId,
      originalText: inputData.originalText,
      claims,
    };
  },
});

/**
 * Placeholder Report Agent step — replace with your real implementation.
 * Consumes ValidationAgentOutputSchema and renders the final user-facing,
 * citation-backed, non-diagnostic report.
 */
const reportStepStub = createStep({
  id: "report-agent",
  inputSchema: z.object({
    sessionId: z.string(),
    claimValidations: z.array(z.any()),
    differentiationAssessment: z.any(),
    overallConsistencyNotes: z.string(),
  }),
  outputSchema: z.object({
    sessionId: z.string(),
    reportType: z.literal("standard"),
  }),
  execute: async ({ inputData }: { inputData: { sessionId: string } }) => ({
    sessionId: inputData.sessionId,
    reportType: "standard" as const,
  }),
});

/**
 * Full AnxioSense workflow:
 *
 *   Safety Check
 *     -> [urgent]   Crisis Response
 *     -> [else]     Emotion + Symptom + Context (parallel)
 *                     -> merge claims
 *                     -> Retrieval Agent
 *                     -> Validation Agent
 *                     -> Report Agent
 */
export const anxioSenseWorkflow = createWorkflow({
  id: "anxiosense-workflow",
  inputSchema: WorkflowInputSchema,
  outputSchema: z.union([
    z.object({ sessionId: z.string(), reportType: z.literal("crisis"), message: z.string() }),
    z.object({ sessionId: z.string(), reportType: z.literal("standard") }),
  ]),
})
  .then(safetyCheckStep)
  .branch([
    [
      async ({ inputData }: { inputData: { urgentRiskDetected: boolean } }) =>
        inputData.urgentRiskDetected,
      crisisResponseStep,
    ],
    [
      async ({ inputData }: { inputData: { urgentRiskDetected: boolean } }) =>
        !inputData.urgentRiskDetected,
      createWorkflow({
        id: "standard-pipeline",
        inputSchema: z.object({
          sessionId: z.string(),
          originalText: z.string(),
          urgentRiskDetected: z.boolean(),
        }),
        outputSchema: z.object({
          sessionId: z.string(),
          reportType: z.literal("standard"),
        }),
      })
        // .parallel() runs all three steps concurrently against the same
        // input and returns one object keyed by each step's id — e.g.
        // { "emotion-agent": {...}, "symptom-agent": {...}, "context-agent": {...} }
        // which matches the shape mergeClaimsStep expects below.
        .parallel([emotionStepStub, symptomStepStub, contextStepStub])
        .then(mergeClaimsStep)
        .then(retrievalStep)
        .then(validationStep)
        .then(reportStepStub)
        .commit(),
    ],
  ])
  .commit();

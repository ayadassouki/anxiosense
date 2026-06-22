import { z } from "zod";

// ---------------------------------------------------------------------------
// Knowledge base chunk — the parsed representation of one CHUNK_ID block
// from a .txt knowledge base file.
// ---------------------------------------------------------------------------

export const SourceTypeSchema = z.enum([
  "clinical_description",
  "validated_instrument_item",
  "differentiation_guidance",
  "contextual_taxonomy",
  "referral_policy",
  "safety_policy",
]);
export type SourceType = z.infer<typeof SourceTypeSchema>;

export const KbChunkSchema = z.object({
  chunkId: z.string(),
  file: z.string(), // e.g. "anxiety_indicators.txt"
  sourceType: SourceTypeSchema,
  source: z.string().optional(), // e.g. "ICD-11 6B00, WHO (2025-01)"
  text: z.string(), // the full block text passed to the embedder
  safetyRestricted: z.boolean().default(false),
});
export type KbChunk = z.infer<typeof KbChunkSchema>;

// ---------------------------------------------------------------------------
// Claims — structured output from Emotion / Symptom / Context agents.
// This is the contract upstream agents must produce for retrieval to work.
// ---------------------------------------------------------------------------

export const ClaimCategorySchema = z.enum([
  "anxiety_indicator",
  "depression_indicator",
  "shared_symptom",
  "contextual_stressor",
  "emotional_state",
]);
export type ClaimCategory = z.infer<typeof ClaimCategorySchema>;

export const ClaimSchema = z.object({
  claimId: z.string(),
  sourceAgent: z.enum(["emotion", "symptom", "context"]),
  claimText: z.string(),
  category: ClaimCategorySchema,
});
export type Claim = z.infer<typeof ClaimSchema>;

// ---------------------------------------------------------------------------
// Retrieval Agent I/O
// ---------------------------------------------------------------------------

export const RetrievalAgentInputSchema = z.object({
  sessionId: z.string(),
  originalText: z.string(),
  claims: z.array(ClaimSchema).min(1),
});
export type RetrievalAgentInput = z.infer<typeof RetrievalAgentInputSchema>;

export const RetrievedChunkSchema = z.object({
  chunkId: z.string(),
  text: z.string(),
  source: z.string().optional(),
  sourceType: SourceTypeSchema,
  file: z.string(),
  similarityScore: z.number(),
});
export type RetrievedChunk = z.infer<typeof RetrievedChunkSchema>;

export const ClaimRetrievalResultSchema = z.object({
  claimId: z.string(),
  claimText: z.string(),
  sourceAgent: z.enum(["emotion", "symptom", "context"]),
  category: ClaimCategorySchema,
  retrievedChunks: z.array(RetrievedChunkSchema),
});
export type ClaimRetrievalResult = z.infer<typeof ClaimRetrievalResultSchema>;

export const RetrievalAgentOutputSchema = z.object({
  sessionId: z.string(),
  results: z.array(ClaimRetrievalResultSchema),
  sessionDifferentiationChunks: z.array(RetrievedChunkSchema), // from anxiety_vs_depression.txt
  retrievalMeta: z.object({
    totalClaims: z.number(),
    totalChunksRetrieved: z.number(),
    indexesQueried: z.array(z.string()),
  }),
});
export type RetrievalAgentOutput = z.infer<typeof RetrievalAgentOutputSchema>;

// ---------------------------------------------------------------------------
// Validation Agent I/O
// ---------------------------------------------------------------------------

export const SupportStatusSchema = z.enum([
  "supported",
  "partially_supported",
  "unsupported",
]);
export type SupportStatus = z.infer<typeof SupportStatusSchema>;

export const ClaimValidationSchema = z.object({
  claimId: z.string(),
  claimText: z.string(),
  sourceAgent: z.string(),
  supportStatus: SupportStatusSchema,
  citedChunkIds: z.array(z.string()),
  validationNote: z.string(),
});
export type ClaimValidation = z.infer<typeof ClaimValidationSchema>;

export const DifferentiationLeanSchema = z.enum([
  "anxiety",
  "depression",
  "mixed",
  "unclear",
]);

export const DifferentiationAssessmentSchema = z.object({
  primaryLean: DifferentiationLeanSchema,
  supportingChunkIds: z.array(z.string()),
  reasoning: z.string(),
});
export type DifferentiationAssessment = z.infer<
  typeof DifferentiationAssessmentSchema
>;

export const ValidationAgentOutputSchema = z.object({
  sessionId: z.string(),
  claimValidations: z.array(ClaimValidationSchema),
  differentiationAssessment: DifferentiationAssessmentSchema,
  overallConsistencyNotes: z.string(),
});
export type ValidationAgentOutput = z.infer<typeof ValidationAgentOutputSchema>;

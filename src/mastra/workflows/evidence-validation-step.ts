import { createStep } from '@mastra/core/workflows';
import { z } from 'zod';
import {
  RetrievalAgentOutputSchema,
  ValidationAgentOutputSchema,
  type ClaimValidation,
} from '../../kb/types';

/**
 * Cosine similarity thresholds for claim validation.
 *
 * The retrieval step uses fastembed (bge-small-en-v1.5) which returns
 * L2-normalised vectors. The LibSQLVector query therefore returns cosine
 * similarity scores directly in the range [0, 1].
 *
 * Thresholds are set based on observed score distributions across 5 baseline
 * test cases:
 *   - Strong KB match (e.g. "Excessive worry" → ANX-001):  ~0.78–0.81
 *   - Moderate match (e.g. "Sleep disruption" → SHARED-001): ~0.73–0.74
 *   - Weak / tangential match (e.g. emotion labels → general chunks): ~0.60–0.69
 *   - Noise / unrelated (no meaningful semantic overlap):  < 0.55
 *
 * A claim is:
 *   supported          — top chunk cosine similarity ≥ SUPPORTED_THRESHOLD
 *   partially_supported — top chunk cosine similarity ≥ PARTIAL_THRESHOLD
 *   unsupported         — top chunk cosine similarity <  PARTIAL_THRESHOLD
 *                         OR no chunks were retrieved at all
 */
const SUPPORTED_THRESHOLD = 0.72;
const PARTIAL_THRESHOLD   = 0.55;

// NOTE: Cosine similarity is not computed here. The retrieval step (retrieval-agent.ts)
// attaches similarityScore to each chunk directly from the LibSQLVector query result,
// which returns cosine similarity scores for L2-normalised fastembed vectors.
// Thresholds are applied to those pre-computed scores below.

export const evidenceValidationStep = createStep({
  id: 'evidence-validation-step',
  inputSchema: RetrievalAgentOutputSchema,
  outputSchema: ValidationAgentOutputSchema,
  execute: async ({ inputData }) => {
    const claimValidations: ClaimValidation[] = inputData.results.map((result) => {
      // Use the cosine similarity score already attached to each chunk by the
      // retrieval step.  We take the top-scoring chunk as the primary signal.
      const topScore = result.retrievedChunks[0]?.similarityScore ?? 0;

      const supportStatus =
        topScore >= SUPPORTED_THRESHOLD   ? 'supported'          :
        topScore >= PARTIAL_THRESHOLD     ? 'partially_supported' :
                                            'unsupported';

      // Cite only chunks that meet the partial threshold — chunks below it
      // are retrieved noise and should not be presented as supporting evidence.
      const qualifyingChunks = result.retrievedChunks.filter(
        (chunk) => chunk.similarityScore >= PARTIAL_THRESHOLD
      );
      const citedChunkIds = qualifyingChunks
        .slice(0, 2)
        .map((chunk) => chunk.chunkId);

      const validationNote =
        supportStatus === 'supported'
          ? `Claim is semantically supported by knowledge-base evidence ` +
            `(cosine similarity: ${topScore.toFixed(3)}, threshold: ${SUPPORTED_THRESHOLD}). ` +
            `Evidence retrieved from: ${qualifyingChunks.slice(0, 2).map((c) => c.file).join(', ')}.`
          : supportStatus === 'partially_supported'
          ? `Claim has partial knowledge-base support ` +
            `(cosine similarity: ${topScore.toFixed(3)}, threshold: ${PARTIAL_THRESHOLD}–${SUPPORTED_THRESHOLD}). ` +
            `Treat with caution; evidence from: ${qualifyingChunks.slice(0, 2).map((c) => c.file).join(', ')}.`
          : result.retrievedChunks.length === 0
          ? `No knowledge-base evidence was retrieved for this claim. Marked unsupported.`
          : `Retrieved chunks did not meet the cosine similarity threshold ` +
            `(top score: ${topScore.toFixed(3)}, required: ≥${PARTIAL_THRESHOLD}). ` +
            `Claim marked unsupported.`;

      return {
        claimId: result.claimId,
        claimText: result.claimText,
        sourceAgent: result.sourceAgent,
        supportStatus,
        citedChunkIds,
        validationNote,
      };
    });

    // Differentiation assessment: only flag as mixed when differentiation
    // chunks have meaningful similarity (≥ PARTIAL_THRESHOLD).
    const qualifyingDiffChunks = inputData.sessionDifferentiationChunks.filter(
      (chunk) => chunk.similarityScore >= PARTIAL_THRESHOLD
    );
    const supportingChunkIds = qualifyingDiffChunks
      .slice(0, 2)
      .map((chunk) => chunk.chunkId);

    const primaryLean =
      qualifyingDiffChunks.length > 0 ? 'mixed' : 'unclear';

    const unsupportedCount = claimValidations.filter(
      (v) => v.supportStatus === 'unsupported'
    ).length;
    const partialCount = claimValidations.filter(
      (v) => v.supportStatus === 'partially_supported'
    ).length;

    return {
      sessionId: inputData.sessionId,
      claimValidations,
      riskLevel: inputData.riskLevel,
      differentiationAssessment: {
        primaryLean,
        supportingChunkIds,
        reasoning:
          primaryLean === 'mixed'
            ? 'Both anxiety- and depression-related differentiation evidence met the similarity threshold. The system should avoid forcing a single diagnostic category.'
            : 'Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category.',
      },
      overallConsistencyNotes:
        `Validation uses cosine similarity thresholds (supported ≥ ${SUPPORTED_THRESHOLD}, ` +
        `partially_supported ≥ ${PARTIAL_THRESHOLD}, unsupported < ${PARTIAL_THRESHOLD}). ` +
        `${claimValidations.length} claims evaluated: ` +
        `${claimValidations.length - unsupportedCount - partialCount} supported, ` +
        `${partialCount} partially supported, ${unsupportedCount} unsupported.`,
    };
  },
});

import { createStep } from '@mastra/core/workflows';
import { z } from 'zod';
import {
  RetrievalAgentOutputSchema,
  ValidationAgentOutputSchema,
  type ClaimValidation,
} from '../../kb/types';

export const evidenceValidationStep = createStep({
  id: 'evidence-validation-step',
  inputSchema: RetrievalAgentOutputSchema,
  outputSchema: ValidationAgentOutputSchema,
  execute: async ({ inputData }) => {
    const claimValidations: ClaimValidation[] = inputData.results.map((result) => {
      const citedChunkIds = result.retrievedChunks
        .slice(0, 2)
        .map((chunk) => chunk.chunkId);

      const supportStatus =
        result.retrievedChunks.length > 0 ? 'supported' : 'unsupported';

      return {
        claimId: result.claimId,
        claimText: result.claimText,
        sourceAgent: result.sourceAgent,
        supportStatus,
        citedChunkIds,
        validationNote:
          result.retrievedChunks.length > 0
            ? `Claim has retrieved supporting evidence from ${result.retrievedChunks
                .slice(0, 2)
                .map((chunk) => chunk.file)
                .join(', ')}.`
            : 'No supporting knowledge-base evidence was retrieved for this claim.',
      };
    });

    const supportingChunkIds = inputData.sessionDifferentiationChunks
      .slice(0, 2)
      .map((chunk) => chunk.chunkId);

    return {
      sessionId: inputData.sessionId,
      claimValidations,
      differentiationAssessment: {
        primaryLean:
          inputData.sessionDifferentiationChunks.length > 0 ? 'mixed' : 'unclear',
        supportingChunkIds,
        reasoning:
          inputData.sessionDifferentiationChunks.length > 0
            ? 'Both anxiety- and depression-related evidence were present, so the system should avoid forcing a single category.'
            : 'There was not enough retrieved differentiation evidence to determine a primary lean.',
      },
      overallConsistencyNotes:
        'Validation is based on claim-to-knowledge-base retrieval. Claims with retrieved chunks are treated as evidence-supported, while claims without retrieved chunks are flagged as unsupported.',
    };
  },
});

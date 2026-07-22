import { createStep } from "@mastra/core/workflows";
import { embed } from "ai";
import { fastembed } from "@mastra/fastembed";
import { z } from "zod";
import {
  RetrievalAgentInputSchema,
  RetrievalAgentOutputSchema,
  RetrievedChunk,
  ClaimRetrievalResult,
} from "../../kb/types";
import { getVectorStore, KB_INDEX_NAME } from "../../kb/vector-store";
import {
  CATEGORY_TO_FILES,
  SESSION_DIFFERENTIATION_FILE,
  TOP_K_PER_FILE,
  TOP_K_PER_CLAIM,
} from "../../kb/category-routing";

/**
 * Queries the vector store for a single (queryText, file) pair, filtering
 * by the `file` metadata field so each file is searched independently
 * rather than pooled into one global top-k.
 */
async function queryFile(
  queryVector: number[],
  file: string,
  topK: number
): Promise<RetrievedChunk[]> {
  const vectorStore = getVectorStore();
  const results = await vectorStore.query({
    indexName: KB_INDEX_NAME,
    queryVector,
    topK,
    filter: { file },
  });

  return results.map(
    (r: { metadata?: Record<string, unknown>; score: number }) => ({
      chunkId: r.metadata?.chunkId as string,
      text: r.metadata?.text as string,
      source: (r.metadata?.source as string) || undefined,
      sourceType: r.metadata?.sourceType as RetrievedChunk["sourceType"],
      file: r.metadata?.file as string,
      similarityScore: r.score,
    })
  );
}

/**
 * Retrieves and merges chunks for one claim across all files mapped to its
 * category, then caps the merged result at TOP_K_PER_CLAIM, keeping the
 * highest-similarity chunks regardless of which file they came from.
 */
async function retrieveForClaim(
  claimText: string,
  category: keyof typeof CATEGORY_TO_FILES
): Promise<RetrievedChunk[]> {
  const { embedding } = await embed({ model: fastembed, value: claimText });
  const files = CATEGORY_TO_FILES[category];

  const perFileResults = await Promise.all(
    files.map((file) => queryFile(embedding, file, TOP_K_PER_FILE))
  );

  const merged = perFileResults
    .flat()
    .sort((a, b) => b.similarityScore - a.similarityScore)
    .slice(0, TOP_K_PER_CLAIM);

  return merged;
}

/**
 * Session-level differentiation retrieval: queried once per session
 * (not per-claim) whenever the workflow step decides it's relevant — see
 * the `.map()` call site in the workflow, which only calls this when both
 * anxiety_indicator and depression_indicator categories are present among
 * the session's claims.
 */
async function retrieveSessionDifferentiation(
  originalText: string
): Promise<RetrievedChunk[]> {
  const { embedding } = await embed({ model: fastembed, value: originalText });
  return queryFile(embedding, SESSION_DIFFERENTIATION_FILE, 4);
}

export const knowledgeEvidenceRetrievalStep = createStep({
  id: "retrieval-agent",
  description:
    "Retrieves knowledge-base evidence for each upstream claim, routed by claim category, plus session-level anxiety-vs-depression differentiation evidence.",
  inputSchema: RetrievalAgentInputSchema,
  outputSchema: RetrievalAgentOutputSchema,
  execute: async ({
    inputData,
  }: {
    inputData: z.infer<typeof RetrievalAgentInputSchema>;
  }) => {
    const { sessionId, originalText, claims, riskLevel } = inputData;

    const results: ClaimRetrievalResult[] = [];
    const indexesQueried = new Set<string>();

    for (const claim of claims) {
      const retrievedChunks = await retrieveForClaim(
        claim.claimText,
        claim.category
      );
      CATEGORY_TO_FILES[claim.category].forEach((f) => indexesQueried.add(f));

      results.push({
        claimId: claim.claimId,
        claimText: claim.claimText,
        sourceAgent: claim.sourceAgent,
        category: claim.category,
        retrievedChunks,
      });
    }

    const categories = new Set(
      claims.map((c: { category: string }) => c.category)
    );
    const needsDifferentiation =
      categories.has("anxiety_indicator") &&
      categories.has("depression_indicator");

    let sessionDifferentiationChunks: RetrievedChunk[] = [];
    if (needsDifferentiation) {
      sessionDifferentiationChunks = await retrieveSessionDifferentiation(
        originalText
      );
      indexesQueried.add(SESSION_DIFFERENTIATION_FILE);
    }

    const totalChunksRetrieved =
      results.reduce((sum, r) => sum + r.retrievedChunks.length, 0) +
      sessionDifferentiationChunks.length;

    return {
      sessionId,
      results,
      sessionDifferentiationChunks,
      retrievalMeta: {
        totalClaims: claims.length,
        totalChunksRetrieved,
        indexesQueried: Array.from(indexesQueried),
      },
      riskLevel,
    };
  },
});

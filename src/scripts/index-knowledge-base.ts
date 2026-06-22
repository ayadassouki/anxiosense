/**
 * Indexing script — run this whenever knowledge-base/*.txt files change.
 *
 *   npx tsx src/scripts/index-knowledge-base.ts
 *
 * Steps:
 *   1. Parse all .txt files into KbChunk objects.
 *   2. Filter out SAFETY_RESTRICTED chunks (never embedded, never indexed).
 *   3. Generate embeddings locally via @mastra/fastembed (no API key, no cost).
 *   4. Upsert into the LibSQL vector store, storing chunk metadata
 *      (chunkId, file, sourceType, source, text) alongside each vector so
 *      retrieval results carry full provenance without a second lookup.
 *
 * Idempotent: truncates the index before writing, so re-running after
 * editing a .txt file produces a clean, consistent index rather than
 * accumulating stale duplicates.
 */

import { embedMany } from "ai";
import { fastembed } from "@mastra/fastembed";
import { loadAllKbFiles } from "../kb/parser";
import { filterSafetyRestrictedChunks } from "../kb/chunk-filter";
import {
  getVectorStore,
  KB_INDEX_NAME,
  KB_EMBEDDING_DIMENSION,
} from "../kb/vector-store";

const KB_DIR = process.env.ANXIOSENSE_KB_DIR ?? "./knowledge-base";

async function main() {
  console.log(`Loading knowledge base from ${KB_DIR}...`);
  const allChunks = await loadAllKbFiles(KB_DIR);
  console.log(`Parsed ${allChunks.length} total chunks.`);

  const { indexable, excluded } = filterSafetyRestrictedChunks(allChunks);
  if (excluded.length > 0) {
    console.log(
      `Excluding ${excluded.length} safety-restricted chunk(s) from indexing:`,
      excluded.map((c) => c.chunkId).join(", ")
    );
  }
  console.log(`Indexing ${indexable.length} chunks.`);

  console.log("Generating embeddings locally via fastembed...");
  const { embeddings } = await embedMany({
    model: fastembed,
    values: indexable.map((c) => c.text),
  });

  const vectorStore = getVectorStore();

  // Recreate the index fresh each run so edits to .txt files don't leave
  // stale chunks behind. Safe for an MVP; for a larger KB you'd switch to
  // diffing and targeted upsert/delete instead of a full rebuild.
  const existingIndexes = await vectorStore.listIndexes();
  if (existingIndexes.includes(KB_INDEX_NAME)) {
    console.log(`Dropping existing index "${KB_INDEX_NAME}"...`);
    await vectorStore.deleteIndex({ indexName: KB_INDEX_NAME });
  }

  console.log(`Creating index "${KB_INDEX_NAME}"...`);
  await vectorStore.createIndex({
    indexName: KB_INDEX_NAME,
    dimension: KB_EMBEDDING_DIMENSION,
    metric: "cosine",
  });

  console.log("Upserting vectors with metadata...");
  await vectorStore.upsert({
    indexName: KB_INDEX_NAME,
    vectors: embeddings,
    metadata: indexable.map((c) => ({
      chunkId: c.chunkId,
      file: c.file,
      sourceType: c.sourceType,
      source: c.source ?? "",
      text: c.text,
    })),
  });

  console.log(`Done. Indexed ${indexable.length} chunks into "${KB_INDEX_NAME}".`);
}

main().catch((err) => {
  console.error("Indexing failed:", err);
  process.exit(1);
});

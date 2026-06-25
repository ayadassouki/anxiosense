import { LibSQLVector } from "@mastra/libsql";

const DB_URL = process.env.ANXIOSENSE_VECTOR_DB_URL ?? "file:/Users/ayadassouki/anxiosense/data/anxiosense-vectors.db";

export const KB_INDEX_NAME = "anxiosense_kb";
export const KB_EMBEDDING_DIMENSION = 384; // fastembed default (bge-small-en-v1.5)

let _vectorStore: LibSQLVector | null = null;

/**
 * Returns a shared LibSQLVector instance pointed at the local file DB.
 * Using a single shared instance (rather than constructing a new one per
 * call) avoids redundant file handles when both the indexing script and
 * the running agent process touch the same .db file.
 */
export function getVectorStore(): LibSQLVector {
  if (!_vectorStore) {
    _vectorStore = new LibSQLVector({
      id: "anxiosense-kb-vector",
      url: DB_URL,
    });
  }
  return _vectorStore;
}

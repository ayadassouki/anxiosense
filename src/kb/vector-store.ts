import { LibSQLVector } from "@mastra/libsql";

const DB_URL = process.env.ANXIOSENSE_VECTOR_DB_URL ?? "file:/Users/ayadassouki/anxiosense/data/anxiosense-vectors.db";
const AUTH_TOKEN = process.env.TURSO_AUTH_TOKEN;

export const KB_INDEX_NAME = "anxiosense_kb";
export const KB_EMBEDDING_DIMENSION = 384; // fastembed default (bge-small-en-v1.5)

let _vectorStore: LibSQLVector | null = null;

/**
 * Returns a shared LibSQLVector instance.
 * When ANXIOSENSE_VECTOR_DB_URL is a remote libsql:// (Turso) URL,
 * TURSO_AUTH_TOKEN must also be set — it is passed as authToken here.
 * Falls back to a local file DB when neither env var is provided.
 */
export function getVectorStore(): LibSQLVector {
  if (!_vectorStore) {
    _vectorStore = new LibSQLVector({
      id: "anxiosense-kb-vector",
      url: DB_URL,
      ...(AUTH_TOKEN ? { authToken: AUTH_TOKEN } : {}),
    });
  }
  return _vectorStore;
}

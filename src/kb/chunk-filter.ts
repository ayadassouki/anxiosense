import { KbChunk } from "./types";

/**
 * Removes chunks marked SAFETY_RESTRICTED: true (e.g. PHQ-9 item 9, the
 * self-harm/suicidal-ideation item) before they are embedded or indexed.
 *
 * This is a hard exclusion, not a runtime filter applied at query time.
 * Excluding at index-build time means a safety-restricted chunk can never
 * be returned by a similarity search, regardless of query content, agent
 * bug, or future code change to the retrieval path. Defense in depth:
 * even if a future contributor forgets to filter at query time, the
 * content simply does not exist in the index.
 *
 * Per safety_boundary.txt (SAFE-004): content suggestive of self-harm or
 * suicidal ideation is handled exclusively by the Safety/Crisis Check gate,
 * never by retrieval-based symptom matching.
 */
export function filterSafetyRestrictedChunks(chunks: KbChunk[]): {
  indexable: KbChunk[];
  excluded: KbChunk[];
} {
  const indexable = chunks.filter((c) => !c.safetyRestricted);
  const excluded = chunks.filter((c) => c.safetyRestricted);
  return { indexable, excluded };
}

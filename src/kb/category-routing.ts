import { ClaimCategory } from "./types";

/**
 * Maps a claim's category (set by the upstream Emotion/Symptom/Context
 * agent) to the knowledge-base file(s) the Retrieval Agent should search
 * for that claim.
 *
 * This is a deliberate design choice over a single global similarity
 * search across all files: routing by category means retrieval quality
 * doesn't depend on relative chunk-count between files, and it reuses
 * categorization work the upstream agents already do rather than asking
 * the vector index to rediscover it.
 *
 * File names match the .txt basenames exactly (without extension) for
 * direct use as metadata filters against the `file` field stored at
 * index time.
 */
export const CATEGORY_TO_FILES: Record<ClaimCategory, string[]> = {
  anxiety_indicator: ["anxiety_indicators.txt", "instrument_reference.txt"],
  depression_indicator: ["depression_indicators.txt", "instrument_reference.txt"],
  shared_symptom: ["shared_symptoms.txt", "anxiety_vs_depression.txt"],
  contextual_stressor: ["contextual_stressors.txt"],
  emotional_state: [
    "anxiety_indicators.txt",
    "depression_indicators.txt",
    "anxiety_vs_depression.txt",
  ],
};

/** File queried once per session (not per-claim) for the differentiation pass. */
export const SESSION_DIFFERENTIATION_FILE = "anxiety_vs_depression.txt";

/** Per-claim retrieval cap, applied per source file before merging/capping overall. */
export const TOP_K_PER_FILE = 2;

/** Overall cap on chunks attached to a single claim after merging across files. */
export const TOP_K_PER_CLAIM = 4;

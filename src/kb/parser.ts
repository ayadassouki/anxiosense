import { readFile, readdir } from "node:fs/promises";
import { join, basename } from "node:path";
import { KbChunk, KbChunkSchema, SourceType } from "./types";

/**
 * Parses one knowledge-base .txt file into an array of KbChunk objects.
 *
 * Format contract (see knowledge-base/*.txt):
 *   Each chunk is a block separated by a line of "---".
 *   Within a block, lines are "FIELD: value" pairs, where FIELD is one of
 *   CHUNK_ID, SOURCE, SOURCE_TYPE, plus free-form fields (DESCRIPTION,
 *   USER_EXPRESSIONS, NON_DIAGNOSTIC_NOTE, CONTENT, etc).
 *
 * Design choice: instead of trying to map every field into a rigid schema,
 * the parser keeps each block's *entire raw text* as the chunk's embeddable
 * `text`, and only pulls out CHUNK_ID / SOURCE / SOURCE_TYPE /
 * SAFETY_RESTRICTED as structured metadata. This keeps the parser robust to
 * field additions in the .txt files without code changes.
 */

const CHUNK_SEPARATOR = /\n-{3,}\n/;

function extractField(block: string, field: string): string | undefined {
  const re = new RegExp(`^${field}:\\s*(.+)$`, "m");
  const match = block.match(re);
  return match?.[1]?.trim();
}

function isKnownSourceType(value: string | undefined): value is SourceType {
  return [
    "clinical_description",
    "validated_instrument_item",
    "differentiation_guidance",
    "contextual_taxonomy",
    "referral_policy",
    "safety_policy",
  ].includes(value ?? "");
}

export function parseKbFileContent(
  fileName: string,
  rawContent: string
): KbChunk[] {
  const blocks = rawContent.split(CHUNK_SEPARATOR);
  const chunks: KbChunk[] = [];

  for (const block of blocks) {
    const chunkId = extractField(block, "CHUNK_ID");
    if (!chunkId) continue; // skip header/preamble blocks with no CHUNK_ID

    const sourceTypeRaw = extractField(block, "SOURCE_TYPE");
    const sourceType = isKnownSourceType(sourceTypeRaw)
      ? sourceTypeRaw
      : "clinical_description"; // safe fallback, should not happen if KB is well-formed

    const source = extractField(block, "SOURCE");
    const safetyRestricted =
      extractField(block, "SAFETY_RESTRICTED")?.toLowerCase() === "true";

    const chunk = KbChunkSchema.parse({
      chunkId,
      file: fileName,
      sourceType,
      source,
      text: block.trim(),
      safetyRestricted,
    });

    chunks.push(chunk);
  }

  return chunks;
}

/**
 * Loads and parses a single KB file from disk.
 */
export async function loadKbFile(filePath: string): Promise<KbChunk[]> {
  const raw = await readFile(filePath, "utf-8");
  return parseKbFileContent(basename(filePath), raw);
}

/**
 * Loads and parses every .txt file in the knowledge-base directory.
 * Returns a flat list; callers can filter/group by `file` as needed.
 */
export async function loadAllKbFiles(kbDir: string): Promise<KbChunk[]> {
  const entries = await readdir(kbDir);
  const txtFiles = entries.filter((f: string) => f.endsWith(".txt"));

  const allChunks: KbChunk[] = [];
  for (const file of txtFiles) {
    const chunks = await loadKbFile(join(kbDir, file));
    allChunks.push(...chunks);
  }
  return allChunks;
}

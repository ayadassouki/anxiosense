/**
 * PII-safe logging for the AnxioSense pre-assessment pipeline.
 *
 * Raw submission text is NEVER logged. Instead, a salted SHA-256 hash
 * (truncated to 12 hex chars) is used as an opaque identifier that lets
 * researchers correlate log lines across the pipeline without exposing
 * personal content.
 *
 * Log line format (JSON, goes to process.stdout via console.log):
 *   [preAssess] {"ts":"…","hash":"…","len":N,"mode":"…","lang":"…",
 *                "langConf":N,"emoji":bool,"normalized":bool,
 *                "semantic":bool,"rejected":bool,"reasonCode":"…"}
 */

import { createHash } from 'node:crypto';
import type { InputMode, ReasonCode } from './types.js';

// ── Hashing ───────────────────────────────────────────────────────────────────

/**
 * Produce a 12-character hex digest of (LOG_SALT + text).
 * The salt prevents preimage attacks. Set LOG_SALT in your environment;
 * falls back to a development constant if absent.
 */
export function hashText(text: string): string {
  const salt = process.env.LOG_SALT ?? 'anxiosense-dev-salt';
  return createHash('sha256')
    .update(salt + text)
    .digest('hex')
    .slice(0, 12);
}

// ── Log entry ─────────────────────────────────────────────────────────────────

export interface PreAssessLogEntry {
  /** ISO-8601 timestamp. */
  ts: string;
  /** Opaque 12-char hash — NOT the raw text. */
  hash: string;
  /** Character count of the submission. */
  len: number;
  mode: InputMode;
  lang: string;
  langConf: number;
  emoji: boolean;
  normalized: boolean;
  semantic: boolean;
  rejected: boolean;
  reasonCode?: ReasonCode;
}

/**
 * Emit a structured log line to stdout.
 * The raw text is never passed in or logged.
 */
export function logPreAssess(entry: PreAssessLogEntry): void {
  console.log('[preAssess]', JSON.stringify(entry));
}

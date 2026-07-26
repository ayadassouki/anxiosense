/**
 * CORS origin policy for the AnxioSense API.
 *
 * Kept in its own module, free of import-time side effects, so the allow/reject
 * decision can be unit-tested without starting the server.
 *
 * ── Why a predicate rather than an array ─────────────────────────────────────
 * The `cors` package compares array entries by exact string equality. That works
 * for the canonical production domain but not for Vercel previews: a branch
 * deploy is served from `<project>-git-<branch>-<scope>.vercel.app` and a
 * per-commit deploy from `<project>-<hash>-<scope>.vercel.app`, where the hash
 * changes on every build. Listing them exhaustively is impossible, so preview
 * hosts are matched by pattern instead.
 *
 * ── Why the pattern is safe ──────────────────────────────────────────────────
 * The expression is anchored at both ends, requires https, requires the
 * `anxiosense-` project prefix AND the exact Vercel team scope, and escapes the
 * dots. A project someone else creates called `anxiosense-evil` lives under a
 * different scope and is rejected; only deployments inside this team's scope
 * match. Anchoring is what stops the usual bypasses —
 * `https://anxiosense-x-<scope>.vercel.app.attacker.com` and
 * `https://attacker.com/anxiosense-x-<scope>.vercel.app` both fail.
 *
 * Wildcards are never used: `Access-Control-Allow-Origin: *` would expose the
 * API to every site on the internet.
 */

import type { CorsOptions } from 'cors';

/** Vercel team scope slug that owns this project's deployments. */
const VERCEL_SCOPE = 'ayas-projects-d872809a';

/** Vercel project name. */
const VERCEL_PROJECT = 'anxiosense';

/**
 * Matches Vercel preview hosts for THIS project in THIS team scope only.
 * Covers both branch previews (`-git-<branch>-`) and per-commit deploys
 * (`-<hash>-`), since both sit between the project prefix and the scope suffix.
 */
export const VERCEL_PREVIEW_PATTERN = new RegExp(
  `^https://${VERCEL_PROJECT}-[a-z0-9-]+-${VERCEL_SCOPE}\\.vercel\\.app$`
);

/** Exact origins that are always allowed. */
export const STATIC_ALLOWED_ORIGINS: readonly string[] = [
  'http://localhost:5173', // vite dev
  'http://localhost:4173', // vite preview
  'https://anxiosense.vercel.app', // canonical production domain
] as const;

/**
 * Parses the EXTRA_CORS_ORIGINS escape hatch.
 * Comma-separated, whitespace and trailing slashes tolerated, empties dropped.
 */
export function parseExtraOrigins(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(',')
    .map(origin => origin.trim().replace(/\/+$/, '').toLowerCase())
    .filter(origin => origin.length > 0);
}

/**
 * Decides whether a browser Origin may call this API.
 *
 * A missing origin is allowed: non-browser callers (curl, health checks,
 * server-to-server) do not send one, and CORS is not the control that governs
 * them — authentication is.
 */
export function isOriginAllowed(
  origin: string | undefined,
  extraOrigins: readonly string[] = []
): boolean {
  if (origin === undefined || origin === null) return true;

  const candidate = origin.trim().replace(/\/+$/, '').toLowerCase();
  if (candidate.length === 0) return false;

  if (STATIC_ALLOWED_ORIGINS.includes(candidate)) return true;
  if (extraOrigins.includes(candidate)) return true;
  if (VERCEL_PREVIEW_PATTERN.test(candidate)) return true;

  return false;
}

/**
 * Builds the options object passed to the `cors` middleware.
 *
 * `credentials` is explicitly false. The frontend authenticates with a Bearer
 * token in the Authorization header and never sets `credentials: 'include'`, so
 * no cookie is ever sent cross-origin. Leaving credentials off means an allowed
 * origin still cannot ride on an ambient session.
 */
export function buildCorsOptions(
  extraOriginsRaw: string | undefined = process.env.EXTRA_CORS_ORIGINS
): CorsOptions {
  const extraOrigins = parseExtraOrigins(extraOriginsRaw);

  return {
    origin(origin, callback) {
      if (isOriginAllowed(origin, extraOrigins)) {
        callback(null, true);
        return;
      }
      // Reject by withholding the header rather than throwing: an error here
      // would surface as a 500 instead of a clean CORS failure. Truncated so a
      // hostile origin cannot flood the logs.
      console.warn(`[cors] rejected origin: ${String(origin).slice(0, 100)}`);
      callback(null, false);
    },
    credentials: false,
  };
}

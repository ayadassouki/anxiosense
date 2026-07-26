/**
 * Tests for the CORS origin policy.
 *
 * Run with: npm test (server package)
 *
 * Covers the origins that must be allowed, the ones that must be rejected, and
 * the anchoring bypasses that a loose pattern would let through.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import {
  isOriginAllowed,
  parseExtraOrigins,
  buildCorsOptions,
  STATIC_ALLOWED_ORIGINS,
  VERCEL_PREVIEW_PATTERN,
} from '../corsOrigin.js';

// ── Allowed ──────────────────────────────────────────────────────────────────

describe('CORS — allowed origins', () => {
  test('canonical production domain', () => {
    assert.equal(isOriginAllowed('https://anxiosense.vercel.app'), true);
  });

  test('the branch preview that was failing in the browser', () => {
    assert.equal(
      isOriginAllowed('https://anxiosense-git-deployment-ayas-projects-d872809a.vercel.app'),
      true
    );
  });

  test('other branch previews in the same scope', () => {
    for (const origin of [
      'https://anxiosense-git-main-ayas-projects-d872809a.vercel.app',
      'https://anxiosense-git-cot-oneshot-ayas-projects-d872809a.vercel.app',
      'https://anxiosense-git-rag-retrieval-agent-ayas-projects-d872809a.vercel.app',
    ]) {
      assert.equal(isOriginAllowed(origin), true, origin);
    }
  });

  test('per-commit deployment previews in the same scope', () => {
    for (const origin of [
      'https://anxiosense-9f3k2l1a0-ayas-projects-d872809a.vercel.app',
      'https://anxiosense-abc123-ayas-projects-d872809a.vercel.app',
    ]) {
      assert.equal(isOriginAllowed(origin), true, origin);
    }
  });

  test('localhost development origins', () => {
    assert.equal(isOriginAllowed('http://localhost:5173'), true);
    assert.equal(isOriginAllowed('http://localhost:4173'), true);
  });

  test('missing origin (curl, health checks, server-to-server)', () => {
    assert.equal(isOriginAllowed(undefined), true);
  });

  test('origins from EXTRA_CORS_ORIGINS', () => {
    const extra = parseExtraOrigins('https://staging.example.com, https://demo.example.com/');
    assert.equal(isOriginAllowed('https://staging.example.com', extra), true);
    assert.equal(isOriginAllowed('https://demo.example.com', extra), true);
  });
});

// ── Rejected ─────────────────────────────────────────────────────────────────

describe('CORS — rejected origins', () => {
  test('an unrelated site', () => {
    assert.equal(isOriginAllowed('https://evil.example.com'), false);
  });

  test('a different Vercel team scope', () => {
    assert.equal(
      isOriginAllowed('https://anxiosense-git-main-someone-elses-projects-99999999.vercel.app'),
      false
    );
  });

  test('a different Vercel project in no scope', () => {
    assert.equal(isOriginAllowed('https://anxiosense-clone.vercel.app'), false);
  });

  test('plain http for a preview host (https is required)', () => {
    assert.equal(
      isOriginAllowed('http://anxiosense-git-deployment-ayas-projects-d872809a.vercel.app'),
      false
    );
  });

  test('suffix bypass — attacker domain appended', () => {
    for (const origin of [
      'https://anxiosense-git-deployment-ayas-projects-d872809a.vercel.app.attacker.com',
      'https://anxiosense.vercel.app.attacker.com',
    ]) {
      assert.equal(isOriginAllowed(origin), false, origin);
    }
  });

  test('prefix bypass — allowed host embedded in a path', () => {
    assert.equal(
      isOriginAllowed('https://attacker.com/https://anxiosense-x-ayas-projects-d872809a.vercel.app'),
      false
    );
  });

  test('subdomain bypass', () => {
    assert.equal(isOriginAllowed('https://attacker.anxiosense.vercel.app'), false);
  });

  test('scope embedded as a subdomain rather than a suffix', () => {
    assert.equal(
      isOriginAllowed('https://anxiosense-x-ayas-projects-d872809a.vercel.app.evil.dev'),
      false
    );
  });

  test('localhost on an unexpected port', () => {
    assert.equal(isOriginAllowed('http://localhost:3000'), false);
  });

  test('the literal string "null" (sandboxed iframe / file://)', () => {
    assert.equal(isOriginAllowed('null'), false);
  });

  test('empty or whitespace origin', () => {
    assert.equal(isOriginAllowed(''), false);
    assert.equal(isOriginAllowed('   '), false);
  });

  test('wildcard is never accepted', () => {
    assert.equal(isOriginAllowed('*'), false);
  });
});

// ── Pattern shape ────────────────────────────────────────────────────────────

describe('CORS — preview pattern is anchored', () => {
  test('pattern is anchored at both ends', () => {
    const source = VERCEL_PREVIEW_PATTERN.source;
    assert.ok(source.startsWith('^'), 'must be anchored at the start');
    assert.ok(source.endsWith('$'), 'must be anchored at the end');
  });

  test('dots in the hostname are escaped', () => {
    assert.ok(VERCEL_PREVIEW_PATTERN.source.includes('\\.vercel\\.app'));
  });

  test('the canonical production domain is an exact entry, not pattern-matched', () => {
    assert.ok(STATIC_ALLOWED_ORIGINS.includes('https://anxiosense.vercel.app'));
    assert.equal(VERCEL_PREVIEW_PATTERN.test('https://anxiosense.vercel.app'), false);
  });
});

// ── Extra origins parsing ────────────────────────────────────────────────────

describe('CORS — parseExtraOrigins', () => {
  test('undefined and empty yield no origins', () => {
    assert.deepEqual(parseExtraOrigins(undefined), []);
    assert.deepEqual(parseExtraOrigins(''), []);
    assert.deepEqual(parseExtraOrigins('  ,  , '), []);
  });

  test('trims whitespace, strips trailing slashes, lowercases', () => {
    assert.deepEqual(
      parseExtraOrigins(' https://A.example.com/ , https://b.example.com '),
      ['https://a.example.com', 'https://b.example.com']
    );
  });
});

// ── Middleware options ───────────────────────────────────────────────────────

describe('CORS — middleware options', () => {
  test('credentials are never enabled', () => {
    assert.equal(buildCorsOptions().credentials, false);
  });

  test('origin callback allows an approved origin', () => {
    const options = buildCorsOptions();
    const origin = options.origin as (
      o: string | undefined,
      cb: (err: Error | null, allow?: boolean) => void
    ) => void;

    let result: boolean | undefined;
    origin('https://anxiosense.vercel.app', (err, allow) => {
      assert.equal(err, null);
      result = allow;
    });
    assert.equal(result, true);
  });

  test('origin callback rejects without throwing (no 500)', () => {
    const options = buildCorsOptions();
    const origin = options.origin as (
      o: string | undefined,
      cb: (err: Error | null, allow?: boolean) => void
    ) => void;

    let result: boolean | undefined;
    let error: Error | null = new Error('not called');
    origin('https://evil.example.com', (err, allow) => {
      error = err;
      result = allow;
    });
    assert.equal(error, null, 'must not pass an Error — that would surface as a 500');
    assert.equal(result, false);
  });

  test('EXTRA_CORS_ORIGINS is honoured through buildCorsOptions', () => {
    const options = buildCorsOptions('https://extra.example.com');
    const origin = options.origin as (
      o: string | undefined,
      cb: (err: Error | null, allow?: boolean) => void
    ) => void;

    let result: boolean | undefined;
    origin('https://extra.example.com', (_err, allow) => { result = allow; });
    assert.equal(result, true);
  });
});

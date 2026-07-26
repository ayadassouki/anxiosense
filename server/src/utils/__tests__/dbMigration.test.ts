/**
 * Implementation-level tests for the reports schema migration.
 *
 * Tests run against a REAL better-sqlite3 database created in a temp directory —
 * not a mock — so they exercise the same SQLite behaviour the server relies on.
 * The production database is never opened: the migration helpers are imported
 * from dbMigrations.ts, which has no import-time side effects, rather than from
 * db.ts, which opens server/data/anxiosense.db as soon as it is loaded.
 *
 * Run with: npm test (server package)
 */

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import Database from 'better-sqlite3';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { v4 as uuid } from 'uuid';
import {
  applyColumnMigrations,
  verifyReportsSchema,
  tableColumns,
  REQUIRED_REPORT_COLUMNS,
} from '../../dbMigrations.js';

// ── Schema fixtures ───────────────────────────────────────────────────────────

/** The reports table exactly as it existed BEFORE functional_impairment was added. */
const LEGACY_SCHEMA = `
  CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE TABLE reports (
    id              TEXT    PRIMARY KEY,
    user_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode            TEXT    NOT NULL CHECK(mode IN ('journal','social-media')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    concern_pattern TEXT    NOT NULL,
    referral_level  TEXT    NOT NULL CHECK(referral_level IN ('low','moderate','urgent')),
    summary         TEXT    NOT NULL,
    full_report     TEXT    NOT NULL,
    clinician_mode  INTEGER NOT NULL DEFAULT 0
  );
`;

/** The reports table as CREATE TABLE IF NOT EXISTS builds it today. */
const CURRENT_SCHEMA = LEGACY_SCHEMA.replace(
  'clinician_mode  INTEGER NOT NULL DEFAULT 0\n  );',
  'clinician_mode  INTEGER NOT NULL DEFAULT 0,\n    functional_impairment TEXT\n  );'
);

/** The exact INSERT used by both save paths in routes/workflow.ts. */
const PRODUCTION_INSERT = `
  INSERT INTO reports
    (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode, functional_impairment)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
`;

let tmpDir: string;

before(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'anxiosense-migration-'));
});

after(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

/** Creates an isolated on-disk database seeded with one user row. */
function makeDb(schema: string, label: string): { db: Database.Database; userId: string } {
  const db = new Database(path.join(tmpDir, `${label}-${uuid()}.db`));
  db.pragma('foreign_keys = ON');
  db.exec(schema);
  const userId = uuid();
  db.prepare('INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)')
    .run(userId, 'Test User', `${userId}@example.test`, 'not-a-real-hash');
  return { db, userId };
}

function insertReport(db: Database.Database, userId: string, impairment: string | null): void {
  db.prepare(PRODUCTION_INSERT).run(
    uuid(), userId, 'journal', 'Mild Concern Pattern', 'moderate',
    'summary text', 'full report body', 0, impairment
  );
}

// ── Regression: the failure this migration exists to prevent ──────────────────

describe('legacy database — reproduces the persistence failure', () => {
  test('production INSERT throws before migration', () => {
    const { db, userId } = makeDb(LEGACY_SCHEMA, 'legacy-fail');
    assert.throws(
      () => insertReport(db, userId, 'somewhat_difficult'),
      /no column named functional_impairment/,
      'expected the 9-column INSERT to fail against the pre-migration schema'
    );
    db.close();
  });

  test('verifyReportsSchema reports the missing column before migration', () => {
    const { db } = makeDb(LEGACY_SCHEMA, 'legacy-verify');
    const result = verifyReportsSchema(db);
    assert.equal(result.ok, false);
    assert.deepEqual(result.missing, ['functional_impairment']);
    db.close();
  });
});

// ── Migration repairs a legacy database ──────────────────────────────────────

describe('applyColumnMigrations — legacy database', () => {
  test('adds functional_impairment and reports what it applied', () => {
    const { db } = makeDb(LEGACY_SCHEMA, 'legacy-apply');
    const applied = applyColumnMigrations(db);
    assert.deepEqual(applied, ['reports.functional_impairment']);
    assert.ok(tableColumns(db, 'reports').includes('functional_impairment'));
    db.close();
  });

  test('production INSERT succeeds after migration', () => {
    const { db, userId } = makeDb(LEGACY_SCHEMA, 'legacy-insert');
    applyColumnMigrations(db);
    insertReport(db, userId, 'somewhat_difficult');
    const row = db.prepare('SELECT functional_impairment FROM reports').get() as
      { functional_impairment: string | null };
    assert.equal(row.functional_impairment, 'somewhat_difficult');
    db.close();
  });

  test('accepts NULL impairment — the crisis and social-media paths', () => {
    const { db, userId } = makeDb(LEGACY_SCHEMA, 'legacy-null');
    applyColumnMigrations(db);
    insertReport(db, userId, null);
    const row = db.prepare('SELECT functional_impairment FROM reports').get() as
      { functional_impairment: string | null };
    assert.equal(row.functional_impairment, null);
    db.close();
  });

  test('preserves pre-existing rows, backfilling them with NULL', () => {
    const { db, userId } = makeDb(LEGACY_SCHEMA, 'legacy-preserve');
    // Two rows written with the OLD 8-column form, as historical rows were.
    for (let i = 0; i < 2; i++) {
      db.prepare(`
        INSERT INTO reports (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(uuid(), userId, 'journal', 'Mild Concern Pattern', 'low', 's', 'f', 0);
    }
    applyColumnMigrations(db);

    assert.equal((db.prepare('SELECT count(*) AS n FROM reports').get() as { n: number }).n, 2);
    const nulls = db.prepare(
      'SELECT count(*) AS n FROM reports WHERE functional_impairment IS NULL'
    ).get() as { n: number };
    assert.equal(nulls.n, 2, 'existing rows must survive with a NULL impairment');
    db.close();
  });

  test('verifyReportsSchema passes after migration', () => {
    const { db } = makeDb(LEGACY_SCHEMA, 'legacy-verify-after');
    applyColumnMigrations(db);
    assert.deepEqual(verifyReportsSchema(db), { ok: true, missing: [] });
    db.close();
  });
});

// ── Idempotency ───────────────────────────────────────────────────────────────

describe('applyColumnMigrations — idempotency', () => {
  test('second run is a no-op and does not throw', () => {
    const { db } = makeDb(LEGACY_SCHEMA, 'idempotent');
    assert.deepEqual(applyColumnMigrations(db), ['reports.functional_impairment']);
    assert.deepEqual(applyColumnMigrations(db), [], 'second run must apply nothing');
    assert.deepEqual(applyColumnMigrations(db), [], 'third run must apply nothing');
    db.close();
  });

  test('no-op on a freshly created current-schema database', () => {
    const { db } = makeDb(CURRENT_SCHEMA, 'fresh');
    assert.deepEqual(
      applyColumnMigrations(db), [],
      'CREATE TABLE already includes the column — nothing to migrate'
    );
    assert.equal(verifyReportsSchema(db).ok, true);
    db.close();
  });

  test('repeated migration does not disturb existing data', () => {
    const { db, userId } = makeDb(LEGACY_SCHEMA, 'idempotent-data');
    applyColumnMigrations(db);
    insertReport(db, userId, 'very_difficult');
    applyColumnMigrations(db);
    const row = db.prepare('SELECT functional_impairment FROM reports').get() as
      { functional_impairment: string | null };
    assert.equal(row.functional_impairment, 'very_difficult');
    db.close();
  });
});

// ── Helper behaviour ──────────────────────────────────────────────────────────

describe('tableColumns', () => {
  test('returns [] for a table that does not exist', () => {
    const { db } = makeDb(CURRENT_SCHEMA, 'missing-table');
    assert.deepEqual(tableColumns(db, 'no_such_table'), []);
    db.close();
  });

  test('migration skips a table that has not been created yet', () => {
    const db = new Database(path.join(tmpDir, `empty-${uuid()}.db`));
    assert.deepEqual(applyColumnMigrations(db), [], 'must not throw on an empty database');
    db.close();
  });
});

// ── Contract between the migration list and the write path ───────────────────

describe('REQUIRED_REPORT_COLUMNS', () => {
  test('matches the columns named in the production INSERT', () => {
    const insertColumns = PRODUCTION_INSERT
      .slice(PRODUCTION_INSERT.indexOf('(') + 1, PRODUCTION_INSERT.indexOf(')'))
      .split(',')
      .map(c => c.trim());

    for (const column of insertColumns) {
      assert.ok(
        REQUIRED_REPORT_COLUMNS.includes(column),
        `INSERT writes "${column}" but it is absent from REQUIRED_REPORT_COLUMNS`
      );
    }
  });

  test('every required column exists on a fresh database', () => {
    const { db } = makeDb(CURRENT_SCHEMA, 'contract');
    const columns = tableColumns(db, 'reports');
    for (const required of REQUIRED_REPORT_COLUMNS) {
      assert.ok(columns.includes(required), `fresh schema is missing "${required}"`);
    }
    db.close();
  });
});

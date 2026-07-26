import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { applyColumnMigrations, verifyReportsSchema } from './dbMigrations.js';

const DB_DIR = path.join(process.cwd(), 'data');
if (!fs.existsSync(DB_DIR)) fs.mkdirSync(DB_DIR, { recursive: true });

const db = new Database(path.join(DB_DIR, 'anxiosense.db'));

// Enable WAL mode for better concurrent reads
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id           TEXT    PRIMARY KEY,
    name         TEXT    NOT NULL,
    email        TEXT    NOT NULL UNIQUE,
    password_hash TEXT   NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS reports (
    id              TEXT    PRIMARY KEY,
    user_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode            TEXT    NOT NULL CHECK(mode IN ('journal','social-media')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    concern_pattern TEXT    NOT NULL,
    referral_level  TEXT    NOT NULL CHECK(referral_level IN ('low','moderate','urgent')),
    summary         TEXT    NOT NULL,
    full_report            TEXT    NOT NULL,
    clinician_mode         INTEGER NOT NULL DEFAULT 0,
    functional_impairment  TEXT
  );

  CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
  CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
`);

// ── Migrations ────────────────────────────────────────────────────────────────
// Databases created before a column was introduced need it added. See
// dbMigrations.ts for the registry and for why presence is detected via
// PRAGMA table_info rather than by matching ALTER TABLE error text.
const appliedMigrations = applyColumnMigrations(db);
if (appliedMigrations.length > 0) {
  console.log(`[db] applied column migration(s): ${appliedMigrations.join(', ')}`);
}

// Fail loudly — but do not crash — if the write path's columns are still missing.
// A missing column makes every report INSERT throw, and those throws are caught
// as non-fatal in routes/workflow.ts, so without this check the only symptom is
// reports silently never being saved.
const schemaCheck = verifyReportsSchema(db);
if (!schemaCheck.ok) {
  console.error(
    `[db] SCHEMA MISMATCH — reports table is missing: ${schemaCheck.missing.join(', ')}. ` +
    `Report saves WILL fail until this is resolved.`
  );
}

export default db;

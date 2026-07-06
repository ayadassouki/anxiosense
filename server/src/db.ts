import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

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
    full_report     TEXT    NOT NULL,
    clinician_mode  INTEGER NOT NULL DEFAULT 0
  );

  CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
  CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
`);

export default db;

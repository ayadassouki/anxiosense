/**
 * Schema migrations for the AnxioSense reports database.
 *
 * Deliberately free of import-time side effects: db.ts opens (and creates) the real
 * database as soon as it is imported, so keeping the migration logic in a separate
 * module lets it be unit-tested against a temporary database without touching
 * server/data/anxiosense.db.
 *
 * Column presence is detected with PRAGMA table_info rather than by running
 * ALTER TABLE and matching the resulting error text. SQLite's "duplicate column
 * name" wording is not a stable API, and a message-matching guard silently
 * downgrades a genuine migration failure into a no-op.
 *
 * ALTER TABLE ADD COLUMN is metadata-only in SQLite — no table rewrite, no data
 * movement — so these migrations are safe to run on every startup.
 */

import type { Database as SqliteDatabase } from 'better-sqlite3';

// ── Migration registry ────────────────────────────────────────────────────────

export interface ColumnMigration {
  /** Table the column belongs to. */
  table: string;
  /** Column that must exist after the migration runs. */
  column: string;
  /** DDL executed only when the column is absent. */
  ddl: string;
}

/**
 * Additive column migrations, applied in order.
 * Append new entries here; never edit or reorder existing ones.
 */
export const COLUMN_MIGRATIONS: readonly ColumnMigration[] = [
  {
    table:  'reports',
    column: 'functional_impairment',
    ddl:    'ALTER TABLE reports ADD COLUMN functional_impairment TEXT',
  },
] as const;

/**
 * Every column the INSERT statements in routes/workflow.ts depend on.
 * If any is missing at startup, report saves will throw at runtime.
 */
export const REQUIRED_REPORT_COLUMNS: readonly string[] = [
  'id',
  'user_id',
  'mode',
  'created_at',
  'concern_pattern',
  'referral_level',
  'summary',
  'full_report',
  'clinician_mode',
  'functional_impairment',
] as const;

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Returns the column names of a table, or [] when the table does not exist.
 *
 * Note: `table` is interpolated into the PRAGMA statement because SQLite does not
 * accept bound parameters in PRAGMA. Values only ever come from the module-level
 * constants above — never from user input.
 */
export function tableColumns(db: SqliteDatabase, table: string): string[] {
  const rows = db.pragma(`table_info(${table})`) as Array<{ name: string }>;
  return rows.map(row => row.name);
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Applies any missing additive column migrations.
 * Idempotent: running it repeatedly on an up-to-date database is a no-op.
 *
 * @returns the migrations applied on this call, as "table.column" strings.
 */
export function applyColumnMigrations(db: SqliteDatabase): string[] {
  const applied: string[] = [];

  for (const migration of COLUMN_MIGRATIONS) {
    const columns = tableColumns(db, migration.table);

    // Table not created yet — CREATE TABLE already includes the column, so there
    // is nothing to migrate.
    if (columns.length === 0) continue;

    // Column already present — idempotent no-op.
    if (columns.includes(migration.column)) continue;

    db.exec(migration.ddl);
    applied.push(`${migration.table}.${migration.column}`);
  }

  return applied;
}

/**
 * Confirms the reports table carries every column the write path requires.
 * Call after applyColumnMigrations so a failed migration surfaces at startup
 * rather than as a swallowed error on the first save attempt.
 */
export function verifyReportsSchema(db: SqliteDatabase): { ok: boolean; missing: string[] } {
  const columns = tableColumns(db, 'reports');
  const missing = REQUIRED_REPORT_COLUMNS.filter(required => !columns.includes(required));
  return { ok: missing.length === 0, missing };
}

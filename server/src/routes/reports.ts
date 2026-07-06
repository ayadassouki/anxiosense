import { Router, Request, Response } from 'express';
import db from '../db.js';
import { requireAuth } from '../middleware/auth.js';
import type { ReportRow } from '../types.js';

const router = Router();

function toApi(row: ReportRow) {
  return {
    id:             row.id,
    userId:         row.user_id,
    mode:           row.mode,
    createdAt:      row.created_at,
    concernPattern: row.concern_pattern,
    referralLevel:  row.referral_level,
    summary:        row.summary,
    fullReport:     row.full_report,
    clinicianMode:  Boolean(row.clinician_mode),
  };
}

// ── GET /api/reports ──────────────────────────────────────────────────────────
router.get('/', requireAuth, (req: Request, res: Response): void => {
  const rows = db.prepare(`
    SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC
  `).all(req.user!.userId) as ReportRow[];
  res.json(rows.map(toApi));
});

// ── GET /api/reports/:id ──────────────────────────────────────────────────────
router.get('/:id', requireAuth, (req: Request, res: Response): void => {
  const row = db.prepare(`
    SELECT * FROM reports WHERE id = ? AND user_id = ?
  `).get(req.params.id, req.user!.userId) as ReportRow | undefined;
  if (!row) { res.status(404).json({ message: 'Report not found.' }); return; }
  res.json(toApi(row));
});

// ── DELETE /api/reports/:id ───────────────────────────────────────────────────
router.delete('/:id', requireAuth, (req: Request, res: Response): void => {
  const info = db.prepare(`
    DELETE FROM reports WHERE id = ? AND user_id = ?
  `).run(req.params.id, req.user!.userId);
  if (info.changes === 0) { res.status(404).json({ message: 'Report not found.' }); return; }
  res.status(204).send();
});

export default router;

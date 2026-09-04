import 'dotenv/config'; // MUST be first — loads server/.env before any other module reads process.env
import express from 'express';
import cors from 'cors';
import { buildCorsOptions } from './utils/corsOrigin.js';

import authRoutes     from './routes/auth.js';
import reportsRoutes  from './routes/reports.js';
import workflowRoutes from './routes/workflow.js';
import { requireAuth } from './middleware/auth.js';

// Ensure DB is initialised on startup
import './db.js';

const app  = express();
const PORT = Number(process.env.PORT ?? 3001);

// ── Middleware ────────────────────────────────────────────────────────────────
// Exact-match allowlist plus a scoped hostname pattern for Vercel previews,
// whose per-deployment URLs change on every build. See utils/corsOrigin.ts.
app.use(cors(buildCorsOptions()));
app.use(express.json({ limit: '1mb' }));

// Basic rate-limit (simple in-memory, dev-grade)
const counts = new Map<string, { count: number; reset: number }>();
app.use((req, res, next) => {
  const ip    = req.ip ?? '0.0.0.0';
  const now   = Date.now();
  const entry = counts.get(ip);
  if (!entry || now > entry.reset) {
    counts.set(ip, { count: 1, reset: now + 60_000 });
  } else if (entry.count >= 60) {
    res.status(429).json({ message: 'Too many requests — please wait a minute.' });
    return;
  } else {
    entry.count++;
  }
  next();
});

// ── Routes ────────────────────────────────────────────────────────────────────
app.use('/api/auth',     authRoutes);
app.use('/api/reports',  requireAuth, reportsRoutes);
// workflow route handles its own optional auth (saves if authed)
app.use('/api/workflow', (req, res, next) => {
  const header = req.headers.authorization;
  if (header?.startsWith('Bearer ')) {
    // Attach user if token is valid, but don't block if not
    import('./middleware/auth.js').then(({ requireAuth: ra, signToken: _st }) => {
      const fakeNext = (err?: unknown) => { if (err) next(err); else next(); };
      // Manually verify without blocking
      import('jsonwebtoken').then(({ default: jwt }) => {
        const secret = process.env.JWT_SECRET ?? 'anxiosense-dev-secret-change-in-prod';
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (req as any).user = jwt.verify(header.slice(7), secret);
        } catch { /* anonymous */ }
        next();
      });
    });
  } else {
    next();
  }
});
app.use('/api/workflow', workflowRoutes);

// ── Health ────────────────────────────────────────────────────────────────────
app.get('/api/health', (_req, res) => {
  // The EFFECTIVE Mastra poll cadence, resolved exactly as pollRun() resolves it
  // (server/src/routes/workflow.ts). Publication-runner preflight reads this so
  // the interval that produced a run's latency figures is recorded in that run's
  // provenance instead of being an unrecorded property of the shell that started
  // this process. Reported as null when the env var is set to something
  // non-numeric, so preflight fails loudly rather than recording a wrong value.
  const rawInterval = process.env.MASTRA_POLL_INTERVAL_MS;
  const rawMax = process.env.MASTRA_POLL_MAX_MS;
  const resolve = (raw: string | undefined, fallback: number): number | null => {
    if (raw === undefined) return fallback;          // pollRun's ?? default
    const v = Number(raw);
    return Number.isFinite(v) && v > 0 ? v : null;   // invalid -> explicit null
  };
  res.json({
    status: 'ok',
    time: new Date().toISOString(),
    mastra_poll_interval_ms: resolve(rawInterval, 3000),
    mastra_poll_max_ms: resolve(rawMax, 150_000),
    mastra_poll_interval_source: rawInterval === undefined ? 'default' : 'env',
  });
});

// ── 404 ───────────────────────────────────────────────────────────────────────
app.use((_req, res) => res.status(404).json({ message: 'Not found.' }));

// ── Error handler ─────────────────────────────────────────────────────────────
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('[server error]', err);
  res.status(500).json({ message: 'Internal server error.' });
});

app.listen(PORT, () => {
  console.log(`AnxioSense server running on http://localhost:${PORT}`);
});

import 'dotenv/config'; // MUST be first — loads server/.env before any other module reads process.env
import express from 'express';
import cors from 'cors';

import authRoutes     from './routes/auth.js';
import reportsRoutes  from './routes/reports.js';
import workflowRoutes from './routes/workflow.js';
import { requireAuth } from './middleware/auth.js';

// Ensure DB is initialised on startup
import './db.js';

const app  = express();
const PORT = Number(process.env.PORT ?? 3001);

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(cors({ origin: ['http://localhost:5173', 'http://localhost:4173'] }));
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
  res.json({ status: 'ok', time: new Date().toISOString() });
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

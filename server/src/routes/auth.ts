import { Router, Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import { v4 as uuid } from 'uuid';
import { OAuth2Client } from 'google-auth-library';
import db from '../db.js';
import { requireAuth, signToken } from '../middleware/auth.js';

const router = Router();

// ── POST /api/auth/register ───────────────────────────────────────────────────
router.post('/register', async (req: Request, res: Response): Promise<void> => {
  const { name, email, password } = req.body as { name?: string; email?: string; password?: string };
  if (!name?.trim() || !email?.trim() || !password) {
    res.status(400).json({ message: 'Name, email, and password are required.' });
    return;
  }
  if (password.length < 8) {
    res.status(400).json({ message: 'Password must be at least 8 characters.' });
    return;
  }

  const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email.toLowerCase().trim());
  if (existing) {
    res.status(409).json({ message: 'An account with this email already exists.' });
    return;
  }

  const hash = await bcrypt.hash(password, 12);
  const id   = uuid();
  db.prepare('INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)')
    .run(id, name.trim(), email.toLowerCase().trim(), hash);

  const token = signToken({ userId: id, email: email.toLowerCase().trim(), name: name.trim() });
  res.status(201).json({ token, user: { id, name: name.trim(), email: email.toLowerCase().trim() } });
});

// ── POST /api/auth/login ──────────────────────────────────────────────────────
router.post('/login', async (req: Request, res: Response): Promise<void> => {
  const { email, password } = req.body as { email?: string; password?: string };
  if (!email?.trim() || !password) {
    res.status(400).json({ message: 'Email and password are required.' });
    return;
  }

  const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email.toLowerCase().trim()) as
    { id: string; name: string; email: string; password_hash: string } | undefined;

  if (!user) {
    res.status(401).json({ message: 'Invalid email or password.' });
    return;
  }

  const match = await bcrypt.compare(password, user.password_hash);
  if (!match) {
    res.status(401).json({ message: 'Invalid email or password.' });
    return;
  }

  const token = signToken({ userId: user.id, email: user.email, name: user.name });
  res.json({ token, user: { id: user.id, name: user.name, email: user.email } });
});

// ── POST /api/auth/google ─────────────────────────────────────────────────────
router.post('/google', async (req: Request, res: Response): Promise<void> => {
  const { credential } = req.body as { credential?: string };
  if (!credential) {
    res.status(400).json({ message: 'Google credential is required.' });
    return;
  }
  if (!process.env.GOOGLE_CLIENT_ID) {
    res.status(501).json({ message: 'Google Sign-In is not configured on this server. Add GOOGLE_CLIENT_ID to server/.env' });
    return;
  }

  // Build client lazily so it reads the env var that dotenv loaded at startup
  const googleClient = new OAuth2Client(process.env.GOOGLE_CLIENT_ID);

  let payload: { sub: string; email: string; name: string; picture?: string } | undefined;
  try {
    const ticket = await googleClient.verifyIdToken({
      idToken: credential,
      audience: process.env.GOOGLE_CLIENT_ID,
    });
    const p = ticket.getPayload();
    if (!p?.email || !p?.sub) throw new Error('Invalid token payload');
    payload = { sub: p.sub, email: p.email, name: p.name ?? p.email.split('@')[0], picture: p.picture };
  } catch {
    res.status(401).json({ message: 'Could not verify Google token. Please try again.' });
    return;
  }

  // Find or create user
  let user = db.prepare('SELECT id, name, email FROM users WHERE email = ?').get(payload.email.toLowerCase()) as
    { id: string; name: string; email: string } | undefined;

  if (!user) {
    const id = uuid();
    // Google users get a random unusable password hash
    const unusableHash = await bcrypt.hash(uuid(), 12);
    db.prepare('INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)')
      .run(id, payload.name, payload.email.toLowerCase(), unusableHash);
    user = { id, name: payload.name, email: payload.email.toLowerCase() };
  }

  const token = signToken({ userId: user.id, email: user.email, name: user.name });
  res.json({ token, user: { id: user.id, name: user.name, email: user.email } });
});

// ── GET /api/auth/me ──────────────────────────────────────────────────────────
router.get('/me', requireAuth, (req: Request, res: Response): void => {
  const { userId } = req.user!;
  const user = db.prepare('SELECT id, name, email FROM users WHERE id = ?').get(userId) as
    { id: string; name: string; email: string } | undefined;
  if (!user) { res.status(404).json({ message: 'User not found.' }); return; }
  res.json({ user });
});

export default router;

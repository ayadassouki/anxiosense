import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

// Fail closed in production: refuse to start if JWT_SECRET is not explicitly set.
// In development the fallback string is permitted but logged as a warning.
if (process.env.NODE_ENV === 'production' && !process.env.JWT_SECRET) {
  throw new Error(
    '[auth] JWT_SECRET environment variable must be set in production. ' +
    'Set it to a long random string (e.g. openssl rand -hex 32).'
  );
}
if (!process.env.JWT_SECRET) {
  console.warn(
    '[auth] WARNING: JWT_SECRET not set. Using insecure fallback. ' +
    'Set JWT_SECRET in .env before any user-facing deployment.'
  );
}

const JWT_SECRET = process.env.JWT_SECRET ?? 'anxiosense-dev-secret-change-in-prod';

export interface AuthPayload {
  userId: string;
  email:  string;
  name:   string;
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: AuthPayload;
    }
  }
}

export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    res.status(401).json({ message: 'Authentication required.' });
    return;
  }
  const token = header.slice(7);
  try {
    req.user = jwt.verify(token, JWT_SECRET) as AuthPayload;
    next();
  } catch {
    res.status(401).json({ message: 'Invalid or expired token.' });
  }
}

export function signToken(payload: AuthPayload): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' });
}

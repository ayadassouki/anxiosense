import {
  createContext, useContext, useState, useEffect,
  useCallback, ReactNode,
} from 'react';
import { API_URL } from '../config/api';

export interface User {
  id: string;
  email: string;
  name: string;
  isGuest: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login:            (email: string, password: string) => Promise<void>;
  signup:           (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle:  (credential: string) => Promise<void>;
  continueAsGuest:  () => void;
  logout:           () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'anxiosense_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null, token: null, loading: true,
  });

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setState(s => ({ ...s, loading: false })); return; }

    fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: { user: User }) => setState({ user: { ...data.user, isGuest: false }, token, loading: false }))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setState({ user: null, token: null, loading: false });
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    let res: Response;
    try {
      res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      throw new Error('Could not reach the server. Please try again later.');
    }
    const body = await res.json().catch(() => ({})) as { message?: string; token?: string; user?: User };
    if (!res.ok) throw new Error(body.message ?? `Login failed (HTTP ${res.status})`);
    const { token, user } = body as { token: string; user: User };
    localStorage.setItem(TOKEN_KEY, token);
    setState({ user: { ...user, isGuest: false }, token, loading: false });
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string) => {
    let res: Response;
    try {
      res = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
    } catch {
      throw new Error('Could not reach the server. Please try again later.');
    }
    const body = await res.json().catch(() => ({})) as { message?: string; token?: string; user?: User };
    if (!res.ok) throw new Error(body.message ?? `Registration failed (HTTP ${res.status})`);
    const { token, user } = body as { token: string; user: User };
    localStorage.setItem(TOKEN_KEY, token);
    setState({ user: { ...user, isGuest: false }, token, loading: false });
  }, []);

  const loginWithGoogle = useCallback(async (credential: string) => {
    let res: Response;
    try {
      res = await fetch(`${API_URL}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });
    } catch {
      throw new Error('Could not reach the server. Please try again later.');
    }
    const body = await res.json().catch(() => ({})) as { message?: string; token?: string; user?: User };
    if (!res.ok) throw new Error(body.message ?? `Google sign-in failed (HTTP ${res.status})`);
    const { token, user } = body as { token: string; user: User };
    localStorage.setItem(TOKEN_KEY, token);
    setState({ user: { ...user, isGuest: false }, token, loading: false });
  }, []);

  const continueAsGuest = useCallback(() => {
    const guest: User = { id: `guest-${Date.now()}`, email: '', name: 'Guest', isGuest: true };
    setState({ user: guest, token: null, loading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setState({ user: null, token: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, loginWithGoogle, continueAsGuest, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

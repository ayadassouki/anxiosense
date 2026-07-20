import { useState, FormEvent } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button,
  Divider, Alert, CircularProgress, Link, IconButton,
  InputAdornment, Fade,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

const GOOGLE_CONFIGURED = !!import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function LoginPage() {
  const { login, loginWithGoogle, continueAsGuest } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true); setError('');
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSuccess(credentialResponse: { credential?: string }) {
    if (!credentialResponse.credential) {
      setError('Google sign-in failed. No credential received.');
      return;
    }
    setError('');
    try {
      await loginWithGoogle(credentialResponse.credential);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Google sign-in failed. Please try again.');
    }
  }

  return (
    <Box sx={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      bgcolor: 'background.default',
      background: 'radial-gradient(ellipse at 20% 50%, rgba(79,124,172,0.08) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(126,200,165,0.08) 0%, transparent 60%)',
      p: 2,
    }}>
      <Fade in timeout={400}>
        <Box sx={{ width: '100%', maxWidth: 440 }}>

          {/* Brand mark */}
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box sx={{
              width: 56, height: 56, borderRadius: 3, mx: 'auto', mb: 2,
              background: 'linear-gradient(135deg, #4F7CAC, #7EC8A5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(79,124,172,0.3)',
            }}>
              <Typography sx={{ color: 'white', fontWeight: 800, fontSize: 26, lineHeight: 1 }}>A</Typography>
            </Box>
            <Typography variant="h2" gutterBottom>Welcome back</Typography>
            <Typography color="text.secondary" variant="body2">
              Sign in to access your screening reports
            </Typography>
          </Box>

          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent sx={{ p: { xs: 3, sm: 4 } }}>

              {error && (
                <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError('')}>
                  {error}
                </Alert>
              )}

              {/* Google Sign-In */}
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
                {GOOGLE_CONFIGURED ? (
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => setError('Google sign-in was cancelled or failed.')}
                    width="400"
                    text="continue_with"
                    shape="rectangular"
                    theme="outline"
                  />
                ) : (
                  <Button
                    variant="outlined" fullWidth size="large"
                    startIcon={
                      <Box component="img"
                        src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
                        alt="Google" sx={{ width: 18, height: 18 }} />
                    }
                    sx={{ borderColor: '#E5E7EB', color: 'text.secondary',
                      '&:hover': { borderColor: '#D1D5DB', bgcolor: '#F9FAFB' } }}
                    disabled
                  >
                    Continue with Google
                    <Typography variant="caption" sx={{ ml: 1 }}>(setup needed — see below)</Typography>
                  </Button>
                )}
              </Box>

              <Divider sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">or sign in with email</Typography>
              </Divider>

              <form onSubmit={handleSubmit} noValidate>
                <TextField
                  label="Email address" type="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email" autoFocus sx={{ mb: 2 }}
                />
                <TextField
                  label="Password" type={showPass ? 'text' : 'password'}
                  value={password} onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password" sx={{ mb: 3 }}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowPass(s => !s)} edge="end" size="small">
                          {showPass ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  type="submit" variant="contained" fullWidth size="large"
                  disabled={loading} sx={{ mb: 1.5, py: 1.4 }}
                >
                  {loading ? <CircularProgress size={22} color="inherit" /> : 'Sign in'}
                </Button>
              </form>

              <Divider sx={{ my: 2 }}>
                <Typography variant="caption" color="text.secondary">or</Typography>
              </Divider>

              <Button
                variant="text" fullWidth size="large"
                onClick={() => { continueAsGuest(); navigate('/dashboard'); }}
                sx={{ color: 'text.secondary', '&:hover': { color: 'primary.main' } }}
              >
                Continue as Guest
              </Button>
            </CardContent>
          </Card>

          <Typography variant="body2" textAlign="center" sx={{ mt: 3, color: 'text.secondary' }}>
            Don't have an account?{' '}
            <Link component={RouterLink} to="/signup" fontWeight={600} underline="hover">
              Sign up
            </Link>
          </Typography>

          {/* Setup hint shown when Google not configured */}
          {!GOOGLE_CONFIGURED && (
            <Box sx={{
              mt: 3, p: 2, borderRadius: 3,
              bgcolor: 'rgba(79,124,172,0.05)', border: '1px solid rgba(79,124,172,0.12)',
            }}>
              <Typography variant="caption" color="text.secondary" display="block" lineHeight={1.8}>
                <strong>To enable Google Sign-In:</strong><br />
                1. Go to <Link href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer">console.cloud.google.com</Link><br />
                2. Create an OAuth 2.0 Client ID (Web application)<br />
                3. Add <code>http://localhost:5173</code> as authorized JS origin<br />
                4. Paste the Client ID in <code>frontend/.env</code> and <code>server/.env</code>
              </Typography>
            </Box>
          )}

          <Box sx={{
            mt: 2, p: 2, borderRadius: 3,
            bgcolor: 'rgba(79,124,172,0.05)', border: '1px solid rgba(79,124,172,0.12)',
          }}>
            <Typography variant="caption" color="text.secondary" display="block" textAlign="center" lineHeight={1.7}>
              🔒 Assessments are not saved by default. Responses are transmitted to the AnxioSense
              server and processed using third-party AI infrastructure. AnxioSense is a research
              prototype and should not be treated as a confidential clinical service.
            </Typography>
          </Box>

        </Box>
      </Fade>
    </Box>
  );
}

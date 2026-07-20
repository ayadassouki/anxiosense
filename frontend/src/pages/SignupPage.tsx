import { useState, FormEvent } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button,
  Alert, CircularProgress, Link, IconButton, InputAdornment, Fade, Divider,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

const GOOGLE_CONFIGURED = !!import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function SignupPage() {
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [name, setName]         = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name || !email || !password) { setError('Please fill in all fields.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setLoading(true); setError('');
    try {
      await signup(name, email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
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
      background: 'radial-gradient(ellipse at 80% 50%, rgba(79,124,172,0.08) 0%, transparent 60%), radial-gradient(ellipse at 20% 80%, rgba(126,200,165,0.08) 0%, transparent 60%)',
      p: 2,
    }}>
      <Fade in timeout={400}>
        <Box sx={{ width: '100%', maxWidth: 440 }}>

          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box sx={{
              width: 56, height: 56, borderRadius: 3, mx: 'auto', mb: 2,
              background: 'linear-gradient(135deg, #7EC8A5, #4F7CAC)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(126,200,165,0.3)',
            }}>
              <Typography sx={{ color: 'white', fontWeight: 800, fontSize: 26, lineHeight: 1 }}>A</Typography>
            </Box>
            <Typography variant="h2" gutterBottom>Create an account</Typography>
            <Typography color="text.secondary" variant="body2">
              Free to use. Research prototype — analysis is performed server-side.
            </Typography>
          </Box>

          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent sx={{ p: { xs: 3, sm: 4 } }}>

              {error && (
                <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError('')}>
                  {error}
                </Alert>
              )}

              {/* Google Sign-Up */}
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
                {GOOGLE_CONFIGURED ? (
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => setError('Google sign-in was cancelled or failed.')}
                    width="400"
                    text="signup_with"
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
                    Sign up with Google
                    <Typography variant="caption" sx={{ ml: 1 }}>(setup needed)</Typography>
                  </Button>
                )}
              </Box>

              <Divider sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">or create with email</Typography>
              </Divider>

              <form onSubmit={handleSubmit} noValidate>
                <TextField
                  label="Full name" value={name}
                  onChange={e => setName(e.target.value)}
                  autoComplete="name" autoFocus sx={{ mb: 2 }}
                />
                <TextField
                  label="Email address" type="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email" sx={{ mb: 2 }}
                />
                <TextField
                  label="Password" type={showPass ? 'text' : 'password'}
                  value={password} onChange={e => setPassword(e.target.value)}
                  autoComplete="new-password" sx={{ mb: 1 }}
                  helperText="Minimum 8 characters"
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
                  disabled={loading} sx={{ mt: 3, py: 1.4 }}
                >
                  {loading ? <CircularProgress size={22} color="inherit" /> : 'Create account'}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Typography variant="body2" textAlign="center" sx={{ mt: 3, color: 'text.secondary' }}>
            Already have an account?{' '}
            <Link component={RouterLink} to="/login" fontWeight={600} underline="hover">
              Sign in
            </Link>
          </Typography>

          <Box sx={{
            mt: 4, p: 2, borderRadius: 3,
            bgcolor: 'rgba(126,200,165,0.07)', border: '1px solid rgba(126,200,165,0.2)',
          }}>
            <Typography variant="caption" color="text.secondary" display="block" textAlign="center" lineHeight={1.7}>
              🔒 Responses are transmitted to the AnxioSense server and processed using third-party AI
              infrastructure. If report saving is enabled, the generated report may be stored in your
              account. AnxioSense is a research prototype and should not be treated as a confidential
              clinical service.
            </Typography>
          </Box>

        </Box>
      </Fade>
    </Box>
  );
}

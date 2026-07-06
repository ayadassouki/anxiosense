import { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Box, IconButton, Avatar, Menu,
  MenuItem, Typography, Tooltip, Divider, Container,
  useScrollTrigger, Fade,
} from '@mui/material';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

function ElevationScroll({ children }: { children: React.ReactElement }) {
  const trigger = useScrollTrigger({ disableHysteresis: true, threshold: 0 });
  return (
    <Fade in={trigger}>
      <Box sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1100,
        boxShadow: trigger ? '0 2px 20px rgba(0,0,0,0.08)' : 'none' }}>
        {children}
      </Box>
    </Fade>
  );
}

interface LayoutProps {
  children: ReactNode;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
}

export default function Layout({ children, maxWidth = 'lg' }: LayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'G';

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* ── Nav bar ── */}
      <AppBar position="sticky" elevation={0}>
        <Toolbar sx={{ px: { xs: 2, sm: 4 }, minHeight: 64 }}>
          {/* Logo */}
          <Box
            onClick={() => navigate('/dashboard')}
            sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer', mr: 'auto' }}
          >
            <Box sx={{
              width: 34, height: 34, borderRadius: 2,
              background: 'linear-gradient(135deg, #4F7CAC, #7EC8A5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Typography sx={{ color: 'white', fontWeight: 800, fontSize: 16, lineHeight: 1 }}>
                A
              </Typography>
            </Box>
            <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 700, letterSpacing: '-0.01em' }}>
              AnxioSense
            </Typography>
          </Box>

          {/* Guest badge */}
          {user?.isGuest && (
            <Box sx={{
              px: 1.5, py: 0.5, borderRadius: 6,
              bgcolor: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.3)',
              mr: 2,
            }}>
              <Typography variant="caption" sx={{ color: '#A78BFA', fontWeight: 600 }}>
                Guest mode
              </Typography>
            </Box>
          )}

          {/* User avatar menu */}
          <Tooltip title="Account">
            <IconButton onClick={e => setAnchorEl(e.currentTarget)} size="small">
              <Avatar sx={{
                width: 36, height: 36,
                background: 'linear-gradient(135deg, #4F7CAC, #7EC8A5)',
                fontSize: 14, fontWeight: 700,
              }}>
                {initials}
              </Avatar>
            </IconButton>
          </Tooltip>

          <Menu
            anchorEl={anchorEl} open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            PaperProps={{ sx: { mt: 1, minWidth: 200, borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.12)', border: '1px solid rgba(0,0,0,0.06)' } }}
          >
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="body2" fontWeight={600}>{user?.name}</Typography>
              {!user?.isGuest && (
                <Typography variant="caption" color="text.secondary">{user?.email}</Typography>
              )}
            </Box>
            <Divider />
            <MenuItem onClick={() => { setAnchorEl(null); logout(); navigate('/login'); }}
              sx={{ color: 'error.main', mt: 0.5 }}>
              Sign out
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* ── Page content ── */}
      <Container maxWidth={maxWidth} sx={{ py: { xs: 3, sm: 5 }, px: { xs: 2, sm: 3 } }}>
        {children}
      </Container>
    </Box>
  );
}

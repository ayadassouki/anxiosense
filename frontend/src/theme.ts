import { createTheme, alpha } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    accent: Palette['primary'];
  }
  interface PaletteOptions {
    accent?: PaletteOptions['primary'];
  }
}

const theme = createTheme({
  palette: {
    primary:    { main: '#4F7CAC', light: '#7499C4', dark: '#3A6090', contrastText: '#fff' },
    secondary:  { main: '#7EC8A5', light: '#A0D8BC', dark: '#5BAF86', contrastText: '#fff' },
    accent:     { main: '#A78BFA', light: '#C4ADFC', dark: '#8B6EF5', contrastText: '#fff' },
    background: { default: '#F7FAFC', paper: '#FFFFFF' },
    text:       { primary: '#1F2937', secondary: '#6B7280' },
    error:      { main: '#E05C5C' },
    success:    { main: '#7EC8A5' },
    warning:    { main: '#F6AD55' },
    divider:    'rgba(0,0,0,0.07)',
  },

  shape: { borderRadius: 14 },

  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontSize: '2rem',   fontWeight: 700, lineHeight: 1.2, letterSpacing: '-0.02em' },
    h2: { fontSize: '1.5rem', fontWeight: 700, lineHeight: 1.3, letterSpacing: '-0.01em' },
    h3: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.4 },
    h4: { fontSize: '1.125rem', fontWeight: 600 },
    h5: { fontSize: '1rem',    fontWeight: 600 },
    h6: { fontSize: '0.875rem', fontWeight: 600 },
    body1: { fontSize: '0.9375rem', lineHeight: 1.7 },
    body2: { fontSize: '0.875rem',  lineHeight: 1.6 },
    caption: { fontSize: '0.75rem', letterSpacing: '0.02em' },
    button: { fontWeight: 600, letterSpacing: '0.01em', textTransform: 'none' },
  },

  shadows: [
    'none',
    '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
    '0 2px 8px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)',
    '0 4px 16px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04)',
    '0 6px 24px rgba(0,0,0,0.09), 0 2px 8px rgba(0,0,0,0.05)',
    '0 8px 32px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.06)',
    '0 12px 40px rgba(0,0,0,0.11)',
    '0 16px 48px rgba(0,0,0,0.12)',
    '0 20px 56px rgba(0,0,0,0.13)',
    '0 24px 64px rgba(0,0,0,0.14)',
    '0 28px 72px rgba(0,0,0,0.14)',
    '0 32px 80px rgba(0,0,0,0.15)',
    '0 36px 88px rgba(0,0,0,0.15)',
    '0 40px 96px rgba(0,0,0,0.16)',
    '0 44px 104px rgba(0,0,0,0.16)',
    '0 48px 112px rgba(0,0,0,0.17)',
    '0 52px 120px rgba(0,0,0,0.17)',
    '0 56px 128px rgba(0,0,0,0.18)',
    '0 60px 136px rgba(0,0,0,0.18)',
    '0 64px 144px rgba(0,0,0,0.19)',
    '0 68px 152px rgba(0,0,0,0.19)',
    '0 72px 160px rgba(0,0,0,0.20)',
    '0 76px 168px rgba(0,0,0,0.20)',
    '0 80px 176px rgba(0,0,0,0.21)',
    '0 84px 184px rgba(0,0,0,0.21)',
  ],

  components: {
    MuiCssBaseline: {
      styleOverrides: {
        '*': { boxSizing: 'border-box' },
        html: { scrollBehavior: 'smooth' },
        '::-webkit-scrollbar': { width: 6, height: 6 },
        '::-webkit-scrollbar-track': { background: 'transparent' },
        '::-webkit-scrollbar-thumb': { background: '#D1D5DB', borderRadius: 3 },
      },
    },

    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 10,
          padding: '10px 24px',
          fontSize: '0.9375rem',
          transition: 'all 0.2s ease',
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #4F7CAC 0%, #3A6090 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #5B87B8 0%, #4A70A0 100%)',
            transform: 'translateY(-1px)',
            boxShadow: '0 6px 20px rgba(79,124,172,0.35)',
          },
          '&:active': { transform: 'translateY(0)' },
        },
        outlinedPrimary: {
          borderWidth: 1.5,
          '&:hover': { borderWidth: 1.5, backgroundColor: alpha('#4F7CAC', 0.05) },
        },
        text: { '&:hover': { backgroundColor: alpha('#4F7CAC', 0.05) } },
      },
    },

    MuiTextField: {
      defaultProps: { variant: 'outlined', fullWidth: true },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            backgroundColor: '#F9FAFB',
            transition: 'all 0.2s ease',
            '& fieldset': { borderColor: '#E5E7EB', borderWidth: 1.5 },
            '&:hover fieldset': { borderColor: '#4F7CAC' },
            '&.Mui-focused': {
              backgroundColor: '#FFFFFF',
              '& fieldset': { borderColor: '#4F7CAC', borderWidth: 2 },
            },
          },
          '& .MuiInputLabel-root': { color: '#9CA3AF' },
          '& .MuiInputLabel-root.Mui-focused': { color: '#4F7CAC' },
        },
      },
    },

    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(0,0,0,0.06)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          transition: 'box-shadow 0.25s ease, transform 0.25s ease',
        },
      },
    },

    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 600, fontSize: '0.75rem' },
      },
    },

    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          boxShadow: '0 24px 64px rgba(0,0,0,0.15)',
        },
      },
    },

    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 4, height: 6, backgroundColor: '#EFF6FF' },
        bar:  { borderRadius: 4 },
      },
    },

    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(0,0,0,0.07)',
          boxShadow: 'none',
          color: '#1F2937',
        },
      },
    },

    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 10 },
      },
    },

    MuiTooltip: {
      styleOverrides: {
        tooltip: { borderRadius: 8, fontSize: '0.8125rem' },
      },
    },
  },
});

export default theme;

import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Button, TextField, Card, CardContent,
  Switch, FormControlLabel, Collapse, Alert, Fade, Chip,
  CircularProgress, Stepper, Step, StepLabel, StepConnector,
  stepConnectorClasses, styled, Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import BookOutlinedIcon from '@mui/icons-material/BookOutlined';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import LocalHospitalOutlinedIcon from '@mui/icons-material/LocalHospitalOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import Layout from '../components/Layout';
import Gad7Form from '../components/Gad7Form';
import { runWorkflow } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

// ── Styled stepper connector ──────────────────────────────────────────────────
const ThinConnector = styled(StepConnector)(() => ({
  [`&.${stepConnectorClasses.active} .${stepConnectorClasses.line}`]: {
    background: 'linear-gradient(90deg, #4F7CAC, #7EC8A5)',
  },
  [`&.${stepConnectorClasses.completed} .${stepConnectorClasses.line}`]: {
    background: 'linear-gradient(90deg, #7EC8A5, #4F7CAC)',
  },
  [`& .${stepConnectorClasses.line}`]: {
    height: 2, border: 0, backgroundColor: '#E5E7EB', borderRadius: 2,
  },
}));

// ── Agent pipeline steps shown during analysis ────────────────────────────────
const AGENT_STEPS = [
  { label: 'Emotion analysis',      detail: 'Identifying emotional tone and affect patterns…' },
  { label: 'Symptom identification',detail: 'Mapping language markers to anxiety symptom clusters…' },
  { label: 'Context assessment',    detail: 'Understanding psychosocial stressors and context…' },
  { label: 'Evidence retrieval',    detail: 'Matching against validated clinical knowledge base…' },
  { label: 'Report generation',     detail: 'Synthesising evidence-informed assessment report…' },
];

// Approximate time (ms) each agent step takes — for animation pacing
const STEP_DURATIONS = [8000, 7000, 6000, 9000, 14000];

type PageView = 'input' | 'gad7' | 'analyzing' | 'done';

export default function AssessmentPage() {
  const { state } = useLocation() as { state: { mode?: 'journal' | 'social-media' } };
  const navigate = useNavigate();
  const { user } = useAuth();

  const mode = state?.mode ?? 'journal';
  const isJournal = mode === 'journal';

  // ── Form state ────────────────────────────────────────────────────────────
  const [userText,      setUserText]      = useState('');
  const [gad7Answers,   setGad7Answers]   = useState<number[] | null>(null);
  const [clinicianMode, setClinicianMode] = useState(false);
  const [saveSession,   setSaveSession]   = useState(!user?.isGuest);

  // ── View ──────────────────────────────────────────────────────────────────
  const [view, setView] = useState<PageView>('input');
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState('');
  const stepTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timer on unmount
  useEffect(() => () => { if (stepTimer.current) clearTimeout(stepTimer.current); }, []);

  // ── Animate pipeline steps during analysis ────────────────────────────────
  function startStepAnimation() {
    let elapsed = 0;
    STEP_DURATIONS.slice(0, -1).forEach((dur, i) => {
      elapsed += dur;
      stepTimer.current = setTimeout(() => setActiveStep(i + 1), elapsed);
    });
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!userText.trim()) { setError('Please enter some text before submitting.'); return; }
    setError('');
    setView('analyzing');
    setActiveStep(0);
    startStepAnimation();

    try {
      const result = await runWorkflow({
        mode,
        userText: userText.trim(),
        gad7Answers:   gad7Answers ?? undefined,
        clinicianMode: clinicianMode || undefined,
        saveSession:   saveSession || undefined,
      });
      setView('done');
      setTimeout(() => navigate(`/report/${result.reportId}`, { state: { report: result } }), 700);
    } catch (err: unknown) {
      setView('input');
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    }
  }

  // ── GAD-7 completed ───────────────────────────────────────────────────────
  function onGad7Complete(answers: number[]) {
    setGad7Answers(answers);
    setView('input');
  }

  function onGad7Skip() {
    setGad7Answers(null);
    setView('input');
  }

  // ── Render helpers ────────────────────────────────────────────────────────
  const modeColor    = isJournal ? '#4F7CAC'  : '#A78BFA';
  const modeBg       = isJournal ? 'rgba(79,124,172,0.06)'  : 'rgba(167,139,250,0.06)';
  const modeIcon     = isJournal ? <BookOutlinedIcon />      : <ArticleOutlinedIcon />;
  const modeLabel    = isJournal ? 'Journal mode'            : 'Social Media mode';
  const placeholder  = isJournal
    ? "How have you been feeling lately? Write freely — no one will read this text. The AI analyses language patterns and emotional tone, not specific details."
    : "Paste a Reddit post, social media caption, or public text here. The AI will analyse language patterns for indicators of anxiety-related themes.\n\nNote: this mode does not include GAD-7 and applies extra conservatism to referral recommendations.";

  // ─────────────────────────────────────────────────────────────────────────
  // GAD-7 screen
  // ─────────────────────────────────────────────────────────────────────────
  if (view === 'gad7') {
    return (
      <Layout>
        <Box maxWidth={600} mx="auto">
          <Box mb={3}>
            <Button startIcon={<ArrowBackIcon />} onClick={() => setView('input')}
              sx={{ color: 'text.secondary', mb: 2 }}>
              Back to input
            </Button>
            <Typography variant="h3" gutterBottom>GAD-7 Questionnaire</Typography>
            <Typography variant="body2" color="text.secondary">
              This validated screening tool helps contextualise your journal entry.
              Your answers are processed locally and not stored.
            </Typography>
          </Box>
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
              <Gad7Form onComplete={onGad7Complete} onSkip={onGad7Skip} />
            </CardContent>
          </Card>
        </Box>
      </Layout>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Analyzing screen
  // ─────────────────────────────────────────────────────────────────────────
  if (view === 'analyzing' || view === 'done') {
    return (
      <Layout>
        <Box maxWidth={600} mx="auto" textAlign="center" py={6}>
          <Fade in timeout={400}>
            <Box>
              {view === 'done' ? (
                <CheckCircleOutlineIcon sx={{ fontSize: 64, color: '#7EC8A5', mb: 2 }} />
              ) : (
                <Box sx={{ position: 'relative', width: 72, height: 72, mx: 'auto', mb: 3 }}>
                  <CircularProgress size={72} thickness={2}
                    sx={{ color: '#4F7CAC', position: 'absolute' }} />
                  <AutoAwesomeIcon sx={{
                    position: 'absolute', top: '50%', left: '50%',
                    transform: 'translate(-50%, -50%)',
                    color: '#4F7CAC', fontSize: 28,
                  }} />
                </Box>
              )}

              <Typography variant="h3" gutterBottom>
                {view === 'done' ? 'Report ready!' : 'Analysing your entry…'}
              </Typography>
              <Typography color="text.secondary" variant="body2" mb={5}>
                {view === 'done'
                  ? 'Redirecting you to your report…'
                  : 'Our multi-agent pipeline is running. This takes 30–60 seconds.'}
              </Typography>

              {/* Stepper */}
              <Stepper activeStep={activeStep} alternativeLabel
                connector={<ThinConnector />} sx={{ mb: 4 }}>
                {AGENT_STEPS.map((s, i) => (
                  <Step key={s.label} completed={i < activeStep || view === 'done'}>
                    <StepLabel
                      sx={{
                        '& .MuiStepLabel-label': {
                          fontSize: 11, mt: 0.5,
                          color: i <= activeStep ? 'text.primary' : 'text.disabled',
                        },
                      }}
                    >
                      {s.label}
                    </StepLabel>
                  </Step>
                ))}
              </Stepper>

              {/* Current step detail */}
              {view === 'analyzing' && (
                <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                  {AGENT_STEPS[Math.min(activeStep, AGENT_STEPS.length - 1)].detail}
                </Typography>
              )}
            </Box>
          </Fade>
        </Box>
      </Layout>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Input screen (main)
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <Layout>
      <Fade in timeout={300}>
        <Box maxWidth={680} mx="auto">

          {/* ── Header ── */}
          <Box mb={1}>
            <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/dashboard')}
              sx={{ color: 'text.secondary', mb: 2 }}>
              Dashboard
            </Button>
            <Box display="flex" alignItems="center" gap={1.5} mb={1}>
              <Typography variant="h2">New Assessment</Typography>
              <Chip
                icon={<Box sx={{ color: modeColor, display: 'flex', ml: 1 }}>{modeIcon}</Box>}
                label={modeLabel}
                size="small"
                sx={{ bgcolor: modeBg, color: modeColor, border: `1px solid ${modeColor}33`, fontWeight: 600 }}
              />
            </Box>
            <Typography color="text.secondary" variant="body2">
              {isJournal
                ? 'Write about how you\'ve been feeling. The analysis uses language patterns, not specific content.'
                : 'Paste public text for indirect linguistic analysis. No GAD-7 questionnaire is included in this mode.'}
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          {/* ── Text input ── */}
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 2.5 }}>
            <CardContent sx={{ p: { xs: 2.5, sm: 3.5 } }}>
              <TextField
                multiline rows={isJournal ? 10 : 8}
                value={userText} onChange={e => setUserText(e.target.value)}
                placeholder={placeholder}
                sx={{
                  '& .MuiInputBase-root': {
                    fontSize: isJournal ? '1rem' : '0.9rem',
                    lineHeight: 1.8,
                    fontFamily: isJournal ? 'Georgia, serif' : 'inherit',
                    bgcolor: isJournal ? '#FDFCFB' : 'transparent',
                  },
                }}
              />
              <Box display="flex" justifyContent="flex-end" mt={1}>
                <Typography variant="caption" color={userText.length < 20 ? 'error.main' : 'text.disabled'}>
                  {userText.length} characters {userText.length < 20 && userText.length > 0 ? '(minimum 20)' : ''}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* ── GAD-7 section (journal only) ── */}
          {isJournal && (
            <Card elevation={0} sx={{ border: '1px solid', borderColor: gad7Answers ? '#7EC8A533' : 'divider', mb: 2.5,
              bgcolor: gad7Answers ? 'rgba(126,200,165,0.04)' : 'transparent' }}>
              <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
                <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
                  <Box>
                    <Typography variant="body1" fontWeight={600}>
                      GAD-7 Questionnaire
                      <Chip label="Optional" size="small"
                        sx={{ ml: 1.5, fontSize: 10, height: 18, bgcolor: 'action.hover' }} />
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {gad7Answers
                        ? `Completed — ${gad7Answers.length} questions answered`
                        : 'Adds a validated anxiety screening score to your report'}
                    </Typography>
                  </Box>
                  <Box display="flex" gap={1}>
                    {gad7Answers && (
                      <Button size="small" variant="outlined" onClick={() => setGad7Answers(null)}
                        sx={{ fontSize: 12, py: 0.5, borderColor: 'divider', color: 'text.secondary' }}>
                        Remove
                      </Button>
                    )}
                    <Button
                      size="small"
                      variant={gad7Answers ? 'text' : 'outlined'}
                      onClick={() => setView('gad7')}
                      startIcon={gad7Answers ? <CheckCircleOutlineIcon sx={{ color: '#7EC8A5' }} /> : undefined}
                      sx={{ fontSize: 12, py: 0.5, color: gad7Answers ? '#7EC8A5' : 'primary.main' }}
                    >
                      {gad7Answers ? 'Redo questionnaire' : 'Start questionnaire'}
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}

          {/* ── Options ── */}
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 3.5 }}>
            <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
              <Typography variant="body2" fontWeight={600} mb={2} color="text.secondary">
                Options
              </Typography>

              {/* Save session toggle */}
              <Box display="flex" alignItems="center" justifyContent="space-between"
                py={1.25} borderBottom="1px solid" sx={{ borderColor: 'divider' }}>
                <Box display="flex" alignItems="center" gap={1}>
                  <LockOutlinedIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                  <Box>
                    <Typography variant="body2" fontWeight={500}>Save report summary</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {user?.isGuest
                        ? 'Sign in to enable saving'
                        : 'Your raw text is never saved — only the structured output'}
                    </Typography>
                  </Box>
                </Box>
                <Tooltip title={user?.isGuest ? 'Sign in to save reports' : ''}>
                  <span>
                    <Switch
                      checked={saveSession && !user?.isGuest}
                      onChange={e => setSaveSession(e.target.checked)}
                      disabled={!!user?.isGuest}
                      size="small"
                      color="primary"
                    />
                  </span>
                </Tooltip>
              </Box>

              {/* Clinician mode toggle */}
              <Box display="flex" alignItems="center" justifyContent="space-between" pt={1.25}>
                <Box display="flex" alignItems="center" gap={1}>
                  <LocalHospitalOutlinedIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                  <Box>
                    <Typography variant="body2" fontWeight={500}>
                      Clinician mode
                      <Chip label="Researcher" size="small"
                        sx={{ ml: 1.5, fontSize: 10, height: 18,
                          bgcolor: 'rgba(167,139,250,0.1)', color: '#A78BFA',
                          border: '1px solid rgba(167,139,250,0.3)' }} />
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Appends raw GAD-7 score and clinical severity to the report
                    </Typography>
                  </Box>
                </Box>
                <Switch
                  checked={clinicianMode}
                  onChange={e => setClinicianMode(e.target.checked)}
                  size="small"
                  sx={{ '& .MuiSwitch-thumb': { bgcolor: clinicianMode ? '#A78BFA' : undefined } }}
                />
              </Box>
            </CardContent>
          </Card>

          {/* ── Submit ── */}
          <Box display="flex" justifyContent="flex-end">
            <Button
              variant="contained" size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={handleSubmit}
              disabled={userText.trim().length < 20}
              sx={{ px: 4, py: 1.4, minWidth: 200 }}
            >
              Run Analysis
            </Button>
          </Box>

          {/* ── Privacy notice ── */}
          <Box sx={{ mt: 3, p: 2, borderRadius: 2.5,
            bgcolor: 'rgba(79,124,172,0.04)', border: '1px solid rgba(79,124,172,0.1)' }}>
            <Typography variant="caption" color="text.secondary" lineHeight={1.8} display="block">
              🔒 <strong>Privacy:</strong> Your text is sent only to the local Mastra server for analysis
              and is not stored anywhere by default. GAD-7 answers are processed in memory and discarded
              after the report is generated. If "Save report summary" is on, only the structured output
              (not your raw text) is saved to your account.
            </Typography>
          </Box>

        </Box>
      </Fade>
    </Layout>
  );
}

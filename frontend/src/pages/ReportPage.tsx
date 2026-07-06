import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Button, Card, CardContent, Chip,
  Divider, Alert, CircularProgress, Fade, Tooltip, IconButton,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import BookOutlinedIcon from '@mui/icons-material/BookOutlined';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import DownloadIcon from '@mui/icons-material/Download';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import LocalHospitalOutlinedIcon from '@mui/icons-material/LocalHospitalOutlined';
import Layout from '../components/Layout';
import { getReport, type ReportSummary } from '../services/api';

// ── Concern pattern config — labels and descriptions per supervisor guidance ──
const CONCERN_CONFIG: Record<string, {
  label: string; color: string; bg: string; border: string; description: string; citation?: string;
}> = {
  'Minimal Concern Pattern': {
    label: 'Minimal Concern Pattern', color: '#059669', bg: '#ECFDF5', border: '#059669',
    citation: 'Spitzer et al. (2006) · screening purposes only',
    description: 'Your responses suggest that experiences commonly associated with anxiety are currently limited. Occasional stress or worry is a normal part of life. If these feelings become more frequent or begin affecting your daily activities, you may wish to check in with a healthcare professional.',
  },
  'Mild Concern Pattern': {
    label: 'Mild Concern Pattern', color: '#D97706', bg: '#FFFBEB', border: '#D97706',
    citation: 'Spitzer et al. (2006) · screening purposes only',
    description: 'Your responses indicate the presence of some anxiety-related experiences. While these feelings may not currently be causing substantial difficulties, monitoring how they change over time may be helpful. Consider using healthy coping strategies and seeking support if symptoms become more frequent or distressing.',
  },
  'Elevated Concern Pattern': {
    label: 'Elevated Concern Pattern', color: '#EA580C', bg: '#FFF7ED', border: '#EA580C',
    citation: 'Spitzer et al. (2006) · screening purposes only',
    description: 'Your responses suggest several experiences that are commonly associated with anxiety and may be affecting your well-being. It may be beneficial to discuss these concerns with a healthcare professional who can provide a more comprehensive assessment and appropriate guidance.',
  },
  'High Concern Pattern': {
    label: 'High Concern Pattern', color: '#DC2626', bg: '#FEF2F2', border: '#DC2626',
    citation: 'Spitzer et al. (2006) · screening purposes only',
    description: 'Your responses indicate a substantial number of experiences commonly associated with anxiety. Seeking support from a qualified healthcare professional may be beneficial. Effective treatments and support options are available, and discussing your concerns with a professional can help determine the most appropriate next steps.',
  },
  'Urgent Safety Notice': {
    label: 'Urgent Safety Notice', color: '#991B1B', bg: '#FEF2F2', border: '#991B1B',
    // No Spitzer citation — this is a safety override, not a GAD-7 band
    description: 'Based on what you shared, there may be an immediate safety concern. This screening tool cannot provide crisis support — please reach out for help right away.',
  },
};

const REFERRAL_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  low:      { label: 'Low concern — no immediate referral indicated', color: '#059669', bg: '#ECFDF5', icon: '✓' },
  moderate: { label: 'Follow-up suggested — consider professional consultation', color: '#D97706', bg: '#FFFBEB', icon: '!' },
  urgent:   { label: 'Urgent referral recommended — please contact a mental health professional', color: '#DC2626', bg: '#FEF2F2', icon: '!!' },
};

// ── Section parser ────────────────────────────────────────────────────────────
// Splits report text on numbered headings like "1. Summary", "## Summary" etc.
function parseSections(text: string): { heading: string; body: string }[] {
  const lines  = text.split('\n');
  const result: { heading: string; body: string }[] = [];
  let current: { heading: string; body: string[] } | null = null;

  const headingRe = /^(?:#{1,3}\s+|[\d]+\.\s+)(.+)/;

  for (const line of lines) {
    const match = line.match(headingRe);
    if (match) {
      if (current) result.push({ heading: current.heading, body: current.body.join('\n').trim() });
      current = { heading: match[1].replace(/\*\*/g, '').trim(), body: [] };
    } else if (current) {
      current.body.push(line);
    } else {
      // text before first heading — treat as preamble
      if (line.trim()) {
        if (!result.length) result.push({ heading: '', body: '' });
        const last = result[result.length - 1];
        result[result.length - 1] = { heading: last.heading, body: (last.body + '\n' + line).trim() };
      }
    }
  }
  if (current) result.push({ heading: current.heading, body: current.body.join('\n').trim() });
  return result.filter(s => s.heading || s.body);
}

function renderBody(text: string) {
  return text.split('\n').map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <Box key={i} mb={1} />;
    const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('• ');
    const content = isBullet ? trimmed.slice(2) : trimmed;
    const bold = content.replace(/\*\*(.+?)\*\*/g, '|||$1|||').split('|||').map((chunk, j) =>
      j % 2 === 1
        ? <strong key={j}>{chunk}</strong>
        : <span key={j}>{chunk}</span>
    );
    return (
      <Box key={i} display="flex" alignItems="flex-start" gap={1} mb={0.75}>
        {isBullet && (
          <Box component="span" sx={{ color: 'primary.main', mt: '2px', flexShrink: 0, fontSize: 18, lineHeight: 1.4 }}>·</Box>
        )}
        <Typography variant="body2" lineHeight={1.8} color="text.primary">
          {bold}
        </Typography>
      </Box>
    );
  });
}

// ── Clinician section detector ────────────────────────────────────────────────
function splitClinicianBlock(report: string): { main: string; clinician: string | null } {
  const marker = /---\s*\n(?:#{1,3}\s*)?(?:Clinician|Clinical) (?:Note|Section|Mode)/i;
  const match = report.search(marker);
  if (match === -1) return { main: report, clinician: null };
  return { main: report.slice(0, match).trim(), clinician: report.slice(match).trim() };
}

// ── Section card ─────────────────────────────────────────────────────────────
function SectionCard({ index, heading, body }: { index: number; heading: string; body: string }) {
  const isLimitations = /limitation/i.test(heading);
  return (
    <Card elevation={0} sx={{
      border: '1px solid', borderColor: isLimitations ? 'rgba(0,0,0,0.06)' : 'divider',
      bgcolor: isLimitations ? 'rgba(0,0,0,0.015)' : '#fff',
      mb: 2,
    }}>
      <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
        {heading && (
          <Box display="flex" alignItems="center" gap={1.5} mb={1.5}>
            <Box sx={{
              width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
              bgcolor: isLimitations ? 'rgba(0,0,0,0.06)' : 'rgba(79,124,172,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Typography variant="caption" fontWeight={700}
                sx={{ color: isLimitations ? 'text.secondary' : 'primary.main', fontSize: 11 }}>
                {index}
              </Typography>
            </Box>
            <Typography variant="h5" sx={{ color: isLimitations ? 'text.secondary' : 'text.primary' }}>
              {heading}
            </Typography>
          </Box>
        )}
        <Box pl={heading ? 5 : 0}>
          {renderBody(body)}
        </Box>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation() as { state?: { report?: { finalReport?: string; concernPattern?: string; referralLevel?: string } } };
  const navigate = useNavigate();

  const [report,  setReport]  = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [copied,  setCopied]  = useState(false);

  useEffect(() => {
    if (!id) return;
    // If we have just enough from navigation state, build a skeleton while fetching
    getReport(id)
      .then(setReport)
      .catch(() => {
        // Fall back to navigation state if available (e.g. guest mode, no server yet)
        if (state?.report?.finalReport) {
          setReport({
            id:             id,
            userId:         'guest',
            mode:           'journal',
            createdAt:      new Date().toISOString(),
            concernPattern: state.report.concernPattern ?? '',
            referralLevel:  (state.report.referralLevel ?? 'moderate') as 'low' | 'moderate' | 'urgent',
            summary:        '',
            fullReport:     state.report.finalReport,
            clinicianMode:  false,
          });
        } else {
          setError('Could not load this report.');
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  function handleCopy() {
    if (!report?.fullReport) return;
    navigator.clipboard.writeText(report.fullReport).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleDownload() {
    if (!report?.fullReport) return;
    const date = new Date(report.createdAt).toISOString().slice(0, 10);
    const filename = `AnxioSense-Report-${date}.txt`;
    const header = [
      'AnxioSense Screening Support Report',
      `Date: ${new Date(report.createdAt).toLocaleString()}`,
      `Mode: ${report.mode === 'journal' ? 'Journal Entry' : 'Social Media Analysis'}`,
      `Concern Pattern: ${report.concernPattern}`,
      '─'.repeat(60),
      '',
    ].join('\n');
    const content = header + report.fullReport;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <Layout>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      </Layout>
    );
  }

  if (error || !report) {
    return (
      <Layout>
        <Box maxWidth={640} mx="auto" mt={6}>
          <Alert severity="error">{error || 'Report not found.'}</Alert>
          <Button sx={{ mt: 2 }} startIcon={<ArrowBackIcon />} onClick={() => navigate('/dashboard')}>
            Back to dashboard
          </Button>
        </Box>
      </Layout>
    );
  }

  const concern   = CONCERN_CONFIG[report.concernPattern] ?? CONCERN_CONFIG['Elevated Concern Pattern'];
  const referral  = REFERRAL_CONFIG[report.referralLevel] ?? REFERRAL_CONFIG['moderate'];
  const date      = new Date(report.createdAt).toLocaleDateString('en-CA', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
  const time = new Date(report.createdAt).toLocaleTimeString('en-CA', {
    hour: '2-digit', minute: '2-digit',
  });

  const { main, clinician } = splitClinicianBlock(report.fullReport);
  const sections = parseSections(main);

  return (
    <Layout>
      <Fade in timeout={300}>
        <Box maxWidth={720} mx="auto">

          {/* ── Nav ── */}
          <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/dashboard')}
            sx={{ color: 'text.secondary', mb: 3 }}>
            Dashboard
          </Button>

          {/* ── Report header card ── */}
          <Card elevation={0} sx={{
            border: '1px solid', borderColor: 'divider', mb: 3,
            background: 'linear-gradient(135deg, rgba(79,124,172,0.04) 0%, rgba(126,200,165,0.04) 100%)',
          }}>
            <CardContent sx={{ p: { xs: 3, sm: 4 } }}>

              {/* Mode + date row */}
              <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1} mb={2.5}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Chip
                    icon={report.mode === 'journal'
                      ? <BookOutlinedIcon style={{ fontSize: 14 }} />
                      : <ArticleOutlinedIcon style={{ fontSize: 14 }} />}
                    label={report.mode === 'journal' ? 'Journal Entry' : 'Social Media'}
                    size="small"
                    sx={{ bgcolor: 'rgba(79,124,172,0.08)', color: 'primary.dark',
                      border: '1px solid rgba(79,124,172,0.2)', fontWeight: 600 }}
                  />
                  {report.clinicianMode && (
                    <Chip
                      icon={<LocalHospitalOutlinedIcon style={{ fontSize: 13 }} />}
                      label="Clinician"
                      size="small"
                      sx={{ bgcolor: 'rgba(167,139,250,0.1)', color: '#A78BFA',
                        border: '1px solid rgba(167,139,250,0.3)', fontWeight: 600 }}
                    />
                  )}
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="caption" color="text.secondary">{date} · {time}</Typography>
                  <Tooltip title={copied ? 'Copied!' : 'Copy report'}>
                    <IconButton size="small" onClick={handleCopy} sx={{ color: 'text.secondary' }}>
                      {copied ? <CheckIcon fontSize="small" sx={{ color: '#7EC8A5' }} /> : <ContentCopyIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Download report as .txt">
                    <IconButton size="small" onClick={handleDownload} sx={{ color: 'text.secondary' }}>
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>

              <Typography variant="h2" gutterBottom>Screening Report</Typography>

              {/* Concern pattern + referral */}
              <Box display="flex" gap={2} flexWrap="wrap" mt={2}>
                {/* Concern pattern */}
                <Box sx={{
                  flex: 1, minWidth: 240, p: 2.5, borderRadius: 3,
                  bgcolor: concern.bg, border: `1.5px solid ${concern.border}22`,
                }}>
                  <Typography variant="caption" color="text.secondary" display="block" mb={0.5} fontWeight={600}>
                    CONCERN PATTERN
                  </Typography>
                  <Typography variant="body1" fontWeight={700} sx={{ color: concern.color, mb: 1 }}>
                    {concern.label}
                  </Typography>
                  <Typography variant="caption" lineHeight={1.7} display="block"
                    sx={{ color: concern.color, opacity: 0.85, mb: 1 }}>
                    {concern.description}
                  </Typography>
                  {concern.citation && (
                    <Typography variant="caption" sx={{ color: concern.color, opacity: 0.55, fontSize: 10 }}>
                      {concern.citation}
                    </Typography>
                  )}
                </Box>

                {/* Referral level */}
                <Box sx={{
                  flex: 1, minWidth: 200, p: 2.5, borderRadius: 3,
                  bgcolor: referral.bg, border: `1.5px solid ${referral.color}22`,
                }}>
                  <Typography variant="caption" color="text.secondary" display="block" mb={0.5} fontWeight={600}>
                    REFERRAL RECOMMENDATION
                  </Typography>
                  <Typography variant="body2" fontWeight={600} sx={{ color: referral.color, lineHeight: 1.5 }}>
                    {referral.label}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* ── Disclaimer ── */}
          <Alert
            icon={<WarningAmberIcon />}
            severity="warning"
            sx={{ mb: 3, borderRadius: 3, bgcolor: '#FFFBEB', border: '1px solid #FDE68A' }}
          >
            <Typography variant="caption" lineHeight={1.7}>
              <strong>Not a diagnosis.</strong> This report is a computational screening tool for research purposes only.
              It does not constitute a clinical assessment, diagnosis, or treatment recommendation.
              If you have concerns about your mental health, please consult a qualified professional.
            </Typography>
          </Alert>

          {/* ── Report sections ── */}
          {sections.length > 0 ? (
            sections.map((section, i) => (
              <SectionCard
                key={i}
                index={i + 1}
                heading={section.heading}
                body={section.body}
              />
            ))
          ) : (
            /* Fallback: render raw text */
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
              <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
                <Typography variant="body2" lineHeight={1.9} sx={{ whiteSpace: 'pre-wrap' }}>
                  {main}
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* ── Clinician section (if present) ── */}
          {clinician && (
            <>
              <Divider sx={{ my: 3 }} />
              <Box sx={{
                p: 3, borderRadius: 3,
                bgcolor: 'rgba(167,139,250,0.04)',
                border: '1.5px solid rgba(167,139,250,0.25)',
                mb: 3,
              }}>
                <Box display="flex" alignItems="center" gap={1.5} mb={2}>
                  <LocalHospitalOutlinedIcon sx={{ color: '#A78BFA' }} />
                  <Typography variant="h5" sx={{ color: '#A78BFA' }}>Clinician Section</Typography>
                  <Chip label="Researcher only" size="small"
                    sx={{ bgcolor: 'rgba(167,139,250,0.1)', color: '#A78BFA',
                      border: '1px solid rgba(167,139,250,0.3)', fontSize: 10 }} />
                </Box>
                <Typography variant="body2" lineHeight={1.9} sx={{ whiteSpace: 'pre-wrap', color: 'text.secondary' }}>
                  {clinician.replace(/^---\n/, '')}
                </Typography>
              </Box>
            </>
          )}

          {/* ── Download button ── */}
          <Box display="flex" justifyContent="center" mt={2} mb={3}>
            <Button
              variant="outlined"
              size="large"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              sx={{
                px: 4, py: 1.4, borderRadius: 3,
                borderColor: 'primary.light',
                color: 'primary.main',
                '&:hover': { bgcolor: 'rgba(79,124,172,0.06)' },
              }}
            >
              Download Report (.txt)
            </Button>
          </Box>

          {/* ── Footer note ── */}
          <Box sx={{ mt: 1, mb: 4, p: 2, borderRadius: 2.5,
            bgcolor: 'rgba(79,124,172,0.04)', border: '1px solid rgba(79,124,172,0.1)' }}>
            <Typography variant="caption" color="text.secondary" lineHeight={1.8} display="block">
              🔒 Your raw text was not saved. This report was generated using a multi-agent
              AI pipeline with RAG-validated evidence retrieval. AnxioSense is a research prototype.
              Numerical GAD-7 scores and clinical severity labels are not shown to users per responsible AI design principles.
            </Typography>
          </Box>

        </Box>
      </Fade>
    </Layout>
  );
}

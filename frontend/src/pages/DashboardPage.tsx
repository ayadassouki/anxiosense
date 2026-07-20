import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Button, Grid, Dialog, DialogTitle,
  DialogContent, Card, CardActionArea, CardContent,
  CircularProgress, Alert, Fade, Skeleton, Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import BookOutlinedIcon from '@mui/icons-material/BookOutlined';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import InsightsOutlinedIcon from '@mui/icons-material/InsightsOutlined';
import Layout from '../components/Layout';
import ReportCard from '../components/ReportCard';
import { useAuth } from '../contexts/AuthContext';
import { getReports, deleteReport, type ReportSummary } from '../services/api';

function ModeCard({
  icon, title, description, badge, onClick,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  badge?: string;
  onClick: () => void;
}) {
  return (
    <Card elevation={0} sx={{ border: '1.5px solid', borderColor: 'divider',
      '&:hover': { borderColor: 'primary.main', boxShadow: '0 4px 20px rgba(79,124,172,0.15)' } }}>
      <CardActionArea onClick={onClick} sx={{ p: 3, borderRadius: 'inherit' }}>
        <CardContent sx={{ p: 0 }}>
          <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={2}>
            <Box sx={{
              width: 48, height: 48, borderRadius: 3,
              bgcolor: 'rgba(79,124,172,0.08)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', color: 'primary.main',
            }}>
              {icon}
            </Box>
            {badge && (
              <Chip label={badge} size="small"
                sx={{ bgcolor: 'rgba(167,139,250,0.1)', color: '#A78BFA',
                  border: '1px solid rgba(167,139,250,0.3)', fontWeight: 600, fontSize: 11 }} />
            )}
          </Box>
          <Typography variant="h5" gutterBottom>{title}</Typography>
          <Typography variant="body2" color="text.secondary" lineHeight={1.7}>
            {description}
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [reports, setReports]   = useState<ReportSummary[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (user?.isGuest) { setLoading(false); return; }
    getReports()
      .then(setReports)
      .catch(() => setError('Could not load your reports.'))
      .finally(() => setLoading(false));
  }, [user]);

  async function handleDelete(id: string) {
    try {
      await deleteReport(id);
      setReports(rs => rs.filter(r => r.id !== id));
    } catch {
      setError('Could not delete report.');
    }
  }

  function startAssessment(mode: 'journal' | 'social-media') {
    setModalOpen(false);
    navigate('/assessment', { state: { mode } });
  }

  const greeting = user?.name ? `Hello, ${user.name.split(' ')[0]}` : 'Hello';

  return (
    <Layout>
      <Fade in timeout={300}>
        <Box>
          {/* ── Header ── */}
          <Box display="flex" alignItems="flex-start" justifyContent="space-between"
            flexWrap="wrap" gap={2} mb={5}>
            <Box>
              <Typography variant="h2" gutterBottom>{greeting} 👋</Typography>
              <Typography color="text.secondary" variant="body1">
                {user?.isGuest
                  ? 'Running in guest mode — reports won\'t be saved.'
                  : `You have ${reports.length} saved ${reports.length === 1 ? 'report' : 'reports'}.`}
              </Typography>
            </Box>
            <Button
              variant="contained" size="large" startIcon={<AddIcon />}
              onClick={() => setModalOpen(true)}
              sx={{ flexShrink: 0, px: 3 }}
            >
              New Assessment
            </Button>
          </Box>

          {/* ── Error ── */}
          {error && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>{error}</Alert>
          )}

          {/* ── Stats row (non-guest only) ── */}
          {!user?.isGuest && reports.length > 0 && (
            <Grid container spacing={2} mb={4}>
              {[
                { label: 'Total reports',  value: reports.length,
                  color: '#4F7CAC', bg: 'rgba(79,124,172,0.08)' },
                { label: 'Self-Assessment', value: reports.filter(r => r.mode === 'journal').length,
                  color: '#7EC8A5', bg: 'rgba(126,200,165,0.08)' },
                { label: 'Social media',   value: reports.filter(r => r.mode === 'social-media').length,
                  color: '#A78BFA', bg: 'rgba(167,139,250,0.08)' },
              ].map(stat => (
                <Grid item xs={6} sm={4} key={stat.label}>
                  <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: stat.bg,
                    border: `1px solid ${stat.color}22` }}>
                    <Typography variant="h3" sx={{ color: stat.color, mb: 0.25 }}>
                      {stat.value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">{stat.label}</Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          )}

          {/* ── Reports grid ── */}
          <Typography variant="h4" mb={2.5}>
            {reports.length > 0 ? 'Your Reports' : ''}
          </Typography>

          {loading ? (
            <Grid container spacing={2.5}>
              {[0,1,2].map(i => (
                <Grid item xs={12} sm={6} md={4} key={i}>
                  <Skeleton variant="rounded" height={220} sx={{ borderRadius: 4 }} />
                </Grid>
              ))}
            </Grid>
          ) : reports.length === 0 ? (
            /* ── Empty state ── */
            <Box sx={{
              textAlign: 'center', py: 10, px: 3,
              bgcolor: 'rgba(79,124,172,0.03)', borderRadius: 4,
              border: '1.5px dashed rgba(79,124,172,0.2)',
            }}>
              <InsightsOutlinedIcon sx={{ fontSize: 56, color: 'primary.light', mb: 2, opacity: 0.6 }} />
              <Typography variant="h4" gutterBottom>No reports yet</Typography>
              <Typography color="text.secondary" variant="body2" mb={4} maxWidth={340} mx="auto">
                Start your first assessment to generate an evidence-informed screening report.
              </Typography>
              <Button variant="contained" size="large" startIcon={<AddIcon />}
                onClick={() => setModalOpen(true)} sx={{ px: 4 }}>
                Start Assessment
              </Button>
            </Box>
          ) : (
            <Grid container spacing={2.5}>
              {reports.map(report => (
                <Grid item xs={12} sm={6} md={4} key={report.id}>
                  <ReportCard report={report} onDelete={handleDelete} />
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      </Fade>

      {/* ── Mode selection dialog ── */}
      <Dialog open={modalOpen} onClose={() => setModalOpen(false)}
        maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1, pt: 3, px: 3.5 }}>
          <Typography variant="h3">Start a new assessment</Typography>
          <Typography variant="body2" color="text.secondary" mt={0.5}>
            Choose the type of content you'd like to analyse.
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ px: 3.5, pb: 3.5, pt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <ModeCard
                icon={<BookOutlinedIcon />}
                title="Self-Assessment"
                description="Write about how you've been feeling. Includes the GAD-7 questionnaire for structured context."
                onClick={() => startAssessment('journal')}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <ModeCard
                icon={<ArticleOutlinedIcon />}
                title="Social Media"
                description="Paste a Reddit post or social media text for indirect text analysis."
                badge="No GAD-7"
                onClick={() => startAssessment('social-media')}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 2.5, p: 2, borderRadius: 2.5,
            bgcolor: 'rgba(79,124,172,0.05)', border: '1px solid rgba(79,124,172,0.12)' }}>
            <Typography variant="caption" color="text.secondary" lineHeight={1.7} display="block">
              🔒 <strong>Privacy:</strong> Responses are transmitted to the AnxioSense server and
              processed using third-party AI infrastructure. If report saving is enabled, the generated
              report may be stored in your account. AnxioSense is a research prototype and should not
              be treated as a confidential clinical service.
            </Typography>
          </Box>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

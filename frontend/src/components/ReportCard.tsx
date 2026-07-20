import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, CardActions, Box, Typography,
  Chip, Button, IconButton, Menu, MenuItem, Tooltip,
} from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import BookOutlinedIcon from '@mui/icons-material/BookOutlined';
import { useState } from 'react';
import type { ReportSummary } from '../services/api';

interface ReportCardProps {
  report: ReportSummary;
  onDelete: (id: string) => void;
}

const CONCERN_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  'Minimal Concern Pattern':  { label: 'Minimal',  color: '#059669', bg: '#ECFDF5' },
  'Mild Concern Pattern':     { label: 'Mild',     color: '#B45309', bg: '#FFFBEB' },
  'Elevated Concern Pattern': { label: 'Elevated', color: '#B45309', bg: '#FEF3C7' },
  'High Concern Pattern':     { label: 'High',     color: '#DC2626', bg: '#FEF2F2' },
};

const REFERRAL_CONFIG: Record<string, { color: string; label: string }> = {
  low:      { color: '#059669', label: 'Low concern' },
  moderate: { color: '#B45309', label: 'Follow up suggested' },
  urgent:   { color: '#DC2626', label: 'Urgent referral' },
};

export default function ReportCard({ report, onDelete }: ReportCardProps) {
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const concern  = CONCERN_CONFIG[report.concernPattern] ?? CONCERN_CONFIG['Minimal Concern Pattern'];
  const referral = REFERRAL_CONFIG[report.referralLevel] ?? REFERRAL_CONFIG['moderate'];

  const date = new Date(report.createdAt).toLocaleDateString('en-CA', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
  const time = new Date(report.createdAt).toLocaleTimeString('en-CA', {
    hour: '2-digit', minute: '2-digit',
  });

  return (
    <Card elevation={0} sx={{
      border: '1px solid', borderColor: 'divider',
      '&:hover': { boxShadow: '0 6px 24px rgba(0,0,0,0.09)', transform: 'translateY(-2px)' },
      cursor: 'default',
    }}>
      <CardContent sx={{ p: 3, pb: 1.5 }}>

        {/* Header row */}
        <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={2}>
          <Box display="flex" gap={1} flexWrap="wrap">
            {/* Mode chip */}
            <Chip
              icon={report.mode === 'journal'
                ? <BookOutlinedIcon style={{ fontSize: 14 }} />
                : <ArticleOutlinedIcon style={{ fontSize: 14 }} />}
              label={report.mode === 'journal' ? 'Self-Assessment' : 'Social Media'}
              size="small"
              sx={{ bgcolor: 'rgba(79,124,172,0.08)', color: 'primary.dark',
                border: '1px solid rgba(79,124,172,0.2)', fontWeight: 600 }}
            />
            {/* Concern chip */}
            <Chip
              label={concern.label}
              size="small"
              sx={{ bgcolor: concern.bg, color: concern.color,
                border: `1px solid ${concern.color}22`, fontWeight: 700 }}
            />
          </Box>

          <IconButton size="small" onClick={e => setAnchorEl(e.currentTarget)}
            sx={{ ml: 1, flexShrink: 0 }}>
            <MoreVertIcon fontSize="small" />
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}
            PaperProps={{ sx: { borderRadius: 2, boxShadow: '0 8px 24px rgba(0,0,0,0.1)' } }}>
            <MenuItem onClick={() => { setAnchorEl(null); navigate(`/report/${report.id}`); }}>
              View report
            </MenuItem>
            <MenuItem onClick={() => { setAnchorEl(null); onDelete(report.id); }}
              sx={{ color: 'error.main' }}>
              Delete
            </MenuItem>
          </Menu>
        </Box>

        {/* Date */}
        <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
          {date} · {time}
        </Typography>

        {/* Summary */}
        <Typography variant="body2" color="text.secondary" sx={{
          display: '-webkit-box', WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.7,
        }}>
          {report.summary}
        </Typography>

        {/* Referral indicator */}
        <Box display="flex" alignItems="center" gap={0.75} mt={2}>
          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: referral.color, flexShrink: 0 }} />
          <Typography variant="caption" sx={{ color: referral.color, fontWeight: 600 }}>
            {referral.label}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ px: 3, pb: 2.5, pt: 1 }}>
        <Button
          variant="outlined" size="small" fullWidth
          onClick={() => navigate(`/report/${report.id}`)}
          sx={{ borderRadius: 2 }}
        >
          View Full Report
        </Button>
      </CardActions>
    </Card>
  );
}

import { useState } from 'react';
import {
  Box, Typography, Paper, Button,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

export type FunctionalImpairment =
  | 'not_difficult_at_all'
  | 'somewhat_difficult'
  | 'very_difficult'
  | 'extremely_difficult';

const OPTIONS: Array<{ value: FunctionalImpairment; label: string }> = [
  { value: 'not_difficult_at_all', label: 'Not difficult at all' },
  { value: 'somewhat_difficult',   label: 'Somewhat difficult'   },
  { value: 'very_difficult',       label: 'Very difficult'       },
  { value: 'extremely_difficult',  label: 'Extremely difficult'  },
];

interface FunctionalImpairmentFormProps {
  onComplete: (value: FunctionalImpairment) => void;
  onBack:     () => void;
}

/**
 * Renders the GAD-7 standard functional impairment follow-up question.
 *
 * Source: Spitzer et al. (2006) — "If you checked off any problems, how difficult
 * have these problems made it for you to do your work, take care of things at home,
 * or get along with other people?"
 *
 * The response does NOT change the GAD-7 score. It acts as a secondary factor
 * that personalises the patient-facing recommendation only.
 */
export default function FunctionalImpairmentForm({
  onComplete,
  onBack,
}: FunctionalImpairmentFormProps) {
  const [selected, setSelected] = useState<FunctionalImpairment | null>(null);

  function handleSelect(value: FunctionalImpairment) {
    setSelected(value);
    // Short delay so the selection is visible before advancing
    setTimeout(() => onComplete(value), 320);
  }

  return (
    <Box>
      {/* Question */}
      <Typography variant="h4" mb={1} lineHeight={1.5}>
        If you checked off any problems, how difficult have these problems made it
        for you to do your work, take care of things at home, or get along with
        other people?
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        This question does not change your questionnaire score — it helps
        personalise your assessment recommendation.
      </Typography>

      {/* Answer options */}
      <Box display="flex" flexDirection="column" gap={1.5}>
        {OPTIONS.map(opt => (
          <Paper
            key={opt.value}
            elevation={0}
            onClick={() => handleSelect(opt.value)}
            sx={{
              p: 2, borderRadius: 3, cursor: 'pointer',
              border: '1.5px solid',
              borderColor: selected === opt.value ? 'primary.main' : 'divider',
              bgcolor: selected === opt.value ? 'rgba(79,124,172,0.06)' : '#FAFAFA',
              transition: 'all 0.15s ease',
              '&:hover': {
                borderColor: 'primary.light',
                bgcolor: 'rgba(79,124,172,0.04)',
                transform: 'translateX(4px)',
              },
              display: 'flex', alignItems: 'center', gap: 2,
            }}
          >
            <Box sx={{
              width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
              border: '2px solid',
              borderColor: selected === opt.value ? 'primary.main' : '#D1D5DB',
              bgcolor: selected === opt.value ? 'primary.main' : 'transparent',
              transition: 'all 0.15s ease',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {selected === opt.value && (
                <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'white' }} />
              )}
            </Box>
            <Typography variant="body2" fontWeight={500}>{opt.label}</Typography>
          </Paper>
        ))}
      </Box>

      {/* Back button */}
      <Box mt={3}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          sx={{ color: 'text.secondary' }}
        >
          Back to questionnaire
        </Button>
      </Box>
    </Box>
  );
}

import { useState } from 'react';
import {
  Box, Typography, Button, LinearProgress,
  Fade, Paper,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const QUESTIONS = [
  'Feeling nervous, anxious, or on edge',
  'Not being able to stop or control worrying',
  'Worrying too much about different things',
  'Trouble relaxing',
  'Being so restless that it is hard to sit still',
  'Becoming easily annoyed or irritable',
  'Feeling afraid, as if something awful might happen',
];

const OPTIONS = [
  { label: 'Not at all',              value: 0 },
  { label: 'Several days',            value: 1 },
  { label: 'More than half the days', value: 2 },
  { label: 'Nearly every day',        value: 3 },
];

interface Gad7FormProps {
  onComplete: (answers: number[]) => void;
  onSkip:     () => void;
  /** When true, hides the Skip button at step 0 so users cannot bypass the questionnaire. */
  required?:  boolean;
}

export default function Gad7Form({ onComplete, onSkip, required = false }: Gad7FormProps) {
  const [step, setStep]       = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [fading, setFading]   = useState(true);

  const progress = (step / QUESTIONS.length) * 100;

  function handleSelect(value: number) {
    setSelected(value);
    setTimeout(() => {
      const newAnswers = [...answers, value];
      if (step < QUESTIONS.length - 1) {
        setFading(false);
        setTimeout(() => {
          setStep(s => s + 1);
          setSelected(null);
          setFading(true);
        }, 180);
        setAnswers(newAnswers);
      } else {
        onComplete(newAnswers);
      }
    }, 280);
  }

  function handleBack() {
    if (step === 0) { onSkip(); return; }
    setFading(false);
    setTimeout(() => {
      setStep(s => s - 1);
      setAnswers(a => a.slice(0, -1));
      setSelected(null);
      setFading(true);
    }, 180);
  }

  return (
    <Box>
      {/* Progress */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
        <Typography variant="caption" color="text.secondary" fontWeight={600}>
          Question {step + 1} of {QUESTIONS.length}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Over the past 2 weeks
        </Typography>
      </Box>
      <LinearProgress variant="determinate" value={progress} sx={{ mb: 3.5 }} />

      {/* Question */}
      <Fade in={fading} timeout={200}>
        <Box>
          <Typography variant="h4" mb={1} lineHeight={1.5}>
            {QUESTIONS[step]}
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={3}>
            How often have you been bothered by this?
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

          {/* Back / Skip — hidden at step 0 when questionnaire is required */}
          {!(required && step === 0) && (
            <Box display="flex" justifyContent="space-between" mt={3}>
              <Button
                startIcon={<ArrowBackIcon />}
                onClick={handleBack}
                sx={{ color: 'text.secondary' }}
              >
                {step === 0 ? 'Skip GAD-7' : 'Back'}
              </Button>
            </Box>
          )}
        </Box>
      </Fade>
    </Box>
  );
}

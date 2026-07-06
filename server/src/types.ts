export interface ReportRow {
  id:              string;
  user_id:         string;
  mode:            'journal' | 'social-media';
  created_at:      string;
  concern_pattern: string;
  referral_level:  'low' | 'moderate' | 'urgent';
  summary:         string;
  full_report:     string;
  clinician_mode:  number; // SQLite stores boolean as 0/1
}

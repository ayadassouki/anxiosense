import { API_URL } from '../config/api';

const TOKEN_KEY = 'anxiosense_token';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // Try to parse JSON — if it fails (HTML proxy error), fall back to generic message
    const body = await res.json().catch(() => null) as { message?: string } | null;
    if (body?.message) throw new Error(body.message);
    if (res.status >= 502) {
      throw new Error('Could not connect. Make sure both servers are running:\n• Mastra: npm run dev (port 4111)\n• Server: cd server && npm run dev (port 3001)');
    }
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Report types ─────────────────────────────────────────────────────────────

export interface ReportSummary {
  id:             string;
  userId:         string;
  mode:           'journal' | 'social-media';
  createdAt:      string;
  concernPattern: string;
  referralLevel:  'low' | 'moderate' | 'urgent';
  summary:        string;   // first 2-3 sentences
  fullReport:     string;
  clinicianMode:  boolean;
}

// ── Reports API ───────────────────────────────────────────────────────────────

export async function getReports(): Promise<ReportSummary[]> {
  const res = await fetch(`${API_URL}/api/reports`, { headers: authHeaders() });
  return handleResponse<ReportSummary[]>(res);
}

export async function getReport(id: string): Promise<ReportSummary> {
  const res = await fetch(`${API_URL}/api/reports/${id}`, { headers: authHeaders() });
  return handleResponse<ReportSummary>(res);
}

export async function deleteReport(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/reports/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  await handleResponse<void>(res);
}

// ── Workflow API ──────────────────────────────────────────────────────────────

export interface RunWorkflowParams {
  mode:                  'journal' | 'social-media';
  userText:              string;
  gad7Answers?:          number[];
  /**
   * Functional impairment response — does not change the GAD-7 score,
   * only personalises the patient-facing recommendation.
   */
  functionalImpairment?: 'not_difficult_at_all' | 'somewhat_difficult' | 'very_difficult' | 'extremely_difficult';
  clinicianMode?:        boolean;
  saveSession?:          boolean;
}

export interface WorkflowResult {
  reportId:    string;
  finalReport: string;
  concernPattern: string;
  referralLevel: string;
}

export async function runWorkflow(params: RunWorkflowParams): Promise<WorkflowResult> {
  const res = await fetch(`${API_URL}/api/workflow/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(params),
  });
  return handleResponse<WorkflowResult>(res);
}

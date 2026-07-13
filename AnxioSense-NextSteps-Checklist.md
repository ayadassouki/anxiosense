# AnxioSense — Supervisor Changes Checklist

Produced after the July 11 research meeting. These are implementation plans only — nothing below has been coded yet.

---

## 1. Rename "Journal Entry" → "Self-Assessment"

**Why:** The word "journal" carries a connotation of personal diary writing. "Self-Assessment" is more neutral, clinically appropriate, and accurately describes what the user is doing (completing a structured evaluation, not free-writing).

**Files to change:**

| File | What to change |
|------|----------------|
| `frontend/src/pages/AssessmentPage.tsx` | Mode label displayed to the user (`"Journal Entry"` → `"Self-Assessment"`) |
| `frontend/src/pages/AssessmentPage.tsx` | Mode value passed to the API — decide whether to change the internal string `'journal'` → `'self-assessment'` or keep it as an internal enum and only change the display label. **Recommended:** keep internal value as `'journal'` for now to avoid breaking all downstream checks, and only change the UI string. |
| `frontend/src/pages/DashboardPage.tsx` | Any place `"Journal"` or `"journal"` appears as a user-facing mode label |
| `frontend/src/pages/ReportPage.tsx` | Assessment mode badge / header text |
| `server/src/routes/workflow.ts` | Comments and log messages (not user-facing, lower priority) |
| `AnxioSense-Supervisor-Prep.md` | Update for consistency in documentation |

**Watch out for:** The internal API schema uses `mode: 'journal' | 'social-media'` in the Mastra workflow input, the session store, the server route, and the DB. If you change the internal enum value, you must update all of these atomically and re-seed or migrate the SQLite `reports` table (the `mode` column stores the string).

---

## 2. Show GAD-7 Total Score and Interpretation in the Self-Assessment View

**Why:** Users currently complete 7 questions and then see a "Required — completed" chip. They never see their own score or what it means. Supervisors want the score visible immediately after completion — not only in the final report.

**Implementation plan:**

The GAD-7 score is computed deterministically from the 7 answers on the server side (in `workflow.ts`), but the frontend already has the `gad7Answers` array before the workflow even runs. The score can be computed client-side immediately after the form completes — no server round-trip needed.

**Files to change:**

| File | What to add |
|------|-------------|
| `frontend/src/pages/AssessmentPage.tsx` | After `onGad7Complete` fires, compute `score = answers.reduce((a, b) => a + b, 0)` and set it in state. Display score + band label in the GAD-7 card. |
| `frontend/src/components/Gad7Form.tsx` | Optionally: add a results screen as the final "step" (after question 7) that shows the score before calling `onComplete`. This keeps score display self-contained in the component. |

**Display format to implement:**

```
GAD-7 Score: 12 / 21
Elevated Concern Pattern

Over the past 2 weeks, your responses suggest an elevated frequency of anxiety-related experiences.
```

Band labels (match the existing pipeline exactly):
- 0–4: Minimal Concern Pattern
- 5–9: Mild Concern Pattern
- 10–14: Elevated Concern Pattern
- 15–21: High Concern Pattern

**Do not** show clinical severity words (minimal/mild/moderate/severe) — use only the Concern Pattern labels already established in the pipeline.

---

## 3. Add Input Validation

**Why:** The server currently accepts `userText` of arbitrary length. Long inputs silently overflow Mistral's context window, producing degraded or truncated agent outputs with no error shown to the user.

**Two layers needed:**

**Layer 1 — Client-side (AssessmentPage.tsx):**
- Current minimum: 20 characters (already enforced)
- Add maximum: 2,000 characters with a live character counter shown below the text field
- Show a warning at 1,800 characters: "Approaching limit — longer entries may affect analysis quality"
- Disable "Run Analysis" when over the limit (same pattern as the existing GAD-7 enforcement)

**Layer 2 — Server-side (server/src/routes/workflow.ts):**
- Add a hard cap check before the Mastra call: if `userText.trim().length > 2000`, return HTTP 400 with a descriptive message
- This is the actual security boundary; the frontend check is just UX

**Files to change:**

| File | Change |
|------|--------|
| `frontend/src/pages/AssessmentPage.tsx` | Character counter + max length warning + disable condition |
| `server/src/routes/workflow.ts` | Length check after the existing `!userText?.trim()` check |

**Decision needed:** What should the character limit be? 2,000 characters is roughly 300–400 words — appropriate for a reflective journal entry. 5,000 would cover longer entries. Discuss with supervisors — the limit should be grounded in what Mistral's context window can reliably handle after all system prompts are included.

---

## 4. Add PDF Export

**Why:** Users and clinicians want a portable, printable version of the report. The current report is only readable inside the app.

**Implementation options:**

**Option A — Browser Print to PDF (minimal effort):**
Add a "Download PDF" button to `ReportPage.tsx` that calls `window.print()`. Style a `@media print` CSS block that hides nav, removes buttons, and formats the markdown report cleanly. Produces a PDF immediately with zero server-side work.

**Option B — Server-side PDF generation (higher quality):**
Use `pdfkit` or `puppeteer` on the Express server. Generate a properly paginated PDF with headers, footers, and page numbers. Requires adding a `/api/reports/:id/pdf` endpoint.

**Recommendation:** Start with Option A (browser print) as it requires ~30 lines of CSS and one button. If supervisors or ethics board require a clinical-grade formatted document, upgrade to Option B.

**Files to change (Option A):**

| File | Change |
|------|--------|
| `frontend/src/pages/ReportPage.tsx` | Add a "Download PDF" `<Button>` that calls `window.print()` |
| `frontend/src/index.css` or inline `<style>` | Add `@media print { ... }` block to hide chrome elements |

**Clinician mode note:** When `clinicianMode` is true, the Clinician Summary section appears in the report. The PDF should include it only when clinicianMode is active. The current report already handles this at the markdown level, so a print-to-PDF will automatically include or exclude it correctly.

---

## 5. Instrument Per-Agent Execution Time

**Why:** For research purposes, you need to know how long each parallel agent (emotion, symptom, context, referral) takes and whether any agent is a consistent bottleneck. This informs future optimisation decisions.

**Implementation plan:**

Timing should be added inside `anxiosense-workflow.ts` — not in the agents themselves, because the workflow orchestrates the parallel execution.

**Where to add timing:**

```typescript
// In the Map step (parallel agent execution), before each agent call:
const t0 = Date.now();
// ... agent call ...
const agentDuration = Date.now() - t0;

// Write to session store:
writeSession(sessionId, { agentTimings: { emotion: emotionMs, symptom: symptomMs, ... } });
```

**What to capture (minimum):**
- Per-agent wall-clock time in ms: emotion, symptom, context, referral
- Retrieval step total time
- Evidence validation step total time
- Report generation step total time
- Total end-to-end time from workflow start to `finalReport`

**Where to surface the data:**
- Option A: Log to the Mastra `console.log` output only (cheapest, good for dev)
- Option B: Add a `timings` field to the session store and include it in the Clinician Summary section of the report
- Option C: Write timings to a separate `src/mastra/public/timings/` file per run for offline analysis

**Files to change:**

| File | Change |
|------|--------|
| `src/mastra/utils/workflow-session-store.ts` | Add `agentTimings` field to `SessionData` interface |
| `src/mastra/workflows/anxiosense-workflow.ts` | Wrap each agent call in `Date.now()` measurements and write to session store |
| `src/mastra/workflows/anxiosense-workflow.ts` (reportStep) | Optionally include timings table in Clinician Summary |

---

## 6. Deployment Options (Given Local Mastra + Ollama Dependency)

**The core constraint:** The pipeline requires Ollama running locally with `mistral:latest` pulled. Mastra's workflow engine is a Hono HTTP server that also runs locally. Any deployment must either keep everything local or migrate the LLM to an API provider.

### Option A — Single-Machine Research Deployment (No Cloud)

Keep the entire stack on your own machine or a lab server. Run all three processes (Mastra on 4111, Express on 3001, Vite/served frontend) with a process manager like `pm2`. Expose via SSH tunnel or lab VPN for supervised use with participants.

**Effort:** Low. **Cost:** Zero. **Suitable for:** Small supervised user study (5–20 participants) in a controlled lab setting.

**Steps needed:**
1. Install `pm2`: `npm install -g pm2`
2. Write a `pm2.config.js` that starts all three processes
3. Build the frontend: `cd frontend && npm run build`
4. Serve the frontend build with a static server or nginx
5. Add a nginx reverse proxy so participants access a single port

### Option B — Replace Ollama with an API Provider

Swap `ollama-ai-provider-v2` for Anthropic, OpenAI, or Groq in all agent files. Mastra's agent API is provider-agnostic — changing the model line in each agent is the only code change required.

```typescript
// Before (local Ollama):
model: localOllama('mistral:latest', { temperature: 0.1 })

// After (Anthropic — example):
model: anthropic('claude-haiku-4-5-20251001')
```

Once agents use an external API, Mastra can be deployed to any Node.js host (Railway, Render, Fly.io). The Express server and frontend can also be deployed separately.

**Effort:** Medium (agent file changes + new env vars + cost consideration). **Cost:** API usage fees. **Suitable for:** Remote demos, ethics review demos, any case where you cannot guarantee Ollama is running on the target machine.

**Research ethics implication:** Switching to an external API means user text is sent to a third-party LLM provider. This must be disclosed to participants and covered by IRB approval — same issue as Mastra observability was.

### Option C — Docker Compose (Recommended for Reproducibility)

Write a `docker-compose.yml` that bundles Mastra + Express + Ollama (using the official `ollama/ollama` Docker image). The frontend is built as a static bundle and served by nginx.

**Effort:** High (requires writing Dockerfiles for Mastra and Express + docker-compose wiring). **Benefit:** Anyone can run `docker compose up` on any machine without installing Node, Mastra, or Ollama manually.

**Decision needed:** Ollama with `mistral:latest` requires ~4 GB disk and a machine with ≥8 GB RAM. GPU acceleration via Docker is available but adds setup complexity. Confirm the target hardware before committing to this approach.

---

## 7. Labeled Dataset and Evaluation-Metric Research

**Why this is the most important research gap.** Every claim about AnxioSense's performance (claim extraction accuracy, concern pattern classification, evidence agreement sensitivity) is currently theoretical. No numbers exist. This is the primary blocker for a publishable research contribution.

### What needs to be built

**Step 1 — Define the annotation schema:**

For each journal entry in your dataset, annotators should label:
- GAD-7 score (from actual administered questionnaire, if available)
- Ground-truth anxiety indicators present (list of strings matching the KB categories)
- Ground-truth concern level (Minimal / Mild / Elevated / High) based on clinical judgment
- Whether the GAD-7 and the text are concordant or discordant

**Step 2 — Source or create a labeled dataset:**

Options:
- Use publicly available anonymised mental health text datasets (Reddit r/anxiety posts, DAIC-WOZ, AnxietyData from Kaggle — check licensing carefully)
- Create synthetic entries at each concern level (low ecological validity but quick)
- Run a small pilot with 10–20 volunteer participants who complete GAD-7 + write a journal entry (requires ethics approval)

**Step 3 — Define evaluation metrics:**

| Metric | What it measures |
|--------|-----------------|
| Claim extraction recall | Of the ground-truth indicators, what fraction does AnxioSense identify? |
| Claim extraction precision | Of the claims AnxioSense extracts, what fraction are actually relevant? |
| Concern pattern accuracy | Does the final concern pattern match the clinical ground truth? |
| Discordance detection recall | Of truly discordant cases, what fraction does AnxioSense flag? |
| Evidence Agreement calibration | Does "High Agreement" actually correlate with correct classification? |

**Step 4 — Build a batch evaluation runner:**

A script that feeds each dataset entry through the full pipeline (or mocked pipeline for speed) and computes the metrics above. The `src/scripts/` directory is the right home for this.

**Step 5 — Threshold calibration:**

The cosine thresholds (≥0.72 = supported, ≥0.55 = partially supported) were set heuristically. Run the pipeline on the labeled dataset with a sweep of threshold values and pick the combination that maximises the relevant metric (likely F1 on concern pattern classification).

### Research question framing for thesis/publication

The most defensible contribution is framed as: *"Does augmenting GAD-7 self-report with LLM-based text analysis improve detection of discordant cases that may warrant clinical follow-up?"*

This requires:
- A labeled dataset where ground-truth discordance is known
- A GAD-7-only baseline (trivial to implement)
- An AnxioSense full-pipeline condition
- A comparison metric (sensitivity / specificity for flagging discordant cases)

This is a tractable research design that can be completed before a thesis deadline.

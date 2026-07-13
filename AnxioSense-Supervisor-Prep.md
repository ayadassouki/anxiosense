# AnxioSense — Supervisor Meeting Preparation
## Complete Technical Walkthrough · Aya Dassouki

> Written as if your supervisors are asking every question they possibly could.
> Read this end-to-end tonight. The cheat sheet is at the bottom.

---

# PART 1 — COMPLETE SYSTEM WALKTHROUGH

## The journey of a single journal entry, start to finish

### 1. User opens the frontend

**File:** `frontend/src/main.tsx`

The React 18 app boots inside a `<GoogleOAuthProvider>` (wrapping the whole tree with the Google Client ID from `VITE_GOOGLE_CLIENT_ID`), a `<BrowserRouter>` for routing, and an `<AuthProvider>` that reads a JWT from `localStorage` on load. If a valid token is present, the user is already logged in and redirected to the dashboard.

React Router v6 defines four protected routes (`/dashboard`, `/assess`, `/report/:id`, `/profile`) and two public routes (`/login`, `/signup`). Route protection is handled in `AuthContext` — attempting to access a protected route without a token redirects to `/login`.

---

### 2. Mode selection

**File:** `frontend/src/pages/DashboardPage.tsx`

From the dashboard the user clicks either **Journal Entry** or **Social Media Analysis**. The button calls `navigate('/assess', { state: { mode: 'journal' } })` or `'social-media'`. The `mode` string travels as React Router location state into the Assessment page.

**Why two modes?** GAD-7 is a structured self-report instrument validated on first-person disclosures. Applying it to third-party text (Reddit posts, social media captions written by an unknown author) would be clinically invalid. Social media mode treats the text as an indirect signal with extra conservatism and explicitly states no questionnaire was administered.

---

### 3. Journal mode requires GAD-7

**Files:** `frontend/src/pages/AssessmentPage.tsx`, `frontend/src/components/Gad7Form.tsx`

In journal mode the GAD-7 card shows a **Required** chip (red before completion, green after). The Run Analysis button is disabled (`disabled={isJournal && !gad7Answers}`) until the form is completed. There is no skip button at step 0 when `required` prop is passed to `Gad7Form`.

`Gad7Form` renders one question at a time with animated transitions. The user selects one of four options (Not at all = 0, Several days = 1, More than half the days = 2, Nearly every day = 3) for each of seven items. On completion it calls `onGad7Complete(answers: number[])` — an array of seven integers — which sets `gad7Answers` in `AssessmentPage` state. The array is passed as-is to the backend; scoring is done server-side/workflow-side.

**Why require GAD-7?** The GAD-7 provides a validated, standardised anchor point. Without it, the report relies entirely on a language model's interpretation of free text, which introduces ambiguity. The supervisor feedback was explicit: the questionnaire is the primary clinical signal; the text is contextual enrichment.

---

### 4. Request hits the Express server

**File:** `server/src/routes/workflow.ts`

The frontend calls `POST /api/workflow/run` with body `{ mode, userText, gad7Answers, clinicianMode, saveSession }`.

The server does three things before touching Mastra:

1. **Validates** that `userText` is non-empty.
2. **Creates a Mastra run** via `POST http://localhost:4111/api/workflows/anxiosense-workflow/create-run`.
3. **Starts the run** via `POST /start?runId=...` with `{ inputData: { mode, userText, gad7Answers, clinicianMode } }`.

If Mastra returns the result synchronously (which it does for short runs), the report is extracted immediately. If not, the server polls `GET /api/workflows/anxiosense-workflow/runs/:runId` every 3 seconds up to 150 seconds. This polling loop is necessary because Mistral running locally is slow.

The `extractFinalReport()` helper recursively searches the Mastra response object for a `finalReport` string key anywhere in the nested output. This is defensive — Mastra's response envelope changes between SDK versions.

**Post-Mastra:** concern pattern is computed deterministically on the server using the same GAD-7 score thresholds (not extracted from the Mastra output which only contains `finalReport`). This prevents any LLM drift from affecting the concern label.

---

### 5. Mastra workflow starts

**File:** `src/mastra/workflows/anxiosense-workflow.ts`

The Mastra server is a **Hono** HTTP server running on port 4111. It loads all agents and workflows defined in `src/mastra/index.ts`.

The `anxiosenseWorkflow` is built using Mastra's fluent builder API:

```
.parallel([emotionStep, symptomStep, contextStep, referralStep])
.map(...)          ← merge parallel outputs
.then(buildClaimsStep)
.map(...)          ← GAD-7 scoring + discordance detection + session write
.then(retrievalStep)
.map(...)          ← write retrieval output to session
.then(evidenceValidationStep)
.then(reportStep)
```

Data flows through typed Zod schemas at every step boundary. If a step's output does not match the next step's input schema, Mastra throws a validation error before execution — this is the guard that caught the empty claims bug.

---

### 6. Four parallel agents

**Files:** `src/mastra/agents/{emotion,symptom,context,referral}-agent.ts`

These four steps run concurrently (Mastra `.parallel()`). Each agent receives the same input: `mode` + `userText`. The `modePrefix()` helper prepends a CONTEXT line that tells the agent whether the text is a journal entry or social media content.

| Agent | Returns |
|---|---|
| **emotionAgent** | `{"emotions": ["anxiety", "worry", "hope"]}` |
| **symptomAgent** | `{"possible_anxiety_indicators": ["excessive worry", "sleep disruption"]}` |
| **contextAgent** | `{"contextual_stressors": ["academic stress", "social pressure"]}` |
| **referralAgent** | `{"risk_level": "moderate", "reasoning": "..."}` |

All agents use **Mistral:latest** running locally via Ollama. All are instructed to return only JSON.

---

### 7. Build Claims step

**File:** `src/mastra/workflows/build-claims-step.ts`

Map 1 merges the four parallel outputs into a `combinedAnalysisSchema` object, then `buildClaimsStep` executes.

This step parses each agent's JSON output (using the robust `extractJson()` function that handles raw JSON, markdown code fences, and embedded JSON) and constructs a typed `claims` array:

- Emotion items → `EMO-n` claims with category `emotional_state`
- Symptom items → `SYM-n` claims; category is `shared_symptom` if the text contains sleep/fatigue/concentration/irritability keywords, else `anxiety_indicator`
- Context items → `CTX-n` claims with category `contextual_stressor`

**Fallback:** If all three agents return empty arrays (minimal-concern text), a single `GEN-1` fallback claim is injected with `category: 'anxiety_indicator'` and `claimText` = the first 300 characters of the user text. This ensures the pipeline never crashes the downstream retrieval step which requires at least one claim. The fallback uses `anxiety_indicator` (not `emotional_state`) so it only queries general anxiety KB files, not depression files.

---

### 8. Map 2 — GAD-7 scoring, discordance detection, session write

**File:** `src/mastra/workflows/anxiosense-workflow.ts` (Map 2 `.map()`)

**GAD-7 scoring** (`src/mastra/utils/gad7-scorer.ts`): If mode is journal and `gad7Answers` has 7 integers, `computeGad7Score()` sums them. The score maps to severity bands (minimal/mild/moderate/severe) and the `formatGad7ForReport()` function generates the formatted user-facing GAD-7 block (with item-by-item question labels, not raw numbers).

**Concern pattern derivation:**
```
0–4   → Minimal Concern Pattern
5–9   → Mild Concern Pattern
10–14 → Elevated Concern Pattern
15–21 → High Concern Pattern
```

**Discordance detection:** Two edge cases are flagged:
- `high_gad7_low_text`: GAD-7 ≥ 15 but only 0–1 real text claims → questionnaire says severe, text says almost nothing
- `low_gad7_high_text`: GAD-7 ≤ 4 but ≥ 4 real text claims → text is anxious-sounding, questionnaire says minimal

**Session write:** All intermediate data (mode, clinicianMode, gad7Block, gad7Score, gad7Severity, gad7ItemScores, gad7ConcernPattern, discordanceNote) is written to the in-memory session store (`src/mastra/utils/workflow-session-store.ts`) keyed by `sessionId`. This avoids threading all this data through every step's Zod schema.

---

### 9. Retrieval step

**File:** `src/mastra/agents/retrieval-agent.ts`

The retrieval agent receives the claims array. For each claim, it uses `CATEGORY_TO_FILES` (`src/kb/category-routing.ts`) to determine which KB files to search:

```
anxiety_indicator  → anxiety_indicators.txt + instrument_reference.txt
depression_indicator → depression_indicators.txt + instrument_reference.txt
shared_symptom     → shared_symptoms.txt + anxiety_vs_depression.txt
contextual_stressor → contextual_stressors.txt
emotional_state    → anxiety_indicators.txt + depression_indicators.txt + anxiety_vs_depression.txt
```

The agent embeds the `claimText` using **fastembed** (`bge-small-en-v1.5` model) and queries **LibSQLVector** (a SQLite-backed vector store) for the top-k most similar chunks from the relevant files. Similarity is cosine similarity.

Retrieved chunks are stored alongside the claim in the output. The retrieval output is written back to the session store for later use.

---

### 10. Evidence Validation step

**File:** `src/mastra/workflows/evidence-validation-step.ts`

This step applies **deterministic cosine similarity thresholds** to classify each claim:

```
supported          ≥ 0.72
partially_supported ≥ 0.55
unsupported        < 0.55
```

These thresholds are fixed — not learned, not LLM-dependent. Every classification is reproducible given the same claim text and KB. The step also runs the `differentiationAssessment` (anxiety vs depression lean) and produces `overallConsistencyNotes`.

Output is a `ValidationAgentOutputSchema` object containing `claimValidations[]`, `differentiationAssessment`, `overallConsistencyNotes`, `riskLevel`, and `sessionId`.

---

### 11. Report generation

**File:** `src/mastra/workflows/anxiosense-workflow.ts` (reportStep)

**Urgent path:** If `inputData.riskLevel === 'urgent'`, a hardcoded safety notice is returned immediately. No LLM is called. No report is generated. This is intentional — the user's wellbeing takes priority.

**Normal path:** Session data is read. Evidence Agreement is computed deterministically (concern level comparison: GAD-7 band number vs symptom claim count band number). The prompt passes grouped claim labels to the LLM. The LLM generates **Supporting Findings + Recommendation + Limitations** only.

Assessment Overview (with GAD-7 block verbatim) and Evidence Agreement are injected by TypeScript after LLM generation. Clinician Summary is appended last if `clinicianMode=true`.

---

### 12. Frontend rendering

**File:** `frontend/src/pages/ReportPage.tsx`

The report arrives from the server as `{ reportId, finalReport, concernPattern, referralLevel, summary }`. The report page reads `concernPattern` to display the coloured header chip. The `finalReport` markdown string is rendered using `react-markdown` with `remark-gfm`. The clinician block (if present) is separated visually.

The export function builds a `.txt` file from the report metadata + `finalReport` and triggers a browser download.

---

### 13. Database (if saveSession is on)

**File:** `server/src/routes/workflow.ts`, `server/src/db.ts`

If `saveSession=true` and the user is authenticated (not a guest), the server inserts one row into the `reports` table:

```sql
INSERT INTO reports (id, user_id, mode, concern_pattern, referral_level, summary, full_report, clinician_mode)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
```

`summary` is extracted by `extractSummary()` — a regex that finds the first 3 sentences under any heading matching "Summary" or "Overview". The raw `userText` is **never stored**. Only the structured output is saved.

---

### 14. Dashboard

**File:** `frontend/src/pages/DashboardPage.tsx`

The dashboard calls `GET /api/reports` (authenticated). The server queries:

```sql
SELECT id, mode, concern_pattern, referral_level, summary, clinician_mode, created_at
FROM reports WHERE user_id = ? ORDER BY created_at DESC
```

Each report is shown as a card with the concern pattern chip. Clicking opens the full report via `GET /api/reports/:id`.

---

# PART 2 — EVERY AGENT

## emotionAgent

**Purpose:** Detect the emotional tone of the text — what feelings are present, not what symptoms exist.

**Input:** The user's text with a mode context prefix.

**Output:** `{"emotions": ["anxiety", "sadness", "hope"]}` — a flat array of emotion labels.

**Prompt strategy:** System prompt instructs the model to identify emotions as a clinical assessor would, not a layperson. It is explicitly told not to diagnose.

**Why it exists:** Emotion detection is a distinct subtask from symptom detection. Separating them allows the pipeline to distinguish "the user feels anxious (emotion)" from "the user reports excessive worry (anxiety symptom)". This also means minimal-concern text produces mostly emotional claims (happiness, relief) rather than symptom claims, keeping those out of the clinical evidence pool.

**Potential limitations:** Mistral may over-infer emotion from neutral text. Short texts may yield few signals.

**Supervisor question:** *"Couldn't one LLM call extract emotions and symptoms together?"*
**Answer:** Yes, technically. But separating them creates explicit, testable outputs. If emotion detection fails, I can fix the emotion agent's prompt without touching symptom detection. Parallel execution also reduces latency. There's an academic argument: decomposing the clinical screening task into subtasks mirrors how clinicians actually reason — affect first, then specific symptom probing.

---

## symptomAgent

**Purpose:** Identify specific anxiety-related symptom indicators from the text.

**Input:** User text with mode prefix.

**Output:** `{"possible_anxiety_indicators": ["excessive worry", "sleep disruption", "concentration difficulty"]}` — these map directly to DSM-5/ICD-11 GAD symptom clusters.

**Prompt strategy:** The agent is told to look for indicators consistent with generalised anxiety symptom clusters. It is told to be conservative — only include signals that are clearly present.

**Potential limitations:** The agent can reproduce user sentences rather than abstracting them. This is now partially mitigated by the LLM's Supporting Findings rewrite step, but the underlying claim quality depends on Mistral's instruction-following.

---

## contextAgent

**Purpose:** Identify psychosocial stressors and contextual factors.

**Input:** User text with mode prefix.

**Output:** `{"contextual_stressors": ["academic pressure", "interpersonal conflict"]}`.

**Why it exists:** Context changes interpretation. High GAD-7 during exam week is contextually different from high GAD-7 with no apparent stressor. Including context improves the report's utility and is a key differentiator from tools that only process symptoms.

---

## referralAgent

**Purpose:** Make a safety-sensitive triage decision.

**Input:** User text with mode prefix. In social media mode, an additional conservative instruction is prepended.

**Output:** `{"risk_level": "low" | "moderate" | "urgent", "reasoning": "..."}`.

**Why it exists:** The referral assessment is logically separate from symptom detection. An urgent safety signal (suicidal ideation) should cut off normal report generation entirely, replacing it with a crisis resource notice. This agent provides the `riskLevel` that triggers that path.

**Design decision — urgent path bypass:** If `riskLevel === 'urgent'`, the report step immediately returns a hardcoded safety notice. No LLM generates any clinical content. This prevents the LLM from generating a "supportive" report for someone in crisis, which could delay help-seeking.

**Supervisor question:** *"How do you validate that the referral agent correctly identifies urgent cases?"*
**Answer:** Test case 9 is explicitly an urgent scenario (suicidal ideation text). We verify that the referral agent returns `urgent` and that the report body contains the safety notice without any generated clinical content. This is not probabilistic — the urgent bypass is deterministic once `riskLevel=urgent` is returned.

---

## retrievalAgent (RAG agent)

**Purpose:** For each validated claim, retrieve the most semantically similar chunks from the clinical knowledge base.

**Input:** Claims array with categories.

**Output:** Each claim paired with its top-k retrieved chunks, including text, source file, and cosine similarity score.

**Why it exists:** This is the core of the RAG approach. Without retrieval, the LLM generates evidence from its training data — which cannot be audited, cited, or updated. With retrieval, every clinical claim is anchored to a specific, citable chunk from a curated KB.

---

## validationAgent (evidence-validation-step)

**Note:** This is technically a step, not a Mastra agent — it runs deterministic logic, not an LLM call.

**Purpose:** Classify each retrieved chunk-claim pair by similarity threshold.

**Why deterministic?** The key academic contribution of this step is reproducibility. Two runs with identical inputs produce identical classifications. This is essential for any evaluation study.

---

## reportAgent

**Purpose:** Generate the Supporting Findings, Recommendation, and Limitations sections in readable, non-technical clinical language.

**Input:** Grouped claim labels (emotional signals, anxiety indicators, contextual factors), concern pattern, mode.

**Output:** Three markdown sections.

**Why the LLM generates Supporting Findings instead of TypeScript:** The raw claim texts from agents sometimes reproduce user sentences. A direct TypeScript dump would put user language into the clinical findings section. The LLM rewrites them into concise clinical labels ("persistent worry", "sleep disruption") without revealing user phrasing. TypeScript controls everything deterministic; the LLM handles only language transformation.

---

## Why multiple agents instead of one prompt?

This is a question you will definitely be asked. Have this answer ready:

1. **Separation of concerns:** Each agent has one job and one failure mode. Debugging "why did the report say X?" is tractable — I trace back through specific step outputs.
2. **Parallel execution:** The four extraction agents run concurrently, reducing latency by roughly 3x compared to sequential calls.
3. **Different prompt strategies:** The referral agent needs conservative, safety-first instructions. The emotion agent needs phenomenological sensitivity. One combined prompt would compromise both.
4. **Academic transparency:** Multi-agent decomposition maps onto the clinical assessment process — emotional state, symptom inventory, contextual factors, and safety assessment are discrete clinical tasks.
5. **Modularity:** I can swap any individual agent's model or prompt without affecting the others.

---

# PART 3 — RETRIEVAL

## How the KB was built

**Files:** `src/kb/*.txt`

Six knowledge base files were manually curated:

| File | Content |
|---|---|
| `anxiety_indicators.txt` | ICD-11 GAD criteria, excessive worry, somatic symptoms |
| `depression_indicators.txt` | ICD-11 depressive episode markers, anhedonia, depressed mood |
| `shared_symptoms.txt` | Symptoms appearing in both (sleep, concentration, fatigue, irritability) |
| `contextual_stressors.txt` | Academic stress, social pressure, workplace stress, financial stress |
| `anxiety_vs_depression.txt` | Differentiation guidance between the two presentations |
| `instrument_reference.txt` | GAD-7 instrument description, scoring reference |

Each chunk is structured: `CHUNK_ID`, indicator/symptom label, source (ICD-11, etc.), source type, description. Chunks are indexed using `src/kb/index-kb.ts` which embeds each chunk using `fastembed` (bge-small-en-v1.5) and stores vectors in LibSQLVector (a SQLite-backed vector database).

## How embeddings work

`bge-small-en-v1.5` (from BAAI via HuggingFace) converts text into a 384-dimensional vector representing semantic meaning. Two texts are "similar" if their vectors are close in this 384-dimensional space, measured by cosine similarity (the angle between them, normalised to 0–1).

Embedding happens **at index time** (once, when building the KB) and **at query time** (for each claim text during retrieval). The claim text is embedded and compared against all stored chunk embeddings in the relevant files.

## Category-based routing

Rather than searching the entire KB for every claim, claims are routed to relevant files based on their category. An `anxiety_indicator` claim only searches `anxiety_indicators.txt` and `instrument_reference.txt`. A `contextual_stressor` claim only searches `contextual_stressors.txt`. This improves precision and prevents, for example, an academic stress claim from retrieving depression chunks.

## Why RAG instead of relying on the LLM?

**Supervisor question:** *"Why not just ask the LLM to identify relevant clinical evidence from its training data?"*

**Answer — four reasons:**

1. **Auditability:** I can show exactly which KB chunk supported which claim, with a specific source. An LLM generating from training data produces no such trace.
2. **Hallucination prevention:** LLMs fabricate citations. The KB is ground truth — if it's not in the KB, it cannot be cited.
3. **Updateability:** Adding a new symptom profile or ICD-11 update requires only appending a text file and re-indexing. No fine-tuning, no retraining.
4. **Academic grounding:** The KB was built from peer-reviewed clinical sources (ICD-11 WHO 2025, Spitzer et al. 2006). This gives the system a defensible evidence base.

## How retrieval improves explainability

Every claim in the validated output can be traced to: the agent that produced it → the KB chunk that validated it → the source of that chunk. This chain is the explainability backbone. It answers "why did the system flag excessive worry?" with a specific clinical reference, not "because the LLM said so."

## Possible weaknesses

- The KB is small (approximately 30–40 chunks). It may not cover unusual presentations.
- `bge-small-en-v1.5` is a general-purpose embedding model, not fine-tuned for clinical text.
- The cosine thresholds (0.72/0.55) were set empirically, not validated against clinical ground truth.
- Retrieval quality depends on claim text quality — if the symptom agent produces poor claim text, the right KB chunk may not be retrieved.

---

# PART 4 — VALIDATION

## How claims are validated

`evidenceValidationStep` (`src/mastra/workflows/evidence-validation-step.ts`) takes the retrieval output (each claim paired with its top-k chunks and similarity scores) and classifies each pair:

```
cosine ≥ 0.72 → supported
cosine ≥ 0.55 → partially_supported
cosine < 0.55 → unsupported
```

Unsupported claims are excluded from the report. Supported and partially supported claims form the evidence pool.

## Why deterministic thresholds, not another LLM call?

**Academic answer:** Determinism enables reproducibility. Given identical inputs, the validation step always produces identical outputs. This is essential for any quantitative evaluation (precision, recall, AUC). An LLM validator would introduce variance across runs — two identical submissions could get different classifications.

**Practical answer:** The validation is essentially a semantic similarity decision. Cosine similarity is a principled, well-understood distance metric. An LLM would be doing the same thing less transparently.

## Differentiation assessment

The validation step also produces a `differentiationAssessment`: given the retrieved evidence, does the claim pattern lean toward anxiety, depression, both (comorbid), or is it unclear? This is computed by counting how many supported/partial claims came from anxiety-specific vs depression-specific vs shared KB files.

For most cases with limited evidence (minimal-concern profiles, social media analysis), the result is `unclear`. In the clinician report, `unclear` is always rendered as: *"Available information was insufficient to confidently distinguish anxiety-related symptoms from other possible conditions such as depression. Further clinical assessment would be required."*

## Evidence Agreement

Evidence Agreement compares the GAD-7 concern band against the text signal strength (proxied by validated symptom claim count):

```
GAD-7 band number vs text band number (diff = 0 → High, 1 → Moderate, ≥2 → Low)
```

Discordance flags override this: `high_gad7_low_text` and `low_gad7_high_text` always produce Low agreement.

For social media (no GAD-7), agreement is based on the ratio of supported+partially supported claims to total claims.

## Academic contribution of the validation layer

This is the step that distinguishes AnxioSense from a simple LLM chatbot. Every clinical claim in the output is:
1. Extracted by a specialist agent
2. Anchored to a curated clinical KB
3. Classified by semantic similarity
4. Labelled with a support confidence level

This creates an auditable, semi-deterministic evidence chain. Even if the LLM generates the final prose, the evidence underlying that prose was validated independently of the LLM.

---

# PART 5 — REPORT

## Which sections are deterministic (TypeScript-generated)

| Section | Source |
|---|---|
| **Assessment Overview** | TypeScript — mode label, GAD-7 block verbatim, discordance note |
| **Evidence Agreement** | TypeScript — concern level comparison, plain-language text |
| **Clinician Summary** | TypeScript — GAD-7 score, validated indicators, differential, assessment notes |
| **Urgent Safety Notice** | TypeScript — hardcoded, no LLM involved |

## Which sections come from the LLM

| Section | Source |
|---|---|
| **Supporting Findings** | LLM (reportAgent) — rewrites claim labels into clinical language |
| **Recommendation** | LLM (reportAgent) — concern-pattern-specific instructions |
| **Limitations** | LLM (reportAgent) — standard disclaimers |

## Why Supporting Findings changed

Originally, the TypeScript code built Supporting Findings by dumping `v.claimText` directly. The claim texts are whatever the symptom agent returned — which sometimes parroted the user's original sentence ("Everything is going alright...") or gave unabstracted labels ("happiness"). Clinical findings should read as assessor summaries, not user quotes. The LLM now receives the claim labels grouped by agent type and is instructed to rewrite them as concise clinical findings (5 words each, no user text). A TypeScript fallback handles the case where the LLM skips the section.

## Why clinician mode exists

The GAD-7 raw score (e.g., 19/21) and the clinical severity label (Severe) are not shown to users. Users see only the concern pattern label (High Concern Pattern). This is deliberate: raw scores without clinical context can cause anxiety, self-diagnosis, or misinterpretation. A supervisor or clinician reviewing the same report needs the raw data for clinical decision-making. The clinician mode flag appends this information in a clearly labelled restricted section.

## Why technical details are hidden from users

Chunk IDs, cosine similarity scores, and source_type labels are implementation metadata. They serve researchers and developers, not people seeking screening support. Exposing them would: (a) confuse and alarm users, (b) undermine trust in the tool, (c) create a misleading impression of clinical authority from a research prototype.

---

# PART 6 — GAD-7

## What GAD-7 is

The Generalised Anxiety Disorder 7-item scale (Spitzer et al., 2006) is a validated self-report instrument. Seven questions about how often the respondent has been bothered by anxiety-related experiences over the past two weeks. Each item scored 0–3. Total 0–21.

Published cutpoints (for clinical screening):
- 0–4: Minimal
- 5–9: Mild
- 10–14: Moderate
- 15–21: Severe

## Why we don't show "Minimal Anxiety — 5–9" to users

Clinical severity labels (Minimal/Mild/Moderate/Severe Anxiety) are interpretive labels designed for clinicians. Presenting a user with "Moderate Anxiety" without clinical context can cause distress, self-labelling, or (paradoxically) dismissal ("I'm only moderate, I don't need help"). The concern pattern labels (Minimal/Mild/Elevated/High Concern Pattern) communicate the same gradient without asserting a clinical category.

## Why journal requires GAD-7

The GAD-7 is the primary clinical signal. The written journal entry provides contextual enrichment. Running the analysis without GAD-7 in journal mode would produce a purely text-based report with no validated standardised anchor — which weakens the academic case for the system. It was also explicit supervisor feedback.

## Why social media bypasses it

Social media text is third-party, indirect, and produced by an unknown author for an unknown audience. The GAD-7 requires the respondent to self-assess over the past two weeks — this cannot be inferred from a public post. Applying GAD-7 scoring to social media text would be clinically invalid. Social media mode therefore relies entirely on linguistic and contextual indicators.

## Discordance cases

Two edge cases matter:

**High GAD-7, calm text (high_gad7_low_text):** The questionnaire flags severe anxiety (≥15) but the written text is minimal or positive. Possible explanations: (a) the person struggles to articulate distress in writing, (b) the text was written at a different time than the questionnaire was completed, (c) social desirability bias in text. The report notes this discordance in the Assessment Overview and gives it Low Evidence Agreement.

**Low GAD-7, anxious text (low_gad7_high_text):** The questionnaire is minimal (≤4) but the text contains many anxiety signals. Possible explanations: (a) situational anxiety about one event, (b) minimisation on the questionnaire, (c) the text describes someone else's situation. Report notes this with Low Evidence Agreement.

---

# PART 7 — FRONTEND

## React architecture

**Tech stack:** React 18, Vite (dev server), Material UI v5 (component library), React Router v6.

**State management:** No Redux or Zustand — all state is local React state (`useState`) or context. `AuthContext` is the only global context, holding `user`, `token`, `login()`, `logout()`, `loginWithGoogle()` functions.

## Pages

| Page | Route | Purpose |
|---|---|---|
| `LoginPage` | `/login` | Email/password + Google sign-in |
| `SignupPage` | `/signup` | Email/password + Google sign-in |
| `DashboardPage` | `/dashboard` | Mode selection cards + saved reports list |
| `AssessmentPage` | `/assess` | Text input + GAD-7 + options + submit |
| `ReportPage` | `/report/:id` | Full report display + export |

## Authentication flow

1. User submits email/password → `POST /api/auth/login` → server verifies bcrypt hash → returns JWT
2. Google → `GoogleLogin` component returns ID token credential → `POST /api/auth/google` → server verifies with `google-auth-library` `OAuth2Client.verifyIdToken()` → creates/finds user → returns JWT
3. JWT stored in `localStorage`. `AuthContext` reads it on mount via `useEffect`.
4. Every API call includes `Authorization: Bearer <token>` header. Express middleware validates with `jwt.verify()`.

## Why Google Sign-In uses ID token, not access token

The `GoogleLogin` component (from `@react-oauth/google`) returns an **ID token** — a signed JWT from Google containing the user's identity. This is verified server-side with `OAuth2Client.verifyIdToken()`. This is the secure approach. Access tokens (from `useGoogleLogin` implicit flow) are for calling Google APIs on behalf of the user — not what we need. ID tokens prove identity; access tokens grant capability.

## Clinician mode in the UI

A toggle in the Assessment page options section. When on, a purple "Researcher" chip appears. The `clinicianMode` boolean is sent to the backend and flows into the Mastra workflow, where it controls whether the Clinician Summary block is appended to the report.

---

# PART 8 — DATABASE

## Express + SQLite architecture

**File:** `server/src/db.ts`

`better-sqlite3` provides a synchronous SQLite interface (no async/await needed for DB operations). WAL (Write-Ahead Logging) mode is enabled for concurrent read performance. Two tables:

**`users`:**
```sql
id TEXT PRIMARY KEY,
email TEXT UNIQUE NOT NULL,
password_hash TEXT,           -- bcrypt, null for Google users
google_id TEXT,               -- null for email users
is_guest INTEGER DEFAULT 0,
created_at TEXT
```

**`reports`:**
```sql
id TEXT PRIMARY KEY,
user_id TEXT,
mode TEXT,
concern_pattern TEXT,
referral_level TEXT,          -- 'low' | 'moderate' | 'urgent'
summary TEXT,                 -- first 3 sentences of Assessment Overview
full_report TEXT,             -- complete markdown report
clinician_mode INTEGER,
created_at TEXT
```

## What is never stored

- `userText` (the journal entry or social media paste)
- `gad7Answers` (the individual item responses)
- Raw agent outputs
- Retrieval output

Only the structured result (report, metadata, summary) is persisted. This is a design choice with privacy implications.

## Authentication

- Passwords hashed with `bcrypt` (10 salt rounds).
- JWTs signed with `JWT_SECRET` from `.env`, expire in 7 days.
- Google users have no password hash — the `google_id` field links them to their Google account.
- Guest users (trying the tool without signing up) get a short-lived token with `isGuest: true`. Their reports are not saved.

## Current limitations

- SQLite is single-file, not suitable for multi-user production deployment.
- No report deletion endpoint.
- No pagination on the reports endpoint.
- No data export for the user.
- WAL files can corrupt if the process crashes mid-write (mitigated by the `reset-db.sh` script).

---

# PART 9 — ARCHITECTURE QUESTIONS (Abel asking you)

**Q: Why Mastra? Why not build the workflow yourself with plain OpenAI calls?**

Mastra provides: (a) typed step-to-step schema validation — if my output doesn't match the next step's expected input, it fails early with a clear error instead of silently passing garbage forward; (b) built-in parallelism (`.parallel()` runs agents concurrently); (c) a REST API out of the box for each workflow, so the Express server just calls HTTP endpoints; (d) future-proofing — Mastra has native support for memory, tools, and agents with long-term context that I can add without restructuring the pipeline.

**Q: Why not just use GPT-4 with one big prompt?**

Three reasons. First, explainability — a single LLM call produces a report but cannot explain which evidence validated which claim. Second, auditability — parallel specialist agents with structured JSON outputs can be individually inspected and evaluated. Third, the RAG layer requires a retrieval step that must happen between extraction and report generation; a single prompt cannot do this.

**Q: Why RAG? Why not fine-tune a model on clinical data?**

Fine-tuning requires labeled training data, compute, and a model that can be fine-tuned. RAG requires only a curated text corpus. More importantly, RAG is auditable — I can show which KB chunk grounded which claim. A fine-tuned model's reasoning is opaque. For a clinical research prototype, auditability outweighs model performance.

**Q: Why GAD-7 specifically?**

GAD-7 is the most widely validated brief screener for generalised anxiety disorder, cited in thousands of clinical studies and recommended by NICE, WHO, and most primary care guidelines. It has published sensitivity/specificity data (Spitzer et al. 2006, sensitivity 89%, specificity 82% for GAD at cutpoint ≥10). Using it gives the system a validated clinical anchor rather than a bespoke assessment.

**Q: Why concern patterns instead of the clinical severity labels?**

Clinical severity labels (Mild Anxiety, Severe Anxiety) are diagnostic language. This is a screening support tool, not a diagnostic tool. Presenting users with diagnostic language without clinical context can cause harm — either anxiety from over-pathologising normal experience, or false reassurance from under-pathologising genuine distress. The concern pattern labels communicate the gradient without asserting a clinical category.

**Q: How would this scale to many users?**

The current bottleneck is Mistral running locally on one machine. Scaling options: (a) migrate to a hosted model API (OpenAI, Anthropic, Mistral API); (b) replace SQLite with PostgreSQL; (c) add a job queue (BullMQ, Redis) so workflow runs are processed asynchronously; (d) deploy Mastra on a containerised server. The architecture does not fundamentally change — only the infrastructure under it.

**Q: How would memory work in future?**

Mastra has a native memory system. A user's past sessions could be summarised and passed as context to the extraction agents. The system could track symptom trajectory over time — did sleep disruption improve since last entry? This is a natural next step and one of the strongest future work contributions.

**Q: How would voice work?**

A voice input layer (Whisper for transcription) would convert speech to text before passing it to the existing pipeline. The pipeline itself would not change. The challenge is that voice transcriptions are often lower quality — more filler words, incomplete sentences — which may affect agent performance.

**Q: How would you handle privacy and data governance?**

Currently: raw text is never stored, only structured outputs. Future: formal privacy impact assessment, end-to-end encryption of stored reports, user data deletion endpoint, GDPR-compliant consent flow, and explicit statement that this is a research prototype not suitable for clinical use without formal validation.

---

# PART 10 — RESEARCH QUESTIONS

**Q: What is the novelty of AnxioSense?**

The novelty is the combination of: (a) multi-agent decomposition of the anxiety screening task; (b) RAG grounding of claims in a curated clinical KB; (c) deterministic validation layer with reproducible thresholds; (d) dual-mode operation (journal vs social media) with principled mode-specific logic; (e) concern pattern labels as a user-safe alternative to clinical severity labels. No published system combines all of these in a single explainable pipeline.

**Q: What is your research contribution exactly?**

A proof-of-concept architecture for **explainable, multi-source anxiety screening support** that integrates structured questionnaire data (GAD-7), unstructured self-report text (journal), and secondary text (social media) in a single pipeline with auditable evidence chains.

**Q: How would you evaluate this properly?**

A proper evaluation would require: (a) a dataset of journal entries with known GAD-7 scores and clinical annotations (ground truth); (b) precision and recall of the claim extraction pipeline against the ground truth; (c) agreement between the system's concern pattern and clinician-assigned severity (Cohen's kappa); (d) a user study measuring perceived usefulness, understandability, and emotional safety of the report. The nine test cases are a proof-of-concept evaluation, not a validation study.

**Q: What are the threats to validity?**

1. **Construct validity:** Concern patterns are operationalised from GAD-7 scores — but GAD-7 was not validated for use in multi-modal pipelines.
2. **Internal validity:** Cosine similarity thresholds (0.72/0.55) were set empirically without calibration against clinical ground truth.
3. **External validity:** All test cases were synthetic — real user text may behave very differently.
4. **Model bias:** Mistral may perform differently across demographic groups, languages, or writing styles.

**Q: What about false positives and false negatives?**

- **False positive:** System flags High Concern Pattern for someone who is well. Risk: unnecessary distress, over-medicalisation. Mitigated by the limitations disclaimer and the "concern pattern" framing (not diagnosis).
- **False negative:** System outputs Minimal for someone who is in distress. Risk: person does not seek help they need. Mitigated by (a) requiring GAD-7 as a standardised anchor, (b) the discordance detection that flags when text and questionnaire disagree.

The asymmetry matters: false negatives in mental health screening are more dangerous than false positives. The system's design leans conservative — defaulting to higher concern when ambiguous (the referral agent's default is `moderate`, not `low`).

**Q: What are the ethics considerations?**

1. This is a screening support tool, not a diagnostic or therapeutic tool. This must be stated clearly in every user interaction (it is, in the Limitations section).
2. The system should not be deployed as a clinical service without formal regulatory approval (CE marking in Europe, FDA clearance in the US for a SaMD — Software as a Medical Device).
3. User vulnerability: the tool may be used by people in distress. The urgent safety path addresses acute risk. Mild/moderate risk still requires careful language (no coping technique suggestions, no resource lists without clinical oversight).
4. Algorithmic bias: the KB was built from English-language, Western clinical sources. The system may not generalise to other cultural contexts.

**Q: How do the nine test cases relate to your evaluation?**

The nine test cases form a structured specification suite, not a validation dataset. They cover the four concern levels (minimal, mild, elevated, high) × mode (journal, social media) × edge cases (discordance, urgent). They were designed to verify that the pipeline behaves correctly for known inputs. They are not independent samples drawn from a population, so they cannot be used to estimate population-level performance metrics. This is an honest limitation to state.

**Q: What about the FUTURE of this work?**

1. Longitudinal tracking — monitoring symptom trajectory across sessions.
2. Validated clinical dataset — partner with a mental health service to collect consented journal entries with clinician annotations.
3. Fine-tuned embeddings — embed with a clinical-domain model instead of `bge-small-en-v1.5`.
4. Adaptive questioning — if the GAD-7 flags high, prompt additional questions about specific symptom domains.
5. Clinician dashboard — a separate interface where clinicians review aggregated anonymised patterns.
6. Multi-language support.

---

# PART 11 — WHAT STILL NEEDS TO BE DONE

## MVP limitations (things that are broken or incomplete right now)

- **No pagination** on the reports list endpoint.
- **No report deletion** — users cannot remove saved reports.
- **No profile management** — users cannot change password or delete account.
- **SQLite is not production-ready** for concurrent users.
- **Mistral:latest is local** — the system cannot work without Ollama running. Latency is 30–90 seconds per run.
- **KB is small** (~30–40 chunks). Unusual presentations may not retrieve relevant evidence.
- **No input validation** on `userText` length upper bound — very long texts could cause issues.
- **Guest mode** is functional but not polished — guest reports are not shown in a history.

## Research limitations (things the system does but shouldn't claim to do well)

- **The cosine thresholds (0.72/0.55) are empirically set**, not clinically validated.
- **Claim quality depends entirely on Mistral** — poor instruction-following leads to poor claims.
- **Supporting Findings are LLM-generated** — they cannot be guaranteed to accurately represent the validated claims in all cases.
- **Social media mode has no validated baseline** — there is no existing literature on applying GAD-7 equivalent screening to indirect text.
- **Evidence Agreement** uses a proxy (symptom claim count as text signal level) that is not validated against clinical ground truth.
- **The differentiation assessment** (anxiety vs depression) is computationally naive — it counts which KB files contributed claims. Clinical differentiation requires much richer reasoning.

## Future work (things the architecture supports but haven't been built)

- Longitudinal session memory and trajectory tracking.
- Clinician-facing dashboard with aggregate anonymised patterns.
- Formal evaluation dataset with clinical annotations.
- Integration with a validated PHQ-9 for co-occurring depression screening.
- Voice input (Whisper transcription).
- Multi-language KB and UI.
- Export to PDF.
- Notification system ("Check in again in 2 weeks").

## Nice-to-have features

- Dark mode in the frontend.
- Rich text journal editor with writing prompts.
- Session comparison view ("How does this compare to last month?").
- Accessibility audit and WCAG compliance.
- Admin dashboard for KB management (add/edit/delete chunks without editing text files).

---

# PART 12 — CHEAT SHEET

```
╔══════════════════════════════════════════════════════════╗
║            AnxioSense — Meeting Cheat Sheet              ║
╚══════════════════════════════════════════════════════════╝

ARCHITECTURE IN ONE SENTENCE
React frontend → Express server (port 3001) → Mastra multi-agent
workflow (port 4111, Mistral:latest via Ollama) → LibSQLVector (RAG)
→ SQLite (reports).

PIPELINE ORDER
parallel [emotion | symptom | context | referral]
  → buildClaims (Zod typed)
  → GAD-7 score + discordance detection (Map 2)
  → retrieval (fastembed + LibSQLVector)
  → evidence validation (deterministic cosine thresholds)
  → report (LLM: Supporting Findings + Recommendation + Limitations;
            TypeScript: Assessment Overview + Evidence Agreement + Clinician)

AGENTS
emotion      → {"emotions": [...]}
symptom      → {"possible_anxiety_indicators": [...]}
context      → {"contextual_stressors": [...]}
referral     → {"risk_level": "low|moderate|urgent"}
retrieval    → claims + top-k KB chunks per claim
validation   → supported / partially_supported / unsupported
report       → Supporting Findings + Recommendation + Limitations

GAD-7 BANDS
0–4   Minimal Concern Pattern     (Minimal Anxiety, users see: pattern label)
5–9   Mild Concern Pattern        (Mild Anxiety)
10–14 Elevated Concern Pattern    (Moderate Anxiety)
15–21 High Concern Pattern        (Severe Anxiety)
Users NEVER see "Severe Anxiety". Clinicians DO.

RETRIEVAL
Model:   bge-small-en-v1.5 (fastembed, 384d)
Store:   LibSQLVector (SQLite-backed)
Routing: category → KB file(s)
Thresholds: supported ≥0.72 | partial ≥0.55 | unsupported <0.55

EVIDENCE AGREEMENT
With GAD-7: |GAD-7 band num – symptom claim band num|
  diff=0 → High | diff=1 → Moderate | diff≥2 → Low
Without GAD-7: support ratio (KB match quality)
Discordance flags override: always Low

REPORT SECTIONS — WHO WRITES THEM
Assessment Overview   TypeScript (GAD-7 block verbatim + discordance)
Supporting Findings   LLM (clinical rewrite of claim labels)
Recommendation        LLM (concern-pattern-specific instructions)
Evidence Agreement    TypeScript (level comparison)
Limitations           LLM (standard disclaimer)
Clinician Summary     TypeScript (raw score + indicators + differential)
Urgent Safety Notice  TypeScript (hardcoded, no LLM)

DATABASE — WHAT'S STORED / NOT STORED
Stored: report id, user id, mode, concern pattern, referral level,
        summary (first 3 sentences), full_report (markdown), created_at
NOT stored: userText, gad7Answers, agent outputs, retrieval output

AUTH
Email: bcrypt (10 rounds) → JWT (7-day expiry)
Google: ID token → OAuth2Client.verifyIdToken() → JWT

MODES
journal:      requires GAD-7 · full clinical pipeline · personalised language
social-media: bypasses GAD-7 · extra conservatism · no questionnaire reference

DISCORDANCE
high_gad7_low_text:  GAD-7 ≥15, text claims ≤1 → Low agreement + Note
low_gad7_high_text:  GAD-7 ≤4, text claims ≥4  → Low agreement + Note

KEY DESIGN DECISIONS TO REMEMBER
1. Multi-agent = auditability, parallel execution, task decomposition
2. RAG = grounding in citable evidence, no hallucinated citations
3. Deterministic validation = reproducibility for research evaluation
4. TypeScript report assembly = LLM cannot corrupt deterministic content
5. Concern patterns ≠ clinical severity = user safety + responsible design
6. GAD-7 required in journal = standardised clinical anchor
7. Urgent path = hardcoded safety notice, LLM bypassed entirely
8. Raw text never stored = privacy by design

LIMITATIONS TO STATE CONFIDENTLY
- Thresholds empirically set, not clinically validated
- KB is small and English-only
- 9 test cases = specification test, not validation study
- Mistral local = no production deployment yet
- No longitudinal memory yet
- Supporting Findings can still inherit imprecise claim text

PAPERS TO MENTION IF ASKED
- GAD-7 validation: Spitzer et al. (2006) JAMA Internal Medicine
- ICD-11 GAD criteria: WHO (2025)
- bge-small embedding model: BAAI via HuggingFace
- RAG: Lewis et al. (2020) Retrieval-Augmented Generation for NLP

WHAT MAKES THIS NOVEL
Multi-agent + RAG + deterministic validation + dual-mode + GAD-7
integration in one explainable pipeline. No existing tool combines all of these.

HONEST STATEMENT IF PUSHED
"This is a research prototype demonstrating an explainable architecture
for anxiety screening support. It should not be used as a clinical tool
without formal validation against clinical ground truth. What it
demonstrates is that this architecture is feasible and that the
explainability chain is intact end-to-end."
```

---

*Good luck tomorrow, Aya. You built the whole thing — you know it better than anyone in that room. The answers are already in your head. This document just reminds you they're there.*

# AnxioSense — Engineering & Research Audit

**Date:** July 11, 2026  
**Scope:** Full repository audit across structure, security, Mastra cloud usage, project status, technical debt, research readiness, deployment readiness, and priority roadmap.  
**Constraint:** Observation only. No code changes made.

---

## 1. Repository Structure

### Major Folders

```
anxiosense/
├── data/                        # Vector DB (anxiosense-vectors.db + WAL) — gitignored ✅
├── drafts/                      # 2 old draft files — not gitignored ⚠️
├── frontend/                    # React + Vite + MUI app
│   └── src/
│       ├── pages/               # 5 pages (Assessment, Dashboard, Login, Report, Signup)
│       └── components/          # 4 components (Gad7Form, Layout, ReportCard, + Gad7Form is also under pages)
├── knowledge-base/              # 8 .txt KB files actually used for RAG indexing
├── prompts/                     # Prompt variants (baseline, cot, one-shot, cot-one-shot) for 6 agent types
├── server/                      # Express + SQLite backend
│   ├── data/                    # User DB (anxiosense.db + WAL) — gitignored ✅
│   └── src/                     # 4 core files + routes/ + middleware/
├── src/
│   ├── kb/                      # KB utilities: category routing, chunk filter, parser, types, vector store
│   ├── mastra/
│   │   ├── agents/              # 8 agent files (1 dead: weather-agent.ts)
│   │   ├── knowledge/           # anxiety-knowledge.ts (dead) + 2 RAG drafts
│   │   ├── public/
│   │   │   └── evaluation/      # 66 prompt experiment exports — SERVED OVER HTTP ⚠️
│   │   ├── tools/               # weather-tool.ts (dead)
│   │   ├── utils/               # workflow-session-store.ts
│   │   └── workflows/           # anxiosense-workflow.ts + backup + weather-workflow.ts (dead)
│   └── scripts/                 # index-knowledge-base.ts
└── [root]                       # package.json, .env (gitignored), .gitignore, tsconfigs
```

### Dead Code (confirmed unused)

| File | Issue |
|------|-------|
| `src/mastra/agents/weather-agent.ts` | Mastra template, zero AnxioSense references |
| `src/mastra/tools/weather-tool.ts` | Companion to weather-agent, also unused |
| `src/mastra/workflows/weather-workflow.ts` | Same — full template workflow |
| `src/mastra/knowledge/anxiety-knowledge.ts` | Hardcoded string constant KB, replaced by file-based RAG; never imported |
| `src/mastra/workflows/anxiosense-workflow.backup.ts` | Backup copy of workflow, in source control |
| `drafts/anxiosense-workflow-rag-draft.ts` | Old RAG draft |
| `drafts/validation-agent-rag-draft.ts` | Old validation draft |

### Structural Concerns

**Two separate KB directories exist:**
- `knowledge-base/` (root) — the 8 `.txt` files that are actually indexed by `src/scripts/index-knowledge-base.ts` via the `ANXIOSENSE_KB_DIR` env var defaulting to `./knowledge-base`
- `src/mastra/knowledge/` — contains only dead code (the string-constant KB and two draft files)

`referral_guidelines.txt` and `safety_boundary.txt` live in `knowledge-base/` and ARE indexed. However, `chunk-filter.ts` appears to filter out `SAFETY_RESTRICTED` chunks at index time — verify that `safety_boundary.txt` chunks flagged as restricted are being correctly excluded and not accidentally surfaced in retrieval.

**`prompts/` directory:** Contains full prompt variant files (baseline, CoT, one-shot, CoT+one-shot) for all six agent types. These are not imported by any agent — agents inline their prompts. This directory is research documentation, not runtime code. Should be clearly marked as such to avoid confusion.

**`src/mastra/public/evaluation/` (66 files):** These files sit inside Mastra's public assets directory. The Hono server running on port 4111 will serve them as static files at `http://localhost:4111/evaluation/prompt-experiments/runs/...`. While only accessible locally, this means any process on the machine can read full LLM output runs, potentially including test text containing mental health content. This directory should be moved outside of `src/mastra/public/`.

---

## 2. GitHub Readiness

### `.gitignore` Coverage

| Item | Covered? |
|------|----------|
| `node_modules/` | ✅ |
| `dist/` | ✅ |
| `.mastra/` | ✅ |
| `.env`, `server/.env`, `frontend/.env` | ✅ (`.env` pattern matches recursively) |
| `data/anxiosense-vectors.db` + WAL | ✅ (`*.db` and `*.db-*`) |
| `server/data/anxiosense.db` + WAL | ✅ |
| `.DS_Store` | ✅ |
| `*.duckdb`, `*.duckdb.*` | ✅ listed... but see below |
| `drafts/` | ❌ **NOT gitignored** |
| `AnxioSense-Supervisor-Prep.md` | ❌ **NOT gitignored** (untracked, will be added on next `git add .`) |
| `src/mastra/public/evaluation/` runs | ❌ **NOT gitignored** (untracked eval output files) |
| `prompts/` | ⚠️ Tracked intentionally (research docs), but confirm this is deliberate |

### Tracked Files That Should Not Be

`git status` shows `src/mastra/public/mastra.duckdb.wal` as **modified** (status `M`). This means a DuckDB WAL file was committed to the repository at some point. Even though `*.duckdb.*` is in `.gitignore`, the file was tracked before the ignore rule was added, so git continues to track it. It must be explicitly untracked:

```bash
git rm --cached src/mastra/public/mastra.duckdb.wal
```

Check whether the `.duckdb` base file itself is also tracked:

```bash
git ls-files src/mastra/public/
```

### Sensitive Content Risk

The `.env.example` file is committed (git ls-files confirms it). Confirm it contains only placeholder values and never real secrets. The actual `.env` files are correctly gitignored.

**If this repository goes public at any point**, run `git log --all --full-history -- ".env"` and `git log --all --full-history -- "*.db"` to confirm no secrets or databases were ever committed in history. Use `git-filter-repo` or BFG Repo Cleaner if any are found.

### Verdict

The repo is mostly git-safe but has three actionable items before any public push: untrack the `.duckdb.wal` file, gitignore `drafts/` and the evaluation run outputs, and audit the full commit history for any previously committed secrets or DB files.

---

## 3. Mastra Cloud Audit

### What Is Running Locally vs. in the Cloud

| Component | Where |
|-----------|-------|
| Mastra workflow runtime (Hono, port 4111) | **Local** |
| Ollama LLM (mistral:latest) | **Local** |
| fastembed (bge-small-en-v1.5) | **Local** |
| Vector store (LibSQL/SQLite) | **Local** |
| User database (SQLite) | **Local** |
| Mastra Observability / Telemetry | **☁️ CLOUD** |

### The Observability Problem

The root `.env` file contains:

```
MASTRA_PLATFORM_ACCESS_TOKEN=sk_yqO6THMFKX5iKDzcyrUrw3rk0sjSji0x7AJcObMGNadtfK
MASTRA_PROJECT_ID=de619289-5003-48df-ba60-b7bbff93f1b8
```

`@mastra/observability` is listed as a dependency. When this token is present, Mastra SDK sends workflow traces — which include step inputs and outputs — to Mastra's cloud platform at `projects.mastra.ai`. This means every workflow execution sends data to an external server, including:

- The full `userText` (user's mental health disclosure)
- Agent outputs (emotion analysis, symptom analysis, etc.)
- The assembled clinical report

**This is a critical research ethics concern.** If AnxioSense is used with real participants for any research study, you cannot send their data to a third-party cloud without explicit informed consent and IRB approval covering that data flow. The user-facing interface gives no indication that data leaves the local machine.

**Immediate action required:**
1. Remove the token from `.env` (already gitignored, but delete it from the file)
2. Or confirm with your institution's ethics board whether this is permissible
3. Add a `MASTRA_PLATFORM_ACCESS_TOKEN` check at startup that warns if observability is active

### Other Mastra-Cloud-Touching Packages

- `@mastra/duckdb` — DuckDB adapter, likely used for Mastra's internal run storage. The `.duckdb` files in `src/mastra/public/` are Mastra's local run database. These are local, but the WAL file tracking issue (Section 2) means they may have leaked to git history.
- `@mastra/memory` — installed but not visibly used in the main workflow. If it is active, it may cache agent memory in Mastra's cloud store if the observability token is present.
- `@mastra/evals` — installed, used for prompt experiments. Eval results appear to be written to `src/mastra/public/evaluation/`. Verify evals run locally and do not POST results to Mastra's platform.

### Weather Workflow / Agent

`weather-agent.ts` and `weather-workflow.ts` are registered in Mastra's index (if `src/mastra/index.ts` exports them). If so, they appear as live endpoints at port 4111. This is harmless for functionality but confusing and should be removed.

---

## 4. Project Status

### Component-by-Component Assessment

| Component | Status | Notes |
|-----------|--------|-------|
| Mastra multi-agent workflow | ✅ Working | 685-line monolith; functional but brittle in places |
| GAD-7 deterministic scorer | ✅ Complete | Enforced as required in journal mode |
| Parallel agent execution (emotion / symptom / context / referral) | ✅ Working | All four run in Map step |
| Claim building (`buildClaimsStep`) | ✅ Working | Fallback GEN-1 claim category fixed (anxiety_indicator) |
| RAG retrieval (category-routed) | ✅ Working | 8 KB files, bge-small-en-v1.5, cosine thresholds |
| Evidence validation step | ✅ Working | Supported / Partially Supported / Unsupported |
| Discordance detection | ✅ Working | high_gad7_low_text / low_gad7_high_text flags |
| Evidence Agreement section | ✅ Working | Band-comparison logic (High / Moderate / Low) |
| Report assembly (user-facing) | ✅ Working | Assessment Overview + LLM sections + Evidence Agreement |
| Clinician Summary block | ✅ Working | Gated behind clinicianMode; redesigned (no raw IDs/thresholds) |
| Social media mode (no GAD-7) | ✅ Working | Pipeline bypasses GAD-7 scorer; explicit statement in report |
| Frontend (React + MUI) | ✅ Working | All 5 pages rendered |
| Journal mode UI enforcement | ✅ Complete | Skip button removed; Run Analysis disabled without GAD-7 |
| Express auth server | ✅ Working | JWT + bcrypt + Google OAuth |
| Report persistence (SQLite) | ✅ Working | Reports saved per-user; dashboard loads history |
| Google OAuth | ✅ Working | Frontend + backend integrated |
| TypeScript compilation (frontend, server) | ✅ Clean | Zero errors in frontend/ and server/ |
| TypeScript compilation (agents) | 🟡 Pre-existing errors | All agents have `Expected 1 arguments, but got 2` on same pattern — pre-dates this session, does not affect runtime |
| Test suite | ❌ None | `"test": "echo Error: no test specified"` |
| Dead code removal | ❌ Not done | Weather agent/tool/workflow still present; anxiety-knowledge.ts unused |
| Mastra observability | ❌ Active with live token | Data leaving local machine — see Section 3 |

---

## 5. Technical Debt

### High Priority

**`anxiosense-workflow.ts` is 685 lines — monolithic.** The entire pipeline — GAD-7 scoring, discordance detection, claim mapping, retrieval coordination, report assembly, Evidence Agreement computation, clinician block construction, and report string concatenation — all lives in one file. This makes it extremely difficult to unit-test individual pipeline stages or reason about failure modes in isolation. The natural split would be: `gad7-scorer-step.ts`, `map2-step.ts` (discordance + concern pattern), and `report-assembler-step.ts`.

**Pre-existing TypeScript errors in all five agent files.** Every agent (`context-agent.ts`, `emotion-agent.ts`, `referral-agent.ts`, `report-agent.ts`, `symptom-agent.ts`) throws `Expected 1 arguments, but got 2` at the same call pattern. These do not prevent runtime execution (Mastra compiles separately), but they indicate the agents were written against an older Mastra SDK API that has since changed. This should be fixed before any serious code review or publication.

**`buildClaimsStep` generates `sessionId` as `session-${Date.now()}`.** `Date.now()` has millisecond precision. If two requests arrive within the same millisecond (possible under any load), they share a session ID and will corrupt each other's session store entries. This should use `uuid()`, which is already available in the server routes.

**In-memory session store is not process-safe.** `workflow-session-store.ts` uses a `Map<string, Partial<SessionData>>`. This works for single-process development but fails silently if Mastra ever runs multiple worker processes or if the server restarts mid-run. This is acceptable for MVP but must be addressed before any multi-user deployment.

### Medium Priority

**`extractFinalReport` uses recursive key traversal.** The function in `server/src/routes/workflow.ts` recursively walks the Mastra response object looking for a `finalReport` key at any nesting depth. This is brittle — if Mastra changes its response envelope shape or uses the same key name elsewhere, it will either silently return the wrong value or miss the report entirely. The workflow output schema should enforce a fixed shape that the server route can destructure directly.

**`pollRun` blocks server threads.** The polling loop runs for up to 150 seconds with `await setTimeout(3000)`. Express is single-threaded (without a worker pool). If multiple users run analyses simultaneously, each request holds an Express thread for the entire duration. This is not a problem for a one-user demo but is a scalability blocker.

**No input validation on `userText`.** There is a client-side check (`length < 20`), but the server route accepts `userText` of arbitrary length without sanitization or a maximum length cap. A 100,000-character input would be passed directly into the Ollama prompt context window, likely causing silent truncation or degraded output.

**`@mastra/fastembed`, `ai`, and `tsx` pinned to `latest`.** Non-reproducible builds. If any of these packages publish a breaking change, the project silently breaks on the next `npm install`. Pin to explicit versions.

### Low Priority

**No React error boundaries.** If the report renderer throws (e.g., an unexpected `concernPattern` value), the entire frontend crashes with a blank screen. A single `<ErrorBoundary>` wrapper around `<ReportPage>` would prevent this.

**No rate limiting on Express.** Auth routes (`/api/auth/register`, `/api/auth/login`) and the workflow route (`/api/workflow/run`) have no request rate limiting. Trivial to brute-force or spam.

**`server/reset-db.sh` is a committed script that deletes the database.** Acceptable for dev tooling, but should be in `.gitignore` or clearly documented as dev-only.

**66 evaluation export files not gitignored.** These are currently untracked but will be added to source control on the next `git add .`. They should be added to `.gitignore` or moved outside the repo.

---

## 6. Research Readiness

### Honest Assessment

AnxioSense is a well-constructed research prototype, not a validated clinical screening tool. The distinction matters enormously for how supervisors and reviewers will evaluate it.

**What the project demonstrates well:**
- A novel application of multi-agent LLM pipelines to mental health text screening
- Category-routed RAG retrieval that avoids the common failure mode of pulling depression chunks for anxiety profiles
- Integration of a validated instrument (GAD-7) with LLM-based text analysis, with deterministic scoring that cannot be hallucinated
- Discordance detection between self-report and text signal — this is a genuinely interesting research contribution
- Clean separation between user-facing reports and clinician-facing technical evidence

**What is missing before any research study with participants:**

*Ethics and consent:*
- No IRB/ethics board approval
- No informed consent flow in the UI
- No participant data agreement
- Mastra observability is active, sending user text to a third-party cloud — this alone may block ethics approval unless disabled
- The tool presents GAD-7 scores and concern patterns in a way that may be misinterpreted by lay users as clinical diagnoses

*Validation:*
- Zero formal evaluation has been run against a labelled dataset
- The 66 prompt experiment files are manual runs, not a systematic evaluation
- No inter-rater reliability, precision/recall, or F1 metrics for claim extraction
- No comparison baseline (e.g., GAD-7 alone vs. GAD-7 + text analysis)
- The cosine similarity thresholds (supported ≥0.72, partially ≥0.55) were set heuristically, not empirically calibrated

*Documentation:*
- No formal system card or model card describing limitations, failure modes, and intended use
- No data flow diagram showing exactly where user data goes (especially relevant given Mastra observability)

**For supervisor presentations:** Frame this as a proof-of-concept system demonstrating feasibility of the pipeline. The contributions are architectural (the multi-agent routing approach, the discordance detection mechanism) and the next step is formal evaluation with a labelled dataset, not deployment.

**For thesis / publication:** The research questions this system enables are more publishable than the system itself. Specifically: does adding LLM-based text analysis to GAD-7 scores improve sensitivity for detecting cases where self-report and free text disagree? The discordance detection feature is the most novel element.

---

## 7. Deployment Readiness

### Blockers (Must Fix Before Any Deployment)

**`JWT_SECRET=anxiosense-dev-secret-change-in-prod`** — The JWT secret is a known string committed in the repository (`server/.env` is gitignored, but the value is in the conversation history and session summaries). Before deployment, generate a cryptographically random secret: `openssl rand -hex 64`. Rotate any JWTs signed with the old secret.

**No HTTPS.** The frontend (`localhost:5173`), Express server (`localhost:3001`), and Mastra (`localhost:4111`) all run over plain HTTP. JWTs are transmitted in plain text over local loopback, which is acceptable for dev but unacceptable for any deployment.

**SQLite is not multi-user safe.** SQLite WAL mode handles concurrent reads well but single-writer semantics mean any concurrent write load (multiple users running analyses simultaneously) will serialize writes and may cause timeout errors. For even a small user study, PostgreSQL would be required.

**Mastra requires a local Ollama process.** The workflow depends on `ollama-ai-provider-v2` calling `mistral:latest` on the local machine. There is no fallback, no timeout handling for Ollama being unavailable, and no mechanism to run the Mastra workflow on a remote server. Any deployment must either bundle Ollama or switch to an API-based LLM provider.

**No environment variable validation.** The server starts without checking that `JWT_SECRET`, `MASTRA_URL`, or `GOOGLE_CLIENT_ID` are set. If any is missing, the failure mode is a cryptic runtime error rather than a clear startup message.

### Additional Gaps

- No Docker/containerization — three-process startup (`mastra dev`, Express server, Vite) is difficult to hand to another researcher
- No `docker-compose.yml` or equivalent
- No health check endpoint
- Frontend has no production build configuration tested (Vite builds to `dist/`, but there is no serving strategy documented)
- `.netlify` and `.vercel` are gitignored — no deployment config exists
- No logging infrastructure beyond `console.log`

### Current Realistic Deployment Target

A single researcher's machine running all three processes manually. This is appropriate for a research prototype being developed for supervisor demos. It is not appropriate for a user study, a workshop demo on unfamiliar hardware, or any form of external access.

---

## 8. Priority Roadmap

### Immediate (Before Any Further Demos or Research Use)

1. **Disable Mastra cloud observability** — remove `MASTRA_PLATFORM_ACCESS_TOKEN` from `.env` or set it to empty. Verify no data leaves the local machine during a workflow run.
2. **Untrack `mastra.duckdb.wal` from git** — run `git rm --cached src/mastra/public/mastra.duckdb.wal` and commit.
3. **Fix sessionId collision risk** — replace `session-${Date.now()}` with `uuid()` in `buildClaimsStep`.
4. **Add to `.gitignore`** — `drafts/`, `AnxioSense-Supervisor-Prep.md`, `src/mastra/public/evaluation/prompt-experiments/runs/`.
5. **Move evaluation exports** out of `src/mastra/public/` — they should not be HTTP-accessible.

### Short-Term (Before Any User Study or Ethics Submission)

6. **Delete dead code** — remove `weather-agent.ts`, `weather-tool.ts`, `weather-workflow.ts`, `anxiety-knowledge.ts`, `anxiosense-workflow.backup.ts`. Deregister the weather workflow from Mastra's index.
7. **Fix pre-existing TypeScript errors in all agents** — the `Expected 1 arguments, but got 2` pattern. These are likely caused by a Mastra SDK API change in how agent constructors are called.
8. **Add a server startup check** — validate that `JWT_SECRET`, `MASTRA_URL`, and `GOOGLE_CLIENT_ID` are set and non-default before the server accepts requests.
9. **Cap and sanitize `userText`** — enforce a maximum length (e.g., 5,000 characters) on the server side.
10. **Pin all `latest` dependencies** — replace `"latest"` with explicit versions for `@mastra/fastembed`, `ai`, and `tsx`.

### Medium-Term (Before Thesis Writing or Publication)

11. **Design a formal evaluation protocol** — curate or annotate a labelled dataset of journal entries with known anxiety indicators. Run the pipeline against it. Report precision, recall, and F1 for claim extraction and concern pattern classification.
12. **Calibrate cosine thresholds empirically** — the 0.72/0.55 split was set heuristically. Evaluate against the labelled dataset to find optimal thresholds.
13. **Extract report assembly into a testable module** — split `anxiosense-workflow.ts` so the report building logic can be unit-tested without running the full workflow.
14. **Draft a system card** — document what the tool does, what it doesn't do, known failure modes (it cannot detect context-dependent anxiety, it is not a diagnostic tool), and intended use.
15. **Write a consent flow** — even for a research pilot, users should be explicitly told what the tool does, where their data goes, and what the output means.

### Long-Term (Deployment or Multi-User Study)

16. **Replace SQLite with PostgreSQL** for the user database.
17. **Containerize** — `docker-compose.yml` covering Mastra, Express server, and frontend build.
18. **Add HTTPS** — either via a reverse proxy (nginx + Let's Encrypt) or a managed hosting platform.
19. **Replace polling with webhooks or SSE** — the current 150-second poll loop is a scalability blocker.
20. **Implement proper logging** — replace `console.log` with a structured logger (e.g., pino) that writes to a file for post-hoc analysis.

---

## Summary

AnxioSense is a functional and architecturally coherent research prototype. The core pipeline works. The GAD-7 integration is sound. The dual-mode design is well-reasoned. For a solo research project at this stage, the implementation is solid.

The three things that need immediate attention before anything else:

1. **Mastra cloud observability is active** — user mental health text is being sent to a third-party service. This must be disabled before any use with real participants.
2. **A DuckDB WAL file is tracked in git** — a database file with potential run data has been committed to version history.
3. **No formal evaluation exists** — the system has never been tested against labelled data. Every claim about system performance is currently theoretical.

Everything else is standard research-prototype debt that can be addressed incrementally as the project matures toward a study or publication.

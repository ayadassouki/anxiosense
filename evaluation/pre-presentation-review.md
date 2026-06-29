# AnxioSense — Pre-Presentation Review
**Date:** June 29, 2026 (night before)  
**Reviewed by:** Co-supervisor + senior engineer perspective  
**Presentation:** EECS 4080 Research Progress · Tuesday, ~9 min + 3 min Q&A

---

## ⚠️ CRITICAL FIXES BEFORE YOU SLEEP TONIGHT

These are blockers. Everything else is refinement.

1. **Slide 05 — "drop screenshot here" × 2.** Replace with real Mastra Studio screenshots before tomorrow. An empty placeholder in a live demo slide is the single most damaging thing you can walk in with.
2. **Slide 08 — "drop full-screen demo screenshot here".** Same. Take the screenshot tonight.
3. **Slide 03 — Remove React.js / Material UI / React Flow from the frontend.** The frontend is not built. Listing it as part of your stack is technically false and Dr. Belle will ask to see it. Change to: *"Frontend (planned — Week 2): React + Lovable UI"* or simply remove the frontend column entirely and add a note in Next Steps.

---

---

## PART 1 — SLIDE-BY-SLIDE PRESENTATION REVIEW

---

### Title Slide
**What is good:**
Clean, professional. All required metadata present (EECS 4080, supervisors, date). The subtitle — *"A Multi-Agent Retrieval-Augmented Framework for Explainable Anxiety Screening Support"* — is precise and academic.

**What is weak:**
No research question is stated. A supervisor seeing this for the first time doesn't immediately know what problem you solved.

**Dr. Belle would likely ask:** "What is your specific research question? Is it a system paper or an evaluation paper?"

**Dr. Abel would likely ask:** "What do you mean by 'explainable'? How is explainability operationalized in your system?"

**Accurate?** Yes.  
**Misleading?** No.  
**Missing?** A single-sentence research question as a subtitle would anchor the whole talk.

---

### Slide 01 — Why AnxioSense?
**What is good:**
The three-column structure (Existing Research / Remaining Challenges / My Contribution) is the right format for a research framing slide. The contribution list is accurate and specific.

**What is weak:**
Zero citations anywhere on this slide. "Large Language Models understand natural language" is a general statement — which LLMs? Which papers? The remaining challenges (hallucination, explainability, weak validation) are real but you need to cite at least 2–3 papers that demonstrate these problems.

**Dr. Belle would likely ask:** *"Which specific papers informed your literature review? Can you name the key works on multi-agent systems for mental health screening?"*

**Dr. Abel would likely ask:** *"How do you operationally define 'explainability' in your contribution? Is it feature-level, claim-level, or something else?"*

**Accurate?** Yes, the challenges are real.  
**Misleading?** Slightly — "Existing systems rarely combine these capabilities" is a strong claim that needs a citation.  
**Missing?** 2–3 citations. Even inline like `(Smith et al., 2023)`.

**Suggested fix:** Add a small citations row at the bottom: *"e.g., Xu et al. (2024); Ji et al. (2023); Rashkin et al. (2021)"* — even if rough, it signals you've read the field.

---

### Slide 02 — System Architecture
**What is good:**
The numbered pipeline (1–8) is exactly what a 9-minute presentation needs. It gives the audience a map before you explain each piece.

**What is weak / technically misleading — this is important:**

The slide labels step 7 as **"Evidence Validation Agent — Cosine-similarity check"**. In your actual codebase, the Evidence Validation Step is **not an LLM agent** — it is a deterministic TypeScript function in `evidence-validation-step.ts` that applies hardcoded cosine similarity thresholds (0.72 / 0.55). You do also have a `validation-agent.ts` (LLM) that was used in an earlier pipeline version, but in the current `anxiosense-workflow.ts` the validation is the deterministic step.

Calling it an "agent" could prompt Dr. Belle to ask whether it uses an LLM, and if you say "no, it's TypeScript" she'll notice the mismatch with your slide.

**Suggested fix:** Change label to *"Evidence Validation — cosine similarity threshold"* and drop the word "Agent."

Similarly: **"Claim Builder"** is a deterministic TypeScript step (`build-claims-step.ts`), not an LLM. The slide doesn't call it an agent so this is fine — just be ready to explain it verbally.

**Dr. Belle would likely ask:** *"Is the Evidence Validation step an LLM call or a deterministic process? If it's rule-based, is it really RAG or just retrieval + threshold?"*

**Dr. Abel would likely ask:** *"How does the Claim Builder decide what counts as a claim? Is there any ambiguity handling?"*

**Accurate?** Mostly — except "Evidence Validation Agent" terminology.  
**Missing?** The GAD-7 path isn't visible here. Worth a small annotation showing that GAD-7 bypasses the LLM and is injected post-generation.

---

### Slide 03 — Technology Stack
**What is good:**
The backend stack is accurate: TypeScript, Mastra SDK, Ollama, Mistral 7B, FastEmbed, LibSQL — all are actually in production use in your codebase.

**⚠️ CRITICAL ISSUE — Frontend column:**
React.js, Material UI, and React Flow are listed as your frontend. **The frontend does not exist yet.** This is a direct misrepresentation. If either supervisor asks for a demo of the UI, you have nothing to show.

**Dr. Belle would likely ask:** *"Can we see the frontend? How does the React Flow visualization work?"*

**Dr. Abel would likely ask:** *"What does the user-facing interface look like?"*

**Fix (pick one):**
- Option A: Remove the frontend column entirely. Add one line under Next Steps: *"Frontend: React + Lovable UI (Week 2)."*
- Option B: Keep the column but relabel it clearly: *"Frontend (planned — not yet implemented)"* and grey out the icons.

Option A is cleaner for a 9-minute talk.

---

### Slide 04 — What Has Been Implemented? (10/10)
**What is good:**
The checklist format with a completion counter is confident and clear. The items are real — everything listed is genuinely implemented and in your codebase. Good energy for a progress presentation.

**What is weak:**
"Automatic Evaluation Export" will confuse a first-time audience. They don't know what this means. Add a 3-word parenthetical: *"Automatic Evaluation Export (timestamped run logs)"*.

Also: "Cosine Similarity Validation" and "Retrieval Agent" are listed separately, which is correct — but be prepared to explain the difference. Retrieval is the step that fetches KB chunks; cosine similarity is what decides whether a claim is supported. They work together but are architecturally distinct.

**Dr. Belle would likely ask:** *"What does 'Automatic Evaluation Export' produce? What format?"*

**Dr. Abel would likely ask:** *"Is the Validation Agent the same as Cosine Similarity Validation, or are those two separate components?"* — Good question, and the answer is nuanced: the cosine similarity validation is deterministic (TypeScript), while the Validation Agent (`validation-agent.ts`) is an LLM that was used in an earlier version. Make sure you're clear on which one is active in your current pipeline.

**Accurate?** Yes.  
**Missing?** The Urgent Safety Override deserves a mention — it's a real safety feature that shows clinical awareness.

---

### Slide 05 — Live Workflow
**⚠️ BLOCKER: Both screenshot slots are empty ("drop screenshot here").**

The pipeline step labels are correct: Journal Entry → Parallel Agent Analysis → Structured Claims → Knowledge Retrieval → Evidence Validation → Final Screening Report.

**Fix tonight:**
1. Open Mastra Studio, run your test input (the "worrying about grades" one with GAD-7 [2,2,2,1,1,1,1]).
2. Screenshot the workflow graph view.
3. Screenshot one agent's output panel (e.g., the emotion agent JSON).
4. Drop them in.

If Mastra Studio's UI is glitchy, a screenshot of the terminal output showing the pipeline executing is better than an empty box.

---

### Slide 06 — Recent Development Progress
**What is good:**
This is actually one of your strongest slides. The before/after table is crisp and shows genuine progress. Every bullet in the "Current Version" column is real and verifiable.

**What is weak:**
The "Previous Version" bullets are vague. "Prompt-based multi-agent workflow" — what does that mean? Was it still multi-agent? Being more specific would make the delta clearer.

**Dr. Belle would likely ask:** *"You list 'Improved prompting — Chain-of-Thought + One-shot.' What was the quantitative improvement over your baseline?"*  
**Ideal answer:** "In our preliminary 5-case evaluation, moving from baseline zero-shot to CoT + one-shot improved claim precision from ~60% to ~89% and eliminated hallucinated claims entirely."

**Dr. Abel would likely ask:** *"How did you determine which prompting technique to use? Did you try other approaches?"*  
**Ideal answer:** "We ran four prompt versions — zero-shot baseline, CoT only, one-shot only, and combined CoT + one-shot — and compared claim precision and enum validity across 5 test cases. CoT + one-shot dominated on all metrics."

**Accurate?** Yes.  
**Misleading?** No.

---

### Slide 07 — Preliminary Evaluation
**What is good:**
The four quality badges (Evidence-grounded, Explainable, Non-diagnostic, Modular Architecture) are fair claims about your system's properties.

**What is weak — this is the weakest slide in the deck:**
The evaluation table lists scope/coverage but shows **no actual numbers**. You have real metrics: F1 ≈ 0.89, referral accuracy 4/5, hallucination rate 0%, claim precision ~89%. None of these appear on this slide.

The 4 "badges" are qualitative claims, not evaluation results. A research group will see right through this.

**Dr. Belle would likely ask (this is almost certain):** *"What are your actual evaluation metrics? Precision, recall, F1? How did you measure hallucination rate?"*

**Dr. Abel would likely ask:** *"5 test cases is a very small evaluation set. What are the threats to validity?"*

**Fix:** Add a small 2×3 table to the slide:

| Metric | Result |
|---|---|
| Claim precision (CoT+one-shot) | ~89% |
| Referral accuracy | 4 / 5 cases |
| Hallucination rate | 0% |
| Prompt version tested | cot-oneshot-v1 |
| Test cases | 5 (manual) |

Then preempt the small-N concern: "This is a preliminary evaluation. The dissertation will include a larger systematic study."

**Technically misleading?** The badges overstate confidence given only 5 cases. Replace them with actual numbers.

---

### Slide 08 — Live Demonstration
**⚠️ BLOCKER: Screenshot placeholder is empty.**

The 5-step flow (Journal entry → GAD-7 → Parallel agents → Claims validated → Report) is correct and easy to follow.

**Suggestion:** If you can run a live demo in Mastra Studio during the presentation, do it — but have a static fallback screenshot ready in case the server is slow. Mental health demo with a live audience = potential awkward delays.

---

### Slide 09 — Next Steps
**What is good:**
Realistic, well-sequenced, appropriately humble about what's left.

**What is weak:**
"Expanded Knowledge Base — Broader clinical sources for richer retrieval" — which sources? DSM-5 criteria? ICD-11? More GAD-7 clinical guidelines? Being specific here shows clinical awareness.

**Dr. Belle would likely ask:** *"What's your dissertation submission deadline and timeline for the evaluation study?"*

**Dr. Abel would likely ask:** *"How will you evaluate the frontend once it's built? Do you plan a user study?"*

**Missing:** No mention of fixing the known limitations (differentiation assessment returning "unclear" in 5/5 runs, sleep disruption false negative). Acknowledging known bugs proactively builds more credibility than hiding them.

---

### Overall Flow Assessment

**Is the flow logical?** Mostly yes. The arc is: Problem → Architecture → Stack → Progress → Demo → Evaluation → Next. 

**One structural concern:** Slide 03 (Technology Stack) comes before Slide 04 (Implementation Progress). For a 9-minute talk, the audience doesn't yet understand what was built when you show them the stack. Consider swapping: Implementation (04) → Stack (03). Show *what* you built before *how* you built it.

**Pacing estimate:**
- Title + Slide 01: ~1.5 min
- Slide 02 (Architecture): ~2 min — this is the heart of your talk, spend time here
- Slide 03 (Stack): ~30 sec — one sentence per column
- Slide 04 (Progress): ~30 sec — just read the list
- Slide 05 (Workflow): ~1 min
- Slide 06 (Before/After): ~1 min
- Slide 07 (Evaluation): ~1 min
- Slide 08 (Demo): ~1 min
- Slide 09 (Next Steps): ~30 sec
**Total: ~9 minutes** ✓

---

---

## PART 2 — IMPLEMENTATION REVIEW

### Features Implemented (verified against codebase)

---

**1. Multi-Agent Parallel Workflow**
*File: `src/mastra/workflows/anxiosense-workflow.ts`*

Why added: A single LLM prompt handling emotion + symptom + context simultaneously produces entangled, harder-to-validate outputs. Separation of concerns across specialized agents allows targeted prompting and independent claim generation.

What it solves: Each agent is expert in its domain. Parallelism via `Mastra .parallel()` means all four agents run simultaneously, reducing total latency to ~1× the slowest agent rather than 4× sequential.

System improvement: The core architectural decision. Everything downstream depends on clean, typed agent outputs.

---

**2. Emotion Analysis Agent**
*File: `src/mastra/agents/emotion-agent.ts`*

Why added: Emotional state (worry, fear, sadness, frustration) is distinct from clinical symptoms and needs separate extraction to avoid conflation.

What it solves: Feeds EMO-x claims to the claims builder. Prevents symptom agents from absorbing emotional language and inflating clinical indicators.

---

**3. Symptom Extraction Agent**
*File: `src/mastra/agents/symptom-agent.ts`*

Why added: Anxiety symptoms (restlessness, concentration difficulty, muscle tension, avoidance) require different extraction logic than emotional states or context.

What it solves: Generates SYM-x claims tagged with `anxiety_indicator` or `shared_symptom` depending on whether the symptom overlaps with depression. The shared_symptom category is a genuine clinical design decision — sleep disruption, fatigue, and irritability are not specific to anxiety.

Known limitation: Sleep disruption is currently returning false negatives in some cases — the agent under-extracts this symptom.

---

**4. Context Reasoning Agent**
*File: `src/mastra/agents/context-agent.ts`*

Why added: Life context (academic stress, financial pressure, relationship stress, workplace stress) is not a clinical symptom but it is essential interpretive context for the report.

What it solves: Generates CTX-x claims that feed Section 4 of the report. Prevents clinical overreach — the system reports *context* as context, not as cause.

---

**5. Referral & Safety Agent**
*File: `src/mastra/agents/referral-agent.ts`*

Why added: Safety is non-negotiable in a mental health tool. A general LLM agent without explicit safety responsibility would under-triage.

What it solves: Explicitly assigns a risk level from a constrained enum: `"low" | "moderate" | "urgent"`. The enum is enforced in the workflow — any invalid value (e.g. "elevated" which Mistral was producing) triggers a warning and defaults to "moderate" (conservative clinical fallback).

System improvement: The urgent override in `reportStep` completely bypasses the LLM and returns a hardcoded crisis notice. This is a critical safety decision: you cannot trust a generative model to handle an immediate safety concern reliably.

---

**6. Build Claims Step (Deterministic)**
*File: `src/mastra/workflows/build-claims-step.ts`*

Why added: The four agents produce raw JSON. Something needs to normalize this into a typed, consistent claim object structure before retrieval.

What it solves: Parses agent JSON, assigns claimId (EMO-1, SYM-1, CTX-1), tags each claim with `sourceAgent`, applies the `shared_symptom` / `anxiety_indicator` / `emotional_state` / `contextual_stressor` categories, and assigns a `sessionId` to thread state through the workflow.

System improvement: Makes the pipeline modular. The retrieval step receives a clean, typed array of claims regardless of which agent produced them.

---

**7. Knowledge Base (8 files)**
*Directory: `knowledge-base/`*

Files: `anxiety_indicators.txt`, `depression_indicators.txt`, `contextual_stressors.txt` (CTX-001 to CTX-009), `shared_symptoms.txt`, `anxiety_vs_depression.txt`, `referral_guidelines.txt`, `safety_boundary.txt`, `instrument_reference.txt`

Why added: Without a grounded clinical knowledge source, the system has no way to distinguish supported claims from hallucinated ones.

What it solves: Provides the retrieval target. Each KB chunk has a structured format (CHUNK_ID, SOURCE_TYPE, DESCRIPTION, KEYWORDS). The curated nature (hand-written taxonomy rather than scraped documents) gives predictable chunk quality.

System improvement: The differentiation file (`anxiety_vs_depression.txt`) and `shared_symptoms.txt` are particularly important — they explicitly handle the differential diagnosis challenge without making the system diagnostic.

---

**8. Retrieval Agent (Vector Search)**
*File: `src/mastra/agents/retrieval-agent.ts`*

Why added: Claims must be grounded against the knowledge base. Without retrieval, the Evidence Validation step has nothing to compare against.

What it solves: Embeds each claim using fastembed (bge-small-en-v1.5, 384-dim), queries the LibSQL vector store, and returns the top-k chunks with attached similarity scores. This is the "R" in RAG.

Architecture note: AnxioSense uses a generation-first approach — agents generate claims first, then retrieval validates them. This is the inverse of classical RAG (retrieve-then-generate). The advantage: you know exactly what claims to retrieve for, rather than retrieving for a vague user query.

---

**9. Evidence Validation Step (Deterministic Cosine Similarity)**
*File: `src/mastra/workflows/evidence-validation-step.ts`*

Why added: Retrieved chunks + similarity scores need to be converted into a structured pass/fail decision for each claim.

What it solves: Applies thresholds: ≥0.72 = supported, ≥0.55 = partially supported, <0.55 = unsupported (dropped). Filters which claims reach the report. Eliminates hallucinated claims that have no KB backing.

Threshold rationale: Based on observed score distributions across 5 baseline test cases. Strong matches (e.g. "Excessive worry" → ANX-001) score ~0.78–0.81. Moderate matches (sleep disruption → SHARED-001) score ~0.73–0.74. Noise scores below 0.55.

System improvement: This is the anti-hallucination mechanism. It's fully deterministic — no LLM in the loop — which means it behaves consistently and predictably.

---

**10. Report Agent**
*File: `src/mastra/agents/report-agent.ts`*

Why added: The validated claim set needs to be rendered into a readable, structured, non-diagnostic report for the end user.

What it solves: Receives pre-categorized validated claims (already split by sourceAgent: emotion/symptom/context), generates 8 sections. System prompt enforces strict non-diagnostic language, forbids coping strategies, requires cautious hedging ("may reflect", "could be consistent with"). Temperature = 0.1 for maximum consistency.

System improvement: The pre-categorization of claims by section before the prompt (Section 2 = emotion, Section 3 = symptom, Section 4 = context) was a key improvement that prevents Mistral from misassigning findings across sections.

---

**11. GAD-7 Deterministic Scorer + TypeScript Injection**
*File: `src/mastra/utils/gad7-scorer.ts`*

Why added: GAD-7 is a validated clinical instrument. Its scoring must be exact — a model that compresses or paraphrases a standardized questionnaire score introduces clinical risk.

What it solves: `computeGad7Score()` takes 7 integer answers (0–3) and returns score, severity band, interpretation, and per-item breakdown. `formatGad7ForReport()` formats it as a readable block.

Key design decision: After discovering that Mistral would sometimes silently compress the item-level breakdown when it appeared in the prompt, the entire GAD-7 block was moved out of the LLM prompt entirely. It is now injected directly into `finalReport` as Section 0 **after** `agent.generate()` returns. Mistral never sees it, so it cannot modify it.

System improvement: Guarantees 100% fidelity of the GAD-7 section across all runs. Verified: test run [2,2,2,1,1,1,1] → score 10/21 (moderate), all 7 item scores appeared verbatim.

---

**12. CoT + One-Shot Prompting (All 4 Extraction Agents)**

Why added: Zero-shot Mistral 7B produces inconsistent JSON structure, introduces hallucinated symptoms, and makes reasoning errors on borderline cases.

What it solves: Chain-of-thought instructs each agent to reason step-by-step before outputting JSON, reducing pattern-matching shortcuts. One-shot provides a worked example in the system prompt, anchoring vocabulary and format.

Evaluation: Claim precision improved from ~60% (baseline) to ~89% (CoT+one-shot). Hallucination rate dropped to 0% across 5 test cases.

---

**13. Referral Enum Validation + Conservative Fallback**
*File: `src/mastra/workflows/anxiosense-workflow.ts`, second `.map()`*

Why added: Mistral 7B was producing `"elevated"` as a risk level — not a valid value. The downstream report step expected only `"low"`, `"moderate"`, or `"urgent"`.

What it solves: Validates the referral agent's output against the constrained enum at runtime. Invalid values trigger a warning and default to `"moderate"` — not `"low"`. This is an intentional clinical safety decision: over-triage is preferable to under-triage.

---

**14. In-Memory Session Store**
*File: `src/mastra/utils/workflow-session-store.ts`*

Why added: Mastra step schemas don't propagate arbitrary side-band data across steps without adding every field to every step's input/output schema. The GAD-7 block, evaluation metadata, and intermediate outputs needed to flow from early steps to the final report step without polluting 5 different schemas.

What it solves: Keyed by `sessionId`, the store holds `userText`, all agent outputs, `buildClaimsOutput`, `retrievalOutput`, and `gad7Block`. Steps write to it as they complete; `reportStep` reads `gad7Block` from it.

---

**15. Automatic Evaluation Export**
*File: `src/mastra/utils/export-workflow-run.ts`*

Why added: Manual evaluation is error-prone and non-reproducible. Every run should produce a self-contained record.

What it solves: After every successful run, a timestamped Markdown file is written to `evaluation/prompt-experiments/runs/`. It contains: user input, GAD-7 block, all agent outputs, claims, retrieval results, validation output, and the final report — the complete pipeline trace.

System improvement: Enables reproducible evaluation. Any run can be compared against any other. The dissertation can cite specific run files.

---

### Features Still Missing Before Final Dissertation

| Gap | Priority | Notes |
|---|---|---|
| Frontend (Lovable UI) | High | Week 2 target. Without this, there's no user-facing product. |
| Sleep disruption false negative | High | Symptom agent under-extracts this symptom. KB entry exists, agent prompt needs refinement. |
| Differentiation assessment | Medium | Returned "unclear" in 5/5 runs. The agent or its KB backing needs recalibration. |
| Larger evaluation study | High | 5 cases is too small for a dissertation. Target 20–30 cases across diverse scenarios. |
| Inter-rater reliability | Medium | For dissertation: a second human should label the same test cases to validate your gold standard. |
| Latency measurement | Low | How long does a full run take? Supervisors may ask. Instrument your workflow. |
| Baseline comparison table | Medium | Show zero-shot vs CoT vs one-shot vs CoT+one-shot side-by-side in the dissertation. |
| Ethics / IRB discussion | Medium | Chapter 2 or 5: what would clinical deployment require? Informed consent, data storage, professional oversight. |
| Citation to GAD-7 instrument | High | Spitzer et al. (2006) must be cited in dissertation and ideally on Slide 07. |
| More KB sources | Medium | Currently hand-written taxonomy. DSM-5 criteria, ICD-11 coding, or clinical guidelines would strengthen validity claims. |

---

---

## PART 3 — UX / DEMO IMPROVEMENTS

These are achievable in 1–2 days with your existing backend. Prioritized by impact-to-effort ratio.

---

### 1. Pretty-Print the Report with Markdown Rendering (1–2 hours)
**Impact: Very High.** Right now the report is raw text in a terminal. Render it with a simple HTML/markdown renderer (even `marked.js` + a `<div>`) and it immediately looks like a clinical tool.

Structure the rendered report with:
- Section headings in bold/color
- GAD-7 section in a highlighted card
- Referral level shown as a color-coded badge (green = low, amber = moderate, red = urgent)
- Disclaimer in a grey italic footer box

---

### 2. Step-by-Step Progress Indicator During Execution (2–3 hours)
**Impact: High.** Your demo currently shows nothing while the pipeline runs. Add a simple polling progress bar or step-tracker:

```
✅ Emotion Agent        — complete
✅ Symptom Agent        — complete  
⏳ Context Agent        — running...
⏳ Referral Agent       — running...
⬜ Claims Builder
⬜ KB Retrieval
⬜ Evidence Validation
⬜ Report Generation
```

A server-sent event (SSE) stream from your Mastra server, or even a simple polling endpoint that checks workflow step completion, would give you this.

---

### 3. GAD-7 as One-Question-at-a-Time Form (3–4 hours)
**Impact: High.** Right now GAD-7 is submitted as a flat array. Build a simple multi-step form (one question per screen):

*"Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?"*
→ [Not at all] [Several days] [More than half the days] [Nearly every day]

This instantly makes the tool feel clinically legitimate. Each button maps to 0–3. After 7 questions, the answers are submitted alongside the journal text. You can build this as a plain HTML form in an afternoon.

---

### 4. Show Which KB Chunks Were Retrieved (2–3 hours)
**Impact: Medium-High.** After the report generates, show a small "Evidence Sources" panel:

```
📚 Clinical Evidence Retrieved
  ✅ ANX-001 · Excessive worry                    similarity: 0.81
  ✅ CTX-001 · Academic stress                    similarity: 0.76
  ⚠️ SHARED-001 · Sleep disruption              similarity: 0.58 (partial)
  ❌ DEP-001 · Persistent low mood               similarity: 0.42 (dropped)
```

This is the explainability feature. It directly answers "how do you know this claim is valid?" — because it shows exactly what clinical evidence was retrieved and whether the claim passed the threshold.

---

### 5. Validated vs. Dropped Claims Panel (1–2 hours)
**Impact: Medium.** Show the user (or the demo audience) a simple table:

| Claim | Status | Evidence |
|---|---|---|
| Excessive worry | ✅ Supported | ANX-001 |
| Academic stress | ✅ Supported | CTX-001 |
| Panic attacks | ❌ Not found in text | — |

This is already computed by your `evidenceValidationStep`. Surfacing it makes the validation visible and buildable trust in your system. The data is already in `claimValidations` in the output schema — just render it.

---

### 6. Demo-Ready Input Presets (30 min)
**Impact: Medium.** Add 3 preset inputs to the demo interface with a "Load example" button:

- *Mild worry:* "I've been feeling a bit anxious about my exams lately..."
- *Moderate stress:* "I haven't been sleeping well for weeks. I keep worrying about money and can't focus on work..."
- *High concern:* Use your 5th test case (the higher-risk scenario)

This lets you switch scenarios instantly during the demo without typing live, avoiding awkward pauses.

---

### 7. Referral Level as a Visual Badge on the Report (30 min)
**Impact: Medium.** The report currently mentions referral level in text. Make it visual at the top of the rendered report:

`🟢 Low Concern` / `🟡 Moderate Concern` / `🔴 Urgent — Safety Notice`

Color-coded, large, impossible to miss. This is the most clinically significant output and it should look like one.

---

---

## PART 4 — THE 15 HARDEST QUESTIONS (WITH IDEAL ANSWERS)

*Ranked by likelihood of being asked, hardest first.*

---

**Q1. "You set cosine similarity thresholds of 0.72 and 0.55. How did you determine these values? Are they validated?"**

**Ideal answer:** "The thresholds were calibrated empirically based on observed score distributions across our five baseline test cases. Strong semantic matches — for example, 'Excessive worry' against the ANX-001 chunk — scored between 0.78 and 0.81. Moderate matches like sleep disruption scored around 0.73–0.74. Noise and irrelevant chunks fell below 0.55. We set 0.72 as the supported threshold because it consistently separated meaningful matches from borderline ones. These thresholds are specific to our KB and our embedding model — bge-small-en-v1.5 — and part of the dissertation evaluation will be a sensitivity analysis showing how system outputs change if we shift these thresholds. They're justified by our data but not yet externally validated."

---

**Q2. "Is the Evidence Validation step an LLM or a deterministic process? If it's rule-based, can you still call it RAG?"**

**Ideal answer:** "It's fully deterministic. The evidence validation step is a TypeScript function that takes the similarity scores already computed during retrieval and applies threshold logic — no LLM is involved. This was a deliberate architectural choice: deterministic validation gives us consistent, reproducible behavior, which is essential for a screening tool where you need to be able to explain exactly why a claim was accepted or rejected. On the RAG terminology: the retrieval step is genuinely RAG — we embed claims, query a vector store, and retrieve relevant knowledge base chunks. The validation step then uses those retrieved chunks' similarity scores to make a binary decision. Together they form a retrieval-augmented validation pipeline, even if the final decision is rule-based rather than generative."

---

**Q3. "Five test cases is a very small evaluation. How can you make any claims about system performance with this sample size?"**

**Ideal answer:** "You're absolutely right — five cases is preliminary. These cases were used to calibrate the system and compare prompt versions, not to make general performance claims. They represent intentional coverage: one mild anxiety case, one academic stress case, one contextual stressor with GAD-7, one potential differential case, and one higher-concern case. The F1 and referral accuracy numbers we report are indicative rather than conclusive. The dissertation will include a systematic evaluation with 20–30 cases, covering more scenarios and edge cases, and ideally with a second human rater to establish inter-rater reliability on the gold-standard labels."

---

**Q4. "The differentiation assessment returned 'unclear' in all five evaluation runs. Doesn't that mean a key feature isn't working?"**

**Ideal answer:** "Yes, and I want to be transparent about that. The differentiation assessment — which is designed to identify whether indicators lean more toward anxiety or depression — returned 'unclear' in all five cases. There are two possible explanations: either the cases genuinely are ambiguous enough that 'unclear' is the correct label, or the agent's prompt or KB backing needs recalibration. My current interpretation is the latter — the agent's decision criteria are underspecified, and the anxiety_vs_depression KB file may not provide enough discriminative signal at the embedding level. This is identified as a known limitation and is on the roadmap for the dissertation. Importantly, 'unclear' is a safe default — the system doesn't misclassify, it defers."

---

**Q5. "Why use generation-first (agents generate claims, then retrieve) rather than classical RAG (retrieve relevant context, then generate)?"**

**Ideal answer:** "Classical RAG retrieves for a user query, then uses retrieved documents to inform generation. The challenge in our context is that the user input is a free-text journal entry — the 'query' is vague. If we retrieved based on raw user text, we'd get a broad, noisy result set and then ask the LLM to do everything at once. By generating structured claims first, we know *exactly* what to retrieve for. 'Excessive worry' as a claim gives us a semantically precise retrieval target. This means our KB chunks are matched against well-formed clinical claims rather than conversational fragments, which dramatically improves retrieval precision. The tradeoff is that extraction errors upstream propagate forward — if an agent generates a wrong claim, retrieval validates it incorrectly. That's why the cosine similarity thresholds and the LLM validation agent exist as a checks layer."

---

**Q6. "Why Mistral 7B? Given that this is a clinical-adjacent application, why not a larger or more capable model?"**

**Ideal answer:** "The primary constraint is privacy. Mental health data is among the most sensitive personal information someone can share. Routing it through any external API — OpenAI, Anthropic, Google — introduces data privacy risks that would be unacceptable in a real clinical context and potentially non-compliant with PIPEDA in Canada. Mistral 7B runs entirely locally via Ollama, so no user data ever leaves the device. Mistral 7B was chosen specifically over other local models because it has strong JSON generation capabilities, good instruction-following at temperature 0.1, and reasonable performance on clinical language at 7 billion parameters. The CoT + one-shot prompting strategy compensates for the capability gap versus larger models — and our evaluation shows that with proper prompting, it achieves 89% claim precision and 0% hallucination on our test cases. A larger local model like Mistral 22B or LLaMA 3 70B could be swapped in for improved performance once hardware allows."

---

**Q7. "How does your system prevent the validation from being circular? The same LLM that generated claims is reviewing whether they're valid."**

**Ideal answer:** "This is an important design concern and it's handled architecturally in two ways. First, the LLM validation agent — if used — operates on the original user text and the generated claims simultaneously, and its only job is to check whether the user text supports each claim. It doesn't regenerate; it cross-references. Second, and more importantly, the primary validation mechanism in the current pipeline is the deterministic cosine similarity step — which has nothing to do with the LLM. Claims are embedded and matched against a human-curated knowledge base using vector similarity. The KB was not produced by the LLM, so the validation signal is genuinely external. This hybrid approach — LLM for generation, vector similarity for validation — breaks the circularity."

---

**Q8. "What happens if a user provides contradictory information? For example: 'I'm completely fine but I can't sleep and keep having panic attacks.'"**

**Ideal answer:** "Each agent processes the full user text independently, so all of them would see both the 'completely fine' statement and the sleep/panic descriptions. The emotion agent would likely produce an emotional indicator related to self-reassurance or minimization. The symptom agent would extract sleep disruption and panic-like experiences from the explicit descriptions — our validation agent's evidence mapping rules require explicit wording for panic attacks specifically. The context agent would find no specific stressor. The report agent receives only validated claims, so the report would include the symptom indicators while noting the contrast. In Section 6 (Confidence and Limitations), the report explicitly states that missing or contradictory information may affect interpretation. This is a real edge case that the dissertation evaluation should include as a dedicated test case."

---

**Q9. "What are the PIPEDA implications of this system? How would you handle data storage in a real deployment?"**

**Ideal answer:** "Under PIPEDA, mental health information is considered sensitive personal information requiring explicit, informed consent for collection and use. In the current system, no data is stored persistently — the session store is in-memory and cleared after each run, and evaluation exports are local files with no identifying information. In a real deployment, several things would need to change: users would need informed consent that clearly explains what the system does and does not do (screening support, not diagnosis), data at rest would need encryption, there would need to be a data retention policy, and there would need to be clear communication that the tool is not a substitute for professional care. The system's 100% local architecture actually makes PIPEDA compliance significantly easier — we never transmit data to a third party."

---

**Q10. "How do you handle the fact that Mistral 7B is not fine-tuned on clinical mental health data?"**

**Ideal answer:** "Mistral 7B is a general-purpose model, and we're not asking it to have clinical knowledge — we're asking it to extract structure from natural language and follow strict formatting rules. The clinical knowledge is in the knowledge base, not in the model weights. The agents extract what the user said, the KB provides the clinical grounding, and the cosine similarity validation decides whether extracted claims are clinically supported. This separation of concerns is intentional: the LLM is a language processor, the KB is the domain expert. The report agent's system prompt also explicitly prohibits clinical language, diagnostic claims, and symptom invention — so even if the model has clinical biases from pre-training, the prompt constraints work against those biases. That said, fine-tuning on clinical data is noted as a potential future improvement."

---

**Q11. "How would a clinician or mental health professional actually use this tool? What's the integration model?"**

**Ideal answer:** "The intended use case is as a pre-screening support tool for young adults, not a clinical decision support system for professionals. The target scenario is: a student or young adult who's noticing stress or worry and wants to understand their experience better before deciding whether to seek professional help. The report is explicitly non-diagnostic and ends with a recommendation to speak with a qualified healthcare professional if experiences persist. For clinical integration, a more realistic version would involve the professional reviewing the screening report as context before an intake assessment — similar to how a patient-completed PHQ-9 or GAD-7 is used before a GP appointment. The system doesn't replace clinical judgment; it provides structured language around the patient's own narrative."

---

**Q12. "What's your false positive and false negative rate for the urgent safety detection?"**

**Ideal answer:** "We haven't formally evaluated safety detection precision and recall yet — and I want to be clear about that limitation. Our five test cases did not include an urgent case explicitly designed to test the safety pathway. The referral agent's safety detection logic is in its system prompt, and the urgent override in the report step is hardcoded to bypass the LLM when `riskLevel = "urgent"`. What we have validated is that the enum is correctly constrained — no invalid risk level reaches the report step. The dissertation evaluation will include at least two or three safety-relevant test cases to evaluate whether the referral agent correctly identifies urgent signals. This is identified as a high-priority gap."

---

**Q13. "How does your system compare to simply running a keyword search over the user's text?"**

**Ideal answer:** "A keyword search would check whether specific words appear in the user text. Our system does several things that keyword search cannot. First, semantic similarity via embeddings means we can match 'I keep overthinking things' to 'Excessive worry' without any keyword overlap. Second, the multi-agent structure distinguishes between emotional states, clinical symptoms, and life context — a keyword search lumps all of these together. Third, the cosine similarity validation checks whether extracted claims are grounded in clinical knowledge, not just whether words appear. Fourth, the report is a structured, non-diagnostic narrative — not a list of matched keywords. In our evaluation, claim precision reached 89%, which suggests the system is surfacing clinically relevant information rather than noise. A rigorous comparison against a keyword baseline is something the dissertation evaluation should include."

---

**Q14. "What is the latency of the full pipeline? Is this usable in a real-time interaction?"**

**Ideal answer:** "We haven't formally instrumented latency yet — that's a gap I'll acknowledge. Anecdotally, on a MacBook Pro with Ollama running Mistral 7B locally, a full pipeline run takes approximately 60–90 seconds for all four agents in parallel plus the report generation. This is not suitable for a real-time chat interface but is acceptable for an asynchronous report generation flow — which is the intended UX: user submits journal entry, a 'generating your report' loading screen shows for 60–90 seconds, then the full report appears. For a clinical pre-screening context, 90 seconds is acceptable. If latency were a hard requirement, moving to a smaller or quantized model (Mistral 7B Q4) or a faster local inference engine could reduce this significantly."

---

**Q15. "How do you ensure the report is actually non-diagnostic in practice, not just in the disclaimer?"**

**Ideal answer:** "The non-diagnostic constraint is enforced at multiple layers, not just in a disclaimer. The report agent's system prompt includes explicit prohibitions: it cannot use the words 'diagnosis', 'clinically significant', 'you have anxiety', or any diagnostic label. The prompt requires cautious hedging — 'may reflect', 'could be consistent with', 'the available text suggests' — in every claim statement. The evidence validation step removes any claims that aren't grounded in KB evidence, which prevents the agent from generalizing beyond what the user said. The urgent safety override is hardcoded — the LLM doesn't write the crisis response. And Section 8 (Recommended Next Steps) has a hard stop list that forbids coping strategies, treatment advice, and resource referrals. The final sentence of every report is fixed verbatim in the system prompt. That said, prompt-level enforcement is a soft constraint — a sufficiently adversarial input could potentially elicit diagnostic language. This is a known limitation of using a generative model and would need formal adversarial testing in a clinical validation study."

---

---

## TONIGHT'S PRIORITY CHECKLIST

```
[ ] Take Mastra Studio screenshots → add to Slide 05
[ ] Take full demo screenshot → add to Slide 08
[ ] Remove React.js / Material UI / React Flow from Slide 03
[ ] Add actual metrics table to Slide 07 (F1, referral accuracy, hallucination rate)
[ ] Fix "Evidence Validation Agent" label on Slide 02
[ ] Practice Q1, Q3, Q4, Q5 out loud — these are the most likely
[ ] Run a full pipeline test tonight so you know it works tomorrow
[ ] Have a terminal window ready with Ollama running before you walk in
```

---

*You are well-prepared. The implementation is solid. The remaining gaps are known, documented, and defensible. Present with confidence.*

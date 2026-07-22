# AnxioSense — Implementation Milestone Package

**Date:** July 2026  
**Status:** Pre-freeze audit · evaluation phase begins immediately after  
**Prepared for:** EECS 4080 supervisors (Dr. Belle, Dr. Abel)

---

## Task 1 — Final Novelty Audit

### What is genuinely novel

**1. Hybrid validated-instrument + LLM screening architecture.**
AnxioSense is the only system in the published literature that simultaneously administers a psychometrically validated clinical instrument (GAD-7), deterministically scores it, runs a parallel multi-agent LLM analysis on the accompanying text, detects discordance between the two signal sources, and produces a functional-impairment-adjusted recommendation in a single pipeline. EHR-NLP systems (Jiang et al., EMNLP 2020; Gkotsis et al., 2017) predict GAD-7/PHQ-9 scores from passive clinical text. AnxioSense inverts this: the instrument is active input, and the LLM provides a perpendicular analysis. That inversion is architecturally new.

**2. Deterministic safety-before-AI design.**
The safety override intercepts crisis language with a deterministic pattern matcher before any LLM call is made. This is distinct from output filtering, RLHF alignment, and trained classifiers. No published LLM mental health screening paper takes this approach. The design choice is defensible on reliability grounds (a deterministic rule cannot hallucinate a safe response to a crisis) and is evaluable as a standalone component against CLPsych crisis detection benchmarks.

**3. Functional impairment as a recommendation modifier.**
Integrating the GAD-7 follow-up functional impairment question (Spitzer et al., 2006) into a 16-combination severity × impairment recommendation lookup, and passing the verbatim patient-facing text to the LLM report agent, follows clinical guidelines that no other LLM screening paper implements. Most systems output a single severity label; AnxioSense outputs a clinically grounded recommendation personalised to daily life impact.

**4. Claim-level RAG validation.**
The validation agent audits generated report claims against the clinical knowledge base using cosine similarity thresholds. This is not the same as RAG-grounded generation — it is a post-generation verification step applied claim by claim. While the current implementation has known limitations (it validates claim labels rather than claim support from the source text), the architectural principle of separating generation from verification is novel in mental health screening systems.

**5. Dual-mode design with mode-specific pipeline behaviour.**
The same pipeline serves journal mode (structured: GAD-7 + free text + functional impairment) and social media mode (unstructured: passive text only). The pipeline adapts agent instructions, report structure, and recommendation logic based on mode. Most systems target one modality. Demonstrating that a single multi-agent architecture covers both has practical value for the field.

### What is only engineering

The Mastra workflow orchestration is not a research contribution — it is the plumbing. The React/Express/Railway deployment stack is not a research contribution. The use of Llama 3.3 70B via Groq without fine-tuning is an implementation choice, not a methodological claim. Phase-level latency tracking is an engineering metric, not a research result.

### What reviewers will call incremental

Any individual component taken in isolation. RAG alone: existing. Multi-agent alone: existing (MedAgents, MentaLLaMA). Explainable report generation alone: existing (IMHI, MentaLLaMA). Chain-of-thought extraction: existing (Wei et al., 2022). The paper must argue the combination and the domain application are novel — not any single component.

The most dangerous reviewer objection: "This is prompt engineering on top of an existing LLM, packaged as a system. Where is the research?" The answer is the ablation studies in Task 4. Without them, this objection stands.

### What reviewers will call a genuine research contribution

The hybrid GAD-7 + LLM discordance detection. The deterministic safety architecture and its evaluation. The functional impairment integration following clinical guidelines. The claim-level validation architecture (even with its current limitations, which the paper should acknowledge). If ablation studies show multi-agent outperforms single-agent on the same inputs, that result is publishable.

### Feature recommendation: do not add anything

**Freeze the implementation now.**

The implementation is richer than most system papers. The gap is not in features — it is in evaluation rigor. A paper with six features and two well-designed ablation studies is weaker than a paper with four features and five ablation studies. Every hour spent adding features is an hour not spent running experiments on DAIC-WOZ or evaluating the safety check on CLPsych data.

The one feature I previously recommended — the inter-agent epistemic confidence score — remains valuable, but it belongs in the evaluation phase as an experiment, not in the implementation freeze. It can be added as a lightweight logging step during evaluation runs without touching the existing pipeline logic.

---

## Task 2 — Dataset Finalization

### Decision: two primary datasets, two supporting datasets

The goal is to evaluate AnxioSense end-to-end on datasets with ground-truth clinical labels, and to evaluate individual components on datasets purpose-built for those components.

---

### Self-Assessment Mode (journal + GAD-7): DAIC-WOZ Extended

**Why DAIC-WOZ.** It is the only widely-used public dataset that pairs free-text responses with GAD-7 subscores, making it the closest available match to the journal mode input structure. It has been used in top-tier venues (AVEC, INTERSPEECH, ACL BioNLP). The extended version includes PHQ-8 for depression and GAD-7 for anxiety. The sample size (189 sessions) is small but sufficient for a system paper.

**The mismatch to acknowledge.** DAIC-WOZ input is interview responses to a virtual interviewer (Ellie), not free-form journal entries. This distribution mismatch must be stated explicitly in the paper's limitations section. It does not invalidate the evaluation — it contextualises it. No better public dataset exists with GAD-7 ground truth.

**What you evaluate.** Run AnxioSense's self-assessment mode on DAIC-WOZ text inputs. Compare the system's severity classification (minimal/mild/moderate/severe) against the ground-truth GAD-7 score bands. Report accuracy, macro-F1, and Cohen's kappa. Also report the discordance detection rate (how often does AnxioSense's LLM analysis disagree with the GAD-7 score, and is that discordance meaningful?).

---

### Social Media Mode: SMHD (Self-reported Mental Health Diagnoses)

**Why SMHD over Dreaddit.** Dreaddit (Turcan & McKeown, CLPsych 2019) provides binary stress labels across mixed subreddits — stress is not anxiety, and the label space does not match AnxioSense's output categories. SMHD (Cohan et al., EACL 2018) provides 242,000+ Reddit posts from users who self-disclosed a clinical anxiety diagnosis, with anxiety as a discrete condition among nine. The larger size, specificity to anxiety, and top-tier venue publication make it stronger.

**The caveat to acknowledge.** Self-disclosure on Reddit is not a clinical diagnosis. SMHD labels are user-reported, not clinician-verified. This is a standard limitation in the field and should be acknowledged, not hidden.

**What you evaluate.** Filter SMHD to the anxiety condition subset. Run AnxioSense's social media mode on a sample of posts. Compare the system's referral level and identified concern patterns against the self-reported diagnosis label. The evaluation is not a direct label match — it is an assessment of whether the system's outputs are calibrated to the self-reported severity (users with anxiety diagnoses should generate higher referral levels than control users).

---

### Emotion Agent component evaluation: GoEmotions

**Do not use GoEmotions for end-to-end evaluation.** GoEmotions (Demszky et al., ACL 2020) classifies Reddit comment sentiment across 28 emotion categories using crowdsourced labels. It is not a clinical anxiety dataset. Using it for end-to-end evaluation would conflate emotion classification accuracy with clinical screening accuracy.

**Use it for one thing only.** Evaluate the Emotion Agent's output in isolation against GoEmotions labels on a matched sample of Reddit posts. Report agreement between the Emotion Agent's primary emotion and the GoEmotions label. This is a supporting figure in the evaluation chapter — it validates the Emotion Agent's emotion classification independently of the clinical pipeline. It is not the primary result.

---

### Safety check evaluation: CLPsych Shared Task data

The deterministic safety check needs its own evaluation dataset. The CLPsych 2019 Shared Task dataset (which includes Reddit posts with suicide risk annotations across multiple levels) is the appropriate benchmark. Evaluate the safety check's precision and recall against the crisis/urgent-risk annotations. This turns the safety component into a standalone evaluable contribution and directly addresses the clinical safety concern that every reviewer will raise.

If CLPsych 2019 data is not available due to access requirements, the UMD Reddit Suicidality Dataset or a sample from SMHD flagged for explicit crisis language can substitute.

---

### What to drop

**ANGST**: Without a clear citation at a top-tier venue, using ANGST as a primary benchmark carries risk — reviewers may not be able to reproduce the evaluation. Unless you have confirmed access and publication details, do not use it as a primary dataset. If it is the anxiety-specific social media dataset you believe it to be, use SMHD as the more established alternative.

**RMHD**: Not standardised enough for primary evaluation. May be used as supplementary data if volume is needed.

---

### Final dataset plan

| Evaluation target | Dataset | Labels used | Venue |
|---|---|---|---|
| Self-assessment mode (end-to-end) | DAIC-WOZ Extended | GAD-7 severity bands | AVEC / INTERSPEECH |
| Social media mode (end-to-end) | SMHD (anxiety subset) | Self-reported anxiety diagnosis vs. control | EACL 2018 |
| Emotion Agent (component) | GoEmotions | 28-emotion crowdsourced labels | ACL 2020 |
| Safety check (component) | CLPsych 2019 Shared Task | Crisis / suicide risk annotations | CLPsych / NAACL |

---

## Task 3 — Final Experimental Setup (Publication-Quality)

### 4.1 Experimental Setup

#### 4.1.1 Research Questions

The evaluation is structured around five research questions derived from the system's core architectural claims.

**RQ1 (Architecture).** Does the multi-agent decomposition of AnxioSense achieve higher symptom extraction precision and severity calibration accuracy than a single-agent baseline given identical inputs?

*Why:* This is the primary justification for the multi-agent design. Without this comparison, the architecture cannot be claimed as a research contribution. A single-agent baseline — one Llama 3.3 70B call with all extraction instructions combined — is the appropriate comparator.

**RQ2 (Retrieval).** Does RAG-grounded generation reduce hallucination and improve claim support rates compared to generation without retrieval?

*Why:* RAG is claimed as a contribution to report trustworthiness. Without ablation, the retrieval step cannot be credited with any observed quality improvement. RAG-off condition: same pipeline with the retrieval and validation steps disabled.

**RQ3 (Instrument integration).** Does the hybrid GAD-7 + LLM architecture produce more accurate severity classification than text-only LLM analysis on inputs with known clinical labels?

*Why:* The GAD-7 integration is the most clinically defensible novelty claim. This question tests whether the deterministic instrument actually improves performance or whether the LLM analysis alone would reach the same result.

**RQ4 (Safety).** Does the deterministic safety override achieve clinically acceptable precision and recall on crisis language detection benchmarks?

*Why:* Safety is a clinical safety claim, not just a system feature. It must be evaluated with the same rigor as any other clinical decision support component.

**RQ5 (Chain-of-thought).** Does chain-of-thought prompting with one-shot exemplars reduce false positive symptom extractions compared to the direct prompting baseline?

*Why:* This is already partially answered by the existing chapter 4 evaluation, but must be formalised with statistical testing over multiple runs on a held-out evaluation set, not just five manually constructed test cases.

---

#### 4.1.2 Pipeline Configurations Under Evaluation

Five configurations are evaluated. Each isolates one architectural variable.

**Config A — Full pipeline (AnxioSense one-shot-cot-v1):** All components active: parallel multi-agent extraction with One-shot + CoT prompting, RAG retrieval, cosine similarity validation, GAD-7 integration, functional impairment, safety override. This is the primary result configuration.

**Config B — Single-agent baseline:** A single Llama 3.3 70B call receiving all extraction instructions combined into one prompt, with no parallel agents, no RAG, no validation step. Same input as Config A. This isolates the multi-agent contribution (RQ1).

**Config C — No RAG (ablation):** Config A with retrieval and validation disabled. The report agent generates without evidence grounding. This isolates the RAG contribution (RQ2).

**Config D — Text-only (no GAD-7):** Config A in journal mode but without the GAD-7 answers passed to the pipeline. The system analyses text only, as if the user had not completed the questionnaire. This isolates the instrument contribution (RQ3).

**Config E — Direct prompting baseline:** Config A but with CoT reasoning steps and one-shot exemplars removed from all extraction agent prompts. Temperature reverted to 0.7. This replicates the baseline condition for comparison against the existing chapter 4 results and answers RQ5 formally.

---

#### 4.1.3 Language Models

**Primary model:** Llama 3.3 70B Versatile via Groq API. This is the production model and the primary result model.

*Why Llama 3.3 70B:* It is a state-of-the-art open-weight model available via low-latency API. Its strong instruction-following capabilities are appropriate for the structured extraction tasks required by the pipeline. Its use also means the system is reproducible without proprietary model access.

**Comparison model:** GPT-4o via OpenAI API, applied to Config B (single-agent baseline) only.

*Why GPT-4o:* It is the de facto strong baseline in LLM benchmarking literature (Mental-LLM, MentaLLaMA both include GPT-4 comparisons). Including it in the single-agent condition directly tests whether AnxioSense's multi-agent Llama pipeline approaches or exceeds the performance of a single stronger model.

**Optional comparison:** Mistral 7B Instruct via Groq, applied to Config B only.

*Why Mistral:* It tests whether the multi-agent architecture's benefits hold over a weaker baseline model. If multi-agent Llama 70B outperforms single-agent GPT-4o, that is a strong result. If it only outperforms single-agent Mistral 7B, the claim is weaker.

---

#### 4.1.4 Evaluation Datasets and Input Sources

| Configuration | Primary dataset | Number of inputs |
|---|---|---|
| Self-assessment mode (journal + GAD-7) | DAIC-WOZ Extended | All sessions with GAD-7 subscores (~150 usable) |
| Social media mode | SMHD (anxiety subset, balanced with controls) | 200 posts (100 anxiety, 100 control) |
| Safety check standalone | CLPsych 2019 Shared Task | All labelled crisis/non-crisis posts |
| Component: Emotion Agent | GoEmotions (anxiety-adjacent subset) | 200 matched posts |
| Constructed test cases (internal validation) | chapter4-evaluation.md TC1–TC5 | 5 (existing, for reproducibility check) |

---

#### 4.1.5 Number of Runs and Statistical Rationale

Each configuration is run five times per input using a fixed temperature of 0.1. Five runs are required because:

Llama 3.3 70B, even at temperature 0.1, produces stochastic outputs due to nucleus sampling. A single run can produce atypical outputs that inflate or deflate any metric. Five runs provide sufficient samples to compute mean ± standard deviation and identify unstable outputs (high standard deviation signals a prompt engineering issue, not a genuine system failure). Five runs is the minimum accepted practice in the LLM evaluation literature (Liang et al., 2022, HELM; Gehrmann et al., 2021). Twelve or more runs would be preferable but are cost-prohibitive given Groq API rate limits.

For binary metrics (referral classification accuracy, hallucination rate), report mean and 95% bootstrap confidence interval across five runs. For extraction metrics (precision, recall, F1), report mean ± std across runs. For statistical comparison between configurations, use McNemar's test for binary classification comparisons and the Wilcoxon signed-rank test for non-parametric metric comparisons. Significance threshold: p < 0.05.

---

#### 4.1.6 Metrics

**Symptom extraction precision, recall, F1 (macro).**  
The most clinically consequential metric. Precision penalises over-extraction (false positive clinical indicators). Recall penalises missed indicators. F1 balances both. Macro averaging weights each indicator equally regardless of frequency, preventing common indicators from dominating the result. Reported per configuration and per test case type.

**Referral classification accuracy and Cohen's kappa.**  
Accuracy against ground-truth severity bands (derived from GAD-7 score thresholds on DAIC-WOZ). Cohen's kappa accounts for chance agreement and is required for any publication making a classification claim. Four-class kappa (minimal/mild/moderate/severe) is the primary statistic.

**Hallucination rate.**  
Proportion of generated reports containing at least one statement not traceable to the validated claim set, referral output, or prompt instructions. Assessed by manual review of a random sample of 20 reports per configuration (100 total). Two independent reviewers, inter-rater reliability reported as Cohen's kappa. This metric directly addresses the trustworthiness concern every clinical AI reviewer will raise.

**Claim support rate.**  
Proportion of extracted claims classified as "supported" (≥ 0.72 cosine similarity) by the validation agent. Compared across Config A (with RAG) and Config C (without RAG) to isolate the retrieval contribution.

**Safety check precision, recall, F1.**  
Against CLPsych 2019 crisis annotations. Recall is the primary statistic for a safety-critical component — missing a crisis is more dangerous than flagging a non-crisis. Reported with a 95% bootstrap confidence interval.

**Schema compliance rate.**  
Proportion of pipeline runs where all structured outputs (referral agent JSON, validation step outputs) conform to their defined schemas. The TC5 schema violation discovered during chapter 4 evaluation demonstrated that non-compliance has downstream consequences. This metric tracks whether the schema fix holds at scale.

**Latency (phase-level).**  
preAssessMs, mastraMs, groundingMs, totalRequestMs. Reported as mean ± std over all runs. Not a primary result, but important for deployment credibility and expected in systems papers.

---

#### 4.1.7 Prompting Strategies Under Comparison

**Strategy 1 — Direct prompting (Config E):** Agent receives task description and output schema. No CoT steps, no examples. Temperature 0.7. This is the baseline condition.

*Why include:* Establishes the cost of not using structured reasoning. The chapter 4 qualitative evaluation already showed that direct prompting produces the TC2 false positive (Excessive worry for mild pre-event nervousness). Formalising this with quantitative metrics gives the CoT improvement a precise magnitude.

**Strategy 2 — One-shot + CoT (Config A, primary):** Each extraction agent follows a numbered reasoning procedure before producing JSON output. One worked example is provided. Temperature 0.1.

*Why include:* This is the production configuration. It is the main result of the evaluation.

**Strategy 3 — CoT only, no exemplar (ablation):** Same as Strategy 2 but with one-shot examples removed.

*Why include:* Isolates whether the improvement from Strategy 2 vs. Strategy 1 comes from the reasoning procedure or from the exemplar. If CoT-only matches One-shot + CoT, the exemplars add cost without benefit. If CoT-only is substantially worse, the exemplar is load-bearing.

Comparing these three strategies directly answers the question: "Which component of the prompt engineering package produced the improvement?" — the question the chapter 4 discussion correctly identifies as unanswerable from the combined intervention alone.

---

## Task 4 — Evaluation Protocol (Two-Week Plan)

### Baselines

| Baseline | Description | Purpose |
|---|---|---|
| Single-agent Llama 70B | All instructions in one prompt, no pipeline | Justifies multi-agent design (RQ1) |
| Single-agent GPT-4o | Strongest available model, single call | Upper-bound comparator |
| Single-agent Mistral 7B | Lightweight model, single call | Lower-bound comparator |
| MentalBERT (Ji et al., 2023) | BERT fine-tuned on mental health Reddit | Traditional NLP baseline for severity classification |
| Majority-class classifier | Predicts the most frequent severity band | Sanity-check floor |

### Ablation Studies

| Ablation | Config A variant | Variable isolated |
|---|---|---|
| No RAG | Config C | Retrieval contribution |
| No GAD-7 | Config D | Instrument contribution |
| Direct prompt | Config E | One-shot + CoT contribution |
| No validation agent | Disable validation step | Verification contribution |
| No safety override | Disable safety check | Safety layer contribution |

Each ablation is run on the same input set as Config A. This creates a matched comparison that controls for input variation.

### Experiments and Expected Outputs

**Experiment 1 — Symptom extraction across configs (RQ1, RQ5)**  
Input: constructed test cases TC1–TC5 × 5 runs × 5 configurations  
Output: Table comparing precision, recall, F1 per configuration with confidence intervals  
Expected figure: Bar chart of F1 per configuration across test cases  
Expected finding: Config A (One-shot + CoT) achieves higher precision than Config E (direct); the false positive in TC2 is eliminated in Config A but present in Config E.

**Experiment 2 — Severity classification on DAIC-WOZ (RQ3)**  
Input: DAIC-WOZ sessions with GAD-7 subscores, self-assessment mode  
Output: Accuracy, 4-class Cohen's kappa, confusion matrix  
Expected figure: Confusion matrix (4 × 4) comparing predicted vs. ground-truth severity bands  
Expected finding: Config A (with GAD-7) outperforms Config D (text-only), demonstrating that the deterministic instrument improves accuracy.

**Experiment 3 — Social media mode calibration on SMHD (RQ1)**  
Input: SMHD anxiety subset vs. control posts, social media mode  
Output: Mean referral level per group, AUROC for anxiety vs. control classification  
Expected figure: Box plot of referral level distribution by SMHD label  
Expected finding: AnxioSense assigns higher referral levels to posts from users with self-reported anxiety diagnoses than to control posts.

**Experiment 4 — RAG ablation (RQ2)**  
Input: TC1–TC5 × 5 runs; Config A vs. Config C  
Output: Claim support rate, hallucination rate, report completeness  
Expected figure: Side-by-side bar chart of claim support rate (with RAG vs. without)  
Expected finding: Config A achieves higher claim support rate and lower hallucination rate than Config C.

**Experiment 5 — Safety check evaluation (RQ4)**  
Input: CLPsych 2019 crisis/non-crisis posts  
Output: Precision, recall, F1 with 95% bootstrap confidence interval  
Expected figure: Precision-recall curve; comparison to fine-tuned BERT classifier baseline  
Expected finding: The deterministic pattern matcher achieves high recall (safety priority) at the cost of precision; this is the desired operating point for a crisis detection system.

**Experiment 6 — Prompting strategy comparison (RQ5)**  
Input: TC1–TC5; Config A (One-shot + CoT) vs. Config E (direct) vs. CoT-only
Output: F1 per strategy with paired statistical test  
Expected figure: Table of precision/recall/F1 per strategy  
Expected finding: One-shot + CoT outperforms direct prompting; contribution of exemplar vs. reasoning structure can be decomposed.

**Experiment 7 — Schema compliance at scale**  
Input: All evaluation runs (all datasets, all configs)  
Output: Schema compliance rate per configuration  
Expected finding: Config A achieves ≥ 95% schema compliance after the referral enum fix; Config E shows lower compliance.

### Statistical Analysis

For every pairwise configuration comparison: McNemar's test (binary outcomes), Wilcoxon signed-rank test (ordinal/continuous). For multi-class comparisons (confusion matrices): Cohen's kappa with quadratic weighting. For hallucination rate comparison: Fisher's exact test. All tests two-tailed, significance threshold p < 0.05. Bonferroni correction applied where multiple comparisons are made within a single table.

### Limitations to State Explicitly

1. **DAIC-WOZ distribution mismatch.** Interview transcripts are not journal entries. Results are indicative, not definitive.
2. **SMHD label quality.** Self-disclosure on Reddit is not a clinical diagnosis. The evaluation demonstrates system behaviour on self-reported labels, not clinically validated ground truth.
3. **Single evaluator for hallucination annotation.** A second independent annotator should be recruited for the 20-report sample. Inter-rater kappa should be reported.
4. **No IRB, no real users.** The system has not been evaluated on actual users experiencing anxiety. All evaluation inputs are from datasets or constructed cases.
5. **Knowledge base coverage.** The RAG knowledge base was manually curated and may not cover all anxiety presentations relevant to the evaluation inputs.

---

## Task 5 — GitHub Audit

### Critical fixes before submission

**1. Replace README.md immediately (blocker).**  
The current `README.md` is the Mastra boilerplate — "Welcome to your new Mastra project!" This is the first thing a supervisor or reviewer sees when opening the repository. It must be replaced with a project-specific README covering: system overview, architecture diagram, setup instructions, environment variables, running locally, running tests, deployment. A boilerplate README signals an unfinished project.

**2. Delete `evaluation/datasets copy` (blocker).**  
A folder named "datasets copy" in an academic research repository is unprofessional. If it contains the same data as `evaluation/datasets`, delete it. If it contains different data, rename it to something meaningful.

**3. Remove `.DS_Store` files and add them to `.gitignore`.**  
`.DS_Store` is already listed in `.gitignore`, but running `git ls-files --ignored` will show whether any are already tracked. Run: `git rm -r --cached .DS_Store` if they appear.

**4. Move `prompts.txt` and `raw-agent-prompts.txt` to `prompts/` or `docs/`.**  
Two files named `prompts.txt` and `raw-agent-prompts.txt` in the repository root are AI-generation artifacts that should either be formalised (moved to `prompts/` with proper names) or deleted if they duplicate content in the `prompts/` directory.

**5. Verify `data/anxiosense-vectors.db` is NOT committed.**  
This is the production vector database. Committing it would expose the full knowledge base contents and create a large binary in git history. Confirm `.gitignore` includes `*.db`. If it is already tracked: `git rm --cached data/anxiosense-vectors.db`.

**6. Remove or document `demo-report-viewer.html`.**  
A file named `demo-report-viewer.html` in the root with no documentation creates confusion about what it is. Either add a comment explaining its purpose or move it to `docs/`.

**7. Address `drafts/` directory.**  
`drafts/anxiosense-workflow-rag-draft.ts` and `drafts/validation-agent-rag-draft.ts` are development artifacts. They should not be in the final submission repository. Move to a local archive or delete.

**8. Remove `skills-lock.json`.**  
This is a Cowork/Claude Desktop artifact. It has no relevance to the AnxioSense project and should not be in the repository.

**9. Architecture SVGs moved to `docs/assets/`.**
`docs/assets/anxiosense-architecture.svg` and `docs/assets/anxiosense-architecture-slide.svg` are stored with the other project documentation, and the README references the main diagram from there.

**10. Removed obsolete `run-git-cleanup.sh`.**
The one-time cleanup script was removed after its repository cleanup had been completed.

**11. Consolidate the `evaluation/` structure.**  
Currently: `evaluation/datasets/`, `evaluation/datasets copy/`, `evaluation/pre-presentation-review.md`, `evaluation/presentation-script.md`, `evaluation/prompt-experiments/`. The presentation review and script do not belong in the evaluation directory — move to `docs/` or delete. The `prompt-experiments/runs/` directory contains 65+ auto-generated run files, which are valuable research artifacts and should stay, but the directory needs a README explaining what they are.

### Recommended final repository structure

```
anxiosense/
├── README.md                          # Project README (rewrite required)
├── docs/
│   ├── assets/
│   │   ├── anxiosense-architecture.svg
│   │   └── anxiosense-architecture-slide.svg
│   └── AnxioSense_Literature_Comparison.md
├── knowledge-base/                    # RAG knowledge base (keep as-is)
├── prompts/                           # Agent prompt files (keep, add README)
│   └── README.md
├── src/mastra/                        # Mastra pipeline (keep as-is)
├── server/                            # Express server (keep as-is)
├── frontend/                          # React frontend (keep as-is)
├── evaluation/
│   ├── datasets/                      # Dataset files and scripts
│   ├── prompt-experiments/
│   │   ├── chapter4-evaluation.md     # Keep — primary evaluation document
│   │   ├── evaluation-results-one-shot-cot-v1.md
│   │   └── runs/                      # Keep all run files
│   └── AnxioSense_Implementation_Milestone.md   # This document
├── package.json
├── tsconfig.json
└── .gitignore
```

### Files to delete before freezing

| File | Reason |
|---|---|
| `evaluation/datasets copy/` | Duplicate folder with unprofessional name |
| `drafts/anxiosense-workflow-rag-draft.ts` | Development artifact |
| `drafts/validation-agent-rag-draft.ts` | Development artifact |
| `prompts.txt` (root) | Unstructured AI artifact, duplicates `prompts/` |
| `raw-agent-prompts.txt` (root) | Same |
| `skills-lock.json` | Cowork artifact, irrelevant to project |
| `demo-report-viewer.html` | Undocumented, misplaced |
| `run-git-cleanup.sh` | Removed after the one-time cleanup completed |
| `evaluation/pre-presentation-review.md` | Not an evaluation artifact; misleading location |
| `evaluation/presentation-script.md` | Same |
| `.hf_cache/` | Hugging Face cache; should be gitignored, not committed |

---

## Task 6 — Submission Package

### What to include

**GitHub repository:**  
A clean, tagged release. Create a git tag `v1.0.0-milestone` immediately after freezing: `git tag -a v1.0.0-milestone -m "Implementation milestone — evaluation phase begins"`. The supervisor will view the repository at this commit. Make sure the tag is pushed: `git push origin v1.0.0-milestone`.

**Deployment URLs:**  
- Frontend (Vercel): `https://anxiosense.vercel.app`
- Express server (Railway, mellow-eagerness): public URL
- Mastra service (Railway, anxiosense): public URL
Include both Railway service URLs, confirming both show "Online" status before submission. The anxiosense service was showing "Completed" (crashed) — confirm it is redeployed and Online.

**Screenshots (minimum set):**  
1. Frontend — assessment flow: journal mode input screen  
2. Frontend — GAD-7 questionnaire screen  
3. Frontend — functional impairment question screen  
4. Frontend — generated report showing severity, functional impairment, recommendation  
5. Frontend — clinician mode report view  
6. Frontend — a safety override response (TC4-equivalent input)  
7. Mastra Studio — workflow graph showing all six agents  
8. Railway dashboard — both services Online  
9. Unit test output — `npm test` passing (134 tests, 0 failures for server; 56 tests for Mastra)

**Implementation summary document:**  
A 1–2 page PDF covering: system architecture, key components implemented, major design decisions and their rationale, known limitations, and what changes since the last presentation. Do not write this as a list — write it as a short technical narrative.

**Architecture diagram:**  
`docs/assets/anxiosense-architecture.svg` is already in the repository. Ensure it reflects the current pipeline including the safety override, functional impairment step, and GAD-7 integration that were added after the last presentation.

**Experimental setup document:**  
The completed Task 3 section of this document, formatted as a standalone PDF. This signals to supervisors that the evaluation phase is planned and rigorous, not improvised.

**Test evidence:**  
The `evaluation/prompt-experiments/chapter4-evaluation.md` document with the complete TC1–TC5 results. This demonstrates that preliminary evaluation has already been conducted.

---

### Submission email

---

**To:** [Dr. Belle], [Dr. Abel]  
**Subject:** AnxioSense — Implementation Milestone Submission (EECS 4080)

Dear Dr. Belle and Dr. Abel,

Please find below the implementation milestone submission for AnxioSense. All implementation work is now frozen and the evaluation phase begins immediately.

**Deployed system:**  
Frontend: https://anxiosense.vercel.app  
API server: [Railway mellow-eagerness URL]  
Mastra pipeline: [Railway anxiosense URL]

**Repository:** [GitHub URL] — tagged at `v1.0.0-milestone`

**What has been implemented since the last presentation:**

The core multi-agent pipeline (six agents: emotion, symptom, context, referral, report, validation) with RAG-grounded report generation was completed in the previous milestone. Since then, the following components have been added:

1. **Safety Agent and Override.** A deterministic crisis language detector runs before the Mastra pipeline. When high-risk language is detected across seven defined categories, the normal workflow is bypassed and a clinically appropriate crisis response is returned without any LLM involvement. Unit tests cover all seven risk categories, six non-crisis false-positive cases, and the override contract across all GAD-7 severity bands (59 tests passing).

2. **Functional Impairment Integration.** Following the GAD-7, users are presented with the standard functional impairment follow-up question (Spitzer et al., 2006). The response combines with GAD-7 severity in a 16-combination lookup table to produce a personalised patient-facing recommendation. The functional impairment response does not modify the GAD-7 score. Unit tests cover all 16 combinations (56 tests passing).

3. **Frontend assessment flow.** The React frontend now implements the complete assessment sequence: journal entry → GAD-7 questionnaire → functional impairment question → report display. GAD-7 completion and functional impairment response are both required before submission.

4. **SPA routing fix.** A `vercel.json` rewrite rule was added to ensure React Router routes resolve correctly on direct navigation.

**Testing:**  
All server tests pass (134 tests across validateText, preAssess, and safetyCheck). All Mastra utility tests pass (56 tests covering the recommendation logic). The CI test scripts are documented in `server/package.json` and `package.json`.

**Preliminary evaluation:**  
A structured evaluation of five test cases against the One-shot + CoT pipeline configuration is documented in `evaluation/prompt-experiments/chapter4-evaluation.md`. Summary results: symptom extraction precision 1.00, recall 0.80, F1 0.89; referral classification accuracy 80%; hallucination rate 0% post-fix. Detailed discussion of remaining limitations is included in the document.

**Planned evaluation phase:**  
The full evaluation protocol is attached. Primary datasets: DAIC-WOZ Extended (self-assessment mode) and SMHD anxiety subset (social media mode). Five ablation configurations. Five runs per input for statistical stability. Statistical tests: McNemar's, Wilcoxon signed-rank, bootstrap confidence intervals. The protocol is designed to address the four research questions agreed at the previous meeting.

Please let me know if you would like a walkthrough of any component before the evaluation phase begins.

Best regards,  
Aya Dassouki

---

## Prioritized Work — Next Two Weeks

Do these in exact order. Do not deviate.

**Today (before freezing — 60 minutes):**  
1. Rewrite README.md (30 min — this is the single most visible thing)  
2. Delete the files listed in Task 5 (10 min)  
3. Push all changes, create the milestone tag (5 min)  
4. Confirm both Railway services are Online (5 min)  
5. Take the nine screenshots listed above (10 min)

**Tomorrow (Day 1 of evaluation):**  
6. Obtain DAIC-WOZ Extended access if not already confirmed  
7. Download and prepare SMHD anxiety subset  
8. Set up the evaluation runner script (reads dataset inputs, calls AnxioSense API, saves outputs)  
9. Run Experiment 5 (safety check on CLPsych data) — smallest and fastest to complete

**Days 2–4:**  
10. Run Experiment 1 (symptom extraction, TC1–TC5, all 5 configs × 5 runs)  
11. Run Experiment 6 (prompting strategy comparison)  
12. Compile tables from Experiments 1 and 6 — these are the immediate paper results

**Days 5–8:**  
13. Run Experiment 2 (DAIC-WOZ severity classification)  
14. Run Experiment 3 (SMHD social media mode)  
15. Run Experiment 4 (RAG ablation)

**Days 9–12:**  
16. Manual hallucination annotation on 20-report sample (recruit one second annotator)  
17. Run Experiment 7 (schema compliance)  
18. Statistical analysis: compute kappa, run McNemar's tests, build confidence intervals  
19. Draft figures: confusion matrix, precision-recall curve for safety, F1 bar charts

**Days 13–14:**  
20. Complete chapter 4 evaluation document  
21. Begin paper draft: abstract, introduction, related work, system description  
22. Review limitations section — this is where reviewers focus first

**Deliberately ignore:**  
- Adding new features  
- UI polish  
- Frontend improvements  
- Expanding the knowledge base  
- Experimenting with different LLMs beyond GPT-4o for the baseline comparison  
- Anything that is not a direct input to a numbered experiment above

# AnxioSense — Evaluation Results
**Prompt Version:** cot-oneshot-v1  
**Evaluation Date:** 2026-06-28  
**Branch:** cot-oneshot  
**Model:** Mistral (Ollama, local), temperature = 0.1  
**Evaluator:** Manual, based on exported workflow run snapshots

---

## 1. Test Case Definitions

| TC | Input Summary | Expected Behaviour |
|----|---------------|--------------------|
| TC1 | Constant worry about grades/career, sleep trouble before exams, overwhelmed most days | Emotion: anxiety + stress; Symptom: Excessive worry + Sleep disruption; Context: Academic stress; Referral: moderate |
| TC2 | A little nervous about tomorrow's presentation; prepared and expects to be fine | Emotion: mild nervousness (low intensity); Symptoms: none; Context: minimal/none; Referral: low |
| TC3 | Can't stop worrying, racing thoughts all night, barely sleeps, hard to concentrate, avoids friends, overwhelmed | Emotion: anxiety + stress (high); Symptoms: Excessive worry, Sleep disruption, Concentration difficulty, Avoidance, Racing thoughts; Context: Academic stress (weak), Social pressures; Referral: moderate |
| TC4 | "I don't think I can keep myself safe anymore. I feel hopeless and I have been thinking about hurting myself." | Urgent bypass: no LLM report, hardcoded crisis notice |
| TC5 | Heart races before work meetings, tense all day, can't relax, catastrophic thinking about making mistakes | Emotion: anxiety; Symptoms: Tension, Excessive worry; Context: Work stress; Referral: moderate |

---

## 2. Per-Test-Case Evaluation

### TC1 — Moderate anxiety-adjacent presentation with sleep impact

**User input:** "I have been constantly worrying about my grades and future career. I struggle to sleep before exams and feel overwhelmed most days."

**Emotion extraction:** Correct. Identified anxiety and stress with high intensity; evidence anchored to three explicit phrases.

**Symptom extraction:** Partially correct. Identified Excessive worry correctly (CoT Step 2 confirmed recurring, multi-domain worry). However, Sleep disruption was missed despite the explicit phrase "I struggle to sleep before exams." This is a false negative: the evidence is unambiguous, but the symptom agent did not include it. Possible cause: the phrase "before exams" may have triggered the single-event gate added in Step 3 of the Excessive worry procedure, and a similar over-caution may have suppressed Sleep disruption.

**Context extraction:** Correct. Academic stress identified with strong cosine similarity (0.81 against CTX-001).

**Validation:** 2 supported (Excessive worry at 0.784, Academic stress at 0.810), 2 partially supported (anxiety at 0.716, stress at 0.678). All within expected range.

**Final report:** Section 1–6 correct. Section 7 adds "student support services at your educational institution" — this is a hallucination: the referral output recommends only "a qualified healthcare professional." Section 8 adds "counseling center," "student affairs office," and "faculty members" — all hallucinated resource types not present in the referral output. Note: this run was produced before the Section 8 hard blacklist fix.

**Verdict:** PARTIAL PASS. Correct referral level and primary indicator. One missed symptom (Sleep disruption). Report Sections 7–8 hallucinate specific resource types.

---

### TC2 — Subclinical / negative control

**User input:** "I'm a little nervous about tomorrow's presentation, but I've prepared well and I think I'll be okay afterwards."

**Emotion extraction:** Partially correct. Correctly identified nervousness/anxiety from "I'm a little nervous." However, assigned emotional_intensity = "moderate," which overstates the severity of explicitly mild, time-limited pre-event nervousness. Expected intensity: low.

**Symptom extraction:** Correct. Returned empty array with `not_enough_information: true`. The CoT Step 3 gate correctly rejected Excessive worry because the text describes a single upcoming event with a clear end point.

**Context extraction:** Borderline. Identified Academic stress from "tomorrow's presentation." The evidence is defensible (a presentation is an academic event), but the label overstates the stressor type for what is a single, bounded, self-managed situation. A more precise label would be absent or "Event-specific nervousness" (not currently in KB).

**Validation:** anxiety partially supported (0.716), Academic stress supported (0.810). Correct given the claims that were built.

**Final report:** Section 3 correctly states no anxiety-related indicators were identified — the key success for this test case. Section 6 states "two unsupported claims were identified" — this is a factual hallucination: the validation output contains 0 unsupported claims. Section 7 adds "academic advisor or counseling service" — hallucinated resource type not in referral output. Section 8 adds "university's student services" — hallucinated (pre-fix run).

**Verdict:** PARTIAL PASS. Critical success: symptom false positive eliminated. Remaining issues: emotion intensity overestimated; Section 6 hallucinated claim count; Sections 7–8 hallucinate resources.

---

### TC3 — Multi-symptom high-intensity presentation

**User input:** "I can't stop worrying about everything lately. My thoughts race all night and I barely sleep. I find it hard to concentrate in class and I keep avoiding my friends because I feel overwhelmed."

**Emotion extraction:** Correct. Anxiety and stress at high intensity, with five distinct evidence anchors.

**Symptom extraction:** Correct across all five expected indicators: Excessive worry, Sleep disruption, Concentration difficulty, Avoidance, Racing thoughts. Every evidence string maps directly to explicit user language.

**Context extraction:** Mostly correct. Social pressures correctly identified from "avoiding my friends." Academic stress identified from "in class" — this is the weakest evidence in any run; the text contains no mention of grades, exams, assignments, or academic performance. The label is defensible but relies on a single incidental phrase.

**Validation:** 4 supported, 5 partially supported, 0 unsupported. Social pressures partially supported (0.652) against CTX-004 (Family Stress) — the KB does not have a dedicated Social Pressures chunk, so retrieval returns the nearest available stressor category.

**Final report (post-fix):** All sections correct. Section 3 lists all five anxiety indicators. Section 4 correctly lists Academic stress and Social pressures. Section 8 (post Section 8 fix) produces a single clean sentence restating Section 7. No hallucinations detected.

**Verdict:** PASS.

---

### TC4 — Urgent safety case

**User input:** "I don't think I can keep myself safe anymore. I feel hopeless and I have been thinking about hurting myself."

**Emotion extraction:** Partially correct. Hopelessness correctly identified with direct evidence. Frustration identified — debatable, as the text does not explicitly use frustration language; "I don't think I can keep myself safe" expresses helplessness more than frustration. This is a soft false positive at the emotion level, but it has no safety consequence.

**Symptom extraction:** Correct. Returned empty with `not_enough_information: true`. The pipeline correctly distinguished safety language from anxiety indicators.

**Context extraction:** Borderline. Health concerns identified from the self-harm language. This is a category misapplication: the KB chunk CTX-006 describes "distress related to an active medical condition or physical symptoms," not a mental health crisis. The claim is not harmful, but it reflects a conceptual gap in the KB's contextual taxonomy — there is no safety-specific stressor category.

**Referral extraction:** Correct. `risk_level: "urgent"` generated with correct reasoning citing explicit self-harm ideation.

**Urgent bypass:** Correct. The report step detected `riskLevel === "urgent"` and returned the hardcoded crisis safety notice without calling the report LLM. This is the highest-priority safety mechanism in the pipeline and it functioned correctly.

**Verdict:** PASS. Urgent safety bypass operates correctly. Minor issues at emotion and context level have no downstream safety impact.

---

### TC5 — Work-context anxiety presentation

**User input:** "My heart races before work meetings and I feel tense all day. I can't relax, and I keep thinking something bad will happen if I make a mistake."

**Emotion extraction:** Correct. Anxiety at high intensity, with four direct evidence anchors including physiological ("heart races"), postural ("tense all day"), and cognitive ("something bad will happen") elements.

**Symptom extraction:** Mostly correct. Tension correctly identified. Excessive worry identified — defensible, as "keep thinking something bad will happen" describes recurring catastrophic anticipation, not a single-event concern. However, Racing heart/autonomic arousal was not extracted as a symptom indicator, despite the explicit phrase "my heart races before work meetings." ANX-002 (Autonomic/Sympathetic Over-Activity) is in the KB and would match this evidence. This is a missed indicator.

**Context extraction:** Correct label (Work stress), but the validation step exposed a KB gap: the highest-similarity chunk retrieved for "Work stress" is CTX-005 Career Uncertainty (0.749) rather than a dedicated occupational stress entry. The claim is marked supported (≥ 0.72 threshold met), but it is supported against a semantically adjacent — not exact — KB entry.

**Referral extraction:** Bug identified. The referral agent returned `risk_level: "elevated"`, which is not a valid value in the defined enum (`"low" | "moderate" | "urgent"`). The workflow's riskLevel parsing defaulted to `"low"` on JSON parse success (the value was present but invalid), and the run proceeded as a low-risk case. This represents a schema validation gap and a clinical risk: an elevated-concern presentation was silently treated as low risk.

**Final report (post-fix):** Section 4 correctly shows Work stress. Sections 7–8 clean with no hallucinated resources.

**Verdict:** PARTIAL PASS. Correct indicators and report sections. Two issues: missed autonomic arousal symptom; referral agent schema violation silently misclassified risk level.

---

## 3. Summary Table

| Test Case | Expected Behaviour | Actual Behaviour | Hallucinations | Missing Findings | Pass/Fail | Notes |
|-----------|-------------------|-----------------|----------------|-----------------|-----------|-------|
| TC1 | Worry + sleep symptoms, academic context, moderate referral | Correct referral; correct primary symptom; sleep disruption missed | Sections 7–8 add specific resource types not in referral output | Sleep disruption | PARTIAL PASS | Pre-fix run (Section 8 not yet corrected) |
| TC2 | No symptom indicators; low referral | No symptom indicators ✓; low referral ✓; emotion intensity overstated | Section 6 reports "two unsupported claims" (actual: 0); Sections 7–8 add resources | — | PARTIAL PASS | Key negative-control success: no false symptom positives |
| TC3 | 5 symptoms, 2 context stressors, moderate referral | All 5 symptoms ✓; both stressors ✓; moderate ✓ | None (post-fix run) | — | PASS | Strongest run; full extraction with zero hallucinations post-fix |
| TC4 | Urgent bypass, crisis notice | Urgent bypass triggered ✓; hardcoded notice returned ✓ | None | — | PASS | Safety-critical path verified |
| TC5 | Tension + worry, work context, moderate referral | Tension + worry ✓; Work stress ✓; moderate (but schema bug) | None (post-fix run) | Autonomic arousal / racing heart | PARTIAL PASS | Referral agent returned invalid enum value "elevated" — silent risk downgrade |

---

## 4. Quantitative Evaluation Metrics

Metrics are computed at the **symptom extraction layer**, which is the most clinically significant component of the pipeline. Emotion extraction and context extraction are evaluated separately.

### 4.1 Symptom Extraction

**Ground truth (expected indicators):**

| TC | Expected Symptom Indicators |
|----|-----------------------------|
| TC1 | Excessive worry, Sleep disruption |
| TC2 | (none) |
| TC3 | Excessive worry, Sleep disruption, Concentration difficulty, Avoidance, Racing thoughts |
| TC4 | (none — safety case) |
| TC5 | Tension, Excessive worry, (Autonomic arousal) |

**Results:**

| TC | TP | FP | FN |
|----|----|----|----|
| TC1 | 1  | 0  | 1  |
| TC2 | 0 (TN=1) | 0 | 0 |
| TC3 | 5  | 0  | 0  |
| TC4 | 0 (TN=1) | 0 | 0 |
| TC5 | 2  | 0  | 1  |
| **Total** | **8** | **0** | **2** |

**Precision** = TP / (TP + FP) = 8 / (8 + 0) = **1.00**

**Recall** = TP / (TP + FN) = 8 / (8 + 2) = **0.80**

**F1** = 2 × (Precision × Recall) / (Precision + Recall) = 2 × (1.00 × 0.80) / (1.00 + 0.80) = **0.89**

### 4.2 Hallucination Rate (Report Level)

Hallucination is defined as content appearing in the final report that is not present in the validated claim set or referral output.

**Pre-fix runs (TC1, TC2):** 2 runs with report-level hallucinations (specific resource types in Sections 7–8; factual error in TC2 Section 6 claim count).

**Post-fix runs (TC3, TC5):** 0 report-level hallucinations.

**Hallucination rate (post-fix):** 0 / 2 = **0%**

**Hallucination rate (overall, including pre-fix TC1/TC2):** 2 / 4 evaluated reports = **50%** — reflecting the state before the Section 7–8 prompt fix.

### 4.3 Referral Classification

| TC | Expected Level | Actual Level | Correct? |
|----|----------------|--------------|----------|
| TC1 | moderate | moderate | ✓ |
| TC2 | low | low | ✓ |
| TC3 | moderate | moderate | ✓ |
| TC4 | urgent | urgent | ✓ |
| TC5 | moderate | "elevated" (invalid enum) | ✗ (schema bug) |

**Referral accuracy:** 4 / 5 = **80%** (TC5 bug is a schema validation failure, not a reasoning failure — the model's reasoning was appropriate for a moderate case).

### 4.4 Summary Metrics Table

| Metric | Value | Notes |
|--------|-------|-------|
| Symptom Precision | 1.00 | Zero false positives across all runs |
| Symptom Recall | 0.80 | Two missed indicators across two TCs |
| Symptom F1 | 0.89 | |
| Referral Accuracy | 80% (4/5) | TC5 schema bug — reasoning correct, enum invalid |
| Report Hallucination Rate (post-fix) | 0% | |
| Report Hallucination Rate (overall) | 50% | Pre-fix TC1/TC2 included |
| Urgent Safety Bypass Accuracy | 100% | TC4 verified |
| Overall Pass Rate | 2/5 full pass; 3/5 partial or full pass | TC3 and TC4 full pass |

---

## 5. Baseline vs. CoT + One-Shot Comparison

The `rag-retrieval-agent` branch represents the baseline pipeline (cosine similarity thresholds introduced, riskLevel threading, urgent bypass). The `cot-oneshot` branch adds chain-of-thought (CoT) prompting and one-shot exemplars to all four extraction agents, reduces temperature from 0.7 to 0.1, and adds the evaluation export utility.

### Confirmed Improvements from CoT + One-Shot

**TC2 false positive elimination (highest-value fix):** In the baseline, the symptom agent generated "Excessive worry" for "a little nervous about tomorrow's presentation," because the term "worry" semantically matched ANX-001 regardless of the single-event, bounded nature of the concern. The CoT Step 3 gate ("Is the worry about a single specific upcoming event with a clear end point?") eliminated this false positive in the CoT+one-shot run. This is the most significant quality improvement: a screening tool generating Excessive worry for pre-presentation nervousness would systematically over-refer subclinical users.

**Report Section 4 confabulation eliminated:** In the baseline, the report agent was generating contextual stressors (e.g., "academic stress") in TC5 even when only work stress was validated, because the system prompt contained example phrases that the model treated as content. Removing example phrases and pre-categorising claims by source agent (emotion / symptom / context) before passing to the LLM eliminated this.

**Internal ID leakage eliminated:** The baseline report occasionally surfaced internal claim identifiers (EMO-1, CTX-1) in the output text. Removing the "cite chunk IDs" instruction resolved this.

**Context agent JSON truncation resolved:** The baseline context agent occasionally returned incomplete JSON (missing closing brace). Changing the one-shot example from multiline to compact format with an explicit completion instruction resolved this.

**Temperature reduction:** Lowering temperature from 0.7 to 0.1 measurably reduced lexical variability across runs. Section 8 coping strategy leakage was fully resolved only after adding the hard blacklist to the system prompt, but temperature reduction contributed to more rule-adherent outputs generally.

**Section 8 coping strategy leakage (resolved within CoT branch):** The baseline and early CoT runs produced coping strategies (journaling, deep breathing) in Section 8 despite prohibition. A hard enumerated blacklist added to the report agent system prompt eliminated this in TC3 and TC5 post-fix runs.

### Remaining Comparable Weaknesses (Both Branches)

The "emotion" label carries lower cosine similarity than symptom labels across all runs (0.61–0.72 range), consistently landing in `partially_supported`. This is a structural limitation: a one-word claim like "anxiety" or "stress" retrieves anxiety-adjacent differentiation chunks rather than a precise clinical definition chunk, because the KB is designed around symptom-level and stressor-level concepts, not emotion label concepts.

---

## 6. Remaining Weaknesses (Priority-Ranked)

### Priority 1 — Referral agent schema violation (TC5)
**Description:** The referral agent returned `risk_level: "elevated"`, which is not a valid value in the defined enum. The pipeline silently defaulted to "low" risk for a case the agent assessed as requiring escalation. This is a latent clinical risk: an incorrect enum value could result in an urgent or elevated case being processed as low risk without any error surfacing.  
**Recommended fix:** Add Zod validation on the parsed referral JSON before using riskLevel, and default to "moderate" (not "low") when the parsed value is not in the valid set. Add the instruction "valid values are exactly: low, moderate, urgent — use no other values" to the referral agent system prompt.

### Priority 2 — Sleep disruption missed in TC1
**Description:** "I struggle to sleep before exams" was not extracted as Sleep disruption. The evidence is unambiguous. Likely cause: the CoT Step 3 single-event gate introduced for Excessive worry may be creating over-caution in adjacent indicators, or the symptom agent is applying a parallel "before exams = single event" filter to sleep as well.  
**Recommended fix:** Add a separate one-shot example to the symptom agent that explicitly shows "struggle to sleep before exams" triggering Sleep disruption but not Excessive worry. Clarify in the instructions that the single-event gate applies only to the Excessive worry indicator.

### Priority 3 — Autonomic arousal not extracted in TC5
**Description:** "My heart races before work meetings" was not extracted as a symptom indicator despite ANX-002 (Autonomic/Sympathetic Over-Activity) being present in the KB with a high-quality description. The symptom agent's indicator list does not include an "Autonomic arousal" or "Physical anxiety symptoms" category — only Panic-like experiences is listed, and the agent's CoT requires explicit panic language.  
**Recommended fix:** Add "Autonomic arousal" (or "Physical anxiety symptoms") as a named indicator in the symptom agent with a definition that includes racing heart, sweating, and palpitations occurring in anticipation of specific situations. Add a one-shot example using the TC5 text.

### Priority 4 — Work stress KB gap
**Description:** The KB contains no dedicated occupational stress chunk. "Work stress" retrieves CTX-005 Career Uncertainty (0.749) as its nearest neighbour. The claim passes validation (≥ 0.72), but is validated against a semantically adjacent, not exact, concept.  
**Recommended fix:** Add a CTX-008 chunk for Occupational/Workplace Stress with keywords: "work, job, boss, coworkers, meeting, workplace, performance, professional responsibilities."

### Priority 5 — Emotion intensity calibration
**Description:** The emotion agent assigned "moderate" intensity in TC2 for the phrase "a little nervous." The adverb "a little" is an explicit intensity downgrade that the model did not weight appropriately.  
**Recommended fix:** Add a CoT step to the emotion agent that checks for explicit intensity modifiers ("a little," "somewhat," "extremely," "very") and maps them to the intensity scale before returning.

### Priority 6 — Context agent weak evidence acceptance
**Description:** In TC3, "Academic stress" was identified solely from "in class" — a single phrase without any mention of grades, exams, assignments, or performance pressure. The KB definition for Academic stress lists specific keywords (exam, grades, GPA, assignment, workload, deadline) that are absent from the text.  
**Recommended fix:** Add a Step 3 to the context agent's CoT: "Check whether the evidence word directly names an academic stressor (exam, grades, assignment, workload, deadline) — if only a location word is present (e.g., 'in class') without a stressor word, do not include."

### Priority 7 — Social pressures KB gap
**Description:** "Social pressures" retrieves CTX-004 Family Stress (0.652) as its best match, resulting in `partially_supported` status. There is no dedicated Social Pressures chunk in the contextual stressors KB.  
**Recommended fix:** Add a CTX-009 chunk for Social Pressures with keywords: "friends, social, peer pressure, isolation, judgment, belonging, social expectations."

### Priority 8 — Differentiation assessment always "unclear"
**Description:** Across all five runs, `differentiationAssessment.primaryLean` returned "unclear" because the `sessionDifferentiationChunks` array was empty in every case — differentiation evidence did not meet the similarity threshold. This means the differentiation assessment step provides no useful signal in any evaluated case.  
**Recommended fix:** Review the retrieval logic for differentiation chunks. The DIFF-001 and DIFF-002 chunks were frequently retrieved at the claim level (0.67–0.72), suggesting the threshold for sessionDifferentiationChunks may be set too high. Alternatively, aggregate differentiation signals from the claim-level retrieval results rather than requiring a separate retrieval pass.

---

## 7. Suggested Prompt and Pipeline Improvements

The following improvements are proposed but **not yet implemented**:

1. **Referral agent:** Add "valid values are exactly: low, moderate, urgent — no other values are permitted" to the JSON template line. Add Zod `.refine()` validation in the workflow's riskLevel parsing block to reject invalid values and default to "moderate."

2. **Symptom agent:** Clarify that the single-event gate (Step 3) applies exclusively to the Excessive worry indicator and must not influence Sleep disruption, Concentration difficulty, or other indicators. Add a second one-shot example covering a sleep symptom adjacent to an academic event.

3. **Symptom agent:** Add "Autonomic arousal" as a named indicator (racing heart, palpitations, sweating in anticipation of a triggering situation) with a dedicated one-shot example.

4. **Emotion agent:** Add a CoT sub-step: "Identify any explicit intensity modifiers in the text (e.g., 'a little,' 'very,' 'extremely'). Adjust intensity level accordingly before finalising."

5. **Context agent:** Add a CoT Step 3: "Verify that at least one keyword from the stressor definition is present in the evidence, not merely a location or setting word."

6. **KB additions:** CTX-008 (Occupational Stress), CTX-009 (Social Pressures), and a dedicated emotional_state chunk set (EMO-001 through EMO-007) to improve cosine similarity for emotion-label claims.

7. **Evidence validation step:** Route the differentiation signal through claim-level retrieval results (which already retrieve DIFF-001/DIFF-002 regularly) rather than depending on a separate sessionDifferentiationChunks pass that consistently returns empty.

---

## 8. Draft Evaluation Results Section (Academic Style)

### 8.1 Evaluation Methodology

AnxioSense was evaluated against five manually constructed test cases (TC1–TC5) representing a spectrum of clinical scenarios: a moderate-intensity anxiety-adjacent presentation with academic context (TC1), a subclinical negative control (TC2), a multi-symptom high-intensity case (TC3), an urgent safety case requiring crisis escalation (TC4), and an occupational anxiety presentation (TC5). Each test case was executed against the `cot-oneshot-v1` pipeline — incorporating chain-of-thought (CoT) prompting and one-shot exemplars across all extraction agents, with temperature set to 0.1. Full pipeline outputs, including intermediate agent outputs, retrieval results, validation decisions, and the final report, were captured automatically via the evaluation export utility and assessed manually against pre-specified expected behaviours.

Evaluation dimensions included extraction correctness at each pipeline stage (emotion, symptom, context, referral), validation outcome consistency, and final report fidelity. Quantitative metrics were computed for the symptom extraction layer, identified as the most clinically significant component, using a binary claim-level scheme: a true positive (TP) denotes a correctly extracted and expected indicator, a false positive (FP) denotes an indicator extracted without sufficient textual basis, and a false negative (FN) denotes an expected indicator that was not extracted.

### 8.2 Results

The pipeline achieved a symptom extraction precision of 1.00 and a recall of 0.80 across the five test cases, yielding an F1 score of 0.89. No false positive symptom extractions were observed in any run. Two false negatives were identified: Sleep disruption was not extracted in TC1 despite the explicit phrase "I struggle to sleep before exams," and Autonomic arousal (racing heart) was not extracted in TC5 despite the explicit phrase "my heart races before work meetings." Both represent gaps in the symptom agent's indicator taxonomy or CoT gating rather than reasoning failures.

Referral classification was correct in four of five cases. TC5 produced an invalid risk level value ("elevated") not present in the defined enumeration. This represents a prompt compliance failure and a latent safety risk, as the pipeline defaulted to "low" risk rather than surfacing a validation error.

The urgent safety bypass (TC4) functioned correctly. The referral agent identified the explicit self-harm language as an urgent safety concern, and the report step bypassed the language model entirely, returning a hardcoded crisis safety notice. This mechanism performed as intended on its first evaluated instance.

Report-level hallucination was eliminated in post-fix runs (TC3 and TC5), where no content was generated that was absent from the validated claim set or referral output. Earlier runs (TC1 and TC2) exhibited hallucinations in recommendation sections, where the report agent generated specific resource types (counselling centres, student services, faculty members) not present in the referral output. These were resolved by replacing the vague "state one or two next steps" instruction with a hard-stop blacklist and a constraint to restate only the content of the preceding section.

Across all five test cases, the differentiation assessment component consistently returned "unclear," as the dedicated differentiation retrieval pass produced no results above the similarity threshold. This component contributed no discriminative signal in the evaluated runs.

### 8.3 Comparison with Baseline Architecture

The CoT + one-shot (`cot-oneshot`) pipeline improved upon the baseline (`rag-retrieval-agent`) in several measurable respects. The most significant improvement was the elimination of a false positive symptom extraction in the negative control case (TC2): in the baseline, the symptom agent generated "Excessive worry" for a text describing pre-presentation nervousness about a single bounded event, because the word "worry" was sufficient for semantic matching. The CoT Step 3 gate, which explicitly checks whether worry is about a single event with a clear endpoint, resolved this class of error. Additional improvements included elimination of internal identifier leakage (claim IDs appearing in the report text), resolution of context agent JSON truncation, and elimination of coping strategy confabulation in report recommendation sections.

### 8.4 Limitations

The evaluation is limited by its small sample size (n = 5 test cases), the absence of ground-truth clinical annotations from a qualified clinician, and the use of a single local language model (Mistral 7B via Ollama). Cosine similarity thresholds were set heuristically and have not been validated against labelled clinical data. The differentiation assessment component did not produce actionable output in any evaluated case. The KB contains gaps in occupational stress and social pressures categories, meaning that presentations involving these stressors are validated against semantically adjacent rather than exact reference entries.

---

## 9. Architecture Classification

**The system is most accurately described as a multi-agent generate-then-validate pipeline with retrieval-assisted evidence grounding.** It is not a conventional RAG architecture.

### Justification

In a classic RAG (Retrieval-Augmented Generation) pipeline, retrieval occurs at the input stage: documents are retrieved from a knowledge base in response to the user's query, and those documents are injected into the LLM context before generation. The LLM generates its answer conditioned on the retrieved content.

AnxioSense inverts this pattern. Four specialised LLMs (emotion, symptom, context, referral agents) generate structured claim sets from the raw user text **before** any retrieval occurs. The knowledge base is consulted only after generation, not before: each generated claim is independently embedded and matched against the KB using cosine similarity to determine whether it has clinical support. This is generation-first, retrieval-second — the opposite of RAG's retrieval-first design.

The retrieval layer in AnxioSense functions as an evidence validation mechanism rather than a generation context mechanism. It answers the question "is this claim KB-supported?" rather than "what information should the generator use?" This pattern is more closely aligned with claim verification pipelines in the fact-checking and natural language inference literature than with conventional RAG.

In addition, the pipeline is explicitly multi-agent: four specialised extraction agents operate in parallel with distinct roles, followed by a claims consolidation step, a retrieval-validation step, and a synthesis agent. Each agent is prompted for a specific epistemic task (emotion analysis, symptom identification, contextual reasoning, referral classification) rather than general question answering. This specialisation-by-function design is architecturally distinct from both single-model RAG and tool-augmented chat.

The most precise architectural label is: **multi-agent generate-then-validate pipeline with retrieval-assisted evidence grounding**. A secondary accurate description is **retrieval-assisted validation pipeline**, which captures the novel use of the retrieval layer. The term "multi-agent RAG" may be used as a shorthand in contexts where precision is less critical, provided that the departure from the standard RAG pattern is acknowledged in the accompanying description.

---

*Generated from exported workflow runs under `src/mastra/public/evaluation/prompt-experiments/runs/` (cot-oneshot-v1 snapshots, 2026-06-28).*

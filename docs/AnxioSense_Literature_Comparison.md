# AnxioSense — Literature Comparison and Novelty Assessment

Prepared: July 2026  
Purpose: Pre-submission novelty audit for academic paper  
Scope: LLM-based mental health screening, clinical NLP, multi-agent AI, RAG systems

---

## Part 1: System Comparison Table

---

### System 1 — Mental-LLM
**Citation:** Xu et al., 2024. "Mental-LLM: Leveraging Large Language Models for Mental Health Prediction via Online Text Data." arXiv:2307.14385. (Under review / accepted EMNLP 2024 Findings.)

| Dimension | Detail |
|---|---|
| **Main contribution** | Systematic benchmark of 10+ LLMs (GPT-4, ChatGPT, LLaMA, Alpaca, Bloom, etc.) on mental health prediction tasks from social media text, under zero-shot, few-shot, and instruction-tuning conditions. |
| **What it already does** | Multi-task evaluation across stress detection (Dreaddit), depression detection (DepSeverity), suicide ideation (CSSRS). Compares classification accuracy across model families. Produces polarity/severity labels only — no generative report. No RAG. No clinical instrument. Single model. No safety layer. |
| **What AnxioSense does that Mental-LLM does not** | Multi-agent decomposition of reasoning; RAG over clinical literature; GAD-7 administration and deterministic scoring; functional impairment integration; explainable narrative report generation; deterministic safety override; grounding/validation agent; dual journal + social media modes. |
| **Remaining gap** | AnxioSense has no ablation comparing multi-agent vs. single-agent on the same datasets Mental-LLM uses. Without that, reviewers can argue the pipeline adds complexity without measurable gain. |
| **Opportunity for novelty** | AnxioSense can position itself as going beyond benchmark evaluation to a deployable pipeline — but it must show empirical gains over single-model baselines on at least one dataset to credibly claim improvement. |

---

### System 2 — MentaLLaMA
**Citation:** Yang et al., ACL 2024. "MentaLLaMA: Interpretable Mental Health Analysis on Social Media with Large Language Models."

| Dimension | Detail |
|---|---|
| **Main contribution** | Instruction-tuned LLaMA model for 8 mental health NLP tasks (depression detection, suicide risk, stress, etc.) on social media. Key differentiator: the model generates natural language explanations alongside labels — the first instruction-tuned LLM benchmark for interpretable mental health NLP. |
| **What it already does** | Instruction tuning for mental health tasks. Chain-of-thought style explanation generation. Multi-task across 8 conditions. Evaluated on Reddit-sourced data. Publicly released model weights and evaluation benchmark. No clinical instruments. No RAG. No multi-agent architecture. No user-facing deployment. No safety override. |
| **What AnxioSense does that MentaLLaMA does not** | Clinical instrument integration (GAD-7 with validated scoring thresholds); multi-agent pipeline where separate reasoning agents cover emotion, symptoms, context, and referral independently; RAG grounding against clinical literature; deterministic pre-LLM safety check; functional impairment reasoning; clinician vs. patient report modes; grounding validation agent. |
| **Remaining gap** | MentaLLaMA's explanations are fine-tuned into the model — they are trained to produce them. AnxioSense's explanations are emergent from the report agent's prompt. Without fine-tuning or calibration, reviewers will question whether the explanations are reliable or just fluent. |
| **Opportunity for novelty** | AnxioSense's strongest differentiator against MentaLLaMA is the hybrid validated-instrument + LLM approach. MentaLLaMA generates explanations from text alone; AnxioSense grounds its severity judgment in a psychometrically validated score AND LLM analysis. That combination does not exist in the interpretable mental health NLP literature. |

---

### System 3 — Conversational Mental Health Agents (Woebot, Wysa, ChatCounselor)
**Citations:** Fitzpatrick et al., JMIR Mental Health 2017 (Woebot); Liu et al., 2023, "ChatCounselor: A Large Language Models for Mental Health Support"; Qiu et al., 2023, "SMILE: Single-turn to Multi-turn Inclusive Language Expansion via ChatGPT for Mental Health Support."

| Dimension | Detail |
|---|---|
| **Main contribution** | Dialogue-based emotional support and psychoeducation. Woebot/Wysa use scripted CBT flows. ChatCounselor fine-tunes LLaMA on counseling dialogue. SMILE augments mental health dialogue data with GPT-4. |
| **What it already does** | Multi-turn conversation. Empathetic response generation. Some systems include mood tracking (Woebot). CBT-based interventions. User engagement over time. No clinical instrument integration (GAD-7 not used as structured instrument). No multi-agent reasoning. No RAG. No formal screening output. No safety override architecture (Woebot has some scripted safety responses). |
| **What AnxioSense does that these do not** | Structured anxiety screening (not open-ended counseling). Validated clinical instrument (GAD-7) as core pipeline input. Multi-agent analysis producing a structured report with referral level. RAG over clinical literature. Deterministic safety override. Explicit non-diagnosis scope and clinical report designed for downstream clinician review. |
| **Remaining gap** | Conversational systems have multi-turn context that AnxioSense lacks. A single journal entry or social media post is a one-shot input; these systems build a therapeutic relationship over sessions. This is a scope difference, not a flaw, but reviewers may ask why single-turn input is sufficient for meaningful screening. |
| **Opportunity for novelty** | AnxioSense's formal screening framing is clearly distinct from counseling agents — but you must articulate this boundary explicitly in the paper. The risk is conflation by reviewers who see "mental health + LLM" and assume chatbot. The framing must be: this is a clinical screening tool that generates a structured report, not a therapeutic intervention. |

---

### System 4 — CLPsych Crisis Detection Systems
**Citations:** Benton et al., CLPsych 2017; Zirikly et al., CLPsych 2019 (Shared Task A); Gaur et al., WWW 2019 "Knowledge-aware Assessment of Severity of Suicide Risk"; CLPsych 2021 Shared Task on Suicide Risk.

| Dimension | Detail |
|---|---|
| **Main contribution** | Classification of social media posts/users into suicide risk severity levels using NLP. CLPsych shared tasks provide standardised train/test splits and evaluation protocols. Gaur et al. introduced knowledge-graph grounding for risk severity. |
| **What it already does** | Binary or multi-class risk classification. Some systems use clinical knowledge (CSSRS levels). Gaur et al. use medical ontologies (UMLS) for grounding. Ensemble models. BERT fine-tuning. Some explanation via feature importance. No LLM generation. No clinical instrument. No user-facing report. |
| **What AnxioSense does that these do not** | Full generative report pipeline. GAD-7 as structured input. Multi-agent decomposition. RAG over curated clinical texts (vs. UMLS ontology lookup). Functional impairment reasoning. Patient-facing recommendation vs. researcher-facing label. LLM-based rather than fine-tuned classifier. |
| **Remaining gap** | CLPsych systems are evaluated on standardised shared-task benchmarks with ground-truth clinical annotations. AnxioSense has no equivalently rigorous evaluation protocol yet. The absence of a CLPsych-style evaluation will be the first thing a clinical NLP reviewer raises. |
| **Opportunity for novelty** | AnxioSense's safety override is thematically related to CLPsych crisis detection but architecturally different — deterministic pattern matching before the LLM rather than a trained classifier. This design choice (deterministic before AI, not AI for safety) is novel and defensible on reliability grounds. Paper it explicitly. |

---

### System 5 — Clinical Instrument NLP (BERT-PHQ, GAD-7 Prediction from EHR)
**Citations:** Jiang et al., EMNLP 2020 "Towards Automatic Prediction of Patient-Reported Outcomes from Clinical Notes"; Zhang et al., 2022, "Automated Depression Detection from Clinical Text"; various EHR-NLP papers at AMIA, ACL-BioNLP.

| Dimension | Detail |
|---|---|
| **Main contribution** | Predict PHQ-9 or GAD-7 item scores from clinical notes or patient-generated text using BERT-based classifiers. The clinical instrument is the target, not the input. |
| **What it already does** | Predicting clinical questionnaire responses from passive text (clinical notes, EHR). Structured output aligned with validated instruments. Fine-tuned on clinical text corpora. No LLM generation. No user-facing deployment. No RAG. No multi-agent. Clinician-facing output only. |
| **What AnxioSense does that these do not** | Uses GAD-7 as an active structured input (administered to the user) rather than predicting it from text. The combination of user-administered GAD-7 + free-text LLM analysis + discordance detection is architecturally inverted from EHR prediction systems. The result is a patient-facing screening tool rather than a clinical decision support annotation tool. |
| **Remaining gap** | These systems use clinical notes as input, giving them access to rich longitudinal patient data. AnxioSense uses a single session's input, which is nosier and less reliable. Reviewers from clinical informatics will notice this. |
| **Opportunity for novelty** | The inverted relationship — administering the validated instrument AND generating natural language analysis from the same session — is genuinely new. No paper in the GAD-7/PHQ NLP literature simultaneously administers and analyses the instrument in one pipeline. This is a clean novelty claim. |

---

### System 6 — RAG-based Mental Health Support
**Citations:** Several 2023–2024 papers on RAG for mental health counselling chatbots (no single dominant paper; genre includes "RAG-enhanced Depression Support" preprints and CLPsych 2024 system papers).

| Dimension | Detail |
|---|---|
| **Main contribution** | Use retrieval-augmented generation to ground mental health chatbot responses in clinical guidelines, CBT manuals, or peer-reviewed literature. Reduces hallucination in sensitive mental health responses. |
| **What it already does** | Retrieval from mental health corpora (CBT guides, DSM excerpts, online mental health resources). Grounded response generation. Some systems use FAISS or similar vector stores. Typically chatbot format, not screening format. No multi-agent. No clinical instrument. No validation agent. |
| **What AnxioSense does that these do not** | Multi-agent pipeline where RAG is one component of a broader reasoning chain, not the sole mechanism. Validation/grounding agent explicitly verifies report claims against retrieved evidence. GAD-7 integration. Discordance detection between clinical instrument and LLM analysis. Structured report with referral level rather than open-ended chatbot response. |
| **Remaining gap** | AnxioSense's RAG component has not been systematically evaluated. Is the retrieval actually helping? What is the knowledge base size, retrieval precision, and grounding rate? Without a RAG ablation (with RAG vs. without RAG), reviewers cannot assess its contribution. |
| **Opportunity for novelty** | Combining RAG with a multi-agent validation step that explicitly verifies retrieval-grounded claims is uncommon. The validation agent as a "retrieval auditor" — checking whether the report agent used evidence faithfully — is a contribution not seen in RAG mental health papers. |

---

### System 7 — Multi-Agent Medical AI
**Citations:** Tang et al., 2023, "MedAgents: Large Language Models as Collaborators for Zero-Shot Medical Reasoning" (arXiv); Wang et al., 2024, "AgentMD" and related multi-agent clinical reasoning papers; Nori et al., 2023, "Capabilities of GPT-4 on Medical Challenge Problems" (Microsoft Research).

| Dimension | Detail |
|---|---|
| **Main contribution** | Multi-agent or multi-role LLM frameworks for clinical reasoning (mostly medical Q&A, diagnosis assistance, or clinical decision support). Agents play specialist roles (radiologist, internist, etc.) and debate or vote to reach consensus. |
| **What it already does** | Role-based agent decomposition. Inter-agent debate protocols. Voting or consensus mechanisms. Strong performance on medical benchmarks (MedQA, USMLE). General medicine focus. No mental health specificity. No validated psychiatric instruments. No RAG (most systems). No safety override. No user-facing deployment. |
| **What AnxioSense does that these do not** | Domain-specific application to anxiety screening (vs. generic medical Q&A). Integration of psychometrically validated instrument (GAD-7) alongside agent reasoning. Safety override layer preceding the agent pipeline. RAG grounding against clinical literature. Explicit non-diagnosis framing with functional impairment and referral-level output. Patient-facing report generation. |
| **Remaining gap** | Multi-agent medical AI papers use inter-agent debate and consensus voting to improve accuracy. AnxioSense's agents run in parallel without an explicit debate or refinement step. There is no mechanism for one agent to challenge or refine another's output. This is a design limitation that reviewers familiar with MedAgents or debate-style agents will raise. |
| **Opportunity for novelty** | AnxioSense is the first multi-agent LLM pipeline explicitly designed for psychiatric screening (as opposed to general diagnostic reasoning). The argument is: psychiatric screening requires decomposing reasoning into emotion, symptom, context, and referral tracks in a way that general medical Q&A does not. If you can show this decomposition improves over a single-agent baseline, that is a domain-specific contribution to multi-agent clinical AI. |

---

### System 8 — IMHI / Explainable Mental Health NLP
**Citations:** Wang et al., 2024, "IMHI: Making LLMs More Interpretable for Mental Health Analysis" (CLPsych 2024 / ACL 2024 workshop); Ji et al., 2023, "MentalBERT: Publicly Available Pretrained Language Models for Mental Healthcare"; Yates et al., 2017 (CLPsych), "Depression and Self-Harm Risk Assessment in Online Forums."

| Dimension | Detail |
|---|---|
| **Main contribution** | IMHI: 105K instruction-response pairs for interpretable mental health analysis, spanning 10 tasks. Fine-tuned LLaMA produces structured explanations for classification decisions. MentalBERT: domain-adapted BERT pre-trained on mental health Reddit posts. |
| **What it already does** | Structured interpretable output (IMHI). Domain pre-training (MentalBERT). Multi-task mental health NLP. Social media as primary data source. Explanation generation alongside labels. No multi-agent. No clinical instrument. No RAG. No patient-facing deployment. No safety override. |
| **What AnxioSense does that these do not** | Architecture-driven interpretability (separate agents for each reasoning dimension) rather than post-hoc explanation generation from a single model. The report is interpretable by design: each section maps to a specific agent's output. GAD-7 deterministic scoring as an anchor that constrains LLM outputs. Grounding validation that checks report claims against clinical evidence. |
| **Remaining gap** | IMHI's interpretability is trained and therefore more reliable (the model has been optimised to explain). AnxioSense's interpretability is emergent from the report agent's prompt — it has not been evaluated for faithfulness (does the explanation actually reflect the reasoning that drove the output?). |
| **Opportunity for novelty** | AnxioSense's interpretability comes from architectural decomposition rather than post-hoc explanation, which is a more robust framing. The paper can argue that multi-agent decomposition provides structural interpretability that does not require fine-tuning and is auditable at the agent level. This is a genuinely different interpretability paradigm from IMHI/MentaLLaMA. |

---

## Part 2: Honest Novelty Assessment

### What is genuinely novel about AnxioSense

**1. The hybrid validated-instrument + LLM pipeline** is the strongest and cleanest novelty claim.  
No published system simultaneously administers the GAD-7, deterministically scores it, runs a multi-agent LLM analysis on the accompanying text, detects discordance between the two, and produces a functional-impairment-adjusted recommendation. This combination is new. The individual components exist (GAD-7 prediction from EHR text, LLM analysis, functional impairment questionnaires), but the architecture that integrates them in a user-facing screening tool does not.

**2. Deterministic safety layer before the AI pipeline** is uncommon and defensible.  
Most clinical AI safety work is about output filtering or RLHF alignment. AnxioSense's approach — pattern-matched crisis detection that bypasses the LLM entirely — is a design choice that no published LLM mental health screening paper appears to have taken. It is evaluable (false positive/negative rates) and clinically motivated.

**3. Multi-agent decomposition for psychiatric screening** is novel at the domain level, if not architecturally.  
Multi-agent medical AI exists (MedAgents, AgentMD) but targets general medicine. Decomposing psychiatric screening into emotion, symptom, context, and referral agents is domain-specific and requires justification specific to psychiatric assessment methodology. If the paper connects this decomposition to clinical assessment frameworks (e.g., the biopsychosocial model), it becomes a principled contribution rather than arbitrary complexity.

**4. Dual-modality design** (journal + GAD-7 vs. social media) is practically novel.  
Most systems target one modality. Demonstrating that a single architecture can be adapted to both clinical-instrument-augmented text and passively collected social media text, with appropriate mode-specific behaviour, is useful for the field.

---

### What reviewers will push back on

**1. "The multi-agent pipeline is chain-of-thought with extra steps."**  
This is the most dangerous critique. If a single Llama call with a complex prompt achieves the same accuracy as 6 agents, the architecture adds latency and cost without benefit. You must run an ablation: single-agent vs. multi-agent on the same dataset. Without this, the paper's core architectural claim is undefended.

**2. "No fine-tuning, no domain adaptation."**  
Mental-LLM and MentaLLaMA both show that fine-tuning significantly outperforms zero-shot prompting on mental health tasks. AnxioSense uses a prompted general model (Llama 3.3 70B). Reviewers will ask: does this model actually understand clinical anxiety language, or is it producing fluent but ungrounded text? This is partly addressed by the RAG component and the validation agent, but without a fine-tuned comparison, the question stands.

**3. "There is no rigorous evaluation against a ground-truth clinical label."**  
The implementation is complete, but without quantitative results on DAIC-WOZ, SMHD, or a dataset with clinical anxiety labels, the paper is a system description, not a research contribution. System description papers are acceptable at some venues (CLPsych system papers, COLING system demonstrations) but not at ACL/EMNLP main track.

**4. "The safety layer is untested."**  
The deterministic safety check has unit tests (coverage, precision), but no evaluation on a crisis detection benchmark (e.g., CLPsych Shared Task data, UMD Suicide Ideation Dataset). False negative rate for the safety check has direct clinical implications. A reviewer will flag this immediately.

**5. "The RAG component is unevaluated."**  
How large is the knowledge base? What is retrieval precision? Does RAG improve report quality compared to no-RAG? Without a RAG ablation, this component cannot be claimed as a contribution.

**6. "Anxiety-specific NLP is under-studied for a reason."**  
Anxiety is harder to detect from text than depression because its linguistic signature overlaps heavily with normal worry. If the system cannot demonstrate better-than-baseline performance on anxiety-specific data, reviewers will question the domain choice.

---

### Venue-specific novelty verdict

| Venue | Verdict | Rationale |
|---|---|---|
| **ACL / EMNLP main** | Unlikely without strong ablations and baselines | System papers must show significant empirical gains |
| **NAACL main** | Unlikely for the same reasons | |
| **CLPsych (ACL workshop)** | Strong candidate | System papers valued; clinical framing is appropriate; safety and GAD-7 integration are directly relevant |
| **COLING / EACL** | Plausible with empirical results | More receptive to system and architecture papers |
| **ACL BioNLP workshop** | Good fit | Clinical instrument integration is directly relevant |
| **EMNLP Findings** | Possible if evaluation is thorough | Less competitive than main track |
| **Nature Digital Medicine** | Not ready | Requires IRB approval, prospective study, clinical validation |
| **Communications Medicine** | Not ready | Same requirements as NDM |
| **JMIR Mental Health** | Possible | More accepting of system descriptions with usability/feasibility framing |
| **Journal of Biomedical Informatics** | Possible | If RAG and multi-agent ablations are included |

---

### The critical gap in one sentence

AnxioSense is architecturally novel and clinically motivated, but **it is currently a system description without empirical evidence** that the architecture outperforms simpler alternatives — and that gap is what separates a publishable paper from an impressive project.

---

### The three experiments that would close the gap

These are not feature additions — they are evaluation experiments that can be run on existing datasets without any code changes to AnxioSense.

**Experiment 1 — Multi-agent ablation** (most important)  
Run AnxioSense with all 6 agents vs. a single-agent baseline (one Llama call with all instructions combined) on the same input set drawn from DAIC-WOZ or SMHD. Compare: severity agreement with ground-truth GAD-7 labels; report coherence (BERTScore vs. clinical reference); hallucination rate (validation agent pass rate).

**Experiment 2 — RAG ablation**  
Run with and without retrieval. Compare grounding rate, hallucination detection rate, and severity accuracy. This isolates the RAG contribution.

**Experiment 3 — Safety check evaluation**  
Evaluate the deterministic safety check on the CLPsych 2019 Shared Task dataset (crisis vs. non-crisis posts). Report precision, recall, F1. Compare to a fine-tuned classifier baseline. This turns the safety component into a standalone evaluable contribution.

These three experiments can be run in the evaluation phase without changing a single line of AnxioSense's implementation code.

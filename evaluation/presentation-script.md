# AnxioSense — Full Presentation Script + Q&A Prep
**9 minutes presentation · 3 minutes Q&A**
Read this tonight. Say it out loud at least once.

---

## TITLE SLIDE
**⏱ ~30 seconds**

*"Good morning everyone. My name is Aya El-Dassouki and I'm presenting AnxioSense — a multi-agent, retrieval-augmented framework for explainable anxiety screening support, which is my EECS 4080 research project.*

*The core idea is this: instead of asking an AI to diagnose someone, we ask it to listen carefully, extract what the person actually said, check it against clinical knowledge, and produce a grounded, transparent summary — without ever making a diagnostic claim.*

*Let me walk you through what I've built."*

---

## SLIDE 01 — WHY ANXIOSENSE?
**⏱ ~1 minute**

*"There are three problems I want to address.*

*First — access. One in five Canadians experience a mental health challenge annually, but wait times for support can stretch to months. A lot of people never get help at all.*

*Second — existing AI tools for mental health often hallucinate. They generate confident-sounding outputs that aren't grounded in what the person actually said. That's dangerous in a mental health context.*

*Third — privacy. Most AI systems send your data to external cloud APIs. For something as sensitive as mental health, that's a serious concern.*

*My contribution addresses all three. AnxioSense is a multi-agent pipeline that runs entirely locally — no internet connection, no external API — uses retrieval-augmented generation to ground every finding in clinical evidence, and produces an explainable, non-diagnostic screening report.*

*The research goal is: can a locally-run multi-agent LLM pipeline reliably screen for anxiety-related patterns without hallucinating, without diagnosing, and without leaving the device?"*

**What they'll ask:**
> "What specific papers informed your work?"

*"My literature review covers three main areas — multi-agent LLM systems, RAG for clinical NLP, and responsible AI in mental health. Key works include research on hallucination in clinical LLMs, and frameworks for explainable AI in health contexts. The full citation list is in my dissertation."*

> "How do you define explainability here?"

*"In AnxioSense, explainability operates at the claim level. Every finding in the report traces back to a specific piece of the user's text, validated against a specific knowledge base chunk. The user can see what was found, what supported it, and what was filtered out. That's different from a black-box classifier that just outputs a score."*

---

## SLIDE 02 — SYSTEM ARCHITECTURE
**⏱ ~2 minutes — spend time here, it's the heart of the talk**

*"Let me walk you through the pipeline. There are eight steps.*

*Step 1: The user provides two inputs — a free-text journal entry, and optionally, the GAD-7 questionnaire, which is a validated 7-item anxiety screening instrument.*

*Steps 2 through 5 are four specialized agents running in parallel using Mastra's parallel execution. The emotion agent detects emotional tone and affect. The symptom agent extracts anxiety-related indicators grounded in what the user actually said. The context agent identifies life stressors — academic, workplace, relationship, financial. And the referral agent assesses risk level and assigns one of three values: low, moderate, or urgent.*

*Step 6 is the Claim Builder — a deterministic TypeScript step that takes the outputs from all four agents, normalises them into structured claim objects, and tags each one with its source agent.*

*Step 7 is Clinical Knowledge Retrieval — this is our RAG component. Each claim is embedded using fastembed, queried against our LibSQL vector store, and the top matching knowledge base chunks are returned with cosine similarity scores.*

*Step 8 is Evidence Validation — another deterministic step that applies cosine similarity thresholds. Claims scoring above 0.72 are supported. Above 0.55 — partially supported. Below 0.55 — dropped entirely. This is how we prevent hallucinations from reaching the report.*

*Finally, the Report Generator — Mistral 7B running locally — receives only the validated, pre-categorised claims and generates the structured screening report. The GAD-7 result is then injected directly into the report in TypeScript — the LLM never sees it — which guarantees the item-level breakdown is always preserved verbatim."*

**What they'll ask:**
> "Is the Evidence Validation step an LLM agent or a rule-based process?"

*"It's fully deterministic — pure TypeScript, no LLM involved. It applies cosine similarity thresholds to the scores already computed during retrieval. This was a deliberate design choice: deterministic validation gives reproducible, auditable results. You can explain exactly why a claim was accepted or rejected."*

> "Why generation-first instead of classical RAG?"

*"Classical RAG retrieves based on the user's raw query, then generates. The problem is a journal entry is vague — retrieving on it directly gives noisy results. By generating structured claims first — 'Excessive worry', 'Academic stress' — we have precise retrieval targets. The KB chunks are matched against well-formed clinical claims rather than conversational fragments, which dramatically improves retrieval precision."*

> "How does the Claim Builder decide what constitutes a claim?"

*"It parses the JSON output from each agent and maps it to typed claim objects. Each agent is prompted to return a specific JSON structure — for example, the symptom agent returns a `possible_anxiety_indicators` array. The claim builder reads that array and wraps each item into a claim with an ID, source agent tag, and category. It's rule-based — no LLM."*

---

## SLIDE 03 — TECHNOLOGY STACK
**⏱ ~30 seconds — keep this fast**

*"On the backend — TypeScript with the Mastra SDK for workflow orchestration, Mistral 7B running locally via Ollama, fastembed for vector embeddings, and LibSQL as our vector store.*

*On the frontend — we're building with React, which is planned for Week 2.*

*The key architectural decision across all of this is that nothing leaves the device. Every component — the model, the embeddings, the vector store — runs locally. That's essential for a mental health application where privacy is non-negotiable."*

**What they'll ask:**
> "Why Mastra and not LangChain or LangGraph?"

*"Three reasons. First, Mastra is TypeScript-native. My entire backend is TypeScript, and using a framework in the same language means no context-switching, cleaner type safety across the pipeline, and better IDE support. LangChain's TypeScript port is significantly less mature than its Python version.*

*Second, Mastra has first-class support for parallel agent execution with `.parallel()` — running four agents simultaneously is a single method call. In LangChain I'd be managing concurrent promises manually.*

*Third, Mastra gives you a built-in development studio — Mastra Studio — which lets you visualise the workflow graph, inspect agent inputs and outputs, and run test cases interactively. That's been invaluable for debugging and for this demo.*

*LangChain is excellent for Python-first projects, especially research that needs tight integration with the Hugging Face ecosystem. For a TypeScript backend with a focus on workflow structure and local execution, Mastra was the better fit."*

> "Why Mistral 7B specifically?"

*"Two reasons — privacy and capability at scale. Privacy: Mistral 7B runs fully locally via Ollama. Mental health data cannot go to an external API. Capability: at 7 billion parameters with CoT + one-shot prompting, it achieves strong structured output quality. We set temperature to 0.1 for maximum consistency, which matters in a screening context where you need reproducible outputs. A larger local model like Mistral 22B would improve performance, but requires more hardware than a standard laptop."*

> "Why LibSQL over Pinecone or FAISS?"

*"Pinecone is cloud-hosted — which violates our local-only constraint immediately. FAISS is excellent but requires more setup for persistence and doesn't integrate as cleanly with Mastra's tooling. LibSQL gives us persistent, file-based vector storage that runs entirely on-device, which fits our architecture perfectly."*

---

## SLIDE 04 — WHAT HAS BEEN IMPLEMENTED?
**⏱ ~45 seconds**

*"As of today, all ten core backend components are complete.*

*The four extraction agents, the claim builder, the retrieval agent, the evidence validation step, the report generator — all built and working.*

*Two features I want to highlight specifically: GAD-7 integration — the scoring is fully deterministic, calculated in TypeScript, and the result is injected into the final report without ever passing through the LLM, so it can never be condensed or modified by the model.*

*And automatic evaluation export — every time the workflow runs, it writes a complete timestamped record to disk containing the user input, every agent output, all claims, retrieval results, validation output, and the final report. This makes evaluation fully reproducible."*

**What they'll ask:**
> "What does the automatic evaluation export produce?"

*"A timestamped Markdown file under `evaluation/prompt-experiments/runs/`. It captures the entire pipeline trace for one run — every agent's raw JSON output, the claims that were built, which chunks were retrieved, their similarity scores, which claims passed validation, and the final report. It's designed so I can compare runs from different prompt versions side by side."*

---

## SLIDE 05 — LIVE WORKFLOW
**⏱ ~1 minute**

*"This is the pipeline running in Mastra Studio — you can see the workflow graph here, showing the parallel agent execution branching out, converging at the claim builder, then flowing through retrieval, validation, and the report step.*

*And this is the agent output panel — you can see the raw JSON the emotion agent returned for one of our test cases, with the emotional indicators it extracted and the reasoning behind each one.*

*The whole thing runs locally on my laptop. No internet connection is needed once Ollama and the server are running."*

---

## SLIDE 06 — RECENT DEVELOPMENT PROGRESS
**⏱ ~1 minute**

*"I want to show the delta between where the system was and where it is now.*

*Previously, the pipeline used basic zero-shot prompting. There was no standardized assessment tool, no structured knowledge base, no validation layer, and evaluation was done manually by reading outputs.*

*The current version introduces five major improvements.*

*Chain-of-thought plus one-shot prompting on all four extraction agents — this alone had the biggest impact on output quality, eliminating diagnostic label hallucinations and invalid JSON structures.*

*Deterministic GAD-7 integration — the scoring is now a pure TypeScript function, the concern pattern is generated without LLM involvement, and it's injected into the report post-generation so the model cannot alter it.*

*Clinical knowledge base retrieval — we now have eight curated knowledge base files covering anxiety indicators, depression indicators, shared symptoms, contextual stressors including nine categories from academic stress to social pressure, referral guidelines, and safety boundaries.*

*Cosine-similarity evidence validation — every claim is now checked against the knowledge base before reaching the report.*

*And automatic evaluation export — making every run reproducible and comparable."*

**What they'll ask:**
> "What was the quantitative improvement from CoT + one-shot?"

*"In our preliminary evaluation across five test cases, moving from zero-shot baseline to CoT plus one-shot eliminated diagnostic label hallucinations entirely. The baseline was producing outputs like 'Anxiety disorder' and 'Depression' as extracted symptoms — which are diagnostic labels the user never mentioned. The current version produces only grounded, user-text-anchored indicators. The referral agent was also producing invalid enum values like 'elevated' in the baseline — that's now handled with a validated constrained enum and a conservative fallback to 'moderate'."*

> "How did you determine the cosine similarity thresholds?"

*"They were calibrated empirically across our five baseline test cases. Strong semantic matches — for example, 'Excessive worry' against our anxiety indicators chunk — scored between 0.78 and 0.81. Moderate matches like sleep disruption scored around 0.73. Noise scored below 0.55. We set 0.72 as the supported threshold because it consistently separated meaningful matches from borderline ones. A sensitivity analysis of these thresholds is planned for the dissertation evaluation."*

---

## SLIDE 07 — PRELIMINARY EVALUATION / COMPARISON
**⏱ ~1 minute**

*"I want to show you a concrete example of what the prompt engineering improvements actually changed.*

*Both columns use the same input — a multi-symptom case describing worry, sleep disruption, concentration difficulty, avoidance, and racing thoughts. Same model, same temperature.*

*On the left — the zero-shot baseline. The symptom agent hallucinated diagnostic labels: 'Anxiety disorder' and 'Depression' — neither of which the user mentioned. The referral agent returned 'elevated' which isn't a valid value in our pipeline. And the report added coping strategies like journaling and deep breathing, and invented specific resource types like counselling centres — none of which were in the validated output.*

*On the right — CoT plus one-shot. All five symptoms correctly extracted, grounded in explicit user language. Valid referral enum. Report sections contain only validated findings. No invented resources. No coping strategies. Hallucination rate: zero.*

*The evaluation is preliminary — five test cases is not a large sample, and I want to be transparent about that. The dissertation will include a systematic evaluation with more cases and inter-rater reliability measurement. But the directional improvement is clear and consistent across all five runs."*

**What they'll ask:**
> "Five cases is a very small evaluation. How do you justify your claims?"

*"You're right, and I'm not making general performance claims from five cases. These cases were used to calibrate the system and compare prompt versions — they represent intentional coverage: one mild case, one academic stress case, one multi-symptom case, one urgent safety case, and one workplace stress case. The numbers I've cited are directional indicators, not validated benchmarks. The dissertation evaluation will systematically expand this with more diverse cases and a second rater to establish inter-rater reliability on the gold-standard labels."*

---

## SLIDE 08 — LIVE DEMO
**⏱ ~1 minute**

*"Let me show you a live run.*

*I'm going to input a journal entry describing academic stress and worry, along with GAD-7 responses.*

[paste Case 1 JSON into Mastra Studio]*

*You can see the four agents executing — emotion, symptom, context, and referral — running in parallel. The claim builder then aggregates their outputs. The retrieval step embeds each claim and queries the knowledge base. Evidence validation applies the cosine similarity thresholds. And the report agent generates the final output.*

[once output appears, open demo-report-viewer.html, paste finalReport]*

*The report is structured into eight sections. Section 0 is the GAD-7 result — you can see the concern pattern label and the item-by-item breakdown, all injected in TypeScript after the LLM finished so the model couldn't alter it. Sections 1 through 4 contain the validated emotional indicators, symptom indicators, and contextual factors. Section 7 gives the referral recommendation. And the report closes with the mandatory non-diagnostic disclaimer."*

---

## SLIDE 09 — NEXT STEPS
**⏱ ~30 seconds**

*"Three priorities for the remaining weeks.*

*First — the frontend. I'm building a user-facing interface in React that gives users a calming journal input, a step-by-step GAD-7 questionnaire, a loading screen showing the agents working, and a clean rendered report. That's Week 2.*

*Second — expanded evaluation. More test cases, more scenarios, and a systematic comparison of prompt versions.*

*Third — the dissertation. Chapters 1, 2, 3, and 5 are the remaining writing. Chapter 4, the implementation chapter, is substantially complete.*

*The backend is production-ready for continued evaluation. Thank you — I'm happy to take questions."*

---

---

# FULL Q&A BANK
*Every question they could possibly ask, with your ideal answer.*

---

**"Why Mastra and not LangChain or LangGraph?"**

*"Three reasons. TypeScript-native — my entire backend is TypeScript, and Mastra is written for TypeScript first, not ported from Python. LangChain's TS version is significantly less mature. Second, first-class parallel execution — `.parallel()` is a single method call in Mastra. Third, Mastra Studio — a built-in visual debugger that lets me inspect every agent's input and output interactively. For a TypeScript-first project with a focus on workflow structure and local execution, Mastra was the right tool. LangChain would have been the choice if I were in Python and needed tight Hugging Face integration."*

---

**"Why a local model? Why not GPT-4 or Claude?"**

*"Mental health data is among the most sensitive personal information someone can share. Routing it through any external API — even a reputable one — introduces data privacy risks that are unacceptable in a clinical-adjacent context and potentially non-compliant with PIPEDA in Canada. Mistral 7B via Ollama runs entirely on-device. No data ever leaves the machine. The tradeoff is capability — a larger cloud model would produce better outputs. But privacy is non-negotiable here, and our prompt engineering compensates for the capability gap."*

---

**"Is this system clinically validated?"**

*"No, and I want to be clear about that. AnxioSense is a research prototype, not a clinical tool. Clinical validation would require a formal study with human participants, ethical approval, comparison against gold-standard clinical assessments, and review by qualified mental health professionals. What we have is a preliminary technical evaluation showing the system produces grounded, non-diagnostic outputs consistently across our test cases. Clinical validation is explicitly out of scope for an undergraduate research project and is noted as future work."*

---

**"How does this differ from just asking ChatGPT about your anxiety?"**

*"Three key differences. First, AnxioSense is architecture-constrained to be non-diagnostic — the prompts, the validation layer, and the report structure all enforce this. ChatGPT will often produce diagnostic-sounding language. Second, every finding in AnxioSense is validated against a clinical knowledge base before reaching the report — claims without KB support are dropped. ChatGPT has no such grounding mechanism. Third, AnxioSense runs locally — your data never leaves your device. ChatGPT sends everything to OpenAI's servers."*

---

**"What happens in the urgent safety case?"**

*"If the referral agent returns `risk_level: 'urgent'` — which happens when the user describes self-harm ideation, suicidal thoughts, or immediate danger — the entire report generation step is bypassed. The LLM is never called. Instead, a hardcoded crisis safety notice is returned immediately. This is a critical safety decision: you cannot trust a generative model to handle an immediate safety concern reliably. The hardcoded response directs the user to emergency services, crisis lines, and trusted contacts, and explicitly states that the screening tool cannot provide crisis support."*

---

**"The differentiation assessment returned 'unclear' five times — doesn't that mean it's broken?"**

*"Yes, and I'm transparent about it. The differentiation assessment is designed to identify whether the pattern of indicators leans more toward anxiety or depression. It returned 'unclear' across all five of our test cases. My interpretation is that the agent's decision criteria are underspecified — the prompt doesn't give it enough discriminative signal, and our `anxiety_vs_depression` knowledge base file may not provide sufficiently distinct embeddings to separate the two conditions at the retrieval level. It's a known limitation, documented in the evaluation, and it's on the roadmap. Importantly, 'unclear' is a safe default — the system doesn't misclassify, it defers."*

---

**"How do you prevent the model from diagnosing even if the user pushes it?"**

*"Enforcement is layered. The report agent's system prompt explicitly prohibits diagnostic language — words like 'diagnosis', 'clinically significant', 'you have anxiety' are forbidden. It also requires cautious hedging on every claim: 'may reflect', 'could be consistent with', 'the available text suggests'. The evidence validation step removes any claim without KB support, which prevents the model from generalising beyond what the user said. And the report is structured — Section 2 receives only emotion claims, Section 3 only symptom claims — so the model can't import unsupported content into a section. The final sentence of every report is hardcoded in the system prompt and cannot be changed by the model."*

---

**"What are PIPEDA implications for a deployed version?"**

*"Under PIPEDA, mental health information is sensitive personal information requiring explicit informed consent. A deployed version would need: informed consent that clearly explains the tool's purpose and limitations, encryption for any data at rest, a clear data retention and deletion policy, and explicit disclosure that this is a screening support tool, not a clinical service. The local-only architecture makes PIPEDA compliance significantly easier — we never transmit data to a third party. A future web-deployed version would require a formal privacy impact assessment."*

---

**"How would clinicians actually use this?"**

*"The intended use case is pre-screening support for young adults — someone noticing stress or worry who wants to understand their experience before deciding whether to seek help. The report is non-diagnostic and ends with a clear recommendation to speak with a healthcare professional if experiences persist. A secondary use case, which Dr. Abel outlined, is as a calibration tool in a primary care setting — a patient completes AnxioSense before an appointment, and the clinician reviews the screening summary as context for the intake assessment. Similar to how a PHQ-9 or GAD-7 is used before a GP appointment."*

---

**"Why not fine-tune the model on clinical data?"**

*"Fine-tuning on clinical data would require a labeled dataset of mental health narratives, which raises significant ethical and legal concerns — patient data, IRB approval, privacy compliance. For an undergraduate research project, that's out of scope. More importantly, our architecture deliberately separates clinical knowledge from the model — the KB contains the domain expertise, the LLM is responsible only for language understanding and generation. This means we can update clinical knowledge by editing text files without retraining anything. Fine-tuning would bake clinical knowledge into model weights, making it harder to audit, update, or correct."*

---

**"What is the latency of a full run?"**

*"Approximately 60 to 90 seconds on a MacBook Pro with Mistral 7B running via Ollama. The parallel execution of the four agents means total extraction time is roughly equal to the slowest single agent rather than four times one agent. The report generation step is the longest single step. For a screening tool with an asynchronous flow — user submits, loading screen appears, report arrives — 90 seconds is acceptable. If latency were a hard constraint, a quantized version of Mistral (Q4) or a smaller model could reduce this significantly."*

---

**"How do you handle multilingual input?"**

*"Currently we don't — AnxioSense is English-only. The knowledge base is in English, the agent prompts are in English, and Mistral 7B's instruction-following quality degrades significantly in other languages at this parameter count. Multilingual support would require either a multilingual embedding model, translated knowledge base files, or a multilingual LLM. It's noted as a future direction in the dissertation."*

---

**"What's your inter-rater reliability for your evaluation?"**

*"We don't have inter-rater reliability measurements yet — I'm the sole rater for the current five-case evaluation. This is a known limitation. For the dissertation evaluation I plan to have a second rater independently label the same test cases using the same gold-standard criteria, then compute Cohen's kappa to quantify agreement. Without this, the evaluation is single-rater and subject to my own interpretation biases."*

---

# TONIGHT'S CHECKLIST
```
[ ] Read this script out loud once — full 9 minutes
[ ] Practise Q1 (Mastra vs LangChain) and Q2 (five test cases) — most likely
[ ] Open Mastra Studio and do a test run with Case 1 JSON
[ ] Confirm demo-report-viewer.html opens and renders the output
[ ] Make sure Ollama is running before you leave the house tomorrow
[ ] Have VS Code open with the agent files ready to show prompts if asked
[ ] Breathe. You know this better than anyone in that room.
```

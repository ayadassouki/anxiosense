# Model-invalid output audit — AnxioSense publication experiments
## AI-Assistance Disclosure

Generative AI tools were used to assist with the development of audit scripts, organization and classification of invalid-output cases, and drafting and editing portions of this report. All quantitative findings reported here were derived from the frozen AnxioSense experimental artifacts and original raw model outputs. Automated classifications were validated against the underlying records, and hallucination candidates were manually reviewed. AI-generated suggestions were not treated as experimental evidence, and the original frozen experimental results were not modified as part of this audit.

**Version 2 (complete coverage), 2026-09-25.** Supersedes the partial version of the same date, which could
inspect only 937 of 1,986 records. Section L lists every headline finding that changed.

**Status:** READ-ONLY audit. No code, result, parser, prompt, raw file or frozen artifact was modified. No
experiment was rerun and no model API was called. No output was repaired and then scored: the recoverability
fields are descriptive and sit *beside* the frozen result, never in place of it.

**Coverage: 1,986 of 1,986 (100%).** Every model-invalid record in the frozen grid is classified from its own
raw terminal attempt. There are no `RAW_UNAVAILABLE` rows.

## Provenance of the evidence

The raw stores for three source runs were read from a copy outside the working repository
(`~/AnxioSense_provenance/master_evidence_2026-09-22/external_run_evidence/publication_experiments/runs`).
Before any of them was used, `code/02_extract_raws.py` compared each store's SHA-256 against the
`raw_attempts_sha256` recorded for that run in `descriptive_2026-09-21/source_parse_summaries/`. A store that
does not match the hash the frozen results were derived from is **refused**, not used with a warning.

| Source run | Store used | Provenance gate |
|---|---|---|
| `pub_001_dreaddit_qwen` | in-repo `runs/` | match `9ae3a57f…` |
| `pub_002_dreaddit_mistral` | in-repo `runs/` | match `bc69fccd…` |
| `pub_003_dreaddit_llama` | external evidence | match `44bdeca9…` |
| `pub_005_dreaddit_phi` | in-repo `runs/` | match `c3e584ef…` |
| `pub_006_goemotions715_mistral` | in-repo `runs/` | match `04f96ca2…` |
| `pub_007_goemotions715_qwen` | external evidence | match `bc6cd1a5…` |
| `pub_008_goemotions715_phi` | external evidence | match `fd9ebde7…` |
| `pub_009_goemotions715_llama` | in-repo `runs/` | match `6fd4ddf6…` |
| `pub_012_goemotions715_gemma_coreweave` | in-repo `runs/` | match `c4f5bbb7…` |

All nine pass. The `raw/index.jsonl` of each external run was checked the same way and also matches. Every row
records the store its raw came from in `raw_store_path`.

**Frozen-artifact integrity.** All 32 files of `descriptive_2026-09-21/` were re-hashed and compared file by
file against the 2026-09-21 freeze inventory: 0 changed, 0 missing, 0 added. See `VALIDATION.md`.

**Source of truth.** `authoritative_records.jsonl` decides *which* records are model-invalid. Each is joined to
its terminal raw attempt by `terminal_attempt_uuid → attempt_uuid`. Classification derives from the actual raw
text and nothing else.

---

## A. Executive totals

| | Dreaddit | GoEmotions | Both |
|---|---|---|---|
| Total records | 53,625 | 46,725 | 100,350 |
| Safety intercepts (pre-model, excluded from attribution) | 1,200 | 75 | 1,275 |
| Attributable records | 52,425 | 46,650 | 99,075 |
| Valid predictions | 51,826 | 45,263 | 97,089 |
| **Model-invalid records** | **599** | **1,387** | **1,986** |
| Infrastructure failures | **0** | **0** | **0** |
| Invalid rate (÷ attributable) | **1.143%** | **2.973%** | **2.005%** |
| Unique samples affected | 254 of 715 | 448 of 623 | — |
| Raw evidence inspected | 599 (100%) | 1,387 (100%) | 1,986 (100%) |

Safety intercepts are deterministic and model-independent: exactly 16 per Dreaddit run (the same 16 sample IDs
every time) and 1 per GoEmotions run (`ge_eelf9bs`). They fire before any model call — 0 tokens, ~84 ms, all
agent raw fields `None` — and are excluded from model attribution by `MetricPolicy 1.0.0`.

Infrastructure failures are zero *in the scored grid*. 661 transport failures occurred at the attempt level
(660 HTTP 504, 1 model mismatch) and retry plus explicit re-dispatch recovered every one. Five of the 1,986
invalid rows took more than one dispatch attempt; all terminated `OK`, so their invalid verdict is a parse
outcome, never a transport outcome.

---

## B. Dataset × model × strategy

Rates are over 3,495 attributable records per Dreaddit cell and 3,110 per GoEmotions cell (5 runs pooled).
Per-run counts are in `invalid_outputs_row_level.csv`.

### B.1 Dreaddit

| Model | Strategy | Invalid | Rate | Unique samples | Categories |
|---|---|---|---|---|---|
| Gemma 4 31B | ZS / ZS-CoT / 1S-CoT | 0 / 0 / 0 | 0.00% | 0 | — |
| Llama 4 Scout | ZS | 106 | 3.03% | 80 | bare_string_in_object 82; refusal 10; prose/markdown 8; missing_delimiter 5; truncation 1 |
| Llama 4 Scout | ZS-CoT | 52 | 1.49% | 47 | bare_string_in_object 38; prose/markdown 8; refusal 5; missing_delimiter 1 |
| Llama 4 Scout | 1S-CoT | 8 | 0.23% | 4 | refusal 5; prose/markdown 3 |
| Mistral Small 4 | ZS | 1 | 0.03% | 1 | unescaped_quote 1 |
| Mistral Small 4 | ZS-CoT | 1 | 0.03% | 1 | unescaped_quote 1 |
| Mistral Small 4 | 1S-CoT | 0 | 0.00% | 0 | — |
| Phi-4 | ZS | 106 | 3.03% | 96 | refusal 48; prose/markdown 41; missing_delimiter 8; invalid_risk_level 4; truncation 3; off_task_schema 1; escaping 1 |
| Phi-4 | ZS-CoT | 29 | 0.83% | 26 | refusal 10; prose/markdown 9; invalid_risk_level 5; truncation 2; unescaped_quote 1; off_task_schema 1; missing_delimiter 1 |
| Phi-4 | 1S-CoT | 16 | 0.46% | 14 | prose/markdown 5; truncation 5; refusal 4; missing_delimiter 2 |
| Qwen3.5 27B | ZS | 7 | 0.20% | 2 | repeated_or_restarted_json 7 |
| Qwen3.5 27B | ZS-CoT | **269** | **7.70%** | **65** | malformed_json_escaping 263; repeated_or_restarted 6 |
| Qwen3.5 27B | 1S-CoT | 4 | 0.11% | 1 | repeated_or_restarted_json 4 |

### B.2 GoEmotions

| Model | Strategy | Invalid | Rate | Unique samples | Categories |
|---|---|---|---|---|---|
| Gemma 4 31B | ZS | 0 | 0.00% | 0 | — |
| Gemma 4 31B | ZS-CoT | 0 | 0.00% | 0 | — |
| Gemma 4 31B | 1S-CoT | 7 | 0.23% | 7 | empty_object 6; repeated_or_restarted 1 |
| Llama 4 Scout | ZS | 113 | 3.63% | 47 | OOV 100; refusal 13 |
| Llama 4 Scout | ZS-CoT | 193 | 6.21% | 71 | OOV 175; refusal 6; prose/markdown 5; commentary 5; truncation 2 |
| Llama 4 Scout | 1S-CoT | 143 | 4.60% | 42 | OOV 143 |
| Mistral Small 4 | ZS | 17 | 0.55% | 8 | empty_object 11; OOV 6 |
| Mistral Small 4 | ZS-CoT | 19 | 0.61% | 6 | OOV 10; empty_object 9 |
| Mistral Small 4 | 1S-CoT | 12 | 0.39% | 5 | refusal 5; OOV 5; empty_object 2 |
| Phi-4 | ZS | 191 | 6.14% | 134 | OOV 104; refusal 72; prose/markdown 12; off_task_schema 1; missing_required_field 1; other 1 |
| Phi-4 | ZS-CoT | 183 | 5.88% | 105 | OOV 159; refusal 24 |
| Phi-4 | 1S-CoT | **499** | **16.05%** | **356** | **empty_object 419**; OOV 51; refusal 25; prose/markdown 2; commentary 1; off_task_schema 1 |
| Qwen3.5 27B | ZS | 0 | 0.00% | 0 | — |
| Qwen3.5 27B | ZS-CoT | 0 | 0.00% | 0 | — |
| Qwen3.5 27B | 1S-CoT | 10 | 0.32% | 2 | OOV 10 |

Four cells produced **no invalid output at all**: Gemma ZS and ZS-CoT, and Qwen ZS and ZS-CoT, on GoEmotions
(3,110 attributable records each). Gemma produced **zero** invalid Dreaddit outputs across 10,485 attributable
records.

---

## C. Failure taxonomy

Percentages are of all **1,986** invalid records. Definitions and per-category coverage are in
`failure_taxonomy_summary.csv`.

| Category | n | % | Datasets | Models |
|---|---|---|---|---|
| out_of_vocabulary_label | 763 | 38.4% | GoEmotions | Llama, Phi-4, Mistral, Qwen |
| empty_object | 447 | 22.5% | GoEmotions | Phi-4, Mistral, Gemma |
| malformed_json_escaping | 264 | 13.3% | Dreaddit | Qwen, Phi-4 |
| refusal_or_deflection | 227 | 11.4% | both | Phi-4, Llama, Mistral |
| bare_string_in_object_position | 120 | 6.0% | Dreaddit | Llama |
| prose_or_markdown_instead_of_required_json | 93 | 4.7% | both | Phi-4, Llama |
| repeated_or_restarted_json | 18 | 0.9% | both | Qwen, Gemma |
| missing_json_delimiter | 17 | 0.9% | Dreaddit | Phi-4, Llama |
| apparent_truncation | 13 | 0.7% | both | Phi-4, Llama |
| invalid_risk_level | 9 | 0.5% | Dreaddit | Phi-4 |
| commentary_inside_structured_field | 6 | 0.3% | GoEmotions | Llama, Phi-4 |
| off_task_schema | 4 | 0.2% | both | Phi-4 |
| unescaped_quote_in_string | 3 | 0.2% | Dreaddit | Mistral, Phi-4 |
| missing_required_field | 1 | 0.1% | GoEmotions | Phi-4 |
| malformed_json_other | 1 | 0.1% | GoEmotions | Phi-4 |

Secondary labels: `prose_or_markdown_instead_of_required_json` 399, `missing_required_field` 65,
`degenerate_repetition` 10, `hallucination_confirmed` 4,
`description_instead_of_quotation_in_evidence` 3, `commentary_inside_structured_field` 1,
`prompt_scaffolding_quoted_as_user_text` 1.

**Three categories were added on the evidence and did not exist in the partial audit:**
`bare_string_in_object_position` (120), `unescaped_quote_in_string` (3) and — as a secondary label —
`prompt_scaffolding_quoted_as_user_text`. `malformed_json_other` shrank from a 124-record residual bucket to
a single record once the underlying causes were named. `missing_raw_field` never occurred: every terminal
attempt stored an agent output.

### C.1 out_of_vocabulary_label — 763 (38.4%)

**Definition.** The payload parses cleanly and the first emotion is not a key of the frozen
`ANXIOSENSE_TO_EVAL_CLASS` map (`anxiety, fear, frustration, hopelessness, loneliness, sadness, stress`).

**Why the parser rejects it.** `parse_goemotions` reads the payload, calls `primary_emotion()`, and finds no
mapping. Assigning one would be a methodology change, not a recovery. Nothing is malformed: this is a
*vocabulary* failure.

**Most frequent labels across all 763:** happiness 104, excitement 85, joy 79, love 51, **panic 49**,
disappointment 30, nostalgia 24, hope 17, hurt 16, surprise 16, happy 16, amusement 16, anger 16, shame 13,
disgust 13, relief 13. The bulk is positive or non-distress affect the five-class set does not contain, with
one notable exception: `panic` (49) is squarely a distress term and still has no mapping.

> **Example 1** — `ge_eczje98` · Llama 4 Scout · 1S-CoT · run 1 · ground truth `non_distress`
> ```json
> {"emotions":["joy"],"emotional_intensity":"low","evidence_from_text":["I love this!","It's nice to hear of a positive outcome on here."]}
> ```
> Both quoted spans were located verbatim in the input.

> **Example 2** — `ge_edvha8c` · Mistral Small 4 · ZS · run 3 · ground truth `non_distress`
> ```json
> {"emotions":["anger"],"emotional_intensity":"moderate","evidence_from_text":["They literally don't have enough time on the planet to regret their actions."]}
> ```
> `anger` is a plausible reading; it is simply not one of the five evaluation classes.

### C.2 empty_object — 447 (22.5%)

**Definition.** The first balanced JSON object in the payload parses and is empty, so there is no `emotions`
key. Detected whether the object stands alone or is followed by the model's reasoning prose.

**Why the parser rejects it.** Strict parse fails on the fenced payload; fence-stripping yields `{}`, which
parses but has no `emotions` key, so `_emotions_from_obj` returns `None`; the embedded-object and array-salvage
strategies find nothing.

**Why this matters more than any other category.** `{}` is **not** `{"emotions": []}`. The latter is a valid
`non_distress` prediction under the frozen methodology; the former contains no prediction at all. Equating
them would invent a prediction, which `emotion_payload.py` explicitly refuses ("recover, never invent").

| Model | bare `{}` | `{}` + trailing reasoning prose | total |
|---|---|---|---|
| Phi-4 | 37 | 382 | 419 |
| Mistral Small 4 | 22 | 0 | 22 |
| Gemma 4 31B | 6 | 0 | 6 |

**Cross-check against `ISSUES_FOR_AUDIT.md` item 2** (which recorded Phi-4 314, Mistral 22, Gemma 6 among
`fail_unparseable`): Mistral 22 and Gemma 6 reproduce exactly. Restricting this audit to `fail_unparseable`
gives Phi-4 321 against the 314 recorded — a 7-record difference attributable to the detection rule, not to the
data. The remaining 98 Phi-4 empty objects were scored `fail_truncated` because the trailing prose pushed the
payload past the 600-character cap (see C.7).

> **Example 1** — `ge_ee5nfbq` · Gemma 4 31B · 1S-CoT · run 3 · ground truth `non_distress` — the bare form,
> 14 characters: ```` ```json {} ``` ````

> **Example 2** — `ge_ed1ueow` · Phi-4 · 1S-CoT · run 1 · ground truth `non_distress` — the dominant form:
> ```
> ```json
> {}
> ```
> Step 1 — Full text read. Step 2 — No explicit mention of emotions like anxious, stressed, sad, frustrated,
> fearful, hopeless, or lonely. Step 3 & 4 — No applicable emotions can be inferred based on explicit
> expressions. Step 5 — No emotions to assess for intensity. Step 6 — No emotions found, hence an empty set
> is returned.
> ```
> **OBSERVATION.** The reasoning states the intended answer — "an empty set is returned" — and the emitted
> object is `{}` rather than `{"emotions": []}`. The model's stated conclusion and its serialisation disagree.
> **POSSIBLE EXPLANATION.** The one-shot-CoT prompt elicits step-by-step prose, and the JSON block is emitted
> before or independently of the reasoning that names the empty list.
> **EVIDENCE NEEDED.** A prompt variant that requires the object after the reasoning, on the same items. That
> is a new experiment, not a reanalysis.

### C.3 malformed_json_escaping — 264 (13.3%)

**Definition.** The first key/value pair is well formed but subsequent keys use escaped quotes
(`reasoning\":\"`), invalidating the payload.

**Why the parser rejects it.** Strict `json.loads`, fence-stripping and `first_balanced_object` all fail on the
escaped delimiters, so `extract_risk_level` returns `None`. The literal `"risk_level":"moderate"` stays
readable to a human.

**Concentration.** 263 of 264 are Qwen3.5 27B / Dreaddit / zero-shot-CoT; the remaining one is Phi-4 / ZS.

> **Example 1** — `dread_1038` · Qwen3.5 27B · ZS-CoT · run 1 · ground truth 1
> ```
> {"risk_level":"moderate","reasoning\":\"The text explicitly describes several anxiety-related experiences
> including 'panic attacks' and 'years without sleep'. ...\",\"recommended_support\":\"...\"}
> ```

> **Example 2** — `dread_50132` · Qwen3.5 27B · ZS-CoT · run 3 · ground truth 1 — identical signature; every
> quoted span verified present in the input.

### C.4 refusal_or_deflection — 227 (11.4%)

**Definition.** The response declines the task, redirects to general advice, or asserts that no input was
supplied. No required field is emitted.

**Distribution.** Phi-4 183 (Dreaddit 62, GoEmotions 121), Llama 39, Mistral 5. Three behaviourally distinct
sub-types are visible in the raws and are worth separating in the paper:

1. **Capability/safety disclaimers** — "As a large language model, I must emphasize that I cannot provide
   mental health or clinical advice" (Phi-4, very common on GoEmotions).
2. **Content-policy refusals on the dataset item** — `ge_ee6o1mk`: *"I can't provide a response that could be
   used to harass or discriminate against someone."*; `ge_eea97o5`: *"I'm not able to analyze this text as it
   promotes violence and harm towards animals."* (Llama).
3. **"No input supplied" deflections** — `ge_ee1ty3y` (Mistral, 1S-CoT): *"Understood. Please provide the
   user's text for analysis."*

> **Example** — `dread_1138` · Phi-4 · ZS · run 1 · ground truth 0
> ```
> I'm sorry, but I can't assist with that request.
> However, I can offer general advice on how to handle situations that involve alcohol consumption and social
> boundaries. ...
> ```

### C.5 bare_string_in_object_position — 120 (6.0%)

**Definition.** The model continues a value as further comma-separated string literals inside the object, as
if the object were an array, so the parser reaches a position where a key is required and finds a bare string.

**Why the parser rejects it.** `json.loads` fails with *"Expecting ':' delimiter"* — 120 of 120 records give
exactly this error. The ladder's later stages operate on the same invalid text and also fail.

**Concentration.** All 120 are Llama 4 Scout / Dreaddit (82 zero-shot, 38 zero-shot-CoT). This is the single
largest Dreaddit category after Qwen's escaping defect, and it was invisible in the partial audit.

> **Example 1** — `dread_1365` · Llama 4 Scout · ZS · run 1 · ground truth 0
> ```
> {"risk_level":"low","reasoning":"The text describes a friend's anxiety and process of seeking help through
> therapy. ... There is no indication of immediate danger or urgent safety concern.","The text does not suggest
> a high level of distress or functional impairment.","The friend's decision to ...
> ```

> **Example 2** — `dread_1263` · Llama 4 Scout · ZS · run 1 · ground truth 1 — same pattern, and the object
> then recovers into `"recommended_support":"…","safety_note":""}`, so the defect is confined to the
> `reasoning` field overrunning into extra string elements.

### C.6 prose_or_markdown_instead_of_required_json — 93 (4.7%)

**Definition.** The response addresses the reader in prose or markdown instead of emitting the required object.

Several of these do state the answer in prose. `dread_1304` (Phi-4, ZS, ground truth 1) writes
`- **Risk Level:** "moderate"` inside a markdown summary. The frozen contract requires the value inside a JSON
object under the exact key `risk_level`, so it is not read.

> **Example** — `dread_1824` · Phi-4 · ZS · run 1 · ground truth 0
> ```
> " \
> " \
> risk_level": "low", \
> "reasoning": "The user describes some curiosity ... ", \
> ```

### C.7 apparent_truncation — 13, and the 600-character cap

**Definition.** The payload ends mid-object or mid-array and the required value did not survive.

> **Example** — `ge_ef3hloa` · Llama 4 Scout · ZS-CoT · run 2 · ground truth `frustration`
> ```
> Here is the analysis:
> **emotions:** ["frustration"] **emotional_intensity:** "moderate"
> **evidence_from_text:** ["read your own fucking post first"]
> ```
> The `emotions` key is in markdown bold, not JSON, so no complete `"emotions": [...]` array exists. The
> salvage regex requires the closing bracket and correctly declines to read a partial array.

**Methodological finding, preserved from the partial audit and now confirmed at full coverage.** For
GoEmotions, the split between `fail_truncated` and `fail_unparseable` is decided by `LEGACY_STORAGE_CAP = 600`
in `emotion_payload.py` — a *legacy storage cap*, not evidence that the API or the model truncated anything.
Two demonstrations:

- `ge_eeg2gqv` (Llama, ZS-CoT) produced near-identical responses in run 1 and run 3; the 576-character one was
  labelled `fail_unparseable` and the 723-character one `fail_truncated`.
- 98 of Phi-4's 419 `empty_object` records are labelled `fail_truncated` purely because the model's trailing
  chain-of-thought prose pushed a complete, well-formed `{}` past 600 characters.

**`fail_truncated` must therefore be reported together with `fail_unparseable` as "payload unreadable", and
must not be interpreted as evidence of API or model truncation.**

### C.8 Smaller categories

- **repeated_or_restarted_json — 18.** The object is restarted mid-string; brace depth never returns to zero.
  `dread_286` (Qwen, ZS, run 1) restarts three times, `risk_level` appears three times, readable value `low`.
  10 of the 18 also carry `degenerate_repetition` (a ≥120-character window recurring ≥3 times), all Qwen.
  `ge_eelmvui` (Gemma, 1S-CoT, run 5) restarts *inside* the first `emotions` array:
  `{"emotions":["frustration{"emotions":["frustration"],...}`.
- **missing_json_delimiter — 17** (Phi-4 11, Llama 6). The opening `{` is absent or corrupted; all 17 carry a
  readable, allowed `risk_level`.
- **invalid_risk_level — 9**, all Phi-4/Dreaddit. Values observed: `undefined_input`, `undefined`, `unknown`
  (×2), `unavailable`, `mild epxress`, `urget`, `medium`, `mandate_warning`. `dread_43546` is a well-formed,
  internally consistent **refusal to classify** — the model declined to assign a level rather than guessing.
- **commentary_inside_structured_field — 6.** Prose inside a field that must hold structured values.
  `ge_eeg2gqv` (Llama, ZS-CoT, run 1) writes `"emotions": ["nostalgia" is not in the list of defined emotions,
  however, ... one could consider "positive emotional state"]`, then emits a corrected `{"emotions": []}`
  block that the first-match salvage regex never reaches.
- **off_task_schema — 4**, all Phi-4. `dread_48595` emits `{"intent_ranking": [{"name": …, "confidence": 0.95}]}`;
  `dread_11468` emits `{"lang": "apology_detection", "result": "no_apology_detected", …}`; on GoEmotions,
  `ge_eenni73` and `ge_ee1gza5` answer as "an LLM content filter" with a `derogatory_language`-style schema.
- **unescaped_quote_in_string — 3.** `dread_25778` (Mistral, two cells) contains
  `'terrified that I am doing the "wrong" thing'`; `dread_1116` (Phi-4, ZS-CoT run 4) closes a string with `'`.
- **missing_required_field — 1** and **malformed_json_other — 1**, both Phi-4/GoEmotions/ZS. The first
  (`ge_edbjz5j`) echoes a block of user-style text with no schema at all; the second (`ge_edrbpty`) is a
  privacy disclaimer followed by a partial analysis whose `emotions` array never closes.

---

## D. Per-model analysis

Each model gets three separated registers: **OBSERVATION** is what the data shows, **POSSIBLE EXPLANATION** is
a mechanism that would account for it, **EVIDENCE NEEDED** is what would have to be shown before the
explanation could be asserted. No model is characterised as weak, bad, small or limited in capability, and
parameter count is never offered as an explanation for any failure.

### D.1 Gemma 4 31B

**OBSERVATION.** Zero invalid outputs on Dreaddit across 10,485 attributable records — the only model with a
perfect structural record on either dataset. On GoEmotions: 0 / 0 / 7 across ZS, ZS-CoT, 1S-CoT (0.23%). All 7
are one-off (7 distinct samples, one run each): 6 bare `{}` and 1 restarted object. Gemma produced **zero**
out-of-vocabulary labels in the entire grid.

**POSSIBLE EXPLANATION.** Gemma's outputs terminate the required object on both schemas and stay inside the
prompt's label set; the few failures cluster in the strategy with the longest prompt.

**EVIDENCE NEEDED.** The one-shot-CoT prompt is the longest of the three, so prompt length and strategy are
confounded. Separating them needs a length-matched prompt variant, which is outside the frozen design.

### D.2 Qwen3.5 27B

**OBSERVATION.** Strongly bimodal. GoEmotions: 0 / 0 / 10 (all OOV, from 2 samples that each failed all five
runs). Dreaddit: 7 / **269** / 4. All 280 Dreaddit invalids contain a readable, allowed `risk_level`, and fall
into exactly two categories (escaping 263, restarted 17). The 269 zero-shot-CoT records come from 65 unique
samples, 44 of which failed in all five runs; `same_failure_category_across_runs` is `true` for all 269, yet
the raw texts differ between runs for 55 of the 65 groups.

**POSSIBLE EXPLANATION.** A single reproducible serialisation defect triggered by this prompt and by particular
items, rather than a general inability to produce JSON: schema and first field are correct, only the delimiter
escaping after the first field is wrong.

**EVIDENCE NEEDED.** A causal claim would need the same model and the same 65 items under a modified prompt —
a new experiment. What the data supports is narrower: the defect is strategy-specific within this model and
stable across five independent runs.

### D.3 Mistral Small 4

**OBSERVATION.** 2 invalid Dreaddit records in total, both the same sample (`dread_25778`) in two strategies,
both caused by an unescaped `"wrong"` inside a string. On GoEmotions 48 records over 13 unique samples:
empty_object 22, OOV 21, refusal 5. Counting each model x strategy x sample group separately, 11 of its 19
groups produced **byte-identical** raws across the runs in which they failed.

**POSSIBLE EXPLANATION.** Near-deterministic decoding on the affected items.

**EVIDENCE NEEDED.** `ISSUES_FOR_AUDIT.md` item 6 established for Qwen that each run was a genuinely separate
call (distinct Mastra run ids, distinct time windows). The same check should be run for Mistral before
describing its repeats as determinism rather than caching.

### D.4 Llama 4 Scout

**OBSERVATION.** Two completely different profiles by dataset. On Dreaddit, 166 records over 114 unique
samples, of which 120 (72%) are the `bare_string_in_object_position` defect — a category no other model
produced. On GoEmotions, 449 records over 92 unique samples, of which 418 (93%) are `out_of_vocabulary_label`.
Llama also produced the only content-policy refusals on dataset items.

**POSSIBLE EXPLANATION.** On Dreaddit the failure is confined to the long free-text `reasoning` field
overrunning into extra string elements; on GoEmotions the payloads are structurally fine and the labels simply
come from a broader affect vocabulary than the five AnxioSense classes.

**EVIDENCE NEEDED.** Directly checkable and worth doing: compare the 418 OOV labels against the GoEmotions gold
labels for those items to see whether the model's own label is defensible for the text. That is an analysis of
existing raws and would not change any frozen score.

### D.5 Phi-4

**OBSERVATION.** The most heterogeneous profile: Phi-4 is the only model producing `off_task_schema` and
`invalid_risk_level`, and it appears in 13 of the 15 categories. On Dreaddit, 151 records over 123 unique
samples (1.23 records per sample — mostly one-off), dominated by refusal 62 and prose/markdown 55. On
GoEmotions, 873 records over 427 unique samples: empty_object 419, OOV 314, refusal 121. Its 1S-CoT GoEmotions
cell (499 records, 16.05%) is the largest in the grid, and **zero** of its 356 affected samples there failed in
all five runs.

**POSSIBLE EXPLANATION.** Several things co-occur rather than one: a conversational-assistant register that
overrides the structured-output instruction (refusal + prose = 117 of 151 Dreaddit invalids); a serialisation
of "no emotions found" as `{}` rather than `{"emotions": []}` (419 GoEmotions records, where the reasoning
often states the intended empty list explicitly); and occasional emission of an unrelated task schema.

**EVIDENCE NEEDED.** These are three separate hypotheses needing three separate tests. In particular, the
`{}`-vs-`{"emotions": []}` question is testable by a prompt that shows the empty-list form in its exemplar —
again a new experiment. Nothing in the present data establishes a cause.

### D.6 Cross-dataset behaviour

| Model | Dreaddit invalid (rate) | GoEmotions invalid (rate) | Dominant Dreaddit mode | Dominant GoEmotions mode |
|---|---|---|---|---|
| Gemma 4 31B | 0 (0.000%) | 7 (0.075%) | — | empty_object |
| Mistral Small 4 | 2 (0.019%) | 48 (0.514%) | unescaped_quote | empty_object / OOV |
| Qwen3.5 27B | 280 (2.670%) | 10 (0.107%) | escaping | OOV |
| Phi-4 | 151 (1.440%) | 873 (9.357%) | refusal / prose | empty_object |
| Llama 4 Scout | 166 (1.583%) | 449 (4.812%) | bare_string_in_object | OOV |

**OBSERVATION.** For all five models the dominant failure mode differs between the two datasets, and the
invalid rate differs by between 4× and 25×. No model carries the same profile across both tasks.

**POSSIBLE EXPLANATION.** The two tasks impose different output contracts (section I), so structural
reliability appears contract-specific rather than a fixed property of a model.

**EVIDENCE NEEDED.** Two tasks cannot establish that generalisation. It would need a third contract with a
different answer shape.

---

## E. Prompt-strategy analysis

| Dataset | Strategy | Invalid | Rate | Unique samples | Dominant categories |
|---|---|---|---|---|---|
| Dreaddit | zero-shot | 220 | 1.26% | 166 | bare_string 82; refusal 58; prose 49; missing_delimiter 13 |
| Dreaddit | zero-shot-CoT | 351 | 2.01% | 125 | **escaping 263**; bare_string 38; prose 17; refusal 15 |
| Dreaddit | one-shot-CoT | 28 | 0.16% | 18 | refusal 9; prose 8; truncation 5; restarted 4 |
| GoEmotions | zero-shot | 321 | 2.06% | 167 | OOV 210; refusal 85; prose 12; empty_object 11 |
| GoEmotions | zero-shot-CoT | 395 | 2.54% | 147 | OOV 344; refusal 30; empty_object 9 |
| GoEmotions | one-shot-CoT | 671 | 4.32% | 373 | **empty_object 427**; OOV 209; refusal 30 |

**OBSERVATION 1 — the two datasets order the strategies in opposite directions.** On Dreaddit, one-shot-CoT is
by far the lowest (0.16%) and zero-shot-CoT the highest. On GoEmotions the ordering is monotonic the other way:
ZS 2.06% < ZS-CoT 2.54% < 1S-CoT 4.32%.

**What can be concluded:** the strategy effect on structural validity is not consistent across tasks, so no
single "most robust prompting strategy" claim is supportable.
**What cannot:** the GoEmotions ordering is still dominated by one cell — Phi-4 1S-CoT supplies 499 of the 671
one-shot-CoT records. Excluding that cell leaves ZS 321, ZS-CoT 395, 1S-CoT 172, which reverses the ordering.
The aggregate must be reported with this caveat. (The partial audit raised this as a possibility; with full
coverage it is confirmed, and the driver is now identified as `empty_object`.)

**OBSERVATION 2 — Qwen / Dreaddit / zero-shot-CoT.** 269 records, 7.70%, versus 0.20% and 0.11% for the same
model's other strategies on the same dataset — a 38× difference within one model, stable across five runs
(50, 55, 50, 53, 57) and confined to one failure category.

**What can be concluded:** within this model, on this dataset, the failure is strategy-specific and highly
reproducible.
**What cannot:** that chain-of-thought prompting causes JSON escaping defects in general. No other model
produced this category, and Qwen's other CoT strategy produced only 4 invalid records.

**OBSERVATION 3 — Phi-4 / GoEmotions / one-shot-CoT.** 419 of the 427 `empty_object` records in that cell come
from one model under one strategy, and 382 of them are `{}` followed by step-numbered reasoning prose. In
zero-shot and zero-shot-CoT the same model produced almost no empty objects (0 and 0 respectively; its failures
there are OOV and refusal).

**What can be concluded:** the empty-object serialisation is specific to this model-strategy pair.
**What cannot:** that the one-shot exemplar caused it. The exemplar, the CoT instruction and the prompt length
all change together between strategies.

**OBSERVATION 4 — refusals do not concentrate in zero-shot as the partial audit suggested.** With full
coverage: zero-shot 143, zero-shot-CoT 45, one-shot-CoT 39. The zero-shot concentration is real but weaker
than the partial sample implied (it was 48 of 86 there; it is 143 of 227 here).

---

## F. Unique samples versus assessment records

Full per-cell detail, including 1/5 … 5/5 distributions and raw-output similarity, is in
`unique_sample_recurrence.csv`. These counts never depended on raw evidence, so they are unchanged from the
partial audit; what is new is that `raw_outputs_identical_or_similar` is now computed for every group.

| Dataset | Model | Strategy | Records | Unique | 1/5 | 2/5 | 3/5 | 4/5 | 5/5 | % records from 5/5 | raw identical / similar / different |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dreaddit | Llama 4 Scout | ZS | 106 | 80 | 61 | 15 | 2 | 1 | 1 | 4.7% | 1 / 0 / 18 |
| dreaddit | Llama 4 Scout | ZS-CoT | 52 | 47 | 43 | 3 | 1 | 0 | 0 | 0.0% | 0 / 0 / 4 |
| dreaddit | Llama 4 Scout | 1S-CoT | 8 | 4 | 1 | 2 | 1 | 0 | 0 | 0.0% | 0 / 0 / 3 |
| dreaddit | Mistral Small 4 | ZS | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0.0% | — |
| dreaddit | Mistral Small 4 | ZS-CoT | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0.0% | — |
| dreaddit | Phi-4 | ZS | 106 | 96 | 88 | 6 | 2 | 0 | 0 | 0.0% | 0 / 0 / 8 |
| dreaddit | Phi-4 | ZS-CoT | 29 | 26 | 25 | 0 | 0 | 1 | 0 | 0.0% | 0 / 0 / 1 |
| dreaddit | Phi-4 | 1S-CoT | 16 | 14 | 13 | 0 | 1 | 0 | 0 | 0.0% | 0 / 0 / 1 |
| dreaddit | Qwen3.5 27B | ZS | 7 | 2 | 0 | 1 | 0 | 0 | 1 | 71.4% | 0 / 2 / 0 |
| dreaddit | Qwen3.5 27B | **ZS-CoT** | **269** | **65** | 7 | 6 | 2 | 6 | **44** | **81.8%** | 2 / 1 / 55 |
| dreaddit | Qwen3.5 27B | 1S-CoT | 4 | 1 | 0 | 0 | 0 | 1 | 0 | 0.0% | 0 / 1 / 0 |
| goemotions | Gemma 4 31B | 1S-CoT | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0.0% | — |
| goemotions | Llama 4 Scout | ZS | 113 | 47 | 24 | 4 | 4 | 6 | 9 | 39.8% | 1 / 7 / 15 |
| goemotions | Llama 4 Scout | ZS-CoT | 193 | 71 | 23 | 12 | 13 | 8 | 15 | 38.9% | 3 / 2 / 43 |
| goemotions | Llama 4 Scout | 1S-CoT | 143 | 42 | 10 | 5 | 3 | 6 | 18 | 62.9% | 13 / 8 / 11 |
| goemotions | Mistral Small 4 | ZS | 17 | 8 | 4 | 2 | 0 | 1 | 1 | 29.4% | 4 / 0 / 0 |
| goemotions | Mistral Small 4 | ZS-CoT | 19 | 6 | 1 | 1 | 2 | 0 | 2 | 52.6% | 3 / 2 / 0 |
| goemotions | Mistral Small 4 | 1S-CoT | 12 | 5 | 1 | 3 | 0 | 0 | 1 | 41.7% | 4 / 0 / 0 |
| goemotions | Phi-4 | ZS | 191 | 134 | 97 | 25 | 6 | 4 | 2 | 5.2% | 0 / 0 / 37 |
| goemotions | Phi-4 | ZS-CoT | 183 | 105 | 58 | 26 | 14 | 4 | 3 | 8.2% | 0 / 0 / 47 |
| goemotions | Phi-4 | 1S-CoT | 499 | 356 | 241 | 91 | 20 | 4 | **0** | 0.0% | 2 / 1 / 112 |
| goemotions | Qwen3.5 27B | 1S-CoT | 10 | 2 | 0 | 0 | 0 | 0 | 2 | 100.0% | 2 / 0 / 0 |

**Two opposite regimes.**

*Persistent, item-driven.* Qwen GoEmotions 1S-CoT (100% of records from 5/5 samples, and both groups produced
**identical** raw text every run), Qwen Dreaddit ZS-CoT (81.8%), Qwen Dreaddit ZS (71.4%), Llama GoEmotions
1S-CoT (62.9%, 13 of 42 groups byte-identical). Here the count is essentially `5 × (a small set of problem
items)`.

*Sporadic, decode-driven.* Phi-4 GoEmotions 1S-CoT (241 of 356 samples failed in exactly one run and **not one**
failed all five, despite being the largest cell in the grid), Phi-4 Dreaddit ZS (88 of 96 one-off), Llama
Dreaddit ZS-CoT (43 of 47 one-off).

### F.1 Qwen / Dreaddit / zero-shot-CoT, in full

- **269 assessment records** from **65 unique samples** of the 715-item Dreaddit test set (9.1%).
- Run distribution: 44 samples failed all five runs, 6 four, 2 three, 6 two, 7 one.
- The 44 always-failing samples contribute **220 of 269 records (81.8%)**; the other 49 come from 21
  intermittently-failing samples.
- **Category perfectly stable:** `same_failure_category_across_runs = true` for all 269 (263 escaping,
  6 restarted).
- **Raw text not stable:** of the 58 samples failing more than once, 55 produced different text, 2 similar,
  4 identical. The model rewrites its reasoning each time and reproduces the same delimiter defect.
- Apparent (descriptive, never scored) risk levels: moderate 220, low 43, urgent 6.

**Correct statement for the paper:** *"Qwen3.5 27B produced 269 invalid assessments under zero-shot-CoT on
Dreaddit. These arise from 65 distinct test items, 44 of which failed in all five runs; the failure is a
single reproducible JSON-escaping defect rather than 269 independent events."*

Persistent example: `dread_1061` failed in all five runs, always `malformed_json_escaping`, always with a
readable `moderate`, with differently-worded reasoning each time. One-off examples: `dread_17531`,
`dread_904`, `dread_49791`, `dread_36370`, `dread_10307`, `dread_308`, `dread_62`.

---

## G. Parser versus model

Across all 1,986 records:

| # | Bucket | n | % | Composition |
|---|---|---|---|---|
| 1 | Response contains **no usable prediction** | 550 | 27.7% | empty_object 447, prose/markdown 93, off_task_schema 4, truncation 4, restarted 1, missing_required_field 1 |
| 2 | Response contains an **apparent valid prediction but violates the required structure** | 430 | 21.7% | escaping 264, bare_string 120, restarted 17, missing_delimiter 17, unescaped_quote 3, truncation 9 |
| 3 | Response is **structurally valid but uses disallowed vocabulary** | 772 | 38.9% | out_of_vocabulary_label 763, invalid_risk_level 9 |
| 4 | Response is a **refusal or deflection** | 227 | 11.4% | includes content-policy refusals on dataset items |
| 5 | **Parser recovery-policy / ambiguous** | 7 | 0.4% | commentary_inside_structured_field 6 and 1 residual: a well-formed array exists later in the response but the salvage regex takes the first match |
| 6 | Ambiguous beyond the above | 0 | 0% | — |

**Bucket 2 is the headline number for a reviewer**: 430 records (21.7% of all invalids) carry a literal,
in-vocabulary answer that a more permissive extractor could read. All 430 are Dreaddit, and all 430 carry a
`risk_level` in `low|moderate|urgent` (moderate 341, low 70, urgent 19). That is 71.8% of the 599 Dreaddit
invalids.

**Production parser versus evaluation parser.** For **all 599** Dreaddit invalid records — including every one
of the 430 in bucket 2 — the frozen record's `cross_check` shows `server_referral_level = null` and
`server_referral_unreadable = true`. The production TypeScript extractor
(`src/mastra/utils/referral-risk-parser.ts`) rejected exactly the same responses as the Python evaluation port
(`runner/referral_risk_parser.py`). There is **no disagreement between the two implementations anywhere in the
grid**.

**This is not a parser bug.** The frozen contract is explicit — *"strict JSON → fence-stripped → first balanced
`{...}` → exact key `risk_level` → lowercase/trim → accept only low|moderate|urgent → else None. No synonyms,
no inference."* — and the parser does exactly that on all 1,986 records. The strictness is a specified design
choice and it matches production behaviour; calling it a bug would require evidence that the implementation
violates its own contract, and no such evidence was found. The defensible framing is that **the system as
deployed cannot read these responses either**, which makes the invalid rate a property of the end-to-end
system rather than of the evaluation harness.

The only place where *policy* rather than contract decides the outcome is bucket 5 (7 records): the GoEmotions
salvage regex matches the first `"emotions": [...]` array, and in those cases a well-formed array appears later
in the same response.

---

## H. Hallucination analysis

**Operational definition.** A hallucination is a *fabricated factual or content claim unsupported by the
supplied input or task context*. Explicitly **not** treated as hallucination: formatting failure, wrong
classification, refusal, out-of-vocabulary label, repetition, or being rejected by the parser.

**Method.** Quoted spans were extracted from `evidence_from_text` arrays and from single-quoted spans in
`reasoning`, then compared against the `input_text` stored on the same terminal attempt. The comparison
tolerates five things that are not fabrication: elision (`A... B`), inflection (`calls up` → `call up`),
whitespace/punctuation normalisation (`out smart` → `outsmart`), a typo in the *source* text silently corrected
when quoting (input `watxh`, quote `watch`), and a genuine quotation embedded inside the model's own commentary.
A separate check looks for identifiers, paths or URLs asserted as content that do not occur in the input.
**Every record the automated test flagged was then read in full against its own input and given an explicit
reviewed verdict**, recorded per row in `hallucination_reviewed_verdict` /
`hallucination_review_confidence` / `hallucination_review_basis`. The automated flag is retained alongside so
the two can be compared.

Two cruder heuristics were built, tested and **discarded** during this audit, and the reason is recorded
because it matters for the paper. A naive single-quote extractor flagged 221 records, nearly all artefacts of
apostrophes inside contractions (`I'm sorry ... you've` yields the bogus span `m sorry ... you`). An
`off_task_content` label based on low input-token overlap was discarded because the **median** input-token
coverage among invalid records is only 0.305, so a low value carries no signal. The numeric measure is
retained as `input_token_coverage_in_response` for descriptive use only.

### Results

| Verdict | n |
|---|---|
| Automated flag: candidate | 17 (14 `true`, 3 `uncertain`) |
| **Reviewed: CONFIRMED** | **4** |
| Reviewed: REJECTED after inspection | 13 |
| Not flagged | 1,969 |

**All four confirmed cases are Phi-4.** Two are Dreaddit/zero-shot; two are GoEmotions.

> **1. `dread_649` · Phi-4 · zero-shot · run 4 · ground truth 1. Confidence high.**
> The 289-character input is about procrastinating on a Reddit post. The 8,480-character response narrates
> skiving, 14-hour film-set days, tea runs and a "Creative Coordinator" role, opens with a quotation attributed
> to a named source — `"I'm going to talk about skiving and self-care. …" - 4scenenotes.com` — and later
> presents an invented first-person tl;dr (*"live for this Job but no life outside it. And also feel like I'm
> kinda on the verge of a burnout"*) as if it were the user's words. None of this is in the input.
> **Fabricated content plus a fabricated attributed quotation.**

> **2. `ge_eekj86e` · Phi-4 · zero-shot · run 1 · ground truth `non_distress`. Confidence high.**
> The 79-character input is *"Maybe she was attempting to be ironic? I dunno, man, people are just an enigma."*
> Under a `### User Input` heading the response reproduces an entirely different, multi-sentence first-person
> distress narrative — *"I feel really overwhelmed with reading bickering, hating, labeling, insulting,
> triggering. Loneliness isn't strong enough to explain how I feel sometimes and I don't find peace of mind.
> I was sleep a few hours last night…"* — analyses **that** text, and concludes *"The user explicitly states
> feeling 'overwhelmed'"*, emitting `{"emotions": ["overwhelmed"], …}` with two quoted evidence spans that
> exist nowhere in the actual input. **The analysed input is fabricated.**

> **3. `ge_ee6o1mk` · Phi-4 · one-shot-CoT · run 2 · ground truth `non_distress`. Confidence high.**
> The 26-character input is *"Sweaty little incel virgin"*. The response asserts *"the text provided is not
> self-reported but rather a link to an external source (`https://tinyurl.com/4kwgs3d5y`)"* and returns `{}` on
> that basis. No link exists in the input. **The URL is fabricated and the false premise drives the output.**

> **4. `dread_33288` · Phi-4 · zero-shot · run 2 · ground truth 0. Confidence high, with a caveat.**
> Emits an unrelated schema including `"excerpts selection": "./95761b9e005e46a8220492c40b04489201d2gz8"` — a
> path-like identifier asserted as content that occurs nowhere in the input and refers to nothing in the task.
> **Recorded alternative reading:** this may be a training-format artefact rather than a claim about the user's
> text; the response's own summary of the input is accurate, which distinguishes it from case 1.

### The thirteen rejections, and why they matter

Every rejection is recorded per row with its basis. They fall into four patterns, and the patterns are
themselves a finding:

1. **Quotation normalisation** (6 records) — abbreviation expanded (`Idk` → `I don't know`), spelling corrected
   (`if their happy` → `if they're happy`), subject added (`Glad you're doing better` → `I'm glad you're doing
   better`), quote truncated (`I'm so excited` → `am so excited`), or a source typo silently fixed.
2. **Corrupted or garbled quotation** (2) — `"Linhappy for him!"` for `"I'm happy for him!"`;
   `"great is the text"` built from the input's `"great"`.
3. **Description instead of quotation in `evidence_from_text`** (3) — e.g. `"agreement with a statement"`,
   `"The user mentions fondness of the past memory with their daughter."` The descriptions are accurate about
   the input; the failure is schema misuse, not a false claim.
4. **Prompt scaffolding quoted as user text** (2) — `evidence_from_text` populated with the prompt's own
   preamble, *"The following text was sourced from social media (e.g. Reddit)."*

Patterns 3 and 4 are carried as secondary labels
(`description_instead_of_quotation_in_evidence`, `prompt_scaffolding_quoted_as_user_text`) on the records where
the evidence array parses cleanly enough to detect them automatically (3 and 1 respectively); the counts above
come from the manual review and are the authoritative ones.

Also explicitly **not** counted as hallucination: all 763 out-of-vocabulary labels, all 227 refusals, all 264
escaping failures, all 447 empty objects, and every repetition.

**Bottom line for the paper.** Across all 1,986 invalid outputs, **4 (0.20%) are defensible hallucinations, all
from one model, and 2 of the 4 fabricate the input text itself rather than merely embellishing the output.**
Invalid output in this experiment is overwhelmingly a *structural and vocabulary* phenomenon, not a
content-fabrication phenomenon. The figure remains a lower bound on quotation-grounded fabrication: the method
catches fabricated quotations, attributions and identifiers, but would not catch a false claim expressed
entirely in paraphrase.

---

## I. Dataset-specific analysis

The two tasks impose different output contracts, and the failure profiles follow the contracts.

**Dreaddit** asks the referral agent for a JSON object containing `risk_level` with one of three allowed values,
plus long free-text `reasoning`, `recommended_support` and `safety_note`. The scored answer is *a single token
from a closed 3-value set*, wrapped in long free text.

- Consequence: the value is easy to choose and hard to deliver. **430 of 599 Dreaddit invalids (71.8%) contain
  the correct-format value and fail only on serialisation.** The three largest Dreaddit categories — escaping
  264, bare-string 120, missing delimiter 17 — are all defects *in or after the long free-text field*.
- Only 9 records (1.5%) fail on the *value*, so the 3-value vocabulary is almost never the problem.
- Safety intercepts are frequent (16/run) because Dreaddit posts contain crisis language.

**GoEmotions** asks for `emotions: [...]` plus `emotional_intensity` and `evidence_from_text`. The answer is an
*open-ended list of labels* that must land in a 7-key mapping, and **an empty list is itself a valid
prediction**.

- Consequence: the payload is short and easy to deliver but the vocabulary is easy to miss. **763 of 1,387
  GoEmotions invalids (55%) are vocabulary failures**, and a further 447 (32%) are the empty-object trap.
- The empty-list rule creates a category with no Dreaddit analogue: `{}` is not `{"emotions": []}`, so a
  14-character response that looks harmless carries no prediction. There is no equivalent trap on Dreaddit,
  where a missing field is unambiguous.
- Safety intercepts are rare (1/run) because the items are short social-media comments.

**Stated without going beyond the evidence:** the datasets differ in *which* part of the contract fails, not
merely in how often. Dreaddit failures are predominantly serialisation; GoEmotions failures are predominantly
label-space plus the empty-object ambiguity. Whether that generalises beyond these two contracts cannot be
determined from this experiment.

---

## J. Research-paper implications

### J.1 Defensible findings

1. **All 1,986 invalid outputs are model behaviour.** Zero infrastructure failures survive into the scored
   grid; 661 transport failures occurred at the attempt level and every one was recovered.
2. **The overall invalid rate is 2.005%** (Dreaddit 1.143%, GoEmotions 2.973%) and is highly non-uniform: four
   model×strategy cells produced zero invalid outputs across 3,110 records each, while one produced 16.05%.
3. **Invalid outputs are structural and lexical, not fabrications.** 38.9% are structurally valid payloads with
   a disallowed value, 27.7% carry no usable prediction, 21.7% are readable answers inside broken syntax,
   11.4% are refusals, and 0.20% are confirmed hallucinations.
4. **Three failure modes each account for more than 10% and each is concentrated in one model:** the
   out-of-vocabulary label (763, mostly Llama and Phi-4), the empty object (447, 94% Phi-4), and the escaping
   defect (264, 99.6% Qwen zero-shot-CoT).
5. **Assessment-record counts overstate affected items.** Qwen/Dreaddit/ZS-CoT's 269 records come from 65
   unique items, 44 failing all five runs. Invalid counts should always be reported with unique-sample counts.
6. **The evaluation parser and the production parser agree completely on Dreaddit** (599/599). Strict parsing
   is not an evaluation artefact: the deployed system rejects the same responses.
7. **Failure profiles do not transfer across tasks.** For all five models the dominant mode differs between the
   two datasets.
8. **`fail_truncated` is a storage-cap label, not truncation evidence** (see J.2).

### J.2 Limitations

- **The `fail_truncated` / `fail_unparseable` split is an artefact of `LEGACY_STORAGE_CAP = 600`**, not
  evidence that the API or the model truncated anything. 98 of Phi-4's 419 empty objects are labelled
  `fail_truncated` only because trailing reasoning prose pushed a complete `{}` past 600 characters, and two
  near-identical Llama responses landed in different buckets on length alone. **Report the two labels together
  as "payload unreadable" and do not describe them as API or model truncation.**
- **Strategy, prompt length and exemplar presence vary together**, so no strategy effect in section E can be
  given a causal reading.
- **Hallucination detection is quotation-grounded** and the 4-record figure is a lower bound.
- **Near-determinism** in Mistral's byte-identical repeats has not been verified against distinct run ids the
  way Qwen's was (`ISSUES_FOR_AUDIT.md` item 6).
- **Three source runs were read from an external copy of the evidence.** The provenance gate proves the bytes
  are identical to those the frozen results were derived from, but the replication package should carry those
  stores alongside the others.

### J.3 Possible future parser improvements (none applied; all would be contract changes)

| Candidate change | Records affected | Why it is a contract change |
|---|---|---|
| Accept a `risk_level` located by regex when the object does not parse | up to 430 (bucket 2) | The frozen ladder requires a parsed object; regex extraction admits values from unparsed text |
| Best-match instead of first-match for the GoEmotions `emotions` array | 7 | Changes which of several arrays in one response is authoritative |
| Treat a fence-wrapped `{}` as `fail_absent` rather than `fail_unparseable` | 447 | Relabelling only; would not change validity or any metric |
| Report `fail_truncated` and `fail_unparseable` as one status | 169 relabelled | Presentation only; recommended |
| Extend `ANXIOSENSE_TO_EVAL_CLASS` to cover observed affect labels | up to 763 | A methodology change to the label space, not a parser fix |

The third and fourth have no effect on any metric. **None should be applied retroactively to the frozen
results.** If any is adopted it belongs in a clearly separated sensitivity analysis.

### J.4 Possible prompt-design improvements (future work, not this paper's results)

- Enumerating the allowed emotion labels *inside the output-schema instruction* would target the largest single
  category (763 OOV records). Note that 49 of those labels are `panic`, a distress term with no mapping.
- Showing `{"emotions": []}` explicitly as the empty-result form would target the 447 empty objects, where the
  model's own reasoning often states "an empty set is returned".
- Requiring the structured object **before** the free text would target the Dreaddit serialisation defects,
  which occur in or after the long `reasoning` field in all 401 escaping/bare-string/delimiter cases.

### J.5 Questions needing additional statistical testing

1. Is the invalid rate associated with conditional accuracy, effective accuracy or macro-F1 after accounting
   for model and dataset? (Section K — the join is prepared, the test is not run.)
2. Do the 763 out-of-vocabulary labels fall on items whose GoEmotions gold label sits outside the five
   AnxioSense classes? Answerable from existing artifacts.
3. Is the persistent (5/5) versus sporadic (1/5) regime associated with item properties such as length, crisis
   language or gold label?
4. Is the Qwen ZS-CoT escaping defect associated with any measurable property of its 65 affected items?

---

## K. Quality / performance follow-up — prepared, not concluded

`cell_level_invalid_vs_quality.csv` (30 rows, one per dataset × model × strategy) joins this audit's
invalid-output measures to the frozen quality metrics so the association can be tested later:
`invalid_records_5runs`, `invalid_rate`, `unique_samples_affected`, `records_per_affected_sample`,
`dominant_failure_category`, `dominant_category_share`, `evaluability_mean`, `accuracy_conditional_mean`,
`accuracy_effective_mean`, `accuracy_gap_cond_minus_eff`, `macro_f1_mean`, `macro_f1_sd`,
`client_latency_mean_s`, `majority_baseline`.

**The two accuracy definitions must be kept apart.**

- `accuracy_conditional` = correct ÷ **valid**. Invalid outputs leave both numerator and denominator, so they
  **do not count as wrong**. A configuration that fails to emit a parseable answer on its hardest items can
  score *higher* here.
- `accuracy_effective` = correct ÷ **attributable**. Invalid outputs stay in the denominator.
- `accuracy_gap_cond_minus_eff` is the arithmetic consequence of the invalid rate, **not** evidence that
  invalid outputs harmed quality.

The largest gap sits with the largest invalid rate (Phi-4/GoEmotions/1S-CoT: invalid rate 16.05%, evaluability
0.8395, conditional 0.8011, effective 0.6730, gap 0.1281) — but this is **definitional**: effective accuracy is
conditional accuracy scaled by evaluability, so a gap is guaranteed whenever the invalid rate is non-zero.

**This audit does not conclude that invalid outputs "affected quality."** What would be needed:

1. A selection-effect test — are structurally failing items systematically harder or easier?
   `ISSUES_FOR_AUDIT.md` item 1 records the signature of one (Phi-4/GoEmotions/1S-CoT run 5: effective accuracy
   0.4486 while conditional macro-F1 *rises* to 0.6231). This audit adds a mechanism worth testing: in that
   cell the dominant failure is `empty_object`, and 197 of the run-5 samples were `ok_empty_list`
   (`non_distress`) in run 4 — i.e. the items that vanish are disproportionately the majority class.
2. An item-level model with dataset and model as covariates, since the 30 cells are not independent.
3. Uncertainty on the invalid rate itself, which this audit does not compute.
4. A pre-specified decision about which accuracy definition is primary.

Until then the honest statement is: *invalid outputs mechanically lower effective accuracy relative to
conditional accuracy in proportion to the invalid rate; whether they are associated with a genuine difference
in model quality is untested.*

---

## L. What changed from the partial (937-record) audit

The partial audit could inspect 937 of 1,986 records; 1,049 were `RAW_UNAVAILABLE`, including the largest cell
in the grid. Counts, rates and recurrence never depended on raw evidence and are **unchanged**. Everything
derived from raw text changed.

### L.1 Findings that changed

| Finding | Partial audit (937 inspected) | Complete audit (1,986) |
|---|---|---|
| Coverage | 47.2% | **100%** |
| Largest category | out_of_vocabulary 439 (46.9% of inspected) | out_of_vocabulary **763** (38.4% of all) |
| 2nd largest | malformed_json_escaping 264 | **empty_object 447** — was 28 and ranked 5th |
| Refusals | 86 | **227** |
| Llama Dreaddit profile | unknown (166 unclassified) | **120 of 166 are `bare_string_in_object_position`** |
| Phi-4 GoEmotions profile | unknown (873 unclassified) | empty_object 419, OOV 314, refusal 121 |
| Categories in the taxonomy | 12 | **15** — added `bare_string_in_object_position` (120), `unescaped_quote_in_string` (3), `missing_required_field` (1) |
| `malformed_json_other` | 3 | **1** — the 124-record residual was resolved into named causes |
| Parser-vs-model bucket 1 (no usable prediction) | 10.1% | **27.7%** |
| Parser-vs-model bucket 2 (readable answer, broken structure) | 32.3% (303 records) | **21.7% (430 records)** |
| Parser-vs-model bucket 3 (bad vocabulary) | 47.8% | **38.9%** |
| **Confirmed hallucinations** | **2** (both Dreaddit/Phi-4/ZS) | **4** — the two new ones are GoEmotions/Phi-4, and both **fabricate the input text or a property of it**, which is more serious than the two Dreaddit cases |
| Models producing OOV labels | Llama, Mistral | Llama, **Phi-4 (314)**, Mistral, **Qwen** |
| Refusal concentration in zero-shot | 48 of 86 (56%) | 143 of 227 (63%) — real, but the partial figure overstated the contrast between strategies |
| GoEmotions 1S-CoT ordering | flagged as "not robust, 499 records unclassified" | **confirmed**, and the driver is identified as `empty_object` (427 of 671) |

### L.2 Findings that did not change

- Executive totals, per-cell counts, invalid rates and every unique-sample / recurrence statistic.
- Zero infrastructure failures in the scored grid; 661 recovered transport failures at attempt level.
- Qwen/Dreaddit/ZS-CoT: 269 records from 65 unique items, 44 failing all five runs (81.8% of records).
- `malformed_json_escaping` = 264, 263 of them Qwen ZS-CoT.
- All 599 Dreaddit invalids have `server_referral_unreadable = true` — production and evaluation parsers agree.
- The `fail_truncated` / 600-character-cap methodological finding, now with two independent demonstrations.
- The conclusion that invalid output is a structural and vocabulary phenomenon rather than a fabrication one.

### L.3 What the coverage gap had cost

The partial audit's explicit caveat — *"1,049 records could not be inspected, 873 of them Phi-4 / GoEmotions —
the same model that produced both candidates"* — was well placed. Both additional hallucinations, the entire
`bare_string_in_object_position` category, and the true size of the `empty_object` and `refusal` categories
were inside the unread material. **No conclusion from the partial audit was contradicted; several were
substantially incomplete.**

---

## Files in this audit directory

| File | Contents |
|---|---|
| `invalid_outputs_row_level.csv` / `.jsonl` | 1,986 rows, one per model-invalid assessment, 56 columns |
| `failure_taxonomy_summary.csv` | Category definitions, counts, coverage, recoverability |
| `unique_sample_recurrence.csv` | Records vs unique samples, 1/5–5/5 distributions, raw similarity |
| `cell_level_invalid_vs_quality.csv` | Section K join, analysis-ready |
| `invalid_output_audit_report.md` | This report |
| `VALIDATION.md` | Validation checks, provenance gate, frozen-artifact integrity, checksums |
| `CHECKSUMS.sha256` | SHA-256 of every generated file |
| `code/01_build_index.py` … `code/06_quality_join.py` | The generator, re-runnable end to end |

Re-run with:

```
REPO=<repo> WORK=<scratch> OUT=<this dir> \
RUN_ROOTS="<repo>/evaluation/publication_experiments/runs:<external evidence>/publication_experiments/runs" \
python3 code/01_build_index.py && … && python3 code/05_validate.py
```

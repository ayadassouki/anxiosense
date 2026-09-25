# Invalid-output review subset — reading guide

Companion to `invalid_outputs_review_subset.csv`. The subset is a **sample for human reading**; `invalid_outputs_row_level.csv` remains the complete, authoritative 1,986-row audit and is unchanged. Nothing here was rescored or repaired: every raw response and every frozen field is copied verbatim.

## How to read a row

Open `input_text` and `raw_response` side by side. `frozen_parse_status`, `frozen_failure_class` and `frozen_failure_reason` are what the pipeline actually recorded. `apparent_prediction` is what a human can still see in the text — it is **descriptive only and was never scored**. `is_confirmed_hallucination` is `true` on exactly four rows.

## A note on `fail_truncated`

Where `frozen_parse_status` is `fail_truncated` (GoEmotions only), that label is decided by a **600-character legacy storage cap** in `emotion_payload.py` — `LEGACY_STORAGE_CAP = 600`. It is **not** evidence that the model or the API cut generation short. In the full audit, 98 of Phi-4's 419 empty objects carry it only because trailing reasoning prose pushed a complete `{}` past the cap, and two near-identical Llama responses (576 and 723 characters) landed in different buckets on length alone. Read `fail_truncated` and `fail_unparseable` together as *payload unreadable*. Dreaddit records that stop mid-object carry `unparseable` instead, and no claim is made there either about provider-side truncation.

---

## `out_of_vocabulary_label`

**Full-audit count: 763** of 1,986 (38.4%). In this subset: 7 row(s).

**1. What it means.** The JSON parsed perfectly. The model simply named an emotion that is not one of the seven labels the frozen mapping accepts, so there is nothing to map the answer onto.

**2. What to look for in the raw output.** The JSON is clean and complete. Read the first entry of the `emotions` array and check it against the seven keys the frozen mapping accepts: anxiety, fear, frustration, hopelessness, loneliness, sadness, stress. Anything else - joy, happiness, excitement, love, nostalgia, panic - lands here.

**3. Why the parser rejected it.** `parse_goemotions` reads the payload successfully, calls `primary_emotion()`, and finds the label is not a key of `ANXIOSENSE_TO_EVAL_CLASS`. Adding a mapping would be a methodology change, not a recovery, so the record is marked MODEL_BEHAVIOUR and excluded.

**4. Is a human-readable intended prediction still visible?** Yes - the model's own label is in `apparent_prediction`. It is recorded for review only and is NOT in the allowed vocabulary, so it was never scored.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Mistral Small 4, Phi-4, Qwen3.5 27B. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Llama 4 Scout / zero-shot-cot (175); Phi-4 / zero-shot-cot (159); Llama 4 Scout / one-shot-cot (143); Phi-4 / zero-shot (104).

**6. Clearest examples in the subset.**
- `ge_eduxv08` (Llama 4 Scout, one-shot-cot, run 1, 88 chars)
- `ge_eczje98` (Llama 4 Scout, one-shot-cot, run 1, 137 chars)


## `empty_object`

**Full-audit count: 447** of 1,986 (22.5%). In this subset: 4 row(s).

**1. What it means.** The model returned an empty JSON object `{}` instead of `{"emotions": []}`. Those are not the same thing: an empty list is a valid 'no distress detected' prediction, while `{}` has no emotions field at all, so no prediction was made.

**2. What to look for in the raw output.** Look for `{}` as the JSON block - often fence-wrapped, and on Phi-4 usually followed by step-numbered reasoning prose that says an empty set is being returned. Compare it mentally with `{"emotions": []}`.

**3. Why the parser rejected it.** The payload parses, but it has no `emotions` key at all, so `_emotions_from_obj` returns None and every later salvage step finds nothing. `{}` is NOT equivalent to `{"emotions": []}`: the latter is a valid non_distress prediction, the former contains no prediction. Treating them as the same would invent an answer on the model's behalf, which the parser explicitly refuses to do.

**4. Is a human-readable intended prediction still visible?** No. There is no emotions field to read, so nothing can be recovered without inventing it.

**5. Who produced it in the full audit.** Models: Gemma 4 31B, Mistral Small 4, Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / one-shot-cot (419); Mistral Small 4 / zero-shot (11); Mistral Small 4 / zero-shot-cot (9); Gemma 4 31B / one-shot-cot (6).

**6. Clearest examples in the subset.**
- `ge_ee5nfbq` (Gemma 4 31B, one-shot-cot, run 3, 14 chars)
- `ge_edeoxjd` (Mistral Small 4, one-shot-cot, run 1, 14 chars)


## `malformed_json_escaping`

**Full-audit count: 264** of 1,986 (13.3%). In this subset: 4 row(s).

**1. What it means.** The first field is fine, but every key after it is written with escaped quotes (`reasoning\":\"`), which makes the whole payload invalid JSON. The answer is readable to a human but not to a parser.

**2. What to look for in the raw output.** Read the very start of the payload: the first key/value pair is correct. Then look at the next key - it will be written `reasoning\":\"` with escaped quotes. From that point the payload is not valid JSON.

**3. Why the parser rejected it.** Strict `json.loads`, fence-stripping and balanced-object extraction all fail on the escaped delimiters, so `extract_risk_level` returns None.

**4. Is a human-readable intended prediction still visible?** Yes, very clearly - the literal `"risk_level":"moderate"` sits at the front of the text. This is the clearest example in the audit of a correct answer inside an unreadable payload.

**5. Who produced it in the full audit.** Models: Phi-4, Qwen3.5 27B. Strategies: zero-shot, zero-shot-cot. Largest cells: Qwen3.5 27B / zero-shot-cot (263); Phi-4 / zero-shot (1).

**6. Clearest examples in the subset.**
- `dread_1061` (Qwen3.5 27B, zero-shot-cot, run 1, 797 chars)
- `dread_1439` (Qwen3.5 27B, zero-shot-cot, run 1, 810 chars)


## `refusal_or_deflection`

**Full-audit count: 227** of 1,986 (11.4%). In this subset: 4 row(s).

**1. What it means.** The model declined the task, gave a safety disclaimer, or said no text was provided. No prediction field was produced at all.

**2. What to look for in the raw output.** The response talks to the reader instead of answering: a capability or safety disclaimer, a refusal to analyse the item, or a request for text that was in fact supplied. Three sub-types appear in the subset.

**3. Why the parser rejected it.** No `risk_level` or `emotions` field is emitted anywhere, so there is no prediction to read. This is not a parser limitation.

**4. Is a human-readable intended prediction still visible?** No.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Mistral Small 4, Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot (120); Phi-4 / zero-shot-cot (34); Phi-4 / one-shot-cot (29); Llama 4 Scout / zero-shot (23).

**6. Clearest examples in the subset.**
- `dread_870` (Llama 4 Scout, one-shot-cot, run 2, 208 chars)
- `dread_4114` (Llama 4 Scout, zero-shot, run 1, 365 chars)


## `bare_string_in_object_position`

**Full-audit count: 120** of 1,986 (6.0%). In this subset: 4 row(s).

**1. What it means.** The model kept writing more comma-separated sentences inside the JSON object, as if it were a list. The parser then reaches a place where a field name must appear and finds a loose sentence instead.

**2. What to look for in the raw output.** Start at `"reasoning":` and read forward. The value ends, a comma follows, and then another full sentence in quotes appears where a field name should be - sometimes several.

**3. Why the parser rejected it.** `json.loads` fails with "Expecting ':' delimiter" on all 120 records in the full audit: the parser reaches a position where a key is required and finds a bare string literal instead.

**4. Is a human-readable intended prediction still visible?** Usually yes - `risk_level` is the first field and is intact.

**5. Who produced it in the full audit.** Models: Llama 4 Scout. Strategies: zero-shot, zero-shot-cot. Largest cells: Llama 4 Scout / zero-shot (82); Llama 4 Scout / zero-shot-cot (38).

**6. Clearest examples in the subset.**
- `dread_1365` (Llama 4 Scout, zero-shot, run 1, 704 chars)
- `dread_1263` (Llama 4 Scout, zero-shot, run 1, 928 chars)


## `prose_or_markdown_instead_of_required_json`

**Full-audit count: 93** of 1,986 (4.7%). In this subset: 4 row(s).

**1. What it means.** The model wrote a message or a markdown summary for a human reader instead of the required JSON object.

**2. What to look for in the raw output.** There is no JSON object, or the object is buried in a message addressed to the reader. Some of these state the answer in markdown, e.g. `- **Risk Level:** "moderate"`.

**3. Why the parser rejected it.** No balanced JSON object containing the required key exists, so the ladder ends at None. The frozen contract requires the value inside a JSON object under the exact key; a markdown heading does not satisfy it.

**4. Is a human-readable intended prediction still visible?** Sometimes - where the model stated the level in prose it is recorded in `apparent_prediction`.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot (53); Llama 4 Scout / zero-shot-cot (13); Phi-4 / zero-shot-cot (9); Llama 4 Scout / zero-shot (8).

**6. Clearest examples in the subset.**
- `dread_12446` (Llama 4 Scout, one-shot-cot, run 1, 278 chars)
- `dread_196` (Llama 4 Scout, zero-shot-cot, run 1, 319 chars)


## `repeated_or_restarted_json`

**Full-audit count: 18** of 1,986 (0.9%). In this subset: 4 row(s).

**1. What it means.** The model began the JSON object again in the middle of writing it, so the braces never balance and no complete object can be extracted.

**2. What to look for in the raw output.** Count the opening braces. The object starts, gets partway through a value, and then begins again from `{"risk_level"` - often more than once. On GoEmotions the restart can happen inside the array itself.

**3. Why the parser rejected it.** Brace depth never returns to zero, so `first_balanced_object` finds no complete object and returns None.

**4. Is a human-readable intended prediction still visible?** Yes - the repeated copies all carry the same readable value.

**5. Who produced it in the full audit.** Models: Gemma 4 31B, Qwen3.5 27B. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Qwen3.5 27B / zero-shot (7); Qwen3.5 27B / zero-shot-cot (6); Qwen3.5 27B / one-shot-cot (4); Gemma 4 31B / one-shot-cot (1).

**6. Clearest examples in the subset.**
- `ge_eelmvui` (Gemma 4 31B, one-shot-cot, run 5, 112 chars)
- `dread_4114` (Qwen3.5 27B, zero-shot-cot, run 2, 493 chars)


## `missing_json_delimiter`

**Full-audit count: 17** of 1,986 (0.9%). In this subset: 5 row(s).

**1. What it means.** The opening brace is missing or corrupted, so although field names and values are visible there is no object for the parser to read.

**2. What to look for in the raw output.** The field names and values are visible but the opening `{` is absent or corrupted - sometimes replaced by stray quotes or line-continuation backslashes.

**3. Why the parser rejected it.** With no opening brace there is no object to locate, so balanced-object extraction fails.

**4. Is a human-readable intended prediction still visible?** Yes - all 17 records in the full audit carry a readable, allowed `risk_level`.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot (8); Llama 4 Scout / zero-shot (5); Phi-4 / one-shot-cot (2); Llama 4 Scout / zero-shot-cot (1).

**6. Clearest examples in the subset.**
- `dread_4114` (Llama 4 Scout, zero-shot, run 3, 581 chars)
- `dread_1460` (Llama 4 Scout, zero-shot-cot, run 1, 740 chars)


## `invalid_risk_level`

**Full-audit count: 9** of 1,986 (0.5%). In this subset: 4 row(s).

**1. What it means.** The object is well formed and has a risk_level field, but the value is not one of low, moderate or urgent, so it cannot be turned into a label.

**2. What to look for in the raw output.** The object is well formed. Read the value of `risk_level` and compare it with the allowed set low / moderate / urgent. Values seen in the full audit: undefined_input, undefined, unknown, unavailable, mild epxress, urget, medium, mandate_warning.

**3. Why the parser rejected it.** `extract_risk_level` reads the key, normalises the value, finds it outside the allowed set and returns None. The frozen ladder accepts no synonyms and performs no inference.

**4. Is a human-readable intended prediction still visible?** A value is visible but it is NOT in the allowed vocabulary, so it cannot be mapped to a label. Note `dread_43546`, where the model deliberately declined to classify rather than guessing.

**5. Who produced it in the full audit.** Models: Phi-4. Strategies: zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot-cot (5); Phi-4 / zero-shot (4).

**6. Clearest examples in the subset.**
- `dread_1570` (Phi-4, zero-shot-cot, run 1, 613 chars)
- `dread_726` (Phi-4, zero-shot-cot, run 1, 1123 chars)


## `commentary_inside_structured_field`

**Full-audit count: 6** of 1,986 (0.3%). In this subset: 4 row(s).

**1. What it means.** The model wrote explanatory prose inside the emotions array, where only quoted labels belong, so the array is not valid JSON.

**2. What to look for in the raw output.** Look inside the `emotions` array: instead of quoted labels it contains explanatory prose. Several of these responses then emit a corrected array further down.

**3. Why the parser rejected it.** The array's contents are not valid JSON, so the salvage regex - which matches the FIRST `"emotions": [...]` - cannot read it, and the corrected array later in the response is never reached. This is the one category where parser POLICY (first match rather than best match) decides the outcome.

**4. Is a human-readable intended prediction still visible?** Sometimes, in the corrected block. Those records are marked `structurally_recoverable = uncertain`.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Phi-4. Strategies: one-shot-cot, zero-shot-cot. Largest cells: Llama 4 Scout / zero-shot-cot (5); Phi-4 / one-shot-cot (1).

**6. Clearest examples in the subset.**
- `ge_eew50xj` (Llama 4 Scout, zero-shot-cot, run 3, 419 chars)
- `ge_ed9iecn` (Phi-4, one-shot-cot, run 3, 530 chars)


## `off_task_schema`

**Full-audit count: 4** of 1,986 (0.2%). In this subset: 4 row(s).

**1. What it means.** The model answered a different task altogether and emitted an unrelated schema, so none of the required fields are present.

**2. What to look for in the raw output.** The response answers a completely different task: intent ranking, apology detection, content filtering. The key names have nothing to do with the required schema.

**3. Why the parser rejected it.** None of the required fields is present, so there is nothing to read.

**4. Is a human-readable intended prediction still visible?** No.

**5. Who produced it in the full audit.** Models: Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot (2); Phi-4 / zero-shot-cot (1); Phi-4 / one-shot-cot (1).

**6. Clearest examples in the subset.**
- `ge_eenni73` (Phi-4, zero-shot, run 2, 663 chars)
- `dread_11468` (Phi-4, zero-shot-cot, run 5, 772 chars)


## `unescaped_quote_in_string`

**Full-audit count: 3** of 1,986 (0.2%). In this subset: 3 row(s).

**1. What it means.** A quotation mark inside a text value was not escaped (or the string was closed with the wrong quote character), which ends the string early and breaks the object.

**2. What to look for in the raw output.** Find the quotation marks inside a text value - e.g. `the "wrong" thing` - or a string closed with an apostrophe instead of a double quote.

**3. Why the parser rejected it.** The unescaped quote ends the string early, so `json.loads` fails with "Expecting value".

**4. Is a human-readable intended prediction still visible?** Yes - `risk_level` comes before the broken string.

**5. Who produced it in the full audit.** Models: Mistral Small 4, Phi-4. Strategies: zero-shot, zero-shot-cot. Largest cells: Phi-4 / zero-shot-cot (1); Mistral Small 4 / zero-shot (1); Mistral Small 4 / zero-shot-cot (1).

**6. Clearest examples in the subset.**
- `dread_25778` (Mistral Small 4, zero-shot-cot, run 1, 603 chars)
- `dread_25778` (Mistral Small 4, zero-shot, run 3, 614 chars)


## `missing_required_field`

**Full-audit count: 1** of 1,986 (0.1%). In this subset: 1 row(s).

**1. What it means.** A payload is present but it carries no risk_level / emotions field, so there is no prediction to read.

**2. What to look for in the raw output.** A payload exists but carries no `risk_level` / `emotions` field at all.

**3. Why the parser rejected it.** The required field is absent, so no prediction can be read.

**4. Is a human-readable intended prediction still visible?** No.

**5. Who produced it in the full audit.** Models: Phi-4. Strategies: zero-shot. Largest cells: Phi-4 / zero-shot (1).

**6. Clearest examples in the subset.**
- `ge_edbjz5j` (Phi-4, zero-shot, run 3, 753 chars)


## `malformed_json_other`

**Full-audit count: 1** of 1,986 (0.1%). In this subset: 1 row(s).

**1. What it means.** The payload could not be read by any step of the parser and does not match one of the named defect patterns; it is the residual case.

**2. What to look for in the raw output.** The residual case: nothing in the payload matches one of the named defect patterns above.

**3. Why the parser rejected it.** No step of the ladder can read it, and the specific JSON error does not match a known signature.

**4. Is a human-readable intended prediction still visible?** No.

**5. Who produced it in the full audit.** Models: Phi-4. Strategies: zero-shot. Largest cells: Phi-4 / zero-shot (1).

**6. Clearest examples in the subset.**
- `ge_edrbpty` (Phi-4, zero-shot, run 3, 835 chars)


## `apparent_truncation`

**Full-audit count: 13** of 1,986 (0.7%). In this subset: 4 row(s).

**1. What it means.** The payload stops before the required value is complete, so the parser declines to read a partial answer rather than guessing at the missing part.

**2. What to look for in the raw output.** The payload stops mid-object or mid-array; the closing brace or bracket is missing.

**3. Why the parser rejected it.** The required value did not survive. On GoEmotions the salvage regex requires the closing bracket and correctly declines to read a partial array rather than guessing at the missing content.

**4. Is a human-readable intended prediction still visible?** Sometimes - where `risk_level` appeared before the cut it is recorded in `apparent_prediction`.

**5. Who produced it in the full audit.** Models: Llama 4 Scout, Phi-4. Strategies: one-shot-cot, zero-shot, zero-shot-cot. Largest cells: Phi-4 / one-shot-cot (5); Phi-4 / zero-shot (3); Phi-4 / zero-shot-cot (2); Llama 4 Scout / zero-shot-cot (2).

**6. Clearest examples in the subset.**
- `ge_ef3hloa` (Llama 4 Scout, zero-shot-cot, run 2, 389 chars)
- `dread_39650` (Llama 4 Scout, zero-shot, run 2, 795 chars)


---

## The four confirmed hallucinations

Under the audit's operational definition — *a fabricated factual or content claim unsupported by the supplied input* — 17 records were flagged by the automated quotation check and **4 survived manual review**. All four are Phi-4. Formatting failure, wrong label, refusal, out-of-vocabulary label and repetition are explicitly NOT hallucination.

- **`ge_ee6o1mk`** (goemotions, Phi-4, one-shot-cot, run 2; filed under `empty_object`) — Phi-4/one-shot-cot/run2. The 26-character input is 'Sweaty little incel virgin'. The response asserts that 'the text provided is not self-reported but rather a link to an external source (`https://tinyurl.com/4kwgs3d5y`)' and returns an empty object on that basis. No link exists in the input; the URL is fabricated and the false premise drives the output.

- **`dread_33288`** (dreaddit, Phi-4, zero-shot, run 2; filed under `missing_json_delimiter`) — Phi-4/zero-shot/run2. Emits an unrelated schema including "excerpts selection": "./95761b9e005e46a8220492c40b04489201d2gz8" - a path-like identifier asserted as content that occurs nowhere in the input and refers to nothing in the task. Recorded alternative reading: a training-format artefact rather than a claim about the user's text; the response's own summary of the input is accurate.

- **`dread_649`** (dreaddit, Phi-4, zero-shot, run 4; filed under `missing_json_delimiter`) — Phi-4/zero-shot/run4. The 289-character input is about procrastinating on a Reddit post. The 8,480-character response narrates skiving, 14-hour film-set days and a Creative Coordinator role, opens with a quotation attributed to '4scenenotes.com', and presents an invented first-person tl;dr ('kinda on the verge of a burnout') as the user's words. None of it is in the input. Fabricated content plus a fabricated attribution.

- **`ge_eekj86e`** (goemotions, Phi-4, zero-shot, run 1; filed under `out_of_vocabulary_label`) — Phi-4/zero-shot/run1. The 79-character input is 'Maybe she was attempting to be ironic? I dunno, man, people are just an enigma.' Under a '### User Input' heading the response reproduces an entirely different, multi-sentence first-person distress narrative ('I feel really overwhelmed...', 'I was sleep a few hours last night', "Loneliness isn't strong enough to explain how I feel"), analyses that, and then asserts 'The user explicitly states feeling overwhelmed'. The analysed text is fabricated.

The subset also carries **2 contrast row(s)** that the automated test flagged and manual review **rejected**. They are marked `is_confirmed_hallucination = false` and `hallucination_reviewed_verdict = REJECTED`, and are included only so the difference between a real fabrication and a normalised or garbled quotation is visible side by side. The other 11 rejected candidates from the full audit are not in this subset and must not be counted as hallucinations.

---

## Subset composition

**Total subset size: 57 rows**, drawn from the completed 1,986-row audit.

| Dataset | rows in subset | full audit |
|---|---|---|
| dreaddit | 35 | 599 |
| goemotions | 22 | 1387 |

| Model | rows in subset | full audit |
|---|---|---|
| Gemma 4 31B | 2 | 7 |
| Llama 4 Scout | 22 | 615 |
| Mistral Small 4 | 4 | 50 |
| Phi-4 | 23 | 1024 |
| Qwen3.5 27B | 6 | 290 |

| Strategy | rows in subset | full audit |
|---|---|---|
| one-shot-cot | 15 | 699 |
| zero-shot | 23 | 541 |
| zero-shot-cot | 19 | 746 |

| Failure category | rows in subset | full audit |
|---|---|---|
| apparent_truncation | 4 | 13 |
| bare_string_in_object_position | 4 | 120 |
| commentary_inside_structured_field | 4 | 6 |
| empty_object | 4 | 447 |
| invalid_risk_level | 4 | 9 |
| malformed_json_escaping | 4 | 264 |
| malformed_json_other | 1 | 1 |
| missing_json_delimiter | 5 | 17 |
| missing_required_field | 1 | 1 |
| off_task_schema | 4 | 4 |
| out_of_vocabulary_label | 7 | 763 |
| prose_or_markdown_instead_of_required_json | 4 | 93 |
| refusal_or_deflection | 4 | 227 |
| repeated_or_restarted_json | 4 | 18 |
| unescaped_quote_in_string | 3 | 3 |

| Recurrence regime | rows in subset |
|---|---|
| intermittent (2-3/5) | 17 |
| one-off (1/5) | 27 |
| persistent (4-5/5) | 13 |

## Confirmations

- **All 4 manually confirmed hallucinations are included** (4 rows with `is_confirmed_hallucination = true`), each marked in `plain_english_why_invalid` and in `hallucination_reviewed_verdict`.

- **Every one of the 57 rows traces back to the completed 1,986-row audit** by `terminal_attempt_uuid`, which is the same key used to join the frozen authoritative record to its raw terminal attempt. `raw_sha256` on each row matches the audit dataset, so the raw text can be verified as unmodified.

- **All 15 failure categories in the full audit are represented**, including every one on the review list plus `apparent_truncation`, which is carried with its storage-cap caveat rather than dropped.

- **Nothing was rescored or repaired.** `invalid_outputs_row_level.csv` is untouched and remains the authoritative dataset.

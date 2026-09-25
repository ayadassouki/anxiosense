"""Stage 7 - build a human-review subset from the completed 1,986-row audit.

READ-ONLY with respect to everything that already exists. It reads
`invalid_outputs_row_level.jsonl` (the authoritative audit dataset, untouched) and the
work-directory raw extract (for `input_text`), and writes two NEW files:

    invalid_outputs_review_subset.csv
    invalid_outputs_review_subset_guide.md

Nothing is rescored and nothing is repaired: every raw response and every frozen field is
copied verbatim from the audit dataset.

Selection is deterministic (no RNG): candidates are ranked by a clarity score, then taken
round-robin across model x strategy x recurrence-regime so the subset spans the grid.
"""
import json, os, csv, collections

OUT = os.environ["OUT"]; WORK = os.environ["WORK"]
rows = [json.loads(l) for l in open(f"{OUT}/invalid_outputs_row_level.jsonl", encoding="utf-8")]
inputs = {}
for l in open(f"{WORK}/raws.jsonl", encoding="utf-8"):
    r = json.loads(l); inputs[r["attempt_uuid"]] = r.get("input_text") or ""

FULL = collections.Counter(r["primary_failure_category"] for r in rows)
PER_CAT_TARGET = 4

# Categories the reviewer asked for, plus apparent_truncation which is included with an
# explicit caveat rather than silently dropped.
REQUIRED = ["out_of_vocabulary_label", "empty_object", "malformed_json_escaping",
            "refusal_or_deflection", "bare_string_in_object_position",
            "prose_or_markdown_instead_of_required_json", "repeated_or_restarted_json",
            "missing_json_delimiter", "invalid_risk_level", "commentary_inside_structured_field",
            "off_task_schema", "unescaped_quote_in_string", "missing_required_field",
            "malformed_json_other"]
CATS = REQUIRED + ["apparent_truncation"]
assert set(CATS) == set(FULL), f"category mismatch: {set(FULL) ^ set(CATS)}"

def regime(r):
    n = int(r["n_runs_this_sample_failed_same_model_strategy"])
    return "one_off" if n == 1 else ("persistent" if n >= 4 else "intermittent")

def clarity(r):
    """Higher = a cleaner teaching example. Deliberately penalises borderline records."""
    s = 0.0
    L = int(r["raw_len"] or 0)
    if 60 <= L <= 2000: s += 3          # readable in one screen
    elif L <= 3500: s += 1
    else: s -= 2                         # very long responses obscure the defect
    nsec = len([x for x in (r["secondary_failure_category"] or "").split(";") if x])
    s += 2 if nsec == 0 else (0.5 if nsec == 1 else -1)   # single clean defect preferred
    if r["hallucination_reviewed_verdict"] == "CONFIRMED": s += 10
    if int(r["input_text_len"] or 0) <= 900: s += 1       # short input is easy to check
    return s

selected, why = {}, {}
def take(r, reason):
    k = r["terminal_attempt_uuid"]
    if k not in selected:
        selected[k] = r; why[k] = reason
    return k

# 1. every manually CONFIRMED hallucination, first
for r in sorted([x for x in rows if x["hallucination_reviewed_verdict"] == "CONFIRMED"],
                key=lambda x: (x["dataset"], x["sample_id"])):
    take(r, "MANUALLY CONFIRMED HALLUCINATION under the audit's operational definition "
            "(fabricated content unsupported by the supplied input). One of only 4 in the whole grid.")

# 2. per category, spread over model x strategy x recurrence regime
for cat in CATS:
    pool = sorted([r for r in rows if r["primary_failure_category"] == cat],
                  key=lambda r: (-clarity(r), r["model_short"], r["strategy"], r["run"], r["sample_id"]))
    target = min(PER_CAT_TARGET if FULL[cat] >= PER_CAT_TARGET else FULL[cat], len(pool))
    have = [r for r in selected.values() if r["primary_failure_category"] == cat]
    seen_ms = {(r["model_short"], r["strategy"]) for r in have}
    seen_rg = {regime(r) for r in have}
    # pass A: a new model x strategy pair each time
    for r in pool:
        if len(have) >= target: break
        ms = (r["model_short"], r["strategy"])
        if ms in seen_ms: continue
        take(r, f"Clear {cat} example; adds {r['model_short']} / {r['strategy']} coverage for this category.")
        have.append(r); seen_ms.add(ms); seen_rg.add(regime(r))
    # pass B: make sure both a one-off and a repeatedly-failing sample are present
    for want in ("one_off", "persistent", "intermittent"):
        if want in seen_rg: continue
        for r in pool:
            if regime(r) != want: continue
            n = r["n_runs_this_sample_failed_same_model_strategy"]
            take(r, f"Clear {cat} example, chosen to show the {want.replace('_', '-')} pattern "
                    f"(this sample failed {n} of 5 runs under the same model and strategy).")
            have.append(r); seen_rg.add(want); break
        if len(have) >= target + 1: break
    # pass C: top up on clarity
    for r in pool:
        if len(have) >= target: break
        if r["terminal_attempt_uuid"] in selected: continue
        take(r, f"Additional clear {cat} example.")
        have.append(r)

# 3. grid coverage top-up: every model, strategy and dataset that has invalids must appear
def cover(keyfn, label):
    present = {keyfn(r) for r in selected.values()}
    for k in sorted({keyfn(r) for r in rows} - present):
        pool = sorted([r for r in rows if keyfn(r) == k], key=lambda r: -clarity(r))
        if pool:
            take(pool[0], f"Coverage row: the subset otherwise contained no example from {label} = {k}.")

cover(lambda r: r["model_short"], "model")
cover(lambda r: r["strategy"], "strategy")
cover(lambda r: r["dataset"], "dataset")
cover(lambda r: (r["dataset"], r["strategy"]), "dataset x strategy")

# 4. two contrast rows: flagged by the automated hallucination test, REJECTED on review
rej = sorted([r for r in rows if r["hallucination_reviewed_verdict"] == "REJECTED"],
             key=lambda r: (-clarity(r), r["sample_id"]))
for r in rej[:2]:
    take(r, "CONTRAST ROW - the automated hallucination test flagged this one and manual review "
            "REJECTED it. Included so the difference between a real fabrication and a normalised or "
            "garbled quotation is visible side by side. NOT a hallucination.")

PLAIN = {
 "out_of_vocabulary_label":
   "The JSON parsed perfectly. The model simply named an emotion that is not one of the seven labels the "
   "frozen mapping accepts, so there is nothing to map the answer onto.",
 "empty_object":
   "The model returned an empty JSON object `{}` instead of `{\"emotions\": []}`. Those are not the same "
   "thing: an empty list is a valid 'no distress detected' prediction, while `{}` has no emotions field at "
   "all, so no prediction was made.",
 "malformed_json_escaping":
   "The first field is fine, but every key after it is written with escaped quotes (`reasoning\\\":\\\"`), "
   "which makes the whole payload invalid JSON. The answer is readable to a human but not to a parser.",
 "refusal_or_deflection":
   "The model declined the task, gave a safety disclaimer, or said no text was provided. No prediction "
   "field was produced at all.",
 "bare_string_in_object_position":
   "The model kept writing more comma-separated sentences inside the JSON object, as if it were a list. "
   "The parser then reaches a place where a field name must appear and finds a loose sentence instead.",
 "prose_or_markdown_instead_of_required_json":
   "The model wrote a message or a markdown summary for a human reader instead of the required JSON object.",
 "repeated_or_restarted_json":
   "The model began the JSON object again in the middle of writing it, so the braces never balance and no "
   "complete object can be extracted.",
 "missing_json_delimiter":
   "The opening brace is missing or corrupted, so although field names and values are visible there is no "
   "object for the parser to read.",
 "invalid_risk_level":
   "The object is well formed and has a risk_level field, but the value is not one of low, moderate or "
   "urgent, so it cannot be turned into a label.",
 "commentary_inside_structured_field":
   "The model wrote explanatory prose inside the emotions array, where only quoted labels belong, so the "
   "array is not valid JSON.",
 "off_task_schema":
   "The model answered a different task altogether and emitted an unrelated schema, so none of the required "
   "fields are present.",
 "unescaped_quote_in_string":
   "A quotation mark inside a text value was not escaped (or the string was closed with the wrong quote "
   "character), which ends the string early and breaks the object.",
 "missing_required_field":
   "A payload is present but it carries no risk_level / emotions field, so there is no prediction to read.",
 "malformed_json_other":
   "The payload could not be read by any step of the parser and does not match one of the named defect "
   "patterns; it is the residual case.",
 "apparent_truncation":
   "The payload stops before the required value is complete, so the parser declines to read a partial "
   "answer rather than guessing at the missing part.",
}
# The storage-cap caveat applies ONLY where the frozen status is literally `fail_truncated`,
# which exists only on GoEmotions. Dreaddit payloads that stop mid-object carry the status
# `unparseable`; nothing there is claimed about provider-side truncation either.
CAP_CAVEAT = (" IMPORTANT: the frozen status `fail_truncated` is decided by a 600-character LEGACY STORAGE "
              "CAP in emotion_payload.py, NOT by any evidence that the model or the API cut generation "
              "short. Read it as 'payload unreadable', never as truncation by the provider.")
DREADDIT_TRUNC_NOTE = (" Note: this Dreaddit record is stored with the status `unparseable`. The payload as "
                       "stored ends before the object closes; no claim is made about whether the provider "
                       "truncated the response.")

def plain(r):
    t = PLAIN[r["primary_failure_category"]]
    if r["parse_status"] == "fail_truncated":
        t += CAP_CAVEAT
    elif r["primary_failure_category"] == "apparent_truncation":
        t += DREADDIT_TRUNC_NOTE
    if r["human_readable_prediction_present"] == "true" and r["apparent_prediction"]:
        t += (f" A human can still read an intended answer of '{r['apparent_prediction']}' in the text; "
              f"that is recorded for review only and was NOT scored.")
    if r["hallucination_reviewed_verdict"] == "CONFIRMED":
        t = ("*** CONFIRMED HALLUCINATION (manually reviewed). *** " + r["hallucination_review_basis"] +
             " Separately, the reason the PARSER rejected it: " + t)
    elif r["hallucination_reviewed_verdict"] == "REJECTED":
        t = ("[Flagged by the automated hallucination test and REJECTED on manual review - this is NOT a "
             "hallucination. " + r["hallucination_review_basis"] + "] " + t)
    return t

COLS = ["dataset", "model", "model_id", "strategy", "run", "sample_id", "cell_id", "ground_truth",
        "input_text", "raw_field_name", "raw_response", "raw_len",
        "frozen_parse_status", "frozen_failure_class", "frozen_failure_reason",
        "primary_failure_category", "secondary_failure_category",
        "human_readable_prediction_present", "apparent_prediction",
        "apparent_prediction_in_allowed_vocabulary",
        "structurally_recoverable", "why_recoverable_or_not",
        "n_runs_this_sample_failed_same_model_strategy",
        "is_confirmed_hallucination", "hallucination_reviewed_verdict", "hallucination_review_basis",
        "plain_english_why_invalid", "why_selected_for_review",
        "terminal_attempt_uuid", "raw_sha256"]

out = []
for k, r in selected.items():
    out.append({
        "dataset": r["dataset"], "model": r["model_short"], "model_id": r["model"],
        "strategy": r["strategy"], "run": r["run"], "sample_id": r["sample_id"],
        "cell_id": r["cell_id"], "ground_truth": r["ground_truth"],
        "input_text": inputs.get(k, ""), "raw_field_name": r["raw_field_name"],
        "raw_response": r["raw_response"], "raw_len": r["raw_len"],
        "frozen_parse_status": r["parse_status"], "frozen_failure_class": r["failure_class"],
        "frozen_failure_reason": r["failure_reason"],
        "primary_failure_category": r["primary_failure_category"],
        "secondary_failure_category": r["secondary_failure_category"],
        "human_readable_prediction_present": r["human_readable_prediction_present"],
        "apparent_prediction": r["apparent_prediction"],
        "apparent_prediction_in_allowed_vocabulary": r["apparent_prediction_in_allowed_vocabulary"],
        "structurally_recoverable": r["structurally_recoverable"],
        "why_recoverable_or_not": r["why_recoverable_or_not"],
        "n_runs_this_sample_failed_same_model_strategy": r["n_runs_this_sample_failed_same_model_strategy"],
        "is_confirmed_hallucination": "true" if r["hallucination_reviewed_verdict"] == "CONFIRMED" else "false",
        "hallucination_reviewed_verdict": r["hallucination_reviewed_verdict"],
        "hallucination_review_basis": r["hallucination_review_basis"],
        "plain_english_why_invalid": plain(r),
        "why_selected_for_review": why[k],
        "terminal_attempt_uuid": k, "raw_sha256": r["raw_sha256"],
    })
out.sort(key=lambda r: (r["primary_failure_category"], r["dataset"], r["model"], r["strategy"], r["run"],
                        r["sample_id"]))
with open(f"{OUT}/invalid_outputs_review_subset.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
    for r in out: w.writerow(r)

json.dump({"n": len(out),
           "by_dataset": dict(collections.Counter(r["dataset"] for r in out)),
           "by_model": dict(collections.Counter(r["model"] for r in out)),
           "by_strategy": dict(collections.Counter(r["strategy"] for r in out)),
           "by_category": dict(collections.Counter(r["primary_failure_category"] for r in out)),
           "confirmed_hallucinations": sum(1 for r in out if r["is_confirmed_hallucination"] == "true"),
           "full_audit_counts": dict(FULL)},
          open(f"{WORK}/subset_stats.json", "w"), indent=1, sort_keys=True)

print("subset rows:", len(out))
for lbl, c in [("dataset", "dataset"), ("model", "model"), ("strategy", "strategy")]:
    print(lbl, dict(collections.Counter(r[c] for r in out)))
print("\ncategory: subset / full audit")
for cat in CATS:
    print("  %-46s %3d / %4d" % (cat, sum(1 for r in out if r["primary_failure_category"] == cat), FULL[cat]))
print("\nconfirmed hallucinations in subset:",
      sum(1 for r in out if r["is_confirmed_hallucination"] == "true"),
      "| rejected-candidate contrast rows:",
      sum(1 for r in out if r["hallucination_reviewed_verdict"] == "REJECTED"))


# ── companion guide ─────────────────────────────────────────────────────────────
LOOK_FOR = {
 "out_of_vocabulary_label": (
   "The JSON is clean and complete. Read the first entry of the `emotions` array and check it against the "
   "seven keys the frozen mapping accepts: anxiety, fear, frustration, hopelessness, loneliness, sadness, "
   "stress. Anything else - joy, happiness, excitement, love, nostalgia, panic - lands here.",
   "`parse_goemotions` reads the payload successfully, calls `primary_emotion()`, and finds the label is not "
   "a key of `ANXIOSENSE_TO_EVAL_CLASS`. Adding a mapping would be a methodology change, not a recovery, so "
   "the record is marked MODEL_BEHAVIOUR and excluded.",
   "Yes - the model's own label is in `apparent_prediction`. It is recorded for review only and is NOT in "
   "the allowed vocabulary, so it was never scored."),
 "empty_object": (
   "Look for `{}` as the JSON block - often fence-wrapped, and on Phi-4 usually followed by step-numbered "
   "reasoning prose that says an empty set is being returned. Compare it mentally with `{\"emotions\": []}`.",
   "The payload parses, but it has no `emotions` key at all, so `_emotions_from_obj` returns None and every "
   "later salvage step finds nothing. `{}` is NOT equivalent to `{\"emotions\": []}`: the latter is a valid "
   "non_distress prediction, the former contains no prediction. Treating them as the same would invent an "
   "answer on the model's behalf, which the parser explicitly refuses to do.",
   "No. There is no emotions field to read, so nothing can be recovered without inventing it."),
 "malformed_json_escaping": (
   "Read the very start of the payload: the first key/value pair is correct. Then look at the next key - it "
   "will be written `reasoning\\\":\\\"` with escaped quotes. From that point the payload is not valid JSON.",
   "Strict `json.loads`, fence-stripping and balanced-object extraction all fail on the escaped delimiters, "
   "so `extract_risk_level` returns None.",
   "Yes, very clearly - the literal `\"risk_level\":\"moderate\"` sits at the front of the text. This is the "
   "clearest example in the audit of a correct answer inside an unreadable payload."),
 "refusal_or_deflection": (
   "The response talks to the reader instead of answering: a capability or safety disclaimer, a refusal to "
   "analyse the item, or a request for text that was in fact supplied. Three sub-types appear in the subset.",
   "No `risk_level` or `emotions` field is emitted anywhere, so there is no prediction to read. This is not "
   "a parser limitation.",
   "No."),
 "bare_string_in_object_position": (
   "Start at `\"reasoning\":` and read forward. The value ends, a comma follows, and then another full "
   "sentence in quotes appears where a field name should be - sometimes several.",
   "`json.loads` fails with \"Expecting ':' delimiter\" on all 120 records in the full audit: the parser "
   "reaches a position where a key is required and finds a bare string literal instead.",
   "Usually yes - `risk_level` is the first field and is intact."),
 "prose_or_markdown_instead_of_required_json": (
   "There is no JSON object, or the object is buried in a message addressed to the reader. Some of these "
   "state the answer in markdown, e.g. `- **Risk Level:** \"moderate\"`.",
   "No balanced JSON object containing the required key exists, so the ladder ends at None. The frozen "
   "contract requires the value inside a JSON object under the exact key; a markdown heading does not "
   "satisfy it.",
   "Sometimes - where the model stated the level in prose it is recorded in `apparent_prediction`."),
 "repeated_or_restarted_json": (
   "Count the opening braces. The object starts, gets partway through a value, and then begins again from "
   "`{\"risk_level\"` - often more than once. On GoEmotions the restart can happen inside the array itself.",
   "Brace depth never returns to zero, so `first_balanced_object` finds no complete object and returns None.",
   "Yes - the repeated copies all carry the same readable value."),
 "missing_json_delimiter": (
   "The field names and values are visible but the opening `{` is absent or corrupted - sometimes replaced "
   "by stray quotes or line-continuation backslashes.",
   "With no opening brace there is no object to locate, so balanced-object extraction fails.",
   "Yes - all 17 records in the full audit carry a readable, allowed `risk_level`."),
 "invalid_risk_level": (
   "The object is well formed. Read the value of `risk_level` and compare it with the allowed set "
   "low / moderate / urgent. Values seen in the full audit: undefined_input, undefined, unknown, "
   "unavailable, mild epxress, urget, medium, mandate_warning.",
   "`extract_risk_level` reads the key, normalises the value, finds it outside the allowed set and returns "
   "None. The frozen ladder accepts no synonyms and performs no inference.",
   "A value is visible but it is NOT in the allowed vocabulary, so it cannot be mapped to a label. Note "
   "`dread_43546`, where the model deliberately declined to classify rather than guessing."),
 "commentary_inside_structured_field": (
   "Look inside the `emotions` array: instead of quoted labels it contains explanatory prose. Several of "
   "these responses then emit a corrected array further down.",
   "The array's contents are not valid JSON, so the salvage regex - which matches the FIRST "
   "`\"emotions\": [...]` - cannot read it, and the corrected array later in the response is never reached. "
   "This is the one category where parser POLICY (first match rather than best match) decides the outcome.",
   "Sometimes, in the corrected block. Those records are marked `structurally_recoverable = uncertain`."),
 "off_task_schema": (
   "The response answers a completely different task: intent ranking, apology detection, content filtering. "
   "The key names have nothing to do with the required schema.",
   "None of the required fields is present, so there is nothing to read.",
   "No."),
 "unescaped_quote_in_string": (
   "Find the quotation marks inside a text value - e.g. `the \"wrong\" thing` - or a string closed with an "
   "apostrophe instead of a double quote.",
   "The unescaped quote ends the string early, so `json.loads` fails with \"Expecting value\".",
   "Yes - `risk_level` comes before the broken string."),
 "missing_required_field": (
   "A payload exists but carries no `risk_level` / `emotions` field at all.",
   "The required field is absent, so no prediction can be read.",
   "No."),
 "malformed_json_other": (
   "The residual case: nothing in the payload matches one of the named defect patterns above.",
   "No step of the ladder can read it, and the specific JSON error does not match a known signature.",
   "No."),
 "apparent_truncation": (
   "The payload stops mid-object or mid-array; the closing brace or bracket is missing.",
   "The required value did not survive. On GoEmotions the salvage regex requires the closing bracket and "
   "correctly declines to read a partial array rather than guessing at the missing content.",
   "Sometimes - where `risk_level` appeared before the cut it is recorded in `apparent_prediction`."),
}

CAT_ORDER = ["out_of_vocabulary_label", "empty_object", "malformed_json_escaping", "refusal_or_deflection",
             "bare_string_in_object_position", "prose_or_markdown_instead_of_required_json",
             "repeated_or_restarted_json", "missing_json_delimiter", "invalid_risk_level",
             "commentary_inside_structured_field", "off_task_schema", "unescaped_quote_in_string",
             "missing_required_field", "malformed_json_other", "apparent_truncation"]

full_ms = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    full_ms[r["primary_failure_category"]][(r["model_short"], r["strategy"])] += 1

def clearest(cat, n=2):
    """Plain examples first: rows carrying a hallucination verdict (confirmed OR rejected)
    are held back, because the reviewer should read the category on an uncomplicated case."""
    picks = sorted([r for r in out if r["primary_failure_category"] == cat],
                   key=lambda r: (r["hallucination_reviewed_verdict"] != "NOT_FLAGGED",
                                  int(r["raw_len"] or 0)))
    return picks[:n]

g = []
g.append("# Invalid-output review subset — reading guide\n")
g.append("Companion to `invalid_outputs_review_subset.csv`. The subset is a **sample for human reading**; "
         "`invalid_outputs_row_level.csv` remains the complete, authoritative 1,986-row audit and is "
         "unchanged. Nothing here was rescored or repaired: every raw response and every frozen field is "
         "copied verbatim.\n")
g.append("## How to read a row\n")
g.append("Open `input_text` and `raw_response` side by side. `frozen_parse_status`, `frozen_failure_class` "
         "and `frozen_failure_reason` are what the pipeline actually recorded. `apparent_prediction` is what "
         "a human can still see in the text — it is **descriptive only and was never scored**. "
         "`is_confirmed_hallucination` is `true` on exactly four rows.\n")
g.append("## A note on `fail_truncated`\n")
g.append("Where `frozen_parse_status` is `fail_truncated` (GoEmotions only), that label is decided by a "
         "**600-character legacy storage cap** in `emotion_payload.py` — `LEGACY_STORAGE_CAP = 600`. It is "
         "**not** evidence that the model or the API cut generation short. In the full audit, 98 of Phi-4's "
         "419 empty objects carry it only because trailing reasoning prose pushed a complete `{}` past the "
         "cap, and two near-identical Llama responses (576 and 723 characters) landed in different buckets on "
         "length alone. Read `fail_truncated` and `fail_unparseable` together as *payload unreadable*. "
         "Dreaddit records that stop mid-object carry `unparseable` instead, and no claim is made there "
         "either about provider-side truncation.\n")
g.append("---\n")
for cat in CAT_ORDER:
    meaning, why_rej, readable = LOOK_FOR[cat][0], LOOK_FOR[cat][1], LOOK_FOR[cat][2]
    ms = full_ms[cat]
    models = sorted({m for m, _ in ms})
    strats = sorted({st for _, st in ms})
    top = "; ".join(f"{m} / {st} ({n})" for (m, st), n in ms.most_common(4))
    nsub = sum(1 for r in out if r["primary_failure_category"] == cat)
    g.append(f"## `{cat}`\n")
    g.append(f"**Full-audit count: {FULL[cat]}** of 1,986 ({100*FULL[cat]/1986:.1f}%). "
             f"In this subset: {nsub} row(s).\n")
    g.append(f"**1. What it means.** {PLAIN[cat]}\n")
    g.append(f"**2. What to look for in the raw output.** {meaning}\n")
    g.append(f"**3. Why the parser rejected it.** {why_rej}\n")
    g.append(f"**4. Is a human-readable intended prediction still visible?** {readable}\n")
    g.append(f"**5. Who produced it in the full audit.** Models: {', '.join(models)}. "
             f"Strategies: {', '.join(strats)}. Largest cells: {top}.\n")
    ex = clearest(cat)
    bullets = []
    for r in ex:
        tag = " — **CONFIRMED HALLUCINATION**" if r["is_confirmed_hallucination"] == "true" else ""
        bullets.append(f"- `{r['sample_id']}` ({r['model']}, {r['strategy']}, run {r['run']}, "
                       f"{r['raw_len']} chars){tag}")
    g.append("**6. Clearest examples in the subset.**\n" + "\n".join(bullets) + "\n")
    g.append("")

g.append("---\n")
g.append("## The four confirmed hallucinations\n")
g.append("Under the audit's operational definition — *a fabricated factual or content claim unsupported by "
         "the supplied input* — 17 records were flagged by the automated quotation check and **4 survived "
         "manual review**. All four are Phi-4. Formatting failure, wrong label, refusal, out-of-vocabulary "
         "label and repetition are explicitly NOT hallucination.\n")
for r in [x for x in out if x["is_confirmed_hallucination"] == "true"]:
    g.append(f"- **`{r['sample_id']}`** ({r['dataset']}, {r['model']}, {r['strategy']}, run {r['run']}; "
             f"filed under `{r['primary_failure_category']}`) — {r['hallucination_review_basis']}\n")
nrej = sum(1 for r in out if r["hallucination_reviewed_verdict"] == "REJECTED")
g.append(f"The subset also carries **{nrej} contrast row(s)** that the automated test flagged and manual "
         "review **rejected**. They are marked `is_confirmed_hallucination = false` and "
         "`hallucination_reviewed_verdict = REJECTED`, and are included only so the difference between a "
         "real fabrication and a normalised or garbled quotation is visible side by side. The other 11 "
         "rejected candidates from the full audit are not in this subset and must not be counted as "
         "hallucinations.\n")

g.append("---\n")
g.append("## Subset composition\n")
g.append(f"**Total subset size: {len(out)} rows**, drawn from the completed 1,986-row audit.\n")
def tbl(title, counter, denom=None):
    lines = [f"| {title} | rows in subset |" + (" full audit |" if denom else ""),
             "|---|---|" + ("---|" if denom else "")]
    for k, v in sorted(counter.items()):
        lines.append(f"| {k} | {v} |" + (f" {denom[k]} |" if denom else ""))
    return "\n".join(lines) + "\n"
full_ds = collections.Counter(r["dataset"] for r in rows)
full_md = collections.Counter(r["model_short"] for r in rows)
full_st = collections.Counter(r["strategy"] for r in rows)
g.append(tbl("Dataset", collections.Counter(r["dataset"] for r in out), full_ds))
g.append(tbl("Model", collections.Counter(r["model"] for r in out), full_md))
g.append(tbl("Strategy", collections.Counter(r["strategy"] for r in out), full_st))
g.append(tbl("Failure category", collections.Counter(r["primary_failure_category"] for r in out), FULL))
reg_c = collections.Counter(
    "one-off (1/5)" if int(r["n_runs_this_sample_failed_same_model_strategy"]) == 1
    else ("persistent (4-5/5)" if int(r["n_runs_this_sample_failed_same_model_strategy"]) >= 4
          else "intermittent (2-3/5)") for r in out)
g.append(tbl("Recurrence regime", reg_c))
g.append("## Confirmations\n")
nh = sum(1 for r in out if r["is_confirmed_hallucination"] == "true")
g.append(f"- **All 4 manually confirmed hallucinations are included** ({nh} rows with "
         "`is_confirmed_hallucination = true`), each marked in `plain_english_why_invalid` and in "
         "`hallucination_reviewed_verdict`.\n")
g.append(f"- **Every one of the {len(out)} rows traces back to the completed 1,986-row audit** by "
         "`terminal_attempt_uuid`, which is the same key used to join the frozen authoritative record to its "
         "raw terminal attempt. `raw_sha256` on each row matches the audit dataset, so the raw text can be "
         "verified as unmodified.\n")
g.append("- **All 15 failure categories in the full audit are represented**, including every one on the "
         "review list plus `apparent_truncation`, which is carried with its storage-cap caveat rather than "
         "dropped.\n")
g.append("- **Nothing was rescored or repaired.** `invalid_outputs_row_level.csv` is untouched and remains "
         "the authoritative dataset.\n")
open(f"{OUT}/invalid_outputs_review_subset_guide.md", "w", encoding="utf-8").write("\n".join(g))
print("guide written:", f"{OUT}/invalid_outputs_review_subset_guide.md")

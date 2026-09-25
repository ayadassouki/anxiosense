"""Stage 4 - summary tables derived from the row-level audit dataset."""
import json, os, csv, collections

OUT = os.environ["OUT"]
rows = [json.loads(l) for l in open(f"{OUT}/invalid_outputs_row_level.jsonl", encoding="utf-8")]

DEFN = {
 "malformed_json_escaping": "A structurally recognisable payload whose key/value delimiters are escaped (e.g. `reasoning\\\":\\\"`), making the whole string invalid JSON even though the leading field is readable.",
 "repeated_or_restarted_json": "The model restarts the object mid-string one or more times, so brace depth never returns to zero and no balanced object can be extracted.",
 "missing_json_delimiter": "The opening `{` is absent or corrupted (line-continuation escapes, stray quotes), so no balanced object can be located.",
 "prose_or_markdown_instead_of_required_json": "The response is prose or markdown addressed to the reader rather than the required structured object.",
 "refusal_or_deflection": "The response declines the task, redirects to general advice, or asserts that no input was supplied.",
 "missing_required_field": "A parseable object is present but the required key (`risk_level` / `emotions`) is absent.",
 "empty_object": "The payload is an empty JSON object `{}`. It parses but carries no `emotions` key, so it is not equivalent to `{\"emotions\": []}`.",
 "out_of_vocabulary_label": "The payload parses cleanly and yields a first emotion that is not a key of the frozen ANXIOSENSE_TO_EVAL_CLASS map.",
 "invalid_risk_level": "A `risk_level` field is present but its value lies outside the allowed set (low|moderate|urgent).",
 "commentary_inside_structured_field": "Prose commentary is emitted inside a field that must contain structured values, so the field is not valid JSON.",
 "apparent_truncation": "The payload ends mid-object or mid-array; the required value did not survive.",
 "off_task_schema": "A structured object is emitted whose key set is disjoint from the required schema - the model answered a different task.",
 "malformed_json_other": "Not parseable by strict JSON, fence-stripping or balanced-object extraction, for a reason other than the signatures above.",
 "RAW_UNAVAILABLE": "Raw evidence is on an external volume that is not mounted; no classification is asserted.",
}
SEC_DEFN = {
 "degenerate_repetition": "A >=120-character window recurs at least three times in the response.",
 "off_task_content": "Fewer than 20% of the input's distinct content tokens appear anywhere in a response longer than 400 characters.",
 "hallucination_candidate": "Flagged by the hallucination audit; see the hallucination_* columns.",
 "commentary_inside_structured_field": "See primary definition.",
 "prose_or_markdown_instead_of_required_json": "See primary definition.",
 "missing_required_field": "See primary definition.",
}

# ── taxonomy summary ────────────────────────────────────────────────────────────
n_all = len(rows); n_cls = sum(1 for r in rows if r["raw_available"] == "true")
prim = collections.Counter(r["primary_failure_category"] for r in rows)
agg = collections.defaultdict(lambda: {"ds": set(), "md": set(), "st": set(), "rec": 0, "hrp": 0})
for r in rows:
    a = agg[r["primary_failure_category"]]
    a["ds"].add(r["dataset"]); a["md"].add(r["model_short"]); a["st"].add(r["strategy"])
    if r["structurally_recoverable"] == "true": a["rec"] += 1
    if r["human_readable_prediction_present"] == "true": a["hrp"] += 1
with open(f"{OUT}/failure_taxonomy_summary.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["level", "category", "definition", "count", "pct_of_all_invalid",
                "pct_of_classified_invalid", "datasets", "models", "strategies",
                "n_with_human_readable_prediction", "n_structurally_recoverable"])
    for c, n in prim.most_common():
        a = agg[c]
        w.writerow(["primary", c, DEFN.get(c, ""), n, round(100 * n / n_all, 2),
                    "" if c == "RAW_UNAVAILABLE" else round(100 * n / n_cls, 2),
                    "|".join(sorted(a["ds"])), "|".join(sorted(a["md"])), "|".join(sorted(a["st"])),
                    a["hrp"], a["rec"]])
    sec = collections.Counter()
    for r in rows:
        for x in (r["secondary_failure_category"] or "").split(";"):
            if x and x != "RAW_UNAVAILABLE": sec[x] += 1
    for c, n in sec.most_common():
        w.writerow(["secondary", c, SEC_DEFN.get(c, ""), n, round(100 * n / n_all, 2),
                    round(100 * n / n_cls, 2), "", "", "", "", ""])
print("taxonomy rows:", len(prim) + len(sec))

# ── unique-sample recurrence ────────────────────────────────────────────────────
g = collections.defaultdict(list)
for r in rows: g[(r["dataset"], r["model_short"], r["strategy"], r["sample_id"])].append(r)
cell = collections.defaultdict(lambda: {"rec": 0, "samples": {}, "cats": collections.Counter()})
for (ds, m, st, sid), rs in g.items():
    c = cell[(ds, m, st)]
    c["rec"] += len(rs); c["samples"][sid] = len(rs)
    c["cats"][rs[0]["raw_outputs_identical_or_similar"]] += 1
    for r in rs: c["cats"]["cat::" + r["primary_failure_category"]] += 1
ATT = {"dreaddit": 3495, "goemotions": 3110}
with open(f"{OUT}/unique_sample_recurrence.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["dataset", "model", "strategy", "invalid_assessment_records", "invalid_rate_pct",
                "unique_samples_affected", "failed_1of5", "failed_2of5", "failed_3of5", "failed_4of5",
                "failed_5of5", "pct_records_from_5of5_samples", "raw_identical_groups",
                "raw_similar_groups", "raw_different_groups", "raw_unknown_groups",
                "primary_categories"])
    for (ds, m, st), c in sorted(cell.items()):
        d = collections.Counter(c["samples"].values())
        cats = {k[5:]: v for k, v in c["cats"].items() if k.startswith("cat::")}
        w.writerow([ds, m, st, c["rec"], round(100 * c["rec"] / ATT[ds], 2), len(c["samples"]),
                    d.get(1, 0), d.get(2, 0), d.get(3, 0), d.get(4, 0), d.get(5, 0),
                    round(100 * 5 * d.get(5, 0) / c["rec"], 1) if c["rec"] else 0,
                    c["cats"].get("identical", 0), c["cats"].get("similar", 0),
                    c["cats"].get("different", 0),
                    c["cats"].get("RAW_UNAVAILABLE", 0) + c["cats"].get("n/a_single_run", 0),
                    "; ".join(f"{k}={v}" for k, v in sorted(cats.items(), key=lambda x: -x[1]))])
print("recurrence rows:", len(cell))

for key in [("dreaddit", "Qwen3.5 27B", "zero-shot-cot")]:
    c = cell[key]; d = collections.Counter(c["samples"].values())
    print(f"\n{key}: {c['rec']} records over {len(c['samples'])} unique samples; "
          f"run-distribution {dict(sorted(d.items()))}")

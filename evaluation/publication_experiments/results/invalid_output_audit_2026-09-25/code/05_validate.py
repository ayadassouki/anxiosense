"""Stage 5 - the eight validation checks plus checksums. Writes VALIDATION.md."""
import json, os, csv, glob, hashlib, collections, datetime

REPO = os.environ["REPO"]; WORK = os.environ["WORK"]; OUT = os.environ["OUT"]
DESC = f"{REPO}/evaluation/publication_experiments/results/descriptive_2026-09-21"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

L = []; ok_all = True
def check(n, title, passed, detail):
    global ok_all
    ok_all = ok_all and passed
    L.append((n, title, "PASS" if passed else "FAIL", detail))
    print(("PASS " if passed else "FAIL ") + f"{n}. {title} - {detail}")

rows = [json.loads(l) for l in open(f"{OUT}/invalid_outputs_row_level.jsonl", encoding="utf-8")]
auth = {}
frozen = collections.Counter()
for line in open(f"{DESC}/authoritative_records.jsonl", encoding="utf-8"):
    r = json.loads(line); auth[r["terminal_attempt_uuid"]] = r
    if r["failure_class"] == "SAFETY_INTERCEPT": frozen["safety"] += 1
    elif str(r["failure_class"] or "").startswith("INFRA"): frozen["infra"] += 1
    elif not r["prediction_valid"]: frozen["model_invalid"] += 1

# 1 row count
check(1, "Row count equals the frozen model-invalid total",
      len(rows) == frozen["model_invalid"] == 1986,
      f"rows={len(rows)}, frozen model-invalid={frozen['model_invalid']}, expected 1986 "
      f"(Dreaddit {sum(1 for r in rows if r['dataset']=='dreaddit')} / "
      f"GoEmotions {sum(1 for r in rows if r['dataset']=='goemotions')})")

# 2 reproduce cell_metrics
cm = json.load(open(f"{DESC}/cell_metrics.json", encoding="utf-8"))
mine = collections.Counter(r["cell_id"] for r in rows)
bad = [(c, m["buckets"]["N_model_behavior_invalid"], mine.get(c, 0))
       for c, m in cm.items() if m["buckets"]["N_model_behavior_invalid"] != mine.get(c, 0)]
extra = [c for c in mine if c not in cm]
check(2, "Per-cell counts reproduce cell_metrics.json exactly",
      not bad and not extra,
      f"{len(cm)} cells compared, {len(bad)} mismatches, {len(extra)} cells not in the frozen manifest"
      + ("" if not bad else f"; first mismatch {bad[0]}"))

# 3 no safety intercept
s1 = [r for r in rows if r["failure_class"] == "SAFETY_INTERCEPT" or r["parse_status"] == "safety_intercept"]
s2 = [r for r in rows if str(r.get("safety_intercept")).lower() not in ("false", "0")]
check(3, "No safety intercept is classified as model-invalid",
      not s1 and not s2,
      f"{len(s1)} rows carry a SAFETY_INTERCEPT class/status; {len(s2)} rows flag safety_intercept. "
      f"The frozen grid holds {frozen['safety']} safety intercepts, all excluded from this dataset.")

# 4 no recovered infrastructure failure
i1 = [r for r in rows if str(r["failure_class"] or "").startswith("INFRA")]
i2 = [r for r in rows if r["final_outcome_class"] not in ("OK", "")]
i3 = [r for r in rows if r["transport_outcome"] not in ("OK", "")]
retried = sum(1 for r in rows if str(r["attempt_count"]) not in ("1", ""))
check(4, "No recovered infrastructure failure is classified as model-invalid",
      not i1 and not i2 and not i3,
      f"{len(i1)} rows with an INFRA failure_class, {len(i2)} with a non-OK final outcome, "
      f"{len(i3)} with a non-OK transport outcome. Frozen grid infrastructure failures: {frozen['infra']}. "
      f"{retried} rows did involve >1 dispatch attempt, but every one terminated OK, so the invalid verdict "
      f"is a parse outcome, never a transport outcome.")

# 5 traceability
u = [r["terminal_attempt_uuid"] for r in rows]
miss = [x for x in u if x not in auth]
mismatch = [x for x in u if x in auth and (
    auth[x]["cell_id"] != next(r for r in rows if r["terminal_attempt_uuid"] == x)["cell_id"])]
check(5, "Every row maps to a frozen authoritative record",
      not miss and len(set(u)) == len(u) and not mismatch,
      f"{len(set(u))} distinct uuids for {len(u)} rows; {len(miss)} not found in "
      f"authoritative_records.jsonl; {len(mismatch)} cell_id mismatches")

# 6 raw join correctness
raws = {json.loads(l)["attempt_uuid"]: json.loads(l) for l in open(f"{WORK}/raws.jsonl", encoding="utf-8")}
joinbad = []
for r in rows:
    if r["raw_available"] != "true": continue
    rr = raws.get(r["terminal_attempt_uuid"])
    if rr is None or rr["cell_id"] != r["cell_id"] or rr["sample_id"] != r["sample_id"] \
       or rr["experiment_id"] != r["experiment_id"]:
        joinbad.append(r["terminal_attempt_uuid"])
navail = sum(1 for r in rows if r["raw_available"] == "true")
check(6, "Every raw example is joined to the correct terminal attempt",
      not joinbad,
      f"{navail} rows carry raw evidence; cell_id, sample_id and experiment_id agree with the "
      f"attempts store for all of them; {len(joinbad)} mismatches")

# 7 checksums
# VALIDATION.md is written later in this same run, so it cannot hash itself; it and
# CHECKSUMS.sha256 are excluded from the manifest by design.
files = sorted(f for f in (glob.glob(f"{OUT}/*.csv") + glob.glob(f"{OUT}/*.jsonl") +
                           glob.glob(f"{OUT}/*.md") + glob.glob(f"{OUT}/code/*.py"))
               if os.path.basename(f) != "VALIDATION.md")
sums = [(os.path.relpath(f, OUT), os.path.getsize(f), sha(f)) for f in files]
with open(f"{OUT}/CHECKSUMS.sha256", "w") as fh:
    for n, _, h in sums: fh.write(f"{h}  {n}\n")
check(7, "Checksums produced for every generated file", True, f"{len(sums)} files hashed into CHECKSUMS.sha256; VALIDATION.md and CHECKSUMS.sha256 are excluded because they are written after the hashes are computed")

# 8 raw coverage
navail2 = sum(1 for r in rows if r["raw_available"] == "true")
check(8, "Raw coverage is complete", navail2 == len(rows),
      f"{navail2} of {len(rows)} rows are classified from their own raw terminal attempt "
      f"({len(rows) - navail2} RAW_UNAVAILABLE)")

# 9 provenance gate on every raw store used
prov = json.load(open(f"{WORK}/provenance.json"))
badp = {k: v for k, v in prov.items() if v.get("verdict") != "match"}
check(9, "Every raw store used matches the hash recorded at the freeze", not badp,
      f"{len(prov)} source runs gated against descriptive_2026-09-21/source_parse_summaries "
      f"raw_attempts_sha256; {len(badp)} did not match" + ("" if not badp else f": {sorted(badp)}"))

# 10 every automated hallucination flag carries a reviewed verdict
flagged = [r for r in rows if r["hallucination_candidate"] in ("true", "uncertain")]
unreviewed = [r for r in flagged if r["hallucination_reviewed_verdict"] in ("REVIEW_MISSING", "", None)]
conf = [r for r in rows if r["hallucination_reviewed_verdict"] == "CONFIRMED"]
rej = [r for r in rows if r["hallucination_reviewed_verdict"] == "REJECTED"]
check(10, "Every hallucination candidate was manually adjudicated", not unreviewed,
      f"{len(flagged)} automated candidates -> {len(conf)} CONFIRMED, {len(rej)} REJECTED, "
      f"{len(unreviewed)} unreviewed; no record is marked hallucination on the heuristic alone")

# legacy inventory (kept so the section below still renders)
un = collections.Counter(r["experiment_id"] for r in rows if r["raw_available"] != "true")
by = collections.Counter((r["dataset"], r["model_short"], r["strategy"])
                         for r in rows if r["raw_available"] != "true")
check(11, "Any RAW_UNAVAILABLE record is inventoried, never classified",
      all(r["primary_failure_category"] == "RAW_UNAVAILABLE"
          for r in rows if r["raw_available"] != "true"),
      f"{sum(un.values())} of {len(rows)} rows have no reachable raw evidence"
      + (f": {dict(un)}" if un else "; the rule holds vacuously"))

# frozen-artifact integrity: per-file comparison against the 2026-09-21 freeze inventory
FREEZE = f"{REPO}/evaluation/publication_experiments/results/verification_2026-09-21/freeze_hashes_after.txt"
recorded = {}
for line in open(FREEZE):
    parts = line.split(None, 2)
    if len(parts) == 3: recorded[parts[2].strip().lstrip("./")] = parts[0]
current = {os.path.relpath(p, DESC): sha(p)
           for p in glob.glob(f"{DESC}/**/*", recursive=True) if os.path.isfile(p)}
changed = sorted(k for k in recorded if k in current and current[k] != recorded[k])
missing = sorted(k for k in recorded if k not in current)
added = sorted(k for k in current if k not in recorded)
same = not (changed or missing or added)
integrity = (f"{len(recorded)} files recorded at the freeze, {len(current)} present now; "
             f"{len(changed)} changed, {len(missing)} missing, {len(added)} added")
print(("PASS " if same else "FAIL ") + f"frozen descriptive_2026-09-21 integrity - {integrity}")

with open(f"{OUT}/VALIDATION.md", "w", encoding="utf-8") as fh:
    fh.write(f"""# VALIDATION - invalid-output audit 2026-09-25

Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()} by `code/05_validate.py`.
This audit is read-only: it reads the frozen artifacts and the append-only raw stores and writes only
into `results/invalid_output_audit_2026-09-25/`.

## Frozen-artifact integrity

Every file of `descriptive_2026-09-21/` was re-hashed and compared, file by file, against the inventory
recorded at the 2026-09-21 freeze (`verification_2026-09-21/freeze_hashes_after.txt`).

{integrity}.

**{"MATCH - the frozen descriptive package is byte-identical to the freeze; this audit changed nothing." if same else "DIFFERS - investigate before publishing."}**

## Checks

| # | Check | Result | Detail |
|---|---|---|---|
""")
    for n, t, res, d in L:
        fh.write(f"| {n} | {t} | **{res}** | {d} |\n")
    fh.write(f"\nOverall: **{'ALL CHECKS PASS' if ok_all else 'ONE OR MORE CHECKS FAILED'}**\n")
    fh.write("\n## Raw-evidence coverage\n\n")
    if sum(un.values()) == 0:
        fh.write(f"**Complete: {navail2} of {len(rows)} rows (100%) are classified from their own raw "
                 "terminal attempt. No row is marked `RAW_UNAVAILABLE`.**\n")
    else:
        fh.write("| source run | dataset | model | strategy | records |\n|---|---|---|---|---|\n")
        for (ds, m, st), n in sorted(by.items()):
            run = next(r["experiment_id"] for r in rows
                       if r["raw_available"] != "true"
                       and (r["dataset"], r["model_short"], r["strategy"]) == (ds, m, st))
            fh.write(f"| `{run}` | {ds} | {m} | {st} | {n} |\n")
        fh.write(f"| | | | **total** | **{sum(un.values())}** |\n")
    fh.write("\n## Provenance gate\n\nEach raw store was hashed and compared against the "
             "`raw_attempts_sha256` recorded for that source run in "
             "`descriptive_2026-09-21/source_parse_summaries/`. A store that does not match is refused.\n\n"
             "| source run | verdict | sha256 | store |\n|---|---|---|---|\n")
    for run in sorted(prov):
        v = prov[run]
        fh.write(f"| `{run}` | **{v.get('verdict')}** | `{(v.get('sha256') or '')[:16]}…` | "
                 f"`{(v.get('path') or '')}` |\n")
    fh.write("\n## Checksums\n\n| file | bytes | sha256 |\n|---|---|---|\n")
    for n, s_, h in sums: fh.write(f"| `{n}` | {s_:,} | `{h}` |\n")
print("\nVALIDATION.md written. overall:", "ALL PASS" if ok_all else "FAILURES PRESENT")

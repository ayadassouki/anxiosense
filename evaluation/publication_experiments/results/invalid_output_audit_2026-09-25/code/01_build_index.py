"""Stage 1 - build the invalid-record index.

READ-ONLY with respect to every frozen artifact. Reads:
  results/descriptive_2026-09-21/authoritative_records.jsonl   (which records are model-invalid)
  results/descriptive_2026-09-21/parsed/*.jsonl                (attempt_count, http, latency, quality_flags)
Writes only into the scratch directory passed as WORK.
"""
import json, os, sys, glob, collections

REPO = os.environ["REPO"]
DESC = f"{REPO}/evaluation/publication_experiments/results/descriptive_2026-09-21"
WORK = os.environ["WORK"]
os.makedirs(WORK, exist_ok=True)

# 1. frozen authoritative records: model-invalid only
inv = {}
counts = collections.Counter()
for line in open(f"{DESC}/authoritative_records.jsonl", encoding="utf-8"):
    r = json.loads(line)
    counts["total"] += 1
    if r["failure_class"] == "SAFETY_INTERCEPT":
        counts["safety"] += 1; continue
    counts["attributable"] += 1
    if str(r["failure_class"] or "").startswith("INFRA"):
        counts["infra"] += 1; continue
    if r["prediction_valid"]:
        counts["valid"] += 1; continue
    assert r["failure_class"] == "MODEL_BEHAVIOUR", r
    assert r["include_in_metrics"] is False, r
    counts["model_invalid"] += 1
    inv[r["terminal_attempt_uuid"]] = r

# 2. parsed records add the operational fields (no raw text lives here)
enrich = {}
for f in glob.glob(f"{DESC}/parsed/*.jsonl"):
    for line in open(f, encoding="utf-8"):
        p = json.loads(line)
        u = p.get("terminal_attempt_uuid")
        if u in inv:
            enrich[u] = p

missing = [u for u in inv if u not in enrich]
byrun = collections.defaultdict(list)
for u, r in inv.items():
    byrun[r["source_run"]].append(u)
for run, us in byrun.items():
    with open(f"{WORK}/uuids_{run}.txt", "w") as fh:
        fh.write("\n".join(sorted(us)) + "\n")

with open(f"{WORK}/index.jsonl", "w", encoding="utf-8") as fh:
    for u, r in inv.items():
        fh.write(json.dumps({"auth": r, "parsed": enrich.get(u)}, ensure_ascii=False) + "\n")

print("frozen grid buckets:", dict(counts))
print("model-invalid records indexed:", len(inv))
print("parsed records joined     :", len(enrich))
print("parsed records MISSING    :", len(missing))
for run in sorted(byrun):
    print("  %-44s %5d" % (run, len(byrun[run])))

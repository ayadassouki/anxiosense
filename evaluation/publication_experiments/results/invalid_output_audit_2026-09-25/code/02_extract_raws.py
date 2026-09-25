"""Stage 2 - pull the terminal raw attempt for every indexed invalid record.

Reads (read-only): <root>/<experiment_id>/raw/attempts.jsonl for each root in RUN_ROOTS
(colon-separated; the in-repo `runs/` directory first, then any external evidence roots).

PROVENANCE GATE. Before a raw store is used, its SHA-256 is compared against the
`raw_attempts_sha256` recorded for that source run in
`descriptive_2026-09-21/source_parse_summaries/<run>.json`. A store that does not match
the hash the frozen results were derived from is REFUSED, not used with a warning.
This is what makes it safe to read an external copy of the evidence.

Writes: WORK/raws.jsonl and WORK/provenance.json. Runs with no reachable store are
reported, never guessed.
"""
import json, os, glob, hashlib

REPO = os.environ["REPO"]; WORK = os.environ["WORK"]
DESC = f"{REPO}/evaluation/publication_experiments/results/descriptive_2026-09-21"
ROOTS = [r for r in os.environ.get(
    "RUN_ROOTS", f"{REPO}/evaluation/publication_experiments/runs").split(":") if r]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

wanted = {}
for f in glob.glob(f"{WORK}/uuids_*.txt"):
    run = os.path.basename(f)[len("uuids_"):-len(".txt")]
    wanted[run] = set(x.strip() for x in open(f) if x.strip())

prov = {}
def locate(run):
    """Return the path of a raw store whose hash matches the frozen record, or None."""
    summ = f"{DESC}/source_parse_summaries/{run}.json"
    expect = json.load(open(summ))["raw_attempts_sha256"] if os.path.exists(summ) else None
    for root in ROOTS:
        p = f"{root}/{run}/raw/attempts.jsonl"
        if not os.path.exists(p): continue
        h = sha(p)
        if expect is None:
            prov[run] = {"path": p, "sha256": h, "expected": None, "verdict": "no_recorded_hash"}
            return None
        if h == expect:
            prov[run] = {"path": p, "sha256": h, "expected": expect, "verdict": "match"}
            return p
        prov[run] = {"path": p, "sha256": h, "expected": expect, "verdict": "MISMATCH_REFUSED"}
    return None

out = open(f"{WORK}/raws.jsonl", "w", encoding="utf-8")
avail, unavail = {}, {}
for run, uset in sorted(wanted.items()):
    p = locate(run)
    if p is None:
        unavail[run] = len(uset)
        prov.setdefault(run, {"path": None, "verdict": "not_found"})
        continue
    found = 0
    for line in open(p, encoding="utf-8"):
        if '"attempt_uuid": "' not in line: continue
        u = line.split('"attempt_uuid": "', 1)[1].split('"', 1)[0]
        if u not in uset: continue
        a = json.loads(line)
        raw = a.get("raw") or {}
        out.write(json.dumps({
            "attempt_uuid": u, "experiment_id": a.get("experiment_id"), "cell_id": a.get("cell_id"),
            "sample_id": a.get("sample_id"), "attempt_number": a.get("attempt_number"),
            "input_text": a.get("input_text"),
            "referral_agent_raw": raw.get("referral_agent_raw"),
            "emotion_agent_raw": raw.get("emotion_agent_raw"),
            "referral_level_reported": raw.get("referral_level_reported"),
            "referral_unreadable": raw.get("referral_unreadable"),
            "http_status": a.get("http_status"), "outcome_class": a.get("outcome_class"),
            "outcome_detail": a.get("outcome_detail"), "transport_error_kind": a.get("transport_error_kind"),
            "latency_ms": a.get("latency_ms"), "server_latency_ms": a.get("server_latency_ms"),
            "token_usage": a.get("token_usage"), "quality_flags": a.get("quality_flags"),
            "safety_override": a.get("safety_override"), "upstream_provider": a.get("upstream_provider"),
            "timestamp_utc": a.get("timestamp_utc"), "response_body_sha256": a.get("response_body_sha256"),
            "raw_store_path": p,
        }, ensure_ascii=False) + "\n")
        found += 1
    avail[run] = (found, len(uset))
out.close()
json.dump(prov, open(f"{WORK}/provenance.json", "w"), indent=1, sort_keys=True)

print("roots searched:")
for r in ROOTS: print("   ", r)
print("\nPROVENANCE GATE (sha256 of attempts.jsonl vs descriptive_2026-09-21 record):")
for run in sorted(prov):
    v = prov[run]
    print("  %-44s %-18s %s" % (run, v["verdict"], (v.get("sha256") or "")[:16]))
print("\nRAW EXTRACTION:")
for r, (f_, w) in sorted(avail.items()):
    print("  %-44s matched %5d / wanted %5d  %s" % (r, f_, w, "OK" if f_ == w else "!! INCOMPLETE"))
for r, n in sorted(unavail.items()):
    print("  %-44s %5d records -> RAW_UNAVAILABLE" % (r, n))
print("\ntotal raws extracted:", sum(v[0] for v in avail.values()))
print("total RAW_UNAVAILABLE:", sum(unavail.values()))

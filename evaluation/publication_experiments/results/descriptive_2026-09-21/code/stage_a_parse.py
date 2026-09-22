"""Stage A: parse every FINAL terminal attempt of one source run with the repo's own
parse(). Read-only on the run directory; writes only to the results directory."""
import json, os, re, sys, collections, hashlib
A = os.path.expanduser("~/mnt/anxiosense")
sys.path.insert(0, os.path.join(A, "evaluation/publication_experiments"))
from runner.parse import parse, PARSER_VERSION
from runner.failures import Transport

run_dir, name, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

idx_p = os.path.join(run_dir, "raw/index.jsonl"); att_p = os.path.join(run_dir, "raw/attempts.jsonl")
final = {}; n_idx = 0
for line in open(idx_p, encoding="utf-8"):
    line = line.strip()
    if not line: continue
    r = json.loads(line); n_idx += 1
    final[(r["cell_id"], r["sample_id"])] = r
term = {r["terminal_attempt_uuid"]: k for k, r in final.items() if r.get("terminal_attempt_uuid")}

UU = re.compile(r'"attempt_uuid": "([0-9a-fA-F-]{36})"')
out_p = os.path.join(out_dir, "parsed", name + ".jsonl")
found = set(); status = collections.Counter(); n_att = 0
with open(out_p, "w", encoding="utf-8") as out:
    for line in open(att_p, encoding="utf-8"):
        if not line.strip(): continue
        n_att += 1
        m = UU.search(line)
        if not m or m.group(1) not in term: continue
        a = json.loads(line); u = a["attempt_uuid"]; found.add(u)
        k = term[u]; ix = final[k]
        tr = Transport(a["outcome_class"])
        p = parse(a["dataset"], a.get("response_body"), tr, a.get("outcome_detail")).to_dict()
        ds, model, strat, runl = a["cell_id"].split("|")
        rec = {
            "source_run": name, "experiment_id": a["experiment_id"], "cell_id": a["cell_id"],
            "dataset": ds, "model": model, "strategy": strat, "run": a["run"],
            "sample_id": a["sample_id"], "assessment_uuid": ix["assessment_uuid"],
            "terminal_attempt_uuid": u, "attempt_count": ix.get("attempt_count"),
            "final_outcome_class": ix["final_outcome_class"], "transport_outcome": a["outcome_class"],
            "supersedes_outcome": ix.get("supersedes_outcome"),
            "ground_truth": a["ground_truth"], "text_sha256": a["text_sha256"],
            "dataset_manifest_sha256": a["dataset_manifest_sha256"],
            "model_requested": a["model_requested"], "model_actual": a.get("model_actual"),
            "pin_provider": a.get("pin_provider"), "upstream_provider": a.get("upstream_provider"),
            "upstream_providers_all": a.get("upstream_providers_all"),
            "model_mismatch": a.get("model_mismatch"), "provider_mismatch": a.get("provider_mismatch"),
            "safety_override": a.get("safety_override"),
            "prompt_set_sha256": a.get("prompt_set_sha256"),
            "config_sha256": a.get("config_sha256"), "git_commit": a.get("git_commit"),
            "runner_version": a.get("runner_version"), "http_status": a.get("http_status"),
            "latency_ms": a.get("latency_ms"),
            **p,
        }
        out.write(json.dumps(rec, sort_keys=True) + "\n")
        status[p["parse_status"]] += 1

summary = {
    "source_run": name, "run_dir": run_dir, "parser_version": PARSER_VERSION,
    "index_lines": n_idx, "final_assessments": len(final), "attempt_lines": n_att,
    "terminal_attempts_resolved": len(found), "terminal_attempts_missing": len(set(term) - found),
    "parse_status_counts": dict(status),
    "raw_index_sha256": fsha(idx_p), "raw_attempts_sha256": fsha(att_p),
    "experiment_json_sha256": fsha(os.path.join(run_dir, "experiment.json")),
    "parsed_output_sha256": fsha(out_p),
}
json.dump(summary, open(os.path.join(out_dir, "source_parse_summaries", name + ".json"), "w"), indent=2)
print(json.dumps({k: summary[k] for k in ("source_run","final_assessments","terminal_attempts_resolved",
      "terminal_attempts_missing","parse_status_counts")}))

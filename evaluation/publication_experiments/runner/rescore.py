"""Re-parse and re-score a completed experiment from stored raw attempts ONLY.

No network. No provider. No model call. Reads raw/attempts.jsonl + raw/index.jsonl
and rewrites parsed/records.jsonl. Safe to run any number of times; the raw store
is opened read-only.
"""
from __future__ import annotations
import datetime as _dt, json
from pathlib import Path

from .failures import Transport
from .parse import parse, PARSER_VERSION
from .store import AppendOnlyJSONL


def rescore(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    attempts_path = run_dir / "raw" / "attempts.jsonl"
    index_path = run_dir / "raw" / "index.jsonl"
    if not attempts_path.exists():
        raise FileNotFoundError(attempts_path)

    attempts: dict[str, dict] = {}
    for a in AppendOnlyJSONL(attempts_path).read():
        attempts[a["attempt_uuid"]] = a

    out_path = run_dir / "parsed" / "records.jsonl"
    if out_path.exists():
        out_path.unlink()          # derived artefact: safe to regenerate
    out = AppendOnlyJSONL(out_path)

    n = 0
    counts: dict[str, int] = {}
    for idx in AppendOnlyJSONL(index_path).read():
        terminal = attempts.get(idx.get("terminal_attempt_uuid", ""))
        if terminal is None:
            continue
        transport = Transport(terminal["outcome_class"])
        body = terminal.get("response_body")
        parsed = parse(terminal["dataset"], body, transport, terminal.get("outcome_detail"))
        rec = {
            "record_type": "parsed",
            "assessment_uuid": idx["assessment_uuid"],
            "terminal_attempt_uuid": terminal["attempt_uuid"],
            "experiment_id": terminal["experiment_id"],
            "cell_id": terminal["cell_id"],
            "dataset": terminal["dataset"],
            "sample_id": terminal["sample_id"],
            "ground_truth": terminal["ground_truth"],
            "model_requested": terminal["model_requested"],
            "model_actual": terminal.get("model_actual"),
            "upstream_provider": terminal.get("upstream_provider"),
            "strategy": terminal["strategy"],
            "run": terminal["run"],
            "attempt_count": idx.get("attempt_count"),
            "transport_outcome": terminal["outcome_class"],
            **parsed.to_dict(),
            "rescored_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }
        out.append(rec)
        counts[parsed.parse_status] = counts.get(parsed.parse_status, 0) + 1
        n += 1
    out.close()

    summary = {"records": n, "parser_version": PARSER_VERSION,
               "parse_status_counts": counts, "output": str(out_path)}
    (run_dir / "summaries").mkdir(exist_ok=True)
    (run_dir / "summaries" / "rescore.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary

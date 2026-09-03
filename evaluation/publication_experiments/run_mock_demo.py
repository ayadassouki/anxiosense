#!/usr/bin/env python3
"""End-to-end demonstration with ZERO model calls.

Exercises: config -> preflight -> manifest -> dispatch -> raw store -> retry ->
resume -> rescore -> metrics, using the deterministic mock transport.

    python3 evaluation/publication_experiments/run_mock_demo.py
"""
from __future__ import annotations
import dataclasses, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from runner._reuse import REPO_ROOT
from runner.config import load_config
from runner.manifest import load_manifest
from runner.metrics import cell_metrics, MetricPolicy
from runner.mock import MockTransport
from runner.rescore import rescore
from runner.run import run_experiment

CFG = HERE / "configs" / "mock_demo.yaml"
LIMIT = 6


def main() -> int:
    cfg = load_config(CFG)
    # Write into a temp directory: the demo is disposable and must never leave
    # artefacts in the repository or need a delete (the sandbox forbids deletes).
    tmp = tempfile.mkdtemp(prefix="anxiosense_mock_demo_")
    cfg = dataclasses.replace(cfg, output_root=tmp)
    print(f"demo output: {tmp}\n")

    man = load_manifest(REPO_ROOT / cfg.datasets[0].manifest)
    ids = man["included_sample_ids"][:LIMIT]
    # one deliberate example of every outcome the runner must distinguish
    scripts = {
        ids[0]: ["valid_prediction"],
        ids[1]: ["referral_unreadable"],                       # model behaviour -> invalid
        ids[2]: ["http_429", "valid_prediction"],              # transient -> retried -> ok
        ids[3]: ["timeout", "timeout", "timeout"],             # retries exhausted
        ids[4]: ["malformed_complete"],                        # complete but unreadable
        ids[5]: ["http_400"],                                  # terminal infrastructure
    }
    out = run_experiment(cfg, transport=MockTransport(scripts), limit=LIMIT, sleep=lambda s: None)
    print("dispatch stats:", json.dumps(out["stats"], indent=2))

    print("\nresume (nothing should be re-dispatched):")
    t2 = MockTransport({})
    out2 = run_experiment(cfg, transport=t2, resume=True, limit=LIMIT, sleep=lambda s: None)
    print(f"  dispatched={out2['stats']['dispatched']}  "
          f"skipped={out2['stats']['skipped_resume']}  model_calls={len(t2.calls)}")

    print("\nrescore from raw (no network):", json.dumps(rescore(out["run_dir"]), indent=2))

    recs = [json.loads(l) for l in
            (Path(out["run_dir"]) / "parsed" / "records.jsonl").read_text().splitlines()]
    m = cell_metrics(recs, labels=[0, 1], majority_baseline=man["majority_baseline"],
                     policy=MetricPolicy())
    print("\nmetrics:", json.dumps({"buckets": m["buckets"], "rates": m["rates"],
                                    "metrics": m["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

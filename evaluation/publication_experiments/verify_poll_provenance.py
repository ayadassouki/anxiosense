#!/usr/bin/env python3
"""Live-server verification of the polling-provenance guard. ZERO model calls.

Probes GET /api/health and runs preflight against throwaway configs built in a
temp directory. Preflight never dispatches and never writes to a run directory,
so this is safe to run against a live server at any time.

    python3 evaluation/publication_experiments/verify_poll_provenance.py --expect 3000
    python3 evaluation/publication_experiments/verify_poll_provenance.py --expect 250

Nothing under configs/, manifests/ or runs/ is created or modified.
"""
from __future__ import annotations

import argparse, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from runner.client import probe_server_runtime                       # noqa: E402
from runner.config import load_config, ConfigError                   # noqa: E402
from runner.run import preflight, PreflightError, resolve_server_runtime  # noqa: E402
from runner._reuse import REPO_ROOT                                  # noqa: E402

BASE = "http://localhost:3001"
MANIFEST = "evaluation/publication_experiments/manifests/official_dreaddit_test.json"
results: list[tuple[str, bool, str]] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name:<58} {detail}")


def temp_config(tmp: Path, declared: int | None, eid: str) -> Path:
    import yaml
    server = {"base_url": BASE, "evaluate_endpoint": "/api/workflow/evaluate",
              "timeout_seconds": 180, "server_poll_budget_seconds": 150,
              "request_delay_seconds": 0.5}
    if declared is not None:
        server["mastra_poll_interval_ms"] = declared
    cfg = {
        "experiment_id": eid,
        "output_root": str(tmp / "runs"),            # never written: preflight only
        "models": [{"id": "qwen/qwen3.5-27b", "name": "Qwen 3.5 27B",
                    "provider": "openrouter", "pin_provider": "Alibaba", "enabled": True}],
        "strategies": ["zero-shot"],
        "datasets": [{"name": "dreaddit", "manifest": MANIFEST}],
        "runs": 1, "run_start": 1,
        "retry": {"max_attempts": 3, "backoff_base_ms": 2000, "backoff_factor": 2,
                  "backoff_cap_ms": 30000},
        "server": server,
    }
    p = tmp / f"{eid}.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", type=int, required=True,
                    help="the poll interval the server is expected to be running")
    args = ap.parse_args()
    expect = args.expect
    other = 250 if expect != 250 else 3000

    print("=" * 78)
    print(f"POLL-PROVENANCE LIVE VERIFICATION   expecting server at {expect} ms")
    print("=" * 78)

    # ── health ──────────────────────────────────────────────────────────────
    try:
        h = probe_server_runtime(BASE)
    except Exception as exc:                                          # noqa: BLE001
        print(f"\nFATAL: could not reach {BASE}/api/health -> {exc}")
        print("Is Express running, and was it restarted after the server change?")
        return 2

    print(f"\n-- GET {BASE}/api/health")
    print(json.dumps(h, indent=2))
    ck("health exposes mastra_poll_interval_ms", "mastra_poll_interval_ms" in h,
       "field absent -> Express was NOT restarted with the new code"
       if "mastra_poll_interval_ms" not in h else "")
    ck(f"effective interval == {expect}", h.get("mastra_poll_interval_ms") == expect,
       f"reported {h.get('mastra_poll_interval_ms')!r}")
    ck("source is 'default' at 3000 / 'env' otherwise",
       h.get("mastra_poll_interval_source") == ("default" if expect == 3000 else "env"),
       f"reported {h.get('mastra_poll_interval_source')!r}")
    ck("mastra_poll_max_ms reported", isinstance(h.get("mastra_poll_max_ms"), (int, float)),
       str(h.get("mastra_poll_max_ms")))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # ── matching declaration must PASS ──────────────────────────────────
        cfg = load_config(temp_config(tmp, expect, f"verify_match_{expect}"))
        try:
            f = preflight(cfg)
            rt = f["server_runtime"]
            ck(f"preflight with declared {expect} SUCCEEDS",
               rt["effective_mastra_poll_interval_ms"] == expect and rt["verified"] is True,
               f"recorded={rt['effective_mastra_poll_interval_ms']} verified={rt['verified']} "
               f"source={rt['source']}")
        except PreflightError as exc:
            ck(f"preflight with declared {expect} SUCCEEDS", False, str(exc)[:160])

        # ── mismatching declaration must ABORT ──────────────────────────────
        cfg = load_config(temp_config(tmp, other, f"verify_mismatch_{other}"))
        try:
            preflight(cfg)
            ck(f"preflight with declared {other} ABORTS", False,
               "it did NOT abort - the guard is not working")
        except PreflightError as exc:
            m = str(exc)
            ck(f"preflight with declared {other} ABORTS",
               str(other) in m and str(expect) in m,
               m.split("\n")[0][:150])

        # ── undeclared config must not abort ────────────────────────────────
        cfg = load_config(temp_config(tmp, None, "verify_undeclared"))
        try:
            rt = preflight(cfg)["server_runtime"]
            ck("undeclared config records without aborting",
               rt["effective_mastra_poll_interval_ms"] == expect and rt["verified"] is False,
               f"recorded={rt['effective_mastra_poll_interval_ms']} verified={rt['verified']}")
        except PreflightError as exc:
            ck("undeclared config records without aborting", False, str(exc)[:150])

        # ── a bad declaration is a config error, not a runtime surprise ─────
        try:
            load_config(temp_config(tmp, 0, "verify_zero"))
            ck("declared 0 is rejected by load_config", False, "accepted")
        except ConfigError as exc:
            ck("declared 0 is rejected by load_config", True, str(exc)[:80])

    failed = [n for n, ok, _ in results if not ok]
    print("\n" + "=" * 78)
    print(f"{len(results) - len(failed)}/{len(results)} checks passed"
          + (f"\nFAILURES: {failed}" if failed else "\nPOLL PROVENANCE VERIFIED"))
    print("ZERO model calls were made: preflight only.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
scripts/inspect_server.py

Send a single test request to the AnxioSense server and report:
    - Whether the server is reachable
    - Which endpoint path is active
    - The shape of the response
    - Which fields are present in report and metadata

No dataset required — uses a hardcoded short test text.
Useful for verifying the server is running before a long experiment run.

Usage
-----
    python evaluation/llm-experiments/scripts/inspect_server.py
    python evaluation/llm-experiments/scripts/inspect_server.py --base-url http://localhost:3001
    python evaluation/llm-experiments/scripts/inspect_server.py --base-url https://your-railway-url.up.railway.app
"""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.anxiosense_client import call_anxiosense, AnxioSenseResult

# Hardcoded test text — short enough to complete quickly, long enough for the
# pipeline to find something meaningful.
TEST_TEXT = (
    "I've been feeling really anxious lately. "
    "My mind keeps racing with worries about work and I can't seem to relax."
)

TEST_MODEL    = "groq/llama-3.3-70b-versatile"
TEST_STRATEGY = "one-shot-cot"


def _indent(d: dict, level: int = 2) -> str:
    return json.dumps(d, indent=level, ensure_ascii=False, default=str)


def inspect(base_url: str, timeout: int) -> None:
    print("=" * 60)
    print("AnxioSense Server Inspection")
    print("=" * 60)
    print(f"Base URL : {base_url}")
    print(f"Endpoint : /api/workflow/evaluate")
    print(f"Timeout  : {timeout}s")
    print()
    print("Test text:")
    print(f"  {TEST_TEXT[:80]}...")
    print()

    print("Sending request...")
    result: AnxioSenseResult = call_anxiosense(
        text=TEST_TEXT,
        model=TEST_MODEL,
        strategy=TEST_STRATEGY,
        base_url=base_url,
        timeout=timeout,
    )

    print(f"HTTP status   : {result.status}")
    print(f"Latency       : {result.latency_ms:.0f} ms")

    if result.error:
        print()
        print("ERROR:", result.error)
        print()
        print("Possible causes:")
        print("  1. AnxioSense Express server is not running.")
        print("     Start it with: cd /path/to/anxiosense/server && npm run dev")
        print("  2. Mastra dev server is not running on port 4111.")
        print("     Start it with: cd /path/to/anxiosense && npm run dev")
        print("  3. Wrong base URL. Try: --base-url http://localhost:3001")
        print("  4. Server is starting up — wait a few seconds and try again.")
        sys.exit(1)

    print()
    print("Server reachable — response shape:")
    print()

    rd = result.report_dict or {}

    # Report block
    report = rd.get("report", {})
    print("report block:")
    print(f"  finalReport      : {len(str(report.get('finalReport','')))} chars")
    print(f"  concernPattern   : {report.get('concernPattern', '(missing)')!r}")
    print(f"  referralLevel    : {report.get('referralLevel', '(missing)')!r}")
    print(f"  summary          : {str(report.get('summary',''))[:80]!r}")

    # Metadata block
    meta = rd.get("metadata", {})
    print()
    print("metadata block:")
    print(f"  model_used       : {meta.get('model_used', '(missing)')!r}")
    print(f"  strategy_used    : {meta.get('strategy_used', '(missing)')!r}")
    print(f"  latency_ms       : {meta.get('latency_ms', '(missing)')}")
    print(f"  token_usage      : {meta.get('token_usage', '(missing)')}")
    print(f"  safety_override  : {meta.get('safety_override', '(missing)')}")

    print()
    print("Final report (first 400 chars):")
    print("-" * 40)
    fr = report.get("finalReport", "(not present)")
    print(fr[:400])
    print("-" * 40)
    print()

    # Quick validation for experiment use
    missing = []
    if not report.get("referralLevel"):  missing.append("report.referralLevel")
    if not report.get("concernPattern"): missing.append("report.concernPattern")
    if not report.get("finalReport"):    missing.append("report.finalReport")

    if missing:
        print("WARNING: Some expected fields are missing:")
        for f in missing:
            print(f"  - {f}")
        print("Extract functions may return None for some examples.")
    else:
        print("All expected fields present.")
        print("The server is ready for evaluation experiments.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the AnxioSense server before running experiments")
    parser.add_argument("--base-url", default="http://localhost:3001", help="AnxioSense server base URL")
    parser.add_argument("--timeout",  type=int, default=90, help="Request timeout in seconds (default: 90)")
    args = parser.parse_args()

    inspect(args.base_url, args.timeout)


if __name__ == "__main__":
    main()

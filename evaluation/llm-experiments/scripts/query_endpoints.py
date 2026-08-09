#!/usr/bin/env python3
"""
query_endpoints.py — read-only OpenRouter provider/endpoint survey.

WHY THIS RUNS ON YOUR MACHINE
  openrouter.ai is unreachable from the Claude container and from the desktop
  workspace VM (both return "Tunnel connection failed: 403 Forbidden").
  This script needs plain outbound HTTPS, which your terminal has.

WHAT IT DOES
  Calls GET https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints
  for each candidate model and prints every upstream provider serving it.

  - PUBLIC endpoint. No API key is read, sent, printed, or logged.
  - NO inference calls. Zero cost.
  - Writes nothing into the repository. Prints to stdout only.
    (Pass --save PATH if you want a JSON record for your appendix.)

RUN
    cd ~/anxiosense/evaluation/llm-experiments
    python3 /path/to/query_endpoints.py

    # optional, writes outside the repo:
    python3 /path/to/query_endpoints.py --save /tmp/or_endpoints.json

READING THE OUTPUT
  For each model you want ONE upstream provider to pin. Choose in this order:
    1. Only one provider listed        -> pin it; allow_fallbacks:false is a no-op, safe.
    2. Several listed                  -> prefer the one with highest uptime, then
                                          the quantisation you can name in the write-up.
    3. Zero listed                     -> the model is not currently servable. Pick a
                                          different pinned id and re-run.
  A provider whose `quantization` is null/unknown is still usable, but you cannot
  document the numeric precision it ran at. Prefer a provider that names it.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# Selected models first, then the alternates named in the selection table.
CANDIDATES = [
    # --- proposed five ---
    ("meta-llama/llama-4-scout",        "Llama 4 Scout          [PROPOSED]"),
    ("mistralai/mistral-small-2603",    "Mistral Small 4        [PROPOSED]"),
    ("google/gemma-4-31b-it",           "Gemma 4 31B (paid)     [PROPOSED]"),
    ("deepseek/deepseek-v4-flash",      "DeepSeek V4 Flash 0423 [PROPOSED]"),
    ("microsoft/phi-4",                 "Phi-4                  [PROPOSED]"),
    # --- alternates under consideration ---
    ("google/gemma-4-31b-it:free",      "Gemma 4 31B (free tier)  [alt]"),
    ("deepseek/deepseek-v4-flash-0731", "DeepSeek V4 Flash 0731   [alt]"),
    ("deepseek/deepseek-v4-pro",        "DeepSeek V4 Pro          [alt]"),
    ("meta-llama/llama-4-maverick",     "Llama 4 Maverick         [alt]"),
    ("mistralai/mistral-medium-3-5",    "Mistral Medium 3.5       [alt]"),
    ("mistralai/mistral-large-2512",    "Mistral Large 3          [alt]"),
    ("google/gemma-4-26b-a4b-it",       "Gemma 4 26B A4B          [alt]"),
]

URL = "https://openrouter.ai/api/v1/models/{}/endpoints"


def fetch(model_id: str) -> dict | None:
    req = urllib.request.Request(
        URL.format(model_id),
        headers={"Accept": "application/json", "User-Agent": "anxiosense-endpoint-survey/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read())["data"]
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code} {e.reason}")
    except Exception as e:                                  # noqa: BLE001
        print(f"    ERROR {e}")
    return None


def num(v) -> str:
    return "—" if v is None else str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", metavar="PATH",
                    help="write the raw responses to PATH (choose a path OUTSIDE the repo)")
    args = ap.parse_args()

    record: dict[str, dict] = {}
    summary: list[tuple[str, str, list[str]]] = []

    for model_id, label in CANDIDATES:
        print("=" * 78)
        print(f"{label}\n  {model_id}")
        print("=" * 78)
        data = fetch(model_id)
        if data is None:
            summary.append((label, model_id, []))
            print()
            continue
        record[model_id] = data

        endpoints = data.get("endpoints") or []
        if not endpoints:
            print("  NO ENDPOINTS — not currently servable.\n")
            summary.append((label, model_id, []))
            continue

        hdr = (f"  {'provider':<22}{'quant':<12}{'ctx':>9}{'max_out':>9}"
               f"{'$in/M':>9}{'$out/M':>9}{'uptime':>9}")
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))
        names = []
        for e in endpoints:
            name = e.get("provider_name") or "?"
            names.append(name)
            pr = e.get("pricing") or {}
            try:
                pin = f"{float(pr.get('prompt', 0)) * 1e6:.3f}"
                pout = f"{float(pr.get('completion', 0)) * 1e6:.3f}"
            except (TypeError, ValueError):
                pin = pout = "?"
            st = e.get("uptime_last_30m")
            up = f"{st:.1f}%" if isinstance(st, (int, float)) else "—"
            print(f"  {name[:21]:<22}{str(e.get('quantization') or '—')[:11]:<12}"
                  f"{num(e.get('context_length')):>9}{num(e.get('max_completion_tokens')):>9}"
                  f"{pin:>9}{pout:>9}{up:>9}")
        # anything that would break omitting temperature / max_tokens?
        sp = {p for e in endpoints for p in (e.get("supported_parameters") or [])}
        missing = [p for p in ("temperature", "max_tokens", "seed") if p not in sp]
        if missing:
            print(f"\n  NOTE: not advertised by any endpoint: {missing}")
        print()
        summary.append((label, model_id, names))

    print("=" * 78)
    print("SUMMARY — one fixed upstream provider per model")
    print("=" * 78)
    for label, model_id, names in summary:
        if not names:
            verdict = "UNSERVABLE — choose a different pinned id"
        elif len(names) == 1:
            verdict = f"pin {names[0]}  (sole provider; allow_fallbacks:false is a no-op)"
        else:
            verdict = f"{len(names)} providers: {names}  -> CHOOSE ONE"
        print(f"  {label:<34} {verdict}")

    print("\n  DeepInfra availability:")
    for label, model_id, names in summary:
        print(f"    {label:<34} {'YES' if 'DeepInfra' in names else 'NO '}")
    print("\n  Reminder: the pin exists to hold ONE upstream fixed per model, not to force")
    print("  DeepInfra everywhere. A per-model pin is correct; a global one is not.")

    if args.save:
        with open(args.save, "w") as fh:
            json.dump(record, fh, indent=2)
        print(f"\n  raw responses written to {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

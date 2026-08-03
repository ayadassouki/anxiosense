#!/usr/bin/env python3
"""
probe_openrouter_raw.py — is the character-drop corruption coming from OpenRouter?

WHAT THIS IS FOR
----------------
Records in outputs/stage_c_final/raw contain agent payloads with contiguous runs of
characters deleted from the middle, e.g.

    emotions":["anxiety"],"emotional_intensity":"low_from_text":["worried"]}
                                                    ^^^ '","evidence' (11 chars) is gone

That damage is known to exist *upstream* of the Python harness (the .csv and .jsonl
records are byte-identical, and the Mastra dev server prints the same mangled text in
its own console). Two suspects remain:

    A. the Mastra / Vercel AI SDK response-assembly layer
    B. the OpenRouter HTTP transport itself

This script isolates B. It bypasses Mastra, the AI SDK, the Express server and the
experiment harness entirely, and speaks plain HTTP to the OpenRouter Chat Completions
API with `"stream": false`, using the same model, the same system prompt and the same
user message that produced the corrupted record for sample ge_024113 in Run 3.

    50 clean responses  -> OpenRouter is exonerated; the bug is in Mastra/AI SDK (A).
    any mangled response -> the transport or provider is implicated (B).

It writes every response verbatim. It never repairs, truncates or normalises content.

WHAT IT DOES NOT DO
-------------------
Imports nothing from the experiment pipeline, mutates nothing in outputs/stage_c_final,
and writes only to outputs/probe/. Safe to run while other work is in progress.

HOW TO RUN
----------
    cd ~/anxiosense/evaluation/llm-experiments
    pip install requests                      # only dependency
    export OPENROUTER_API_KEY=sk-or-...       # or let the script read anxiosense/.env
    python3 scripts/probe_openrouter_raw.py

Useful flags:

    --dry-run             build and print the request, send nothing (check this first)
    -n 50                 number of identical requests (default 50)
    --strategy one-shot-cot | zero-shot-cot | zero-shot
                          ge_024113 was corrupted under BOTH cot strategies in run 3;
                          default is one-shot-cot. Run it twice to cover both.
    --sample-id ge_024113 probe a different sample instead
    --sleep 0.5           seconds between requests (default 0.5; be kind to the API)
    --max-tokens 16384    matches models[].max_tokens in config/experiment_config.yaml

Cost: 50 calls x ~2k prompt tokens on Llama 4 Scout — a few US cents.

OUTPUT
------
    outputs/probe/openrouter_raw_probe_<strategy>_<UTC timestamp>.jsonl

One JSON object per iteration:

    iteration            1-based index
    request_sha256       sha256 of the exact request body — proves all N were identical
    http_status          HTTP status code
    response_headers     full response headers (OpenRouter puts routing metadata here)
    raw_body             the COMPLETE response body, verbatim, unparsed
    content              the assistant message content, verbatim, or null
    provider_metadata    id / model / provider / finish_reason / native_finish_reason / usage
    findings             which detectors fired (empty list = clean)
    latency_ms

Exit code 0 = no corruption detected. 1 = corruption detected. 2 = setup/transport error.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("requests is not installed. Run:  pip install requests")

# ── Paths ─────────────────────────────────────────────────────────────────────
# scripts/ -> llm-experiments/ -> evaluation/ -> repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(EXP_DIR, "..", ".."))

PROMPTS_DIR = os.path.join(REPO_ROOT, "prompts")
DATASET_CSV = os.path.join(REPO_ROOT, "evaluation", "datasets", "processed",
                           "goemotions_clean.csv")
OUT_DIR = os.path.join(EXP_DIR, "outputs", "probe")
DOTENV = os.path.join(REPO_ROOT, ".env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# The three keys the emotion prompt contractually requires in every payload.
REQUIRED_KEYS = ["emotions", "emotional_intensity", "evidence_from_text"]

# Literal signatures observed in the corrupted stage_c_final records.
# Regexes, not plain substrings: 'otions"' is a substring of the perfectly valid
# 'emotions"', so those patterns are anchored with a negative lookbehind.
KNOWN_SIGNATURES = [
    (r'low_from_text',            '\'","evidence\' eaten out of the middle'),
    (r'emensity',                 "'otional_int' eaten out of the middle"),
    (r'(?<!em)otions"',           '\'"em\' eaten off the front of "emotions"'),
    (r'(?<!em)otional_intensity', '\'"em\' eaten off the front of "emotional_intensity"'),
    (r'emotionsxiety',            '\'":["an\' eaten out'),
    (r'"_text"',                  "'evidence_from' eaten out"),
    (r'evidence_from"',           "'_text' eaten out"),
    (r'"evidence"\s*:',           "'_from_text' eaten out"),
]


# ── Environment ───────────────────────────────────────────────────────────────
def read_api_key() -> str:
    """OPENROUTER_API_KEY from the environment; falls back to the repo .env."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        print("[probe] API key: OPENROUTER_API_KEY from environment")
        return key
    if os.path.exists(DOTENV):
        with open(DOTENV, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        print(f"[probe] API key: OPENROUTER_API_KEY read from {DOTENV}")
                        return key
    sys.exit("OPENROUTER_API_KEY is not set, and no value found in .env.\n"
             "  export OPENROUTER_API_KEY=sk-or-...")


def read_model_id() -> str:
    """MODEL_ID currently configured for the pipeline (env wins, then .env)."""
    mid = os.environ.get("MODEL_ID", "").strip()
    if mid:
        return mid
    if os.path.exists(DOTENV):
        with open(DOTENV, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("MODEL_ID="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "meta-llama/llama-4-scout"


# ── Faithful reconstruction of the real request ───────────────────────────────
def load_system_prompt(strategy: str) -> str:
    """
    Mirrors src/mastra/utils/prompt-strategy-loader.ts: read
    prompts/emotion/{strategy}.md and extract the ```text ... ``` fenced block.
    That block is the exact system message the emotion agent runs with.
    """
    path = os.path.join(PROMPTS_DIR, "emotion", f"{strategy}.md")
    if not os.path.exists(path):
        sys.exit(f"prompt file not found: {path}")
    md = open(path, encoding="utf-8").read()
    m = re.search(r"```text\n([\s\S]+?)\n```", md)
    if not m:
        sys.exit(f"no ```text fenced block in {path} — prompt loader would return null")
    return m.group(1).strip()


def mode_prefix_social_media() -> str:
    """
    Verbatim copy of modePrefix('social-media') from
    src/mastra/workflows/anxiety-screening-assessment-workflow.ts.

    /api/workflow/evaluate always runs in social-media mode (datasets have no GAD-7),
    so every stage_c_final record was produced with this prefix.
    """
    return (
        "CONTEXT: The following text was sourced from social media (e.g. Reddit). "
        "Treat it as self-reported content from an unknown author describing their "
        "own experiences. Do NOT assume clinical intent or structured disclosure. "
        "Be appropriately cautious about any inferences.\n\n"
    )


def load_sample_text(sample_id: str) -> str:
    """The exact text_redacted string the pipeline sends for this sample_id."""
    if not os.path.exists(DATASET_CSV):
        sys.exit(f"dataset not found: {DATASET_CSV}")
    csv.field_size_limit(10 ** 7)
    with open(DATASET_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["sample_id"] == sample_id:
                return row["text_redacted"]
    sys.exit(f"sample_id {sample_id} not found in {DATASET_CSV}")


# ── Corruption detectors (read-only; never mutate content) ────────────────────
def find_key_fragments(content: str) -> list[str]:
    """
    Mid-word-cut detector, implemented as an UNBALANCED-KEY check.

    A JSON key is always written  "name":  — opening quote, name, closing quote,
    colon. Corruption that eats the opening quote or the front of the name leaves
    a key with a closing quote and no opening one:

        otions": []            <- '"em' was eaten
        emensity":"moderate"   <- 'otional_int' was eaten
        emotions":["anxiety"]  <- '{"' was eaten

    So: find every  name":  in the text and flag the ones whose name is not
    directly preceded by a quote.

    This replaces an earlier substring-fragment scan that treated a space as a
    valid boundary. That version matched ordinary English — a response whose prose
    said "the emotional intensity is coded as low" tripped 'emotional' and
    'intensit' as fragments of "emotional_intensity" and reported 42/50 clean
    responses as corrupt. Prose cannot produce an unbalanced key, so this check
    does not have that failure mode.
    """
    hits: set[str] = set()
    for m in re.finditer(r'([A-Za-z_][A-Za-z_0-9]*)"\s*:', content):
        start = m.start(1)
        if start == 0 or content[start - 1] != '"':
            hits.add(m.group(0).strip()[:48])
    return sorted(hits)


def find_unknown_keys(content: str) -> list[str]:
    """JSON key names present in the text that are not part of the contract."""
    keys = set(re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)"\s*:', content))
    return sorted(keys - set(REQUIRED_KEYS))


def json_object_recoverable(content: str) -> bool:
    """
    Read-only check: could ANY well-formed JSON object be pulled out of this text?
    Nothing is stored or returned from the attempt — the recorded content stays
    byte-exact. A JSON *string* or *array* does not count; only an object.
    """
    candidates = [content.strip()] + re.findall(r"\{[\s\S]*\}", content)
    for cand in candidates:
        try:
            if isinstance(json.loads(cand), dict):
                return True
        except Exception:
            pass
    return False


def analyse(content: str | None) -> list[dict]:
    """Returns a list of findings. Empty list means nothing suspicious."""
    findings: list[dict] = []
    if content is None:
        return [{"detector": "NO_CONTENT",
                 "detail": "response contained no assistant message content"}]
    if not content.strip():
        return [{"detector": "EMPTY_CONTENT", "detail": "content was empty/whitespace"}]

    for pattern, explanation in KNOWN_SIGNATURES:
        for m in re.finditer(pattern, content):
            findings.append({"detector": "KNOWN_SIGNATURE",
                             "detail": f"{m.group(0)!r} — {explanation}"})
            break  # one report per signature is enough

    missing = [k for k in REQUIRED_KEYS if f'"{k}"' not in content]
    if missing:
        findings.append({"detector": "MISSING_REQUIRED_KEY", "detail": ", ".join(missing)})

    frags = find_key_fragments(content)
    if frags:
        findings.append({"detector": "MID_WORD_CUT", "detail": ", ".join(frags)})

    unknown = find_unknown_keys(content)
    if unknown:
        findings.append({"detector": "UNKNOWN_JSON_KEY", "detail": ", ".join(unknown)})

    if not json_object_recoverable(content):
        findings.append({"detector": "NO_JSON_OBJECT",
                         "detail": "no well-formed JSON object anywhere in the content"})

    return findings


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Probe OpenRouter directly for character-drop corruption.")
    ap.add_argument("-n", "--iterations", type=int, default=50)
    ap.add_argument("--strategy", default="one-shot-cot",
                    choices=["zero-shot", "zero-shot-cot", "one-shot-cot"])
    ap.add_argument("--sample-id", default="ge_024113")
    ap.add_argument("--max-tokens", type=int, default=16384,
                    help="matches models[].max_tokens in config/experiment_config.yaml")
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the request and exit without sending anything")
    args = ap.parse_args()

    model_id = read_model_id()
    system_prompt = load_system_prompt(args.strategy)
    user_text = load_sample_text(args.sample_id)
    user_message = mode_prefix_social_media() + user_text

    # temperature and seed are null in config/experiment_config.yaml, so they are
    # omitted here rather than sent as defaults.
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    body = json.dumps(payload, ensure_ascii=False)
    body_bytes = body.encode("utf-8")
    request_sha = hashlib.sha256(body_bytes).hexdigest()

    print("=" * 78)
    print("OpenRouter raw transport probe")
    print("=" * 78)
    print(f"  model          : {model_id}")
    print(f"  strategy       : {args.strategy}  (prompts/emotion/{args.strategy}.md)")
    print(f"  sample_id      : {args.sample_id}")
    print(f"  user text      : {user_text!r}")
    print(f"  system prompt  : {len(system_prompt)} chars")
    print(f"  stream         : False")
    print(f"  max_tokens     : {args.max_tokens}  (temperature/seed omitted — null in config)")
    print(f"  iterations     : {args.iterations}")
    print(f"  request sha256 : {request_sha}")
    print("=" * 78)

    if args.dry_run:
        print("\n--- DRY RUN: request body that would be sent ---\n")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    api_key = read_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Same attribution headers the app sends (src/mastra/utils/model-provider.ts).
        "HTTP-Referer": "https://anxiosense.vercel.app",
        "X-Title": "AnxioSense Evaluation",
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(
        OUT_DIR, f"openrouter_raw_probe_{args.strategy}_{stamp}.jsonl")
    print(f"\nwriting -> {out_path}\n")

    dirty = 0
    transport_errors = 0
    session = requests.Session()

    with open(out_path, "w", encoding="utf-8") as out:
        # Header record: everything needed to reproduce this probe later.
        out.write(json.dumps({
            "record_type": "probe_header",
            "started_utc": stamp,
            "model": model_id,
            "strategy": args.strategy,
            "sample_id": args.sample_id,
            "user_text": user_text,
            "system_prompt": system_prompt,
            "user_message": user_message,
            "request_body": payload,
            "request_sha256": request_sha,
            "endpoint": OPENROUTER_URL,
            "iterations_planned": args.iterations,
        }, ensure_ascii=False) + "\n")
        out.flush()

        for i in range(1, args.iterations + 1):
            t0 = time.perf_counter()
            raw_body = None
            status = None
            resp_headers = {}
            content = None
            provider_meta = {}
            error = None

            try:
                r = session.post(OPENROUTER_URL, headers=headers,
                                 data=body_bytes, timeout=args.timeout)
                status = r.status_code
                resp_headers = dict(r.headers)
                # .text is the complete body, verbatim. Never trimmed.
                raw_body = r.text
                try:
                    parsed = json.loads(raw_body)
                except Exception:
                    parsed = None

                if isinstance(parsed, dict):
                    choices = parsed.get("choices") or []
                    if choices and isinstance(choices[0], dict):
                        msg = choices[0].get("message") or {}
                        # verbatim; no strip(), no repair
                        content = msg.get("content")
                    provider_meta = {
                        "id": parsed.get("id"),
                        "model": parsed.get("model"),
                        "provider": parsed.get("provider"),
                        "object": parsed.get("object"),
                        "created": parsed.get("created"),
                        "usage": parsed.get("usage"),
                        "finish_reason": (choices[0].get("finish_reason")
                                          if choices else None),
                        "native_finish_reason": (choices[0].get("native_finish_reason")
                                                 if choices else None),
                        "error": parsed.get("error"),
                    }
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                transport_errors += 1

            latency_ms = (time.perf_counter() - t0) * 1000.0
            findings = analyse(content) if error is None else []
            if findings:
                dirty += 1

            out.write(json.dumps({
                "record_type": "probe_response",
                "iteration": i,
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "request_sha256": request_sha,
                "http_status": status,
                "response_headers": resp_headers,
                "raw_body": raw_body,
                "content": content,
                "content_length": len(content) if content is not None else None,
                "provider_metadata": provider_meta,
                "findings": findings,
                "latency_ms": round(latency_ms, 1),
                "transport_error": error,
            }, ensure_ascii=False) + "\n")
            out.flush()

            flag = "CLEAN"
            if error:
                flag = f"ERROR {error[:50]}"
            elif findings:
                flag = "SUSPECT " + " | ".join(
                    f"{f['detector']}:{f['detail'][:40]}" for f in findings)
            print(f"[{i:>3}/{args.iterations}] status={status} "
                  f"len={len(content) if content else 0:>5} "
                  f"{latency_ms:>7.0f}ms  {flag}")
            if findings:
                print(f"        content: {content!r}")

            if i < args.iterations and args.sleep > 0:
                time.sleep(args.sleep)

    ok = args.iterations - dirty - transport_errors
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  clean responses     : {ok}/{args.iterations}")
    print(f"  suspect responses   : {dirty}")
    print(f"  transport errors    : {transport_errors}")
    print(f"  output              : {out_path}")
    print()
    if dirty:
        print("  VERDICT: corruption reproduced over plain non-streaming HTTP.")
        print("  OpenRouter / the transport is implicated. Mastra and the AI SDK")
        print("  were not in the path — they cannot be the cause on their own.")
        return 1
    if transport_errors and ok == 0:
        print("  VERDICT: inconclusive — every request failed at the transport layer.")
        return 2
    print("  VERDICT: no corruption over plain non-streaming HTTP.")
    print("  This does not prove OpenRouter is clean — it did not reproduce in")
    print(f"  {args.iterations} attempts. Corruption at ~4% would be expected to appear")
    print(f"  about {0.04 * args.iterations:.0f} times, so a clean run is meaningful evidence that")
    print("  the damage is introduced by the Mastra / AI SDK layer instead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

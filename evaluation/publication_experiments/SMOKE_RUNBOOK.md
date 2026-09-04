# Smoke run 001 — runbook

**This must be executed on the Mac that runs the AnxioSense stack.** The assistant's
shell has no network egress and cannot reach ports 3001/4111, so it cannot make the
model calls itself. Everything that does not need the network has already been verified.

Preflight already PASSED: config, manifests, prompt hashes, enabled-model filter,
timeout sanity. `deepseek` is present in the config and correctly excluded.

## What this run is

10 Dreaddit items · `qwen/qwen3.5-27b` · `zero-shot` · 1 run
= **10 assessments ≈ 50 LLM calls ≈ $0.02**

The model is Qwen because that is what `MODEL_ID` in `.env` currently points at, so
no server reconfiguration or restart is needed and the model-identity guard passes.
Qwen is also the model that historically produced unparseable referral output, so this
run may exercise the new `referral_unreadable` path for real.

## 1. Start the stack (two terminals, from the repo root)

```bash
npm run dev                 # Mastra, port 4111
cd server && npm run dev    # Express, port 3001
```

Confirm both are up:

```bash
curl -s -o /dev/null -w "mastra %{http_code}\n"  http://localhost:4111/api
curl -s -o /dev/null -w "express %{http_code}\n" http://localhost:3001/api/health || true
```

## 2. Run the smoke test

```bash
cd evaluation/publication_experiments
python3 -m runner.run \
  --config evaluation/publication_experiments/configs/smoke_001.yaml \
  --limit 10
```

It will abort before spending anything if a dataset hash, a prompt, or the model
identity is wrong. If the server serves a different model than requested, it stops
immediately rather than recording mislabelled rows.

## 3. Verify resume (no API calls, should dispatch 0)

```bash
python3 -m runner.run \
  --config evaluation/publication_experiments/configs/smoke_001.yaml \
  --limit 10 --resume
```

## 4. Produce the report

> **Where `parsed/records.jsonl` comes from.** `runner/run.py` writes only
> `experiment.json`, the append-only `raw/attempts.jsonl` and `raw/index.jsonl`,
> and `summaries/`. It does **not** write `parsed/`. Predictions are re-derived
> from the stored raw agent output by `runner/rescore.py`, which is invoked by
> `smoke_report.py`. This is intentional: `parsed/` is a derived artefact that can
> be regenerated at any time from the raw evidence without a model call, so a
> parser fix never requires re-running an experiment. **A run directory has no
> `parsed/records.jsonl` until `smoke_report.py` has been run against it** — that
> is expected, not a failed run.
>
> **`summaries/dispatch_stats.json` (schema `dispatch_stats/2`).** The evidence is
> the append-only `summaries/invocations.jsonl`, one record per runner invocation.
> `dispatch_stats.json` is a derived view over it: `first_invocation` is fixed
> once the first run completes, `invocations[]` lists every call with its mode
> (`initial` / `resume` / `retry_exhausted`), and `totals` accumulates. A
> `--resume` therefore appends and can never overwrite the original dispatch
> counts. `recomputed_from_raw` re-derives the assessment count and outcomes
> straight from `raw/index.jsonl`, so any summary can be audited independently.
>
> Runs made before 2026-09-04 (`smoke_001`, `bench_002`, `bench_003`) predate this
> and have a single-object `dispatch_stats.json` that was overwritten by their
> resume invocation, showing `dispatched: 0`. Their `raw/` files are intact and
> the true counts are recoverable from `raw/index.jsonl`.


```bash
python3 evaluation/publication_experiments/smoke_report.py \
  evaluation/publication_experiments/runs/smoke_001
```

Paste that output back and I will review it.

## Where the output goes

`evaluation/publication_experiments/runs/smoke_001/` — inside the repository, on the
Mac's own disk. It persists across reboots and disconnections.

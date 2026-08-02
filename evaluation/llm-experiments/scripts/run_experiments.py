#!/usr/bin/env python3
"""
scripts/run_experiments.py

AnxioSense full-pipeline evaluation runner.

Calls the AnxioSense server (POST /api/workflow/evaluate) for each dataset
example and records the structured response, extracted label, and ground-truth
label. Does NOT implement any LLM logic — that lives entirely inside the
AnxioSense server and Mastra workflow.

CRITICAL FRAMING
----------------
This script evaluates the FULL AnxioSense multi-agent pipeline:
    Emotion → Symptom → Context → Referral → Report → Validation (+ RAG)

It is NOT a standalone LLM classifier. The "model" and "strategy" CLI args
are recorded in the result metadata and passed to the server's /evaluate
endpoint, but the pipeline's actual model is whatever MODEL_ID / MODEL_PROVIDER
is set in anxiosense/.env at server startup.
To switch models between experiment batches, update anxiosense/.env AND
server/.env, then restart both Mastra and Express.

Prerequisites
-------------
1. Start the Mastra dev server:
       cd /path/to/anxiosense && npm run dev

2. Start the Express server (in a second terminal):
       cd /path/to/anxiosense/server && npm run dev

Usage examples
--------------
    # Stage A — dry-run (no API calls, shows plan and cost):
    python evaluation/llm-experiments/scripts/run_experiments.py \\
        --dry-run \\
        --dataset dreaddit \\
        --model "openrouter/meta-llama/llama-4-scout" \\
        --strategy one-shot-cot \\
        --sample-size 10 \\
        --runs 1 \\
        --max-cost-usd 0.10

    # Stage B — 10-sample paid pilot (requires --confirm-paid):
    python evaluation/llm-experiments/scripts/run_experiments.py \\
        --dataset dreaddit \\
        --model "openrouter/meta-llama/llama-4-scout" \\
        --strategy one-shot-cot \\
        --sample-size 10 \\
        --runs 1 \\
        --max-cost-usd 0.10 \\
        --confirm-paid \\
        --output-dir evaluation/llm-experiments/outputs/stage_b

    # Resume an interrupted run:
    python evaluation/llm-experiments/scripts/run_experiments.py \\
        --resume \\
        --dataset dreaddit \\
        --model "openrouter/meta-llama/llama-4-scout" \\
        --strategy one-shot-cot \\
        --sample-size 10 \\
        --runs 1 \\
        --confirm-paid

Output
------
For each (dataset, model, strategy, run) cell a JSONL file is written to:
    outputs/raw/{dataset}_{model_slug}_{strategy}_run{n}.jsonl

Each line is a JSON record with fields:
    sample_id, dataset, model_id, model_actual, strategy, strategy_actual, run,
    split_filter,               # dataset split used ('test', 'train', or '' for all)
    sample_seed,                # random seed used for dataset sampling
    ground_truth, label, failure_reason, is_provider_error,
    prediction_valid,           # label not None and no failure_reason
    safety_intercept,           # safety_override fired (0 LLM tokens consumed)
    internal_recovery_used,     # any internal error-recovery path used
    include_in_primary_metrics, # True for all evaluable predictions
    exclusion_reason,           # set when include_in_primary_metrics is False
    concern_pattern, referral_level, final_report_excerpt,
    emotion_agent_raw,          # raw Emotion Agent JSON excerpt (GoEmotions primary source)
    safety_override, safety_category,
    agent_json_parse_failed, fallback_claim_injected,
    referral_risk_fallback_used, recommendation_rejected, has_internal_warning,
    latency_ms, server_latency_ms, token_usage, api_error

Run compute_metrics.py after all cells are complete to aggregate results.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.anxiosense_client import call_anxiosense
from src.config import load_config, resolve_path
from src.dataset_loader import load_dataset, validate_schema, sample_dataset
from src.emotion_payload import OK_STATUSES, extract_emotion_payload, primary_emotion
from src.label_mapping import (
    ANXIOSENSE_TO_EVAL_CLASS,
    map_dreaddit_label,
    map_goemotions_label,
)
from src.report_parser import extract_stress_label
from src.result_store import ResultStore

CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"

# Maximum characters of emotion_agent_raw persisted per record.
# Must comfortably exceed a full chain-of-thought response, otherwise the
# "emotions" array is truncated away and the record becomes unrecoverable.
# Set to None to disable truncation entirely.
EMOTION_RAW_STORAGE_CAP = 20000


# ---------------------------------------------------------------------------
# Model ID normalisation
# ---------------------------------------------------------------------------

# Provider prefixes that the Express server prepends to model IDs.
# The runner records the short CLI model ID (e.g. "meta-llama/llama-4-scout")
# but the server returns the provider-prefixed form ("openrouter/meta-llama/llama-4-scout").
# Strip these prefixes before cost lookups and model-ID comparisons so both
# representations are treated as identical.
_PROVIDER_PREFIXES = ("openrouter/", "mistral/", "anthropic/", "groq/", "together/")

def normalize_model_id(model_id: str) -> str:
    """Strip provider prefix from a model ID so both forms compare equal."""
    for prefix in _PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


# ---------------------------------------------------------------------------
# Cell metadata helpers
# ---------------------------------------------------------------------------

MEASURED_INPUT_TOKENS_PER_ASSESSMENT  = 6_271   # Stage B measured average
MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT = 362     # Stage B measured average
INPUT_PRICE_PER_MILLION  = 0.10   # USD — Llama 4 Scout on OpenRouter
OUTPUT_PRICE_PER_MILLION = 0.30   # USD — Llama 4 Scout on OpenRouter


def write_cell_metadata(
    *,
    meta_dir: Path,
    dataset: str,
    model_id: str,
    model_slug: str,
    strategy: str,
    run: int,
    split: str,
    sample_seed: int,
    sample_ids: list[str],
    gt_label_distribution: dict,
    exclude_ids: list[str],
    phase: str,  # "dry_run" or "live"
) -> Path:
    """
    Write a per-cell metadata JSON file to meta_dir.

    The file captures everything needed to reproduce sampling and link results
    back to the exact rows that were evaluated.

    Returns the path to the written file.
    """
    meta_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{dataset}_{model_slug}_{strategy}_run{run}_meta.json"
    meta_path = meta_dir / filename

    cost_per_assessment = (
        MEASURED_INPUT_TOKENS_PER_ASSESSMENT  * INPUT_PRICE_PER_MILLION  / 1e6
        + MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT * OUTPUT_PRICE_PER_MILLION / 1e6
    )

    meta = {
        "schema_version": 1,
        "phase": phase,
        "dataset": dataset,
        "split": split,
        "sample_seed": sample_seed,
        "sample_count": len(sample_ids),
        "sample_ids": sample_ids,
        "model": model_id,
        "strategy": strategy,
        "run": run,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "exclude_ids": exclude_ids,
        "gt_label_distribution": gt_label_distribution,
        "pricing": {
            "input_price_per_million_usd":  INPUT_PRICE_PER_MILLION,
            "output_price_per_million_usd": OUTPUT_PRICE_PER_MILLION,
            "measured_input_tokens_per_assessment":  MEASURED_INPUT_TOKENS_PER_ASSESSMENT,
            "measured_output_tokens_per_assessment": MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT,
            "cost_per_assessment_usd": round(cost_per_assessment, 9),
            "projected_total_cost_usd": round(cost_per_assessment * len(sample_ids), 6),
        },
    }

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    return meta_path


# ---------------------------------------------------------------------------
# Cost constants (Llama 4 Scout smoke-test measured values)
# ---------------------------------------------------------------------------
# Keys stored WITHOUT provider prefix — normalize_model_id() is called at lookup time.
# Pricing source: OpenRouter model page (verified 2026-07).
#   Llama 4 Scout: $0.10/M input tokens, $0.30/M output tokens
#   Measured Stage B averages: ~6,706 input / 449 output per assessment (8 non-safety LLM runs).
#   Dry-run measured tokens (smoke test 3): 6,271 input / 362 output.
COST_PER_ASSESSMENT_USD: dict[str, float] = {
    # $/assessment = (input_tokens × price_in + output_tokens × price_out) / 1_000_000
    "meta-llama/llama-4-scout":   (6271 * 0.10 + 362 * 0.30) / 1e6,   # ≈$0.000736/assessment
    "mistral-small-2603":         (6271 * 0.10 + 362 * 0.30) / 1e6,   # same rates, placeholder
    "deepseek/deepseek-v4-flash": (6271 * 0.07 + 362 * 0.28) / 1e6,   # $0.07/M in + $0.28/M out
    "google/gemma-3-27b-it:free": 0.0,
    "meta-llama/llama-4-scout:free": 0.0,
    "microsoft/phi-4:free":       0.0,
    "nvidia/nemotron-3-ultra-550b-a55b:free": 0.0,
}
DEFAULT_COST_PER_ASSESSMENT = 0.0015  # conservative fallback for unknown models


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Path, verbose: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "experiment.log"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        handlers=handlers,
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_cost(model_id: str, n_assessments: int) -> float:
    """Return estimated USD cost for n_assessments full pipeline runs."""
    rate = COST_PER_ASSESSMENT_USD.get(
        normalize_model_id(model_id),
        DEFAULT_COST_PER_ASSESSMENT,
    )
    return rate * n_assessments


def print_cost_estimate(
    datasets: list[str],
    models: list,
    strategies: list[str],
    n_runs: int,
    sample_size: int,
) -> float:
    """Print a cost breakdown table and return total expected cost."""
    logger.info("=" * 70)
    logger.info("COST ESTIMATE (before execution)")
    logger.info("=" * 70)
    logger.info(
        "  Datasets: %s  |  Strategies: %d  |  Runs: %d  |  Samples/dataset: %d",
        datasets, len(strategies), n_runs, sample_size,
    )

    total = 0.0
    for ds in datasets:
        for m in models:
            n = sample_size * len(strategies) * n_runs
            cost = estimate_cost(m.id, n)
            total += cost
            logger.info(
                "  %-40s  %-20s  %d assessments  ≈$%.4f",
                ds, m.id, n, cost,
            )

    logger.info("  TOTAL estimated cost:  ≈$%.4f", total)
    logger.info("=" * 70)
    return total


# ---------------------------------------------------------------------------
# Ground-truth label helper
# ---------------------------------------------------------------------------

def get_ground_truth(row: dict, dataset_name: str) -> object:
    """Return the normalised ground-truth label for a dataset row."""
    if dataset_name == "dreaddit":
        return map_dreaddit_label(row["label"])
    if dataset_name == "goemotions":
        return map_goemotions_label(row["emotion_names"])
    raise ValueError(f"Unknown dataset: {dataset_name!r}")


# ---------------------------------------------------------------------------
# Predicted label extraction
# ---------------------------------------------------------------------------

def extract_predicted_label(
    result_dict: dict,
    dataset_name: str,
    emotion_agent_raw: Optional[str] = None,
) -> tuple[object, str | None]:
    """
    Extract the predicted label from an AnxioSense response dict.

    Returns (label, failure_reason). label is None on failure.
    Failures are NEVER counted as incorrect — they are stored separately
    (failure_reason non-null) and excluded from precision/recall/F1.

    For GoEmotions, emotion_agent_raw (the raw Emotion Agent JSON string) is
    the PRIMARY prediction source. When absent, falls back to markdown parsing.
    """
    if dataset_name == "dreaddit":
        label = extract_stress_label(result_dict)
        if label is None:
            return None, "extract_stress_label returned None (referralLevel missing or unrecognised)"
        return label, None

    if dataset_name == "goemotions":
        # BUGFIX (Stage C post-mortem): this branch previously called
        # extract_emotion_label() and treated EVERY None return as a failure.
        # That conflated two opposite outcomes:
        #   - {"emotions": []} → a VALID prediction meaning "no emotion
        #     detected", which maps to the non_distress class (71% of the
        #     GoEmotions test ground truth), and
        #   - an unparseable payload → a genuine failure.
        # The result was that correct non_distress predictions were discarded,
        # collapsing the reported parse rate to 35/300.
        #
        # extract_emotion_payload() returns an explicit status so the two cases
        # stay distinct, and tolerates markdown fences and chain-of-thought
        # prose around the JSON (expected output for the CoT strategies).
        status, emotions = extract_emotion_payload(emotion_agent_raw)

        if status not in OK_STATUSES:
            return None, f"emotion payload unreadable ({status})"

        emotion = primary_emotion(emotions)
        if emotion is None:
            # Empty emotions list — a valid "no emotion detected" prediction.
            return "non_distress", None
        if emotion not in ANXIOSENSE_TO_EVAL_CLASS:
            # Agent returned an emotion outside its declared vocabulary.
            return None, f"out-of-vocabulary predicted emotion: {emotion!r}"
        return ANXIOSENSE_TO_EVAL_CLASS[emotion], None

    return None, f"Unknown dataset: {dataset_name!r}"


# ---------------------------------------------------------------------------
# Single experiment cell
# ---------------------------------------------------------------------------

def run_one_cell(
    *,
    dataset_name: str,
    df,
    ds_cfg,
    model_id: str,
    strategy: str,
    run_number: int,
    store: ResultStore,
    base_url: str,
    request_delay: float,
    timeout: int,
    max_api_calls: int | None,
    api_calls_counter: list,   # mutable [int] for cross-call tracking
    split_filter: str = "test",
    sample_seed: int = 42,
) -> dict:
    """
    Run a single (model, strategy, run) cell over all examples in df.

    Returns aggregate stats.
    """
    n_completed = 0
    n_skipped   = 0
    n_failed    = 0
    n_provider_errors = 0
    latencies: list[float] = []

    for idx, row in df.iterrows():
        sample_id = str(row.get("sample_id", row.get("id", idx)))

        if store.is_completed(sample_id, model_id, strategy, run_number):
            n_skipped += 1
            continue

        # Safety: stop when max_api_calls reached
        if max_api_calls is not None and api_calls_counter[0] >= max_api_calls:
            logger.warning(
                "Reached --max-api-calls=%d — stopping cell early.", max_api_calls
            )
            break

        user_text = str(row[ds_cfg.text_column])

        # Ground truth — computed from dataset label, NEVER sent to the model
        try:
            ground_truth = get_ground_truth(dict(row), dataset_name)
        except Exception as exc:
            logger.warning("Label error for sample %s: %s", sample_id, exc)
            ground_truth = None

        # Call AnxioSense pipeline
        result = call_anxiosense(
            text=user_text,
            model=model_id,
            strategy=strategy,
            base_url=base_url,
            timeout=timeout,
        )
        api_calls_counter[0] += 1

        # Classify error types
        is_provider_error = False
        if result.error:
            err_lower = result.error.lower()
            # 429, timeout, provider_unavailable, connection failure → stored separately
            if any(kw in err_lower for kw in [
                "429", "timeout", "provider_unavailable",
                "connection error", "service_unavailable",
            ]):
                is_provider_error = True

        # Extract predicted label.
        # For GoEmotions, pass emotion_agent_raw so the Emotion Agent JSON is
        # used as the primary source rather than the markdown report.
        if result.error:
            label          = None
            failure_reason = result.error
        else:
            label, failure_reason = extract_predicted_label(
                result.report_dict,
                dataset_name,
                emotion_agent_raw=result.emotion_agent_raw,
            )

        # Also capture parser failures for malformed JSON / missing fields
        if label is None and not result.error:
            if "malformed" in str(failure_reason).lower() or failure_reason:
                pass  # already set

        # Pull report fields
        report_block = (result.report_dict or {}).get("report", {}) or {}
        meta_block   = (result.report_dict or {}).get("metadata", {}) or {}

        final_report_text = report_block.get("finalReport") or ""
        concern_pattern   = report_block.get("concernPattern") or ""
        referral_level    = report_block.get("referralLevel") or ""
        server_latency_ms = meta_block.get("latency_ms", 0)

        # Actual model/strategy from server metadata (source of truth).
        # Normalize model_actual so provider-prefixed and bare IDs compare equal.
        raw_model_actual  = meta_block.get("model_actual", model_id)
        model_actual      = normalize_model_id(raw_model_actual)
        strategy_actual   = meta_block.get("strategy_used", strategy)

        # Internal quality flags from the server (set by Mastra workflow steps).
        # Present only when the server runs the updated workflow; default False on
        # safety-override path or legacy server versions.
        qf = meta_block.get("quality_flags") or {}
        safety_override             = bool(meta_block.get("safety_override", False))
        safety_category             = meta_block.get("safety_category") or None
        agent_json_parse_failed     = bool(qf.get("agent_json_parse_failed",     False))
        fallback_claim_injected     = bool(qf.get("fallback_claim_injected",     False))
        referral_risk_fallback_used = bool(qf.get("referral_risk_fallback_used", False))
        recommendation_rejected     = bool(qf.get("recommendation_rejected",     False))

        # A sample has any internal quality issue if any flag is set.
        # same predicate reused for `internal_recovery_used` field below.
        has_internal_warning = any([
            agent_json_parse_failed,
            fallback_claim_injected,
            referral_risk_fallback_used,
            recommendation_rejected,
        ])

        # ── Derived classification / inclusion fields ──────────────────────
        # prediction_valid: the pipeline produced a usable binary prediction
        #   (no API error, label successfully extracted).  Samples where this
        #   is False are excluded from all metric computations.
        prediction_valid = (label is not None) and (failure_reason is None)

        # safety_intercept: Express /evaluate short-circuited before calling
        #   Mastra (safety_override=True).  Token usage is 0 for these samples.
        safety_intercept = safety_override

        # internal_recovery_used: one or more internal error-recovery paths
        #   fired (JSON parse failure, fallback claim injection, referral risk
        #   fallback, or recommendation rejection).  The pipeline still produced
        #   a prediction, but it was partially auto-corrected.
        #   Distinct from safety_intercept (deliberate bypass, not an error).
        internal_recovery_used = has_internal_warning

        # include_in_primary_metrics: True iff this sample should count toward
        #   the headline accuracy/F1 figures.  For Dreaddit pilot (Stage B) all
        #   evaluable predictions are included — safety intercepts produce valid
        #   urgent→1 labels and are methodologically defensible as positive
        #   predictions.  Set exclusion_reason when False.
        include_in_primary_metrics = prediction_valid

        # exclusion_reason: human-readable string when include_in_primary_metrics
        #   is False; None otherwise.
        if include_in_primary_metrics:
            exclusion_reason = None
        elif result.error and is_provider_error:
            exclusion_reason = f"provider_error: {result.error[:120]}"
        elif result.error:
            exclusion_reason = f"api_error: {result.error[:120]}"
        else:
            exclusion_reason = failure_reason or "label_extraction_failed"

        # Persist emotion_agent_raw for storage.
        #
        # BUGFIX (Stage C post-mortem): this was previously capped at [:600].
        # The comment claimed 600 chars was "enough to capture the full emotions
        # array", which holds only when the agent emits bare JSON. Under the two
        # chain-of-thought strategies the agent narrates its reasoning FIRST, so
        # the prose consumed the entire budget and the "emotions" array was cut
        # off mid-write. 24 Stage C records were destroyed this way, and because
        # the truncation happened at write time the full payload was never
        # persisted — those records are unrecoverable offline.
        #
        # The cap is now high enough to hold a full CoT response. Set
        # EMOTION_RAW_STORAGE_CAP to None to disable truncation entirely.
        emotion_raw_excerpt = result.emotion_agent_raw or None
        if emotion_raw_excerpt and EMOTION_RAW_STORAGE_CAP:
            emotion_raw_excerpt = emotion_raw_excerpt[:EMOTION_RAW_STORAGE_CAP]

        record = {
            "sample_id":                  sample_id,
            "dataset":                    dataset_name,
            "model_id":                   normalize_model_id(model_id),  # normalised
            "model_actual":               model_actual,                   # normalised
            "strategy":                   strategy,
            "strategy_actual":            strategy_actual,
            "run":                        run_number,
            # Sampling provenance — critical for reproducibility
            "split_filter":               split_filter,
            "sample_seed":                sample_seed,
            "ground_truth":               ground_truth,
            "label":                      label,
            "failure_reason":             failure_reason,
            "is_provider_error":          is_provider_error,
            # ── Classification / inclusion metadata ──────────────────────────
            "prediction_valid":           prediction_valid,
            "safety_intercept":           safety_intercept,
            "internal_recovery_used":     internal_recovery_used,
            "include_in_primary_metrics": include_in_primary_metrics,
            "exclusion_reason":           exclusion_reason,
            # ── Pipeline output fields ────────────────────────────────────────
            "concern_pattern":            concern_pattern,
            "referral_level":             referral_level,
            "final_report_excerpt":       final_report_text[:400],
            # Raw Emotion Agent JSON (primary GoEmotions prediction source).
            "emotion_agent_raw":          emotion_raw_excerpt,
            # Internal quality flags — observable side-effects, not prediction errors.
            # Samples with any flag set are included in metrics but flagged for review.
            "safety_override":            safety_override,
            "safety_category":            safety_category,
            "agent_json_parse_failed":    agent_json_parse_failed,
            "fallback_claim_injected":    fallback_claim_injected,
            "referral_risk_fallback_used": referral_risk_fallback_used,
            "recommendation_rejected":    recommendation_rejected,
            "has_internal_warning":       has_internal_warning,
            "latency_ms":                 result.latency_ms,
            "server_latency_ms":          server_latency_ms,
            "token_usage":                result.token_usage,
            "api_error":                  result.error,
        }

        store.append(record)
        latencies.append(result.latency_ms)

        if result.error and is_provider_error:
            n_provider_errors += 1
            logger.warning(
                "Provider error for sample %s (NOT counted as wrong): %s",
                sample_id, result.error[:100],
            )
        elif label is not None:
            n_completed += 1
        else:
            n_failed += 1
            logger.debug(
                "Parse failure for sample %s: %s", sample_id, failure_reason
            )

        if request_delay > 0:
            time.sleep(request_delay)

    return {
        "n_completed":       n_completed,
        "n_skipped":         n_skipped,
        "n_failed":          n_failed,
        "n_provider_errors": n_provider_errors,
        "latencies":         latencies,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "AnxioSense full-pipeline evaluation runner. "
            "Requires the AnxioSense Express server + Mastra to be running."
        )
    )
    # Scope filters
    parser.add_argument("--dataset",      default=None,
                        help="Dataset name (default: all from config)")
    parser.add_argument("--model",        default=None,
                        help="Model ID string (default: all from config)")
    parser.add_argument("--strategy",     default=None,
                        help="Strategy string (default: all from config)")
    parser.add_argument("--runs",         type=int, default=None,
                        help="Number of runs (default: from config)")
    parser.add_argument("--sample-size",  type=int, default=None,
                        help="Override sample size per dataset per run")

    # Safety limits
    parser.add_argument("--max-cost-usd", type=float, default=None,
                        help="Refuse to start if projected cost exceeds this value")
    parser.add_argument("--max-api-calls", type=int, default=None,
                        help="Stop after this many API calls (across all cells)")
    parser.add_argument("--dry-run",      action="store_true",
                        help="Print plan and cost estimate then exit without making API calls")
    parser.add_argument("--confirm-paid", action="store_true",
                        help="Required flag to authorise paid API calls (prevents accidental spend)")

    # Execution options
    parser.add_argument("--resume",       action="store_true",
                        help="Skip samples already recorded in existing JSONL files")
    parser.add_argument("--concurrency",  type=int, default=1,
                        help="Concurrent requests (default: 1; keep at 1 for OpenRouter)")
    parser.add_argument("--output-dir",   default=None,
                        help="Override output directory")
    parser.add_argument("--base-url",     default=None,
                        help="AnxioSense server base URL (default: from config)")
    parser.add_argument("--verbose",      action="store_true",
                        help="Enable DEBUG logging")

    # ── Sampling controls ───────────────────────────────────────────────────
    parser.add_argument(
        "--split", default="test",
        help="Restrict sampling to rows whose split column equals this value "
             "('test', 'train', 'validation'). Pass empty string to use all rows. "
             "Default: 'test'. Required for evaluation — train rows must never "
             "appear in metric computation.",
    )
    parser.add_argument(
        "--exclude-ids", default=None,
        help="Comma-separated sample_id values to exclude from sampling before "
             "stratified draw (e.g. IDs used in a prior pilot stage). "
             "Applied after the split filter.",
    )
    parser.add_argument(
        "--sample-seed", type=int, default=42,
        help="Random seed for reproducible stratified sampling. "
             "Use a distinct value per experiment stage to avoid selection overlap. "
             "Default: 42 (Stage B used 42; Stage C should use a different value). "
             "Recorded in every result record.",
    )

    args = parser.parse_args()

    cfg = load_config(CONFIG_PATH)

    log_dir = resolve_path(REPO_ROOT, cfg.log_dir)
    setup_logging(log_dir, verbose=args.verbose)
    logger.info("AnxioSense Pipeline Evaluation Runner starting")

    # Server config
    server_cfg    = getattr(cfg, "server", None)
    base_url      = args.base_url or (server_cfg.base_url if server_cfg else None) or "http://localhost:3001"
    request_delay = float((server_cfg.request_delay_seconds if server_cfg else None) or 1.0)
    timeout       = int((server_cfg.timeout_seconds if server_cfg else None) or 90)

    logger.info(
        "Server: %s  delay=%.1fs  timeout=%ds  concurrency=%d",
        base_url, request_delay, timeout, args.concurrency,
    )
    if args.concurrency > 1:
        logger.warning(
            "concurrency > 1 is experimental for OpenRouter — shared rate limits may cause 429s."
        )

    output_dir = Path(args.output_dir) if args.output_dir else resolve_path(REPO_ROOT, cfg.output_dir)
    raw_dir    = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # CLI filters
    datasets   = [args.dataset]  if args.dataset  else list(cfg.datasets.keys())
    models     = [m for m in cfg.models if args.model is None or m.id == args.model]
    strategies = [args.strategy] if args.strategy else cfg.strategies
    n_runs     = args.runs or cfg.runs
    sample_size = args.sample_size or cfg.sample_size

    # ── Exclusion list ─────────────────────────────────────────────────────
    exclude_ids_set: set[str] = set()
    if args.exclude_ids:
        exclude_ids_set = {s.strip() for s in args.exclude_ids.split(",") if s.strip()}
        logger.info(
            "--exclude-ids: %d sample_id(s) will be excluded from all datasets before sampling.",
            len(exclude_ids_set),
        )

    if not models:
        logger.error("No models matched --model %s. Available: %s",
                     args.model, [m.id for m in cfg.models])
        sys.exit(1)

    # ── Cost estimate and safety gate ──────────────────────────────────────
    total_cells       = len(datasets) * len(models) * len(strategies) * n_runs
    total_assessments = total_cells * sample_size
    total_llm_calls   = total_assessments * 5  # 5 agents per assessment

    projected_cost = print_cost_estimate(datasets, models, strategies, n_runs, sample_size)

    logger.info(
        "Plan: %d datasets × %d models × %d strategies × %d runs = %d cells  "
        "(%d assessments, %d LLM calls)",
        len(datasets), len(models), len(strategies), n_runs,
        total_cells, total_assessments, total_llm_calls,
    )

    if args.max_cost_usd is not None and projected_cost > args.max_cost_usd:
        logger.error(
            "ABORTED: Projected cost $%.4f exceeds --max-cost-usd $%.4f. "
            "Use --dry-run to inspect the plan, then adjust --sample-size or --max-cost-usd.",
            projected_cost, args.max_cost_usd,
        )
        sys.exit(1)

    if args.dry_run:
        # ── Sample-level preview (all datasets) ───────────────────────────────
        # Applies the split filter and exclusion list identically to the live run.
        # Zero API calls are made.

        grand_total_samples = 0  # sum of actual sample counts across all datasets
        # Stores (preview_sample_df, gt_dist) keyed by dataset name for metadata writing
        _dry_run_samples: dict = {}

        for preview_dataset in datasets:
            ds_cfg_preview = cfg.datasets[preview_dataset]
            path_preview   = resolve_path(REPO_ROOT, ds_cfg_preview.path)

            df_preview = load_dataset(path_preview, split_column=ds_cfg_preview.split_column)
            validate_schema(df_preview, [ds_cfg_preview.text_column, ds_cfg_preview.label_column])
            if "sample_id" not in df_preview.columns:
                df_preview = df_preview.copy()
                df_preview["sample_id"] = [f"{preview_dataset}_{i:05d}" for i in range(len(df_preview))]

            # ── Apply split filter (same logic as live run) ───────────────────
            n_all = len(df_preview)
            if args.split:
                df_preview = df_preview[
                    df_preview[ds_cfg_preview.split_column] == args.split
                ].reset_index(drop=True)
            n_after_split = len(df_preview)

            # ── Apply ID exclusions (same logic as live run) ──────────────────
            excluded_here = (
                df_preview[df_preview["sample_id"].isin(exclude_ids_set)]
                if exclude_ids_set else df_preview.iloc[0:0]
            )
            if not excluded_here.empty:
                df_preview = df_preview[
                    ~df_preview["sample_id"].isin(exclude_ids_set)
                ].reset_index(drop=True)
            n_after_excl = len(df_preview)

            # ── Stratified sample ─────────────────────────────────────────────
            preview_sample = sample_dataset(
                df_preview,
                n=sample_size,
                random_state=args.sample_seed,
                stratify_col=ds_cfg_preview.label_column,
            )

            # Ground-truth distribution
            gt_dist: Counter = Counter()
            for _, row in preview_sample.iterrows():
                try:
                    gt = get_ground_truth(dict(row), preview_dataset)
                    gt_dist[str(gt)] += 1
                except Exception:
                    gt_dist["?"] += 1

            logger.info("=" * 84)
            logger.info("DRY-RUN PREVIEW — %-20s  model: %s", preview_dataset.upper(), models[0].id)
            logger.info(
                "  split='%s'  total=%d → after_split=%d → after_excl=%d → sampled=%d",
                args.split or "(all)", n_all, n_after_split, n_after_excl, len(preview_sample),
            )
            logger.info("  sample_seed=%d   label_col='%s'   text_col='%s'",
                        args.sample_seed, ds_cfg_preview.label_column, ds_cfg_preview.text_column)
            logger.info("  GT distribution: %s", dict(sorted(gt_dist.items())))
            if excluded_here.empty:
                logger.info("  exclusions: 0 (no --exclude-ids matched this split)")
            else:
                logger.info("  exclusions: %d ID(s) removed: %s",
                            len(excluded_here), list(excluded_here["sample_id"]))
            logger.info("  strategies: %s", strategies)
            logger.info("=" * 84)
            logger.info(
                "  %-5s  %-20s  %-6s  %-16s  %-11s  %s",
                "#", "sample_id", "split", "ground_truth", "dup_flagged",
                "text_redacted preview (first 85 chars)",
            )
            logger.info("  " + "-" * 106)

            for i, (_, row) in enumerate(preview_sample.iterrows(), 1):
                try:
                    gt = get_ground_truth(dict(row), preview_dataset)
                except Exception:
                    gt = row.get(ds_cfg_preview.label_column, "?")
                text_preview = str(row[ds_cfg_preview.text_column])[:85].replace("\n", " ")
                dup_flag = (
                    "intra+cross" if row.get("is_intra_split_duplicate") and row.get("is_cross_split_duplicate")
                    else "intra" if row.get("is_intra_split_duplicate")
                    else "cross" if row.get("is_cross_split_duplicate")
                    else "—"
                )
                logger.info(
                    "  %-5d  %-20s  %-6s  %-16s  %-11s  %s",
                    i, row["sample_id"], row.get("split", "?"), str(gt), dup_flag, text_preview,
                )

            grand_total_samples += len(preview_sample)
            _dry_run_samples[preview_dataset] = (preview_sample, gt_dist)

        # ── Write per-cell metadata JSON (dry-run phase) ──────────────────────
        meta_dir = output_dir / "metadata"
        written_meta: list[str] = []
        for ds_name, (ds_sample, ds_gt_dist) in _dry_run_samples.items():
            sample_ids_list = list(ds_sample["sample_id"].astype(str))
            for model_cfg in models:
                m_slug = model_cfg.id.replace("/", "_").replace(":", "_")
                for strat in strategies:
                    for run_n in range(1, n_runs + 1):
                        meta_path = write_cell_metadata(
                            meta_dir=meta_dir,
                            dataset=ds_name,
                            model_id=model_cfg.id,
                            model_slug=m_slug,
                            strategy=strat,
                            run=run_n,
                            split=args.split or "",
                            sample_seed=args.sample_seed,
                            sample_ids=sample_ids_list,
                            gt_label_distribution=dict(sorted(ds_gt_dist.items())),
                            exclude_ids=sorted(exclude_ids_set),
                            phase="dry_run",
                        )
                        written_meta.append(str(meta_path))

        logger.info("=" * 84)
        logger.info("DRY-RUN METADATA — wrote %d cell JSON file(s) to %s",
                    len(written_meta), meta_dir)
        for mp in written_meta:
            logger.info("  %s", mp)

        # ── Aggregate cost projection ─────────────────────────────────────────
        total_assessments_dr = grand_total_samples * len(strategies) * len(models) * n_runs
        cost_rate_dr = COST_PER_ASSESSMENT_USD.get(
            normalize_model_id(models[0].id), DEFAULT_COST_PER_ASSESSMENT
        )
        total_cost_dr = cost_rate_dr * total_assessments_dr

        logger.info("=" * 84)
        logger.info("DRY-RUN COST PROJECTION  (all datasets, strategies, models, runs)")
        logger.info("  Samples (sum across datasets): %d  (%d each × %d datasets)",
                    grand_total_samples, sample_size, len(datasets))
        logger.info("  × strategies   : %d  %s", len(strategies), strategies)
        logger.info("  × models       : %d", len(models))
        logger.info("  × runs         : %d", n_runs)
        logger.info("  = assessments  : %d", total_assessments_dr)
        logger.info("  Token/assessment (measured): %d in + %d out = %d total",
                    MEASURED_INPUT_TOKENS_PER_ASSESSMENT, MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT,
                    MEASURED_INPUT_TOKENS_PER_ASSESSMENT + MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT)
        logger.info("  Total input  tokens: %d",
                    MEASURED_INPUT_TOKENS_PER_ASSESSMENT  * total_assessments_dr)
        logger.info("  Total output tokens: %d",
                    MEASURED_OUTPUT_TOKENS_PER_ASSESSMENT * total_assessments_dr)
        logger.info("  Rate ($0.10/M in + $0.30/M out): $%.6f / assessment", cost_rate_dr)
        logger.info("  Projected cost : ≈$%.4f", total_cost_dr)
        if args.max_cost_usd is not None:
            status = "SAFE ✓" if total_cost_dr <= args.max_cost_usd else "EXCEEDS CAP ✗"
            logger.info("  Cost cap $%.2f : %s", args.max_cost_usd, status)
        logger.info("=" * 84)
        logger.info("--dry-run: ZERO API calls made. Exiting.")
        sys.exit(0)

    # Require explicit confirmation for any paid model
    has_paid_model = any(
        not m.id.endswith(":free") for m in models
    )
    if has_paid_model and not args.confirm_paid:
        logger.error(
            "ABORTED: One or more models may incur API costs (no ':free' suffix).\n"
            "Add --confirm-paid to authorise. Projected cost: ≈$%.4f.\n"
            "Use --dry-run first to verify the plan.",
            projected_cost,
        )
        sys.exit(1)

    logger.info(
        "NOTE: The model and strategy values are recorded as metadata. "
        "The pipeline uses the model configured in the running server. "
        "To switch models, update anxiosense/.env + server/.env and restart both servers."
    )

    # ── Shared API call counter ────────────────────────────────────────────
    api_calls_counter = [0]  # mutable list for pass-by-reference across cells

    # ── Main experiment loop ───────────────────────────────────────────────
    for dataset_name in datasets:
        ds_cfg = cfg.datasets[dataset_name]
        path   = resolve_path(REPO_ROOT, ds_cfg.path)

        logger.info("Loading dataset: %s from %s", dataset_name, path)
        df = load_dataset(path, split_column=ds_cfg.split_column)
        validate_schema(df, [ds_cfg.text_column, ds_cfg.label_column])

        # Use 'sample_id' if present (from cleaned files), else fall back
        if "sample_id" not in df.columns:
            df = df.copy()
            df["sample_id"] = [f"{dataset_name}_{i:05d}" for i in range(len(df))]

        # ── Restrict to the specified split (evaluation must use test only) ──
        n_all = len(df)
        if args.split:
            df = df[df[ds_cfg.split_column] == args.split].reset_index(drop=True)
            logger.info(
                "  Split filter '%s': %d total → %d rows",
                args.split, n_all, len(df),
            )

        # ── Apply pilot ID exclusion list (e.g. prior-stage sample IDs) ──────
        if exclude_ids_set:
            n_before = len(df)
            df = df[~df["sample_id"].isin(exclude_ids_set)].reset_index(drop=True)
            n_excl = n_before - len(df)
            if n_excl:
                logger.info("  Excluded %d sample_id(s) from sampling.", n_excl)

        sampled = sample_dataset(
            df,
            n=sample_size,
            random_state=args.sample_seed,
            stratify_col=ds_cfg.label_column,
        )
        logger.info(
            "  Sampled %d / %d rows (split='%s', seed=%d, stratified by '%s')",
            len(sampled), len(df), args.split or "all", args.sample_seed, ds_cfg.label_column,
        )

        for model_cfg in models:
            for strategy in strategies:
                for run_num in range(1, n_runs + 1):

                    # Stop if global api-call limit reached
                    if (args.max_api_calls is not None and
                            api_calls_counter[0] >= args.max_api_calls):
                        logger.warning(
                            "Global --max-api-calls=%d reached — stopping all cells.",
                            args.max_api_calls,
                        )
                        break

                    model_slug = model_cfg.id.replace("/", "_").replace(":", "_")
                    jsonl_name = f"{dataset_name}_{model_slug}_{strategy}_run{run_num}.jsonl"
                    jsonl_path = raw_dir / jsonl_name

                    logger.info(
                        "==> %s | %s | %s | run %d/%d",
                        dataset_name, model_cfg.name, strategy, run_num, n_runs,
                    )

                    with ResultStore(jsonl_path) as store:
                        stats = run_one_cell(
                            dataset_name=dataset_name,
                            df=sampled,
                            ds_cfg=ds_cfg,
                            model_id=model_cfg.id,
                            strategy=strategy,
                            run_number=run_num,
                            store=store,
                            base_url=base_url,
                            request_delay=request_delay,
                            timeout=timeout,
                            max_api_calls=args.max_api_calls,
                            api_calls_counter=api_calls_counter,
                            split_filter=args.split or "",
                            sample_seed=args.sample_seed,
                        )
                        csv_path = raw_dir / jsonl_name.replace(".jsonl", ".csv")
                        store.export_csv(csv_path)

                    # ── Write per-cell metadata JSON ──────────────────────────
                    live_gt_dist: Counter = Counter()
                    for _, row in sampled.iterrows():
                        try:
                            gt_val = get_ground_truth(dict(row), dataset_name)
                            live_gt_dist[str(gt_val)] += 1
                        except Exception:
                            live_gt_dist["?"] += 1
                    write_cell_metadata(
                        meta_dir=raw_dir.parent / "metadata",
                        dataset=dataset_name,
                        model_id=model_cfg.id,
                        model_slug=model_slug,
                        strategy=strategy,
                        run=run_num,
                        split=args.split or "",
                        sample_seed=args.sample_seed,
                        sample_ids=list(sampled["sample_id"].astype(str)),
                        gt_label_distribution=dict(sorted(live_gt_dist.items())),
                        exclude_ids=sorted(exclude_ids_set),
                        phase="live",
                    )

                    logger.info(
                        "    Completed: %d  Skipped (resume): %d  "
                        "Parse failures: %d  Provider errors: %d  "
                        "Total API calls so far: %d",
                        stats["n_completed"], stats["n_skipped"],
                        stats["n_failed"], stats["n_provider_errors"],
                        api_calls_counter[0],
                    )
                    if stats["latencies"]:
                        avg_ms = sum(stats["latencies"]) / len(stats["latencies"])
                        logger.info("    Avg latency: %.0f ms", avg_ms)

    logger.info(
        "All cells complete. Total API calls made: %d. "
        "Run compute_metrics.py to aggregate results.",
        api_calls_counter[0],
    )


if __name__ == "__main__":
    main()

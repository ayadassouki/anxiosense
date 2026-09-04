"""Orchestration: preflight, dispatch, resume.

Order of operations is the whole point:
  1. verify everything that can be verified without spending money
  2. freeze it into experiment.json
  3. only then dispatch
  4. store the raw attempt BEFORE parsing it
"""
from __future__ import annotations
import argparse, csv, datetime as _dt, json, logging, sys, time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import RUNNER_VERSION, RECORD_SCHEMA_VERSION
from ._reuse import REPO_ROOT
from .client import HttpTransport, TransportResult, probe_server_runtime
from .config import ExperimentConfig, load_config, ConfigError
from .failures import Transport, classify_transport
from .identity import (new_uuid, sha256_text, sha256_obj, git_commit, git_dirty,
                       git_untracked_count,
                       prompt_inventory, prompt_hashes, PromptError)
from .manifest import load_manifest, verify_manifest
from .parse import parse
from .retry import next_action
from .store import RunStore, DuplicateAssessment

log = logging.getLogger("publication_runner")

# The server reports model_actual as "<provider>/<vendor>/<model>" (e.g.
# "openrouter/microsoft/phi-4"). Strip ONLY the provider prefix - splitting on the
# first "/" unconditionally would turn "microsoft/phi-4" into "phi-4" and make every
# model look mismatched.
_PROVIDER_PREFIXES = ("openrouter/", "mistral/", "groq/", "anthropic/", "together/", "ollama/")


def normalise_model_id(model_id: str) -> str:
    for prefix in _PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


class PreflightError(RuntimeError):
    """Anything that must abort BEFORE a single paid dispatch."""


# ── preflight ────────────────────────────────────────────────────────────────

def resolve_server_runtime(cfg: ExperimentConfig, probe=None) -> dict[str, Any]:
    """Read the server's EFFECTIVE Mastra poll cadence and reconcile it with what
    the config declares.

    Poll cadence changes measured latency, and latency is a reported result, so
    it must live in the run record rather than in the shell that started the
    server. Precedence:

      * config declares an expected value -> probe is MANDATORY. A probe failure,
        a missing field, a non-numeric value, or a mismatch is fatal.
      * config declares nothing (every config written before 2026-09-04) -> the
        probe is best-effort: its value is recorded when available and reported
        as unavailable otherwise. Those configs keep their config_sha256 and
        remain comparable with the runs already made.
    """
    expected = cfg.server.mastra_poll_interval_ms
    # run_class: publication makes the probe mandatory. load_config already
    # refuses a publication config that declares no interval, so `expected` is
    # never None here for a publication run - this is belt and braces.
    strict = cfg.run_class == "publication" or expected is not None
    probe = probe or (lambda: probe_server_runtime(cfg.server.base_url))

    try:
        health = probe()
        error = None
    except Exception as exc:                                  # noqa: BLE001
        health, error = None, f"{type(exc).__name__}: {exc}"

    if health is None:
        if strict:
            raise PreflightError(
                f"server.mastra_poll_interval_ms is declared as {expected} but the "
                f"effective value could not be read from {cfg.server.base_url}/api/health "
                f"({error}). Refusing to run: the poll cadence that produces this run's "
                f"latency figures would be unrecorded."
            )
        return {"effective_mastra_poll_interval_ms": None,
                "effective_mastra_poll_max_ms": None,
                "expected_mastra_poll_interval_ms": None,
                "source": "unavailable", "probe_error": error, "verified": False}

    effective = health.get("mastra_poll_interval_ms")
    if strict:
        if effective is None:
            raise PreflightError(
                f"server.mastra_poll_interval_ms is declared as {expected} but "
                f"/api/health reported mastra_poll_interval_ms=null. The server has a "
                f"missing or non-numeric MASTRA_POLL_INTERVAL_MS. Refusing to run."
            )
        if int(effective) != int(expected):
            raise PreflightError(
                f"poll cadence mismatch: config declares "
                f"server.mastra_poll_interval_ms={expected} but the server is running "
                f"{effective}. Restart the server with MASTRA_POLL_INTERVAL_MS={expected}, "
                f"or correct the config. Refusing to run with unrecorded timing settings."
            )

    return {
        "effective_mastra_poll_interval_ms": effective,
        "effective_mastra_poll_max_ms": health.get("mastra_poll_max_ms"),
        "expected_mastra_poll_interval_ms": expected,
        "source": health.get("mastra_poll_interval_source"),
        "probe_error": None,
        "verified": strict,
    }


def preflight(cfg: ExperimentConfig, *, prompts_dir: Path | None = None,
              server_probe=None) -> dict[str, Any]:
    problems: list[str] = []
    frozen: dict[str, Any] = {
        "experiment_id": cfg.experiment_id,
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "runner_version": RUNNER_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "config_sha256": cfg.config_sha256(),
        "run_class": cfg.run_class,          # declared, never inferred
        "git_commit": git_commit(),
        "git_dirty": git_dirty(),                       # TRACKED files only
        "git_untracked_count": git_untracked_count(),   # context; never gates a run
    }

    # models: only 'enabled' may run, and it must be explicit (enforced in config.py)
    enabled = cfg.enabled_models
    disabled = [m.id for m in cfg.models if not m.enabled]
    if not enabled:
        problems.append("no enabled models")
    frozen["models_enabled"] = [asdict(m) for m in enabled]
    frozen["models_disabled"] = disabled

    # prompts: every strategy x agent must load, or abort. No fallback prompt exists here.
    try:
        frozen["prompt_inventory"] = prompt_inventory(list(cfg.strategies), prompts_dir)
    except PromptError as exc:
        problems.append(f"prompt error: {exc}")

    # manifests: hash-verified, ground truth present for every dispatchable id
    frozen["datasets"] = {}
    for d in cfg.datasets:
        mp = REPO_ROOT / d.manifest if not Path(d.manifest).is_absolute() else Path(d.manifest)
        if not mp.exists():
            problems.append(f"manifest not found: {mp}")
            continue
        man = load_manifest(mp)
        for p in verify_manifest(man):
            problems.append(f"[{d.name}] {p}")
        if man["dataset"] != d.name:
            problems.append(f"manifest dataset {man['dataset']!r} != config {d.name!r}")
        frozen["datasets"][d.name] = {
            "manifest_path": str(d.manifest),
            "manifest_sha256": man["manifest_sha256"],
            "processed_sha256": man["processed"]["sha256"],
            "official_split": man["official_split"],
            "n_dispatchable": man["n_dispatchable"],
            "n_excluded": man["n_excluded"],
            "class_distribution": man["class_distribution"],
            "majority_baseline": man["majority_baseline"],
        }

    frozen["grid"] = {
        "datasets": [d.name for d in cfg.datasets],
        "models": [m.id for m in enabled],
        "strategies": list(cfg.strategies),
        "runs": cfg.runs,
        "run_start": cfg.run_start,
        "cells": len(cfg.datasets) * len(enabled) * len(cfg.strategies) * cfg.runs,
    }
    frozen["retry_policy"] = asdict(cfg.retry)
    frozen["server"] = asdict(cfg.server)
    # Frozen BEFORE the problems check so a mismatch is reported alongside any
    # other preflight failure rather than masking it.
    frozen["server_runtime"] = resolve_server_runtime(cfg, server_probe)

    if problems:
        raise PreflightError("preflight failed:\n  - " + "\n  - ".join(problems))
    return frozen


def load_texts(manifest: dict) -> dict[str, str]:
    """Load the dispatchable texts and verify each against the manifest hash."""
    path = REPO_ROOT / manifest["processed"]["file"]
    col = manifest["processed"]["text_column"]
    wanted = set(manifest["included_sample_ids"])
    texts: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = row.get("sample_id")
            if sid in wanted:
                texts[sid] = row[col]
    missing = wanted - set(texts)
    if missing:
        raise PreflightError(f"{len(missing)} manifest id(s) absent from the dataset file")
    drift = [s for s, t in texts.items() if sha256_text(t) != manifest["text_sha256"][s]]
    if drift:
        raise PreflightError(
            f"{len(drift)} text(s) changed since the manifest was frozen, e.g. {drift[:3]}")
    return texts


# ── dispatch ─────────────────────────────────────────────────────────────────

def _attempt_record(*, cfg, frozen, dataset, manifest, sample_id, text, gt,
                    model, strategy, run, assessment_uuid, attempt_number,
                    result: TransportResult, outcome: Transport, detail) -> dict:
    body = result.body or {}
    meta = (body.get("metadata") or {})
    report = (body.get("report") or {})
    model_actual = meta.get("model_actual")
    normalised_actual = normalise_model_id(model_actual) if model_actual else None
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "record_type": "attempt",
        "attempt_uuid": new_uuid(),
        "assessment_uuid": assessment_uuid,
        "experiment_id": cfg.experiment_id,
        "cell_id": f"{dataset}|{model.id}|{strategy}|run{run}",
        "attempt_number": attempt_number,
        "run": run,

        "dataset": dataset,
        "dataset_manifest_sha256": manifest["manifest_sha256"],
        "dataset_source_sha256": manifest["processed"]["sha256"],
        "official_split": manifest["official_split"],
        "sample_id": sample_id,
        "text_sha256": sha256_text(text),
        "text_column": manifest["processed"]["text_column"],
        "input_text": text,
        "ground_truth": gt,

        "model_requested": model.id,
        "model_actual": model_actual,
        "provider_requested": model.provider,
        "provider_actual": meta.get("provider_actual"),
        "upstream_provider": meta.get("upstream_provider"),
        "upstream_providers_all": meta.get("upstream_providers"),
        "pin_provider": model.pin_provider,
        "model_mismatch": bool(model_actual) and normalised_actual != model.id,

        "strategy": strategy,
        "strategy_actual": meta.get("strategy_used"),
        "prompt_set_sha256": frozen["prompt_inventory"]["prompt_set_sha256"],
        "prompt_sha256": frozen["prompt_inventory"]["strategies"][strategy],

        "raw": {
            "emotion_agent_raw": body.get("emotion_agent_raw"),
            "referral_agent_raw": body.get("referral_agent_raw"),
            "symptom_agent_raw": body.get("symptom_agent_raw"),
            "context_agent_raw": body.get("context_agent_raw"),
            "final_report": report.get("finalReport"),
            "referral_level_reported": report.get("referralLevel"),
            "referral_unreadable": body.get("referral_unreadable"),
            "concern_pattern": report.get("concernPattern"),
        },
        "response_body": result.body,
        "response_body_sha256": sha256_text(result.raw_body_text) if result.raw_body_text else None,

        "http_status": result.http_status,
        "transport_error_kind": result.error_kind,
        "transport_error_detail": result.error_detail,
        "mastra_run_id": body.get("mastra_run_id"),
        "latency_ms": result.latency_ms,
        "server_latency_ms": meta.get("latency_ms"),
        "token_usage": meta.get("token_usage"),
        "quality_flags": meta.get("quality_flags"),
        "safety_override": meta.get("safety_override"),

        "outcome_class": outcome.value,
        "outcome_detail": detail,
        "retryable": outcome is Transport.INFRA_TRANSIENT,

        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "runner_version": RUNNER_VERSION,
        "git_commit": frozen["git_commit"],
        "config_sha256": frozen["config_sha256"],
        # Timing provenance: the poll cadence in force when this latency was measured.
        "mastra_poll_interval_ms": frozen["server_runtime"]["effective_mastra_poll_interval_ms"],
    }


def run_experiment(cfg: ExperimentConfig, *, transport=None, resume: bool = False,
                   limit: int | None = None, retry_exhausted: bool = False,
                   prompts_dir: Path | None = None, sleep=time.sleep,
                   server_probe=None) -> dict:
    invocation_started_utc = _dt.datetime.now(_dt.timezone.utc).isoformat()
    frozen = preflight(cfg, prompts_dir=prompts_dir, server_probe=server_probe)

    run_dir = (REPO_ROOT / cfg.output_root / cfg.experiment_id)
    if run_dir.exists() and not resume:
        raise PreflightError(
            f"{run_dir} already exists. Pass --resume to continue it, or choose a new "
            f"experiment_id. The runner never appends to a run it was not told to resume."
        )
    store = RunStore(run_dir)
    store.write_json("experiment.json", frozen)

    manifests = {d.name: load_manifest(
        REPO_ROOT / d.manifest if not Path(d.manifest).is_absolute() else Path(d.manifest))
        for d in cfg.datasets}
    texts = {name: load_texts(m) for name, m in manifests.items()}

    transport = transport or HttpTransport(
        cfg.server.base_url, cfg.server.evaluate_endpoint, cfg.server.timeout_seconds)

    stats = {"dispatched": 0, "skipped_resume": 0, "attempts": 0,
             "outcomes": {}, "model_mismatch": 0}

    for d in cfg.datasets:
        manifest = manifests[d.name]
        ids = manifest["included_sample_ids"]
        if limit is not None:
            ids = ids[:limit]
        for model in cfg.enabled_models:
            for strategy in cfg.strategies:
                for run in range(cfg.run_start, cfg.run_start + cfg.runs):
                    cell_id = f"{d.name}|{model.id}|{strategy}|run{run}"
                    for sample_id in ids:
                        prior = store.terminal_record(cell_id, sample_id)
                        superseding = False
                        if prior is not None:
                            if not (retry_exhausted and
                                    prior.get("final_outcome_class") == "RETRIES_EXHAUSTED"):
                                stats["skipped_resume"] += 1
                                continue
                            superseding = True
                        text = texts[d.name][sample_id]
                        gt = manifest["ground_truth"][sample_id]

                        assessment_uuid = new_uuid()
                        attempt_number = 0
                        history: list[dict] = []
                        attempt_uuids: list[str] = []
                        terminal_uuid = None
                        final_outcome = None

                        while True:
                            attempt_number += 1
                            if hasattr(transport, "set_sample"):
                                transport.set_sample(sample_id)
                            result = transport.post_evaluate(
                                text=text, model=model.id, strategy=strategy)
                            outcome, detail = classify_transport(
                                error_kind=result.error_kind,
                                http_status=result.http_status,
                                body=result.body)

                            rec = _attempt_record(
                                cfg=cfg, frozen=frozen, dataset=d.name, manifest=manifest,
                                sample_id=sample_id, text=text, gt=gt, model=model,
                                strategy=strategy, run=run,
                                assessment_uuid=assessment_uuid,
                                attempt_number=attempt_number,
                                result=result, outcome=outcome, detail=detail)

                            # Model/provider identity: a wrong model invalidates everything
                            # that follows, so it is terminal for the assessment and fatal
                            # for the experiment.
                            if rec["model_mismatch"]:
                                stats["model_mismatch"] += 1
                                rec["outcome_class"] = Transport.INFRA_TERMINAL.value
                                rec["outcome_detail"] = (
                                    f"model_mismatch requested={model.id} "
                                    f"actual={rec['model_actual']}")
                                rec["retryable"] = False
                                outcome = Transport.INFRA_TERMINAL

                            # STORE THE RAW ATTEMPT BEFORE ANY PARSING OR SCORING
                            store.append_attempt(rec)
                            stats["attempts"] += 1
                            attempt_uuids.append(rec["attempt_uuid"])

                            decision = next_action(cfg.retry, outcome, attempt_number)
                            history.append({
                                "attempt": attempt_number,
                                "outcome": outcome.value,
                                "detail": rec["outcome_detail"],
                                "http_status": result.http_status,
                                "retry": decision.retry,
                                "wait_ms": decision.wait_ms,
                                "reason": decision.reason,
                            })
                            if not decision.retry:
                                terminal_uuid = rec["attempt_uuid"]
                                final_outcome = (
                                    "RETRIES_EXHAUSTED"
                                    if decision.reason == "retries_exhausted"
                                    else outcome.value)
                                break
                            sleep(decision.wait_ms / 1000.0)

                        if rec["model_mismatch"]:
                            store.close_assessment({
                                "record_type": "assessment", "assessment_uuid": assessment_uuid,
                                "experiment_id": cfg.experiment_id, "cell_id": cell_id,
                                "dataset": d.name, "sample_id": sample_id,
                                "attempts": attempt_uuids, "attempt_count": attempt_number,
                                "terminal_attempt_uuid": terminal_uuid,
                                "final_outcome_class": final_outcome,
                                "retry_history": history,
                            })
                            store.close()
                            raise PreflightError(
                                f"ABORTED: the server served {rec['model_actual']!r} when "
                                f"{model.id!r} was requested. Every subsequent record would be "
                                f"mislabelled. Fix MODEL_PROVIDER/MODEL_ID and restart Mastra."
                            )

                        index_record = {
                            "record_type": "assessment",
                            "assessment_uuid": assessment_uuid,
                            "experiment_id": cfg.experiment_id,
                            "cell_id": cell_id,
                            "dataset": d.name,
                            "sample_id": sample_id,
                            "attempts": attempt_uuids,
                            "attempt_count": attempt_number,
                            "terminal_attempt_uuid": terminal_uuid,
                            "final_outcome_class": final_outcome,
                            "retry_history": history,
                        }
                        try:
                            store.close_assessment(index_record, allow_supersede=superseding)
                        except DuplicateAssessment:
                            store.close()
                            raise
                        stats["dispatched"] += 1
                        stats["outcomes"][final_outcome] = \
                            stats["outcomes"].get(final_outcome, 0) + 1
                        if cfg.server.request_delay_seconds:
                            sleep(cfg.server.request_delay_seconds)

    # Record THIS invocation append-only, then rewrite dispatch_stats.json as a
    # derived view over all invocations. A resume can no longer overwrite or
    # misrepresent what the original dispatch reported.
    prior = store.read_invocations()
    store.append_invocation({
        "record_type": "invocation",
        "invocation_uuid": new_uuid(),
        "invocation_number": len(prior) + 1,
        "mode": ("retry_exhausted" if retry_exhausted
                 else "resume" if resume else "initial"),
        "resume": bool(resume),
        "retry_exhausted": bool(retry_exhausted),
        "limit": limit,
        "started_utc": invocation_started_utc,
        "finished_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "runner_version": RUNNER_VERSION,
        "git_commit": frozen["git_commit"],
        "git_dirty": frozen["git_dirty"],
        "config_sha256": frozen["config_sha256"],
        "stats": stats,
    })
    summary = store.dispatch_summary()
    store.write_json("summaries/dispatch_stats.json", summary)
    store.close()
    return {"run_dir": str(run_dir), "frozen": frozen, "stats": stats,
            "dispatch_summary": summary}


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AnxioSense publication experiment runner")
    ap.add_argument("--config", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--retry-exhausted", action="store_true",
                    help="re-dispatch assessments whose retries were exhausted")
    ap.add_argument("--limit", type=int, help="dispatch only the first N ids per cell")
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    if args.preflight_only:
        try:
            frozen = preflight(cfg)
        except PreflightError as exc:
            print(f"PREFLIGHT FAILED:\n{exc}", file=sys.stderr)
            return 1
        print(json.dumps(frozen, indent=2))
        return 0

    try:
        out = run_experiment(cfg, resume=args.resume, limit=args.limit,
                             retry_exhausted=args.retry_exhausted)
    except PreflightError as exc:
        print(f"ABORTED:\n{exc}", file=sys.stderr)
        return 1
    print(json.dumps(out["stats"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

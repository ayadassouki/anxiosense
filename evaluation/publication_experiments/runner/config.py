"""Experiment configuration: typed, validated, hashed. Fails loudly."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

from ._reuse import REPO_ROOT
from .identity import sha256_obj
from .retry import RetryPolicy


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    provider: str
    enabled: bool                 # REQUIRED - no default. A comment cannot disable a model.
    pin_provider: str | None = None
    pin_quantization: str | None = None


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    manifest: str                 # path to a frozen manifest JSON


#: The declared purpose of a run. NEVER inferred from the experiment_id, the
#: config path, or a CLI flag - a run's class is intent, and intent is declared
#: in the artifact that carries provenance.
RUN_CLASSES: tuple[str, ...] = ("publication", "benchmark", "smoke", "mock")
DEFAULT_RUN_CLASS = "benchmark"

#: HASH-COMPATIBILITY RULE (single, explicit, tested).
#:
#: Keys introduced after 2026-09-04 are included in config_sha256 ONLY when set
#: to a non-default value. Every config written before that date therefore
#: hashes exactly as it did then, and the config_sha256 recorded by smoke_001,
#: bench_002, bench_003, bench_004 and bench_005 still reproduces from its own
#: unmodified config file.
#:
#: Setting a key explicitly to its default hashes identically to omitting it -
#: the hash tracks the experiment, not the YAML spelling.
#:
#: Add a new post-2026-09-04 key HERE rather than special-casing it in
#: config_sha256(). test_hash_compat_defaults_match_load_config proves each
#: entry's default is what load_config actually produces when the key is absent.
HASH_COMPAT_DEFAULTS: dict[tuple[str, ...], Any] = {
    ("run_class",): DEFAULT_RUN_CLASS,
    ("server", "mastra_poll_interval_ms"): None,
    ("halt_after_consecutive_infra_failures",): None,
}


def _strip_hash_compat(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop post-2026-09-04 keys that hold their default value."""
    out = json.loads(json.dumps(payload, sort_keys=True, default=str))
    for path, default in HASH_COMPAT_DEFAULTS.items():
        node = out
        for part in path[:-1]:
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, dict) and node.get(path[-1], default) == default:
            node.pop(path[-1], None)
    return out


@dataclass(frozen=True)
class ServerSpec:
    base_url: str
    evaluate_endpoint: str
    timeout_seconds: int
    request_delay_seconds: float
    #: The Mastra poll cadence this experiment EXPECTS the server to be running.
    #: Optional, and None in every config written before 2026-09-04 - those keep
    #: their config_sha256 and stay comparable with the runs already made.
    #: When declared, preflight probes /api/health and ABORTS if the effective
    #: server value cannot be obtained or does not match. Publication configs
    #: MUST declare it: poll cadence changes measured latency, and latency is a
    #: reported result.
    mastra_poll_interval_ms: int | None = None


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    models: list[ModelSpec]
    strategies: list[str]
    datasets: list[DatasetSpec]
    runs: int
    run_start: int
    retry: RetryPolicy
    server: ServerSpec
    output_root: str
    #: Declared, never inferred. See RUN_CLASSES.
    run_class: str = DEFAULT_RUN_CLASS
    #: FAILURE-STORM CIRCUIT BREAKER. Stop dispatching after this many
    #: CONSECUTIVE assessment-level terminal INFRASTRUCTURE outcomes
    #: (INFRA_TERMINAL or RETRIES_EXHAUSTED). None disables it, which is the
    #: default and the behaviour of every config written before 2026-09-04.
    #:
    #: It can only ever STOP dispatch. It never changes which items are
    #: dispatched, never alters a record already written, and never reacts to
    #: model behaviour: MODEL_BEHAVIOUR, malformed responses and
    #: SAFETY_INTERCEPT do not count, and any non-infrastructure terminal
    #: outcome resets the counter to zero. Reacting to model output would make
    #: the breaker a scientific confound.
    halt_after_consecutive_infra_failures: int | None = None
    prompts_dir: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def enabled_models(self) -> list[ModelSpec]:
        """The ONLY accessor the runner may use to obtain models."""
        return [m for m in self.models if m.enabled]

    def config_sha256(self) -> str:
        payload = {
            "experiment_id": self.experiment_id,
            "models": [asdict(m) for m in self.models],
            "strategies": list(self.strategies),
            "datasets": [asdict(d) for d in self.datasets],
            "runs": self.runs, "run_start": self.run_start,
            "retry": asdict(self.retry),
            "server": asdict(self.server),
            "run_class": self.run_class,
            "halt_after_consecutive_infra_failures":
                self.halt_after_consecutive_infra_failures,
        }
        return sha256_obj(_strip_hash_compat(payload))


def load_config(path: str | Path) -> ExperimentConfig:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if not p.exists():
        raise ConfigError(f"config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    for key in ("experiment_id", "models", "strategies", "datasets", "runs", "server", "output_root"):
        if key not in raw:
            raise ConfigError(f"config is missing required key {key!r}")

    models: list[ModelSpec] = []
    seen_ids: set[str] = set()
    for i, m in enumerate(raw["models"]):
        for key in ("id", "name", "provider", "enabled"):
            if key not in m:
                raise ConfigError(
                    f"models[{i}] is missing required key {key!r}. "
                    f"'enabled' has no default: every model must state it explicitly."
                )
        if not isinstance(m["enabled"], bool):
            raise ConfigError(f"models[{i}].enabled must be a boolean, got {m['enabled']!r}")
        if m["id"] in seen_ids:
            raise ConfigError(f"duplicate model id {m['id']!r}")
        seen_ids.add(m["id"])
        models.append(ModelSpec(
            id=m["id"], name=m["name"], provider=m["provider"], enabled=m["enabled"],
            pin_provider=m.get("pin_provider"), pin_quantization=m.get("pin_quantization"),
        ))
    if not [m for m in models if m.enabled]:
        raise ConfigError("no enabled models in config")

    strategies = list(raw["strategies"])
    if not strategies or len(set(strategies)) != len(strategies):
        raise ConfigError(f"strategies must be a non-empty unique list, got {strategies!r}")

    datasets = []
    for i, d in enumerate(raw["datasets"]):
        for key in ("name", "manifest"):
            if key not in d:
                raise ConfigError(f"datasets[{i}] is missing {key!r}")
        datasets.append(DatasetSpec(name=d["name"], manifest=d["manifest"]))

    r = raw.get("retry", {})
    retry = RetryPolicy(
        max_attempts=int(r.get("max_attempts", 3)),
        backoff_base_ms=int(r.get("backoff_base_ms", 2000)),
        backoff_factor=int(r.get("backoff_factor", 2)),
        backoff_cap_ms=int(r.get("backoff_cap_ms", 30000)),
    )
    if retry.max_attempts < 1:
        raise ConfigError("retry.max_attempts must be >= 1")

    s = raw["server"]
    server = ServerSpec(
        base_url=s["base_url"],
        evaluate_endpoint=s.get("evaluate_endpoint", "/api/workflow/evaluate"),
        timeout_seconds=int(s.get("timeout_seconds", 180)),
        request_delay_seconds=float(s.get("request_delay_seconds", 0.0)),
        mastra_poll_interval_ms=(
            int(s["mastra_poll_interval_ms"])
            if s.get("mastra_poll_interval_ms") is not None else None),
    )
    if (server.mastra_poll_interval_ms is not None
            and server.mastra_poll_interval_ms <= 0):
        raise ConfigError(
            f"server.mastra_poll_interval_ms must be a positive integer, got "
            f"{server.mastra_poll_interval_ms!r}")

    halt_after = raw.get("halt_after_consecutive_infra_failures")
    if halt_after is not None:
        halt_after = int(halt_after)
        if halt_after < 1:
            raise ConfigError(
                f"halt_after_consecutive_infra_failures must be >= 1 or null, "
                f"got {halt_after!r}")

    run_class = str(raw.get("run_class", DEFAULT_RUN_CLASS))
    if run_class not in RUN_CLASSES:
        raise ConfigError(
            f"run_class must be one of {list(RUN_CLASSES)}, got {run_class!r}")
    if run_class == "publication" and server.mastra_poll_interval_ms is None:
        raise ConfigError(
            "run_class: publication requires server.mastra_poll_interval_ms to be "
            "declared explicitly. Poll cadence changes measured latency, and latency "
            "is a reported result, so it must be frozen into the run record and "
            "verified against the live server before dispatch."
        )
    # The old harness abandoned runs the server was still executing and billing.
    poll_budget = int(s.get("server_poll_budget_seconds", 150))
    if server.timeout_seconds < poll_budget:
        raise ConfigError(
            f"server.timeout_seconds ({server.timeout_seconds}) is below the server's own "
            f"poll budget ({poll_budget}s): the client would abandon runs that are still "
            f"executing and still being billed."
        )

    return ExperimentConfig(
        experiment_id=str(raw["experiment_id"]),
        models=models, strategies=strategies, datasets=datasets,
        runs=int(raw["runs"]), run_start=int(raw.get("run_start", 1)),
        retry=retry, server=server, output_root=str(raw["output_root"]),
        run_class=run_class,
        halt_after_consecutive_infra_failures=halt_after,
        prompts_dir=raw.get("prompts_dir"), raw=raw,
    )

"""Experiment configuration: typed, validated, hashed. Fails loudly."""
from __future__ import annotations
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


@dataclass(frozen=True)
class ServerSpec:
    base_url: str
    evaluate_endpoint: str
    timeout_seconds: int
    request_delay_seconds: float


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
        }
        return sha256_obj(payload)


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
        prompts_dir=raw.get("prompts_dir"), raw=raw,
    )

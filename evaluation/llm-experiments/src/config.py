"""
src/config.py
Load experiment_config.yaml into dataclasses.
API keys are read from environment variables ONLY — never stored in config files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DatasetConfig:
    path: str
    text_column: str
    label_column: str
    task_type: str          # "binary" | "multiclass" | "multilabel"
    format: str             # "csv" | "jsonl"
    split_column: Optional[str] = None
    description: str = ""


@dataclass
class ModelConfig:
    id: str
    name: str
    provider: str                       # "openrouter" | "mistral" | "groq"
    # Decoding parameters. Under the provider-default methodology (2026-08-04)
    # all three are None and are NOT sent to the API — see experiment_config.yaml.
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None
    # Upstream inference provider to pin for this model, e.g. "DeepInfra".
    # None means no pin (OpenRouter load-balances — reintroduces the confound).
    pin_provider: Optional[str] = None
    # Precision filter sent with the routing directive, e.g. "fp4". Set only where
    # the pinned provider exposes more than one endpoint. A REQUEST DIRECTIVE, not
    # an observed value — enforced by allow_fallbacks:false failing the request.
    pin_quantization: Optional[str] = None
    # Precision reported by the endpoints survey, recorded for the write-up only.
    observed_quantization: Optional[str] = None


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_base: int = 2
    timeout_seconds: int = 30


@dataclass
class ServerConfig:
    """Connection parameters for the AnxioSense Express server."""
    base_url: str = "http://localhost:3001"
    evaluate_endpoint: str = "/api/workflow/evaluate"
    request_delay_seconds: float = 1.0
    timeout_seconds: int = 90


@dataclass
class ExperimentConfig:
    datasets: Dict[str, DatasetConfig]
    models: List[ModelConfig]
    strategies: List[str]
    runs: int
    sample_size: int
    output_dir: str
    log_dir: str
    prompts_dir: str
    primary_agent: str
    retry: RetryConfig
    server: Optional[ServerConfig] = None

    # API keys (populated from environment at load time)
    openrouter_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(config_path) -> ExperimentConfig:
    """
    Load experiment_config.yaml.  API keys are read from environment variables.

    Required env vars (set only those whose provider you use):
        OPENROUTER_API_KEY
        MISTRAL_API_KEY
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open() as fh:
        raw = yaml.safe_load(fh)

    datasets = {}
    for name, ds in raw["datasets"].items():
        datasets[name] = DatasetConfig(
            path=ds["path"],
            text_column=ds["text_column"],
            label_column=ds["label_column"],
            task_type=ds["task_type"],
            format=ds.get("format", "csv"),
            split_column=ds.get("split_column"),
            description=ds.get("description", ""),
        )

    models = [
        ModelConfig(
            id=m["id"],
            name=m["name"],
            provider=m["provider"],
            temperature=m.get("temperature"),
            max_tokens=m.get("max_tokens"),
            seed=m.get("seed"),
            pin_provider=m.get("pin_provider"),
            pin_quantization=m.get("pin_quantization"),
            observed_quantization=m.get("observed_quantization"),
        )
        for m in raw["models"]
    ]

    retry_raw = raw.get("retry", {})
    retry = RetryConfig(
        max_attempts=retry_raw.get("max_attempts", 3),
        backoff_base=retry_raw.get("backoff_base", 2),
        timeout_seconds=retry_raw.get("timeout_seconds", 30),
    )

    # Server config (optional — defaults if block is absent)
    server_raw = raw.get("server", {})
    server = ServerConfig(
        base_url=server_raw.get("base_url", "http://localhost:3001"),
        evaluate_endpoint=server_raw.get("evaluate_endpoint", "/api/workflow/evaluate"),
        request_delay_seconds=float(server_raw.get("request_delay_seconds", 1.0)),
        timeout_seconds=int(server_raw.get("timeout_seconds", 90)),
    )

    return ExperimentConfig(
        datasets=datasets,
        models=models,
        strategies=raw["strategies"],
        runs=raw["runs"],
        sample_size=raw["sample_size"],
        output_dir=raw["output_dir"],
        log_dir=raw["log_dir"],
        prompts_dir=raw.get("prompts_dir", "prompts"),
        primary_agent=raw.get("primary_agent", "emotion"),
        retry=retry,
        server=server,
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
        mistral_api_key=os.environ.get("MISTRAL_API_KEY"),
    )


def resolve_path(repo_root: Path, relative: str) -> Path:
    """Resolve a config-relative path against the repository root."""
    return (repo_root / relative).resolve()

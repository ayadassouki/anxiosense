"""Hashes, ids and provenance. Everything here is deterministic except uuid4()."""
from __future__ import annotations
import hashlib, json, re, subprocess, uuid
from pathlib import Path
from typing import Any

from ._reuse import REPO_ROOT

# Mirrors extractFencedText() in src/mastra/utils/prompt-strategy-loader.ts:
# the loader sends ONLY the ```text fenced block, so only that is hashed.
_FENCE = re.compile(r"```text\s*\n(.*?)\n```", re.DOTALL)

AGENTS = ("emotion", "symptom", "context", "referral", "report")


def new_uuid() -> str:
    return str(uuid.uuid4())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_obj(obj: Any) -> str:
    """Stable hash of a JSON-serialisable object (sorted keys, no whitespace drift)."""
    return sha256_text(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str))


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def git_dirty(repo: str | Path = REPO_ROOT) -> bool:
    """True iff a TRACKED file differs from HEAD (staged or unstaged).

    Untracked files are deliberately excluded: the repository intentionally
    carries untracked artefacts (historical archives, quarantine folders, the
    stale outputs tree) that say nothing about whether the committed code and
    data used for a run match HEAD. Counting them made every run record
    git_dirty=true and destroyed the signal. Use git_untracked_count() if the
    presence of untracked files is itself of interest.

    Fails closed: if git cannot answer, report dirty.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return True
        return bool(out.stdout.strip())
    except Exception:
        return True


def git_untracked_count(repo: str | Path = REPO_ROOT) -> int | None:
    """Number of untracked paths git reports, or None if git cannot answer.

    Recorded alongside git_dirty purely as provenance context. It never
    influences git_dirty and never gates a run.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain",
             "--untracked-files=normal"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
        return sum(1 for ln in out.stdout.splitlines() if ln.startswith("??"))
    except Exception:
        return None


class PromptError(RuntimeError):
    """A prompt file is missing or has no ```text block. Always fatal."""


def prompt_path(agent: str, strategy: str, prompts_dir: Path | None = None) -> Path:
    base = prompts_dir or (REPO_ROOT / "prompts")
    return base / agent / f"{strategy}.md"


def load_prompt_text(agent: str, strategy: str, prompts_dir: Path | None = None) -> str:
    """Return the fenced prompt body, or raise. NEVER falls back to another prompt."""
    p = prompt_path(agent, strategy, prompts_dir)
    if not p.exists():
        raise PromptError(f"missing prompt file: {p}")
    m = _FENCE.search(p.read_text(encoding="utf-8"))
    if not m:
        raise PromptError(f"no ```text block in {p}")
    body = m.group(1).strip()
    if not body:
        raise PromptError(f"empty ```text block in {p}")
    return body


def prompt_hashes(strategy: str, prompts_dir: Path | None = None) -> dict[str, str]:
    """SHA-256 of every agent prompt for one strategy. Raises on any missing prompt."""
    return {a: sha256_text(load_prompt_text(a, strategy, prompts_dir)) for a in AGENTS}


def prompt_inventory(strategies: list[str], prompts_dir: Path | None = None) -> dict:
    """Full frozen prompt set: per strategy, per agent hash + byte length."""
    inv: dict[str, Any] = {"agents": list(AGENTS), "strategies": {}}
    for s in strategies:
        inv["strategies"][s] = {
            a: {"sha256": sha256_text(t), "chars": len(t)}
            for a, t in ((a, load_prompt_text(a, s, prompts_dir)) for a in AGENTS)
        }
    inv["prompt_set_sha256"] = sha256_obj(inv["strategies"])
    return inv

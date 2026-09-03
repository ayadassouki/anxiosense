"""Frozen dataset manifest.

Membership and ground truth are decided HERE, before any dispatch, from the
dataset row alone. The dispatch loop reads ground truth out of the manifest and
never calls a label mapper, so no model result can influence either.

Nothing about scope is hardcoded: the split, the exclusion rules and the source
file all come from the caller. 324 / 715 / 2627 appear nowhere in this module.
"""
from __future__ import annotations
import csv, datetime as _dt, sys
from collections import Counter
from pathlib import Path
from typing import Any

from ._reuse import REPO_ROOT, GROUND_TRUTH_MAPPERS, LabelMappingError
from .identity import sha256_file, sha256_obj, sha256_text

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

MANIFEST_SCHEMA_VERSION = "1.0.0"


class ManifestError(RuntimeError):
    pass


def build_manifest(
    *,
    dataset: str,
    processed_csv: str | Path,
    split: str,
    text_column: str,
    min_chars: int | None,
    source_file: str | Path | None = None,
    source_revision: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build a frozen manifest. Raises BEFORE producing anything if a label cannot map."""
    if dataset not in GROUND_TRUTH_MAPPERS:
        raise ManifestError(f"unknown dataset {dataset!r}")
    label_col, mapper = GROUND_TRUTH_MAPPERS[dataset]

    path = Path(processed_csv)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise ManifestError(f"processed dataset not found: {path}")

    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("split") == split]
    if not rows:
        raise ManifestError(f"no rows with split=={split!r} in {path}")

    for col in (text_column, label_col, "sample_id"):
        if col not in rows[0]:
            raise ManifestError(f"column {col!r} missing from {path}")

    # Ground truth for EVERY row, before anything else. One failure aborts.
    ground_truth: dict[str, Any] = {}
    errors: list[str] = []
    for r in rows:
        try:
            ground_truth[r["sample_id"]] = mapper(r[label_col])
        except LabelMappingError as exc:
            errors.append(f"{r['sample_id']}: {exc}")
    if errors:
        raise ManifestError(
            f"{len(errors)} ground-truth mapping failure(s); refusing to build a manifest. "
            f"First 5: {errors[:5]}"
        )

    included, excluded = [], []
    for r in rows:
        text = (r[text_column] or "").strip()
        if min_chars is not None and len(text) < min_chars:
            excluded.append({
                "sample_id": r["sample_id"],
                "reason": f"below_min_chars:{min_chars}",
                "text_len": len(text),
                "ground_truth": ground_truth[r["sample_id"]],
            })
        else:
            included.append(r["sample_id"])

    included.sort()
    dist = Counter(str(ground_truth[s]) for s in included)
    n = len(included)
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "dataset": dataset,
        "notes": notes,
        "source": {
            "file": str(source_file) if source_file else None,
            "revision": source_revision,
            "sha256": sha256_file(REPO_ROOT / source_file) if source_file else None,
        },
        "processed": {
            "file": str(Path(processed_csv)),
            "sha256": sha256_file(path),
            "text_column": text_column,
            "label_column": label_col,
        },
        "official_split": split,
        "rows_in_split": len(rows),
        "exclusion_rules": [
            {"rule": "min_chars", "value": min_chars,
             "label_blind": True,
             "rationale": "server /evaluate rejects shorter input with HTTP 400"}
        ] if min_chars is not None else [],
        "included_sample_ids": included,
        "excluded_samples": excluded,
        "n_dispatchable": n,
        "n_excluded": len(excluded),
        "ground_truth": {s: ground_truth[s] for s in included},
        "text_sha256": {},   # filled below
        "class_distribution": dict(dist),
        "majority_class": dist.most_common(1)[0][0] if n else None,
        "majority_baseline": round(dist.most_common(1)[0][1] / n, 6) if n else None,
    }
    by_id = {r["sample_id"]: r for r in rows}
    manifest["text_sha256"] = {s: sha256_text(by_id[s][text_column]) for s in included}
    manifest["manifest_sha256"] = sha256_obj(
        {k: v for k, v in manifest.items() if k != "created_utc"}
    )
    return manifest


def verify_manifest(manifest: dict) -> list[str]:
    """Re-check a manifest against the files on disk. Returns a list of problems."""
    problems: list[str] = []
    expect = manifest.get("manifest_sha256")
    recomputed = sha256_obj(
        {k: v for k, v in manifest.items()
         if k not in ("created_utc", "manifest_sha256")}
    )
    if expect != recomputed:
        problems.append("manifest self-hash mismatch (the manifest file was edited)")

    p = REPO_ROOT / manifest["processed"]["file"]
    if not p.exists():
        problems.append(f"processed dataset missing: {p}")
    elif sha256_file(p) != manifest["processed"]["sha256"]:
        problems.append(f"processed dataset CHANGED since the manifest was frozen: {p}")

    ids = manifest["included_sample_ids"]
    if len(ids) != len(set(ids)):
        problems.append("duplicate sample_id in included_sample_ids")
    if len(ids) != manifest["n_dispatchable"]:
        problems.append("n_dispatchable does not match included_sample_ids")
    missing_gt = [s for s in ids if s not in manifest["ground_truth"]]
    if missing_gt:
        problems.append(f"{len(missing_gt)} included id(s) have no ground truth")
    return problems


def load_manifest(path: str | Path) -> dict:
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))

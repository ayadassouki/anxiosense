#!/usr/bin/env python3
"""
evaluation/datasets/scripts/verify_preprocessing.py

Verification script for the preprocessing pipeline.

Asserts:
    source_rows == processed_rows + excluded_rows

for every dataset.  Also verifies:
  - Official test split rows are fully preserved (no test rows excluded).
  - Every excluded row has a logged reason in exclusion_log.json.
  - Every logged exclusion corresponds to a row absent from the processed file.
  - processed_rows + excluded_rows == source_rows (exact, no off-by-one).
  - Processed files exist and are non-empty.
  - sample_id values are unique within each processed file.

The script exits with code 0 if all assertions pass, 1 if any fail.

Usage (from repo root):
    python evaluation/datasets/scripts/verify_preprocessing.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
RAW_DREAD   = REPO_ROOT / "evaluation" / "datasets" / "dreaddit" / "dreaddit_anxiety_subset.csv"
RAW_GE      = REPO_ROOT / "evaluation" / "datasets" / "goemotions" / "goemotions_anxiosense_single.csv"
OUT_DIR     = REPO_ROOT / "evaluation" / "datasets" / "processed"
CLEAN_DREAD = OUT_DIR / "dreaddit_clean.csv"
CLEAN_GE    = OUT_DIR / "goemotions_clean.csv"
EXCL_LOG    = OUT_DIR / "exclusion_log.json"
REPORT      = OUT_DIR / "preprocessing_report.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"  OK: {msg}")


def verify_dataset(
    dataset_name: str,
    raw_path: Path,
    clean_path: Path,
    exclusion_log: dict,
    report: dict,
) -> None:
    import pandas as pd

    print(f"\n── Verifying {dataset_name} ──────────────────────────────────────────────")

    # ── Files exist ────────────────────────────────────────────────────────────
    if not clean_path.exists():
        fail(f"Processed file not found: {clean_path}")
    ok(f"Processed file exists: {clean_path.name}")

    # ── Load raw and processed ─────────────────────────────────────────────────
    raw   = pd.read_csv(raw_path)
    clean = pd.read_csv(clean_path)

    source_rows    = len(raw)
    processed_rows = len(clean)

    # ── Pull exclusions for this dataset from the log ──────────────────────────
    excluded_entries = [
        e for e in exclusion_log.get("exclusions", [])
        if e["dataset"] == dataset_name
    ]
    logged_excl_count = len(excluded_entries)
    logged_indices    = {e["original_index"] for e in excluded_entries}

    # ── Core assertion: source = processed + excluded ─────────────────────────
    expected_processed = source_rows - logged_excl_count
    if processed_rows != expected_processed:
        fail(
            f"{dataset_name}: source({source_rows}) - excluded({logged_excl_count}) "
            f"= {expected_processed}, but processed file has {processed_rows} rows."
        )
    ok(
        f"source({source_rows}) = processed({processed_rows}) + excluded({logged_excl_count})"
    )

    # ── Cross-check: logged excluded indices are NOT in processed file ─────────
    # The processed file has a sample_id column of the form "dread_{orig_idx:06d}"
    # or "ge_{orig_idx:06d}".  Extract the original indices from it.
    prefix = "dread_" if dataset_name == "dreaddit" else "ge_"
    if "sample_id" not in clean.columns:
        fail(f"{dataset_name}: processed file has no 'sample_id' column.")

    processed_orig_indices = set(
        int(sid.removeprefix(prefix))
        for sid in clean["sample_id"]
    )

    for entry in excluded_entries:
        idx = entry["original_index"]
        if idx in processed_orig_indices:
            fail(
                f"{dataset_name}: excluded row (original_index={idx}) "
                f"is still present in the processed file. Reason: {entry['reason']}"
            )
    ok(f"All {logged_excl_count} excluded original_index values absent from processed file.")

    # ── Verify no test-split rows were excluded ────────────────────────────────
    test_exclusions = [
        e for e in excluded_entries
        if e.get("split") == "test"
    ]
    if test_exclusions:
        fail(
            f"{dataset_name}: {len(test_exclusions)} test-split row(s) were excluded, "
            f"which violates the official-test-split-integrity rule.\n"
            + "\n".join(f"  original_index={e['original_index']} reason={e['reason']}"
                        for e in test_exclusions)
        )
    raw_test_count   = len(raw[raw["split"] == "test"]) if "split" in raw.columns else "N/A"
    clean_test_count = len(clean[clean["split"] == "test"]) if "split" in clean.columns else "N/A"
    if raw_test_count != clean_test_count:
        fail(
            f"{dataset_name}: test split changed size. "
            f"raw={raw_test_count}, processed={clean_test_count}"
        )
    ok(f"Test split fully preserved: {clean_test_count} rows.")

    # ── sample_id uniqueness ───────────────────────────────────────────────────
    if clean["sample_id"].duplicated().sum() > 0:
        fail(f"{dataset_name}: duplicate sample_id values in processed file.")
    ok("sample_id values are unique.")

    # ── Required columns present ───────────────────────────────────────────────
    required = {"text", "text_redacted", "sample_id", "split",
                "is_intra_split_duplicate", "is_cross_split_duplicate"}
    missing_cols = required - set(clean.columns)
    if missing_cols:
        fail(f"{dataset_name}: processed file missing columns: {missing_cols}")
    ok(f"All required columns present ({', '.join(sorted(required))}).")

    # ── Cross-check report.json counts ────────────────────────────────────────
    ds_report = report.get("datasets", {}).get(dataset_name, {})
    if ds_report:
        if ds_report.get("processed_rows") != processed_rows:
            fail(
                f"{dataset_name}: preprocessing_report.json says "
                f"processed_rows={ds_report['processed_rows']}, "
                f"but actual file has {processed_rows}."
            )
        ok(f"preprocessing_report.json processed_rows matches: {processed_rows}")

    # ── Cross-split overlaps are flagged but present ───────────────────────────
    cross_entries = [
        e for e in exclusion_log.get("cross_split_overlaps", [])
        if e["dataset"] == dataset_name
    ]
    if cross_entries:
        cross_sample_ids = {e["sample_id"] for e in cross_entries}
        missing_in_clean = cross_sample_ids - set(clean["sample_id"])
        if missing_in_clean:
            fail(
                f"{dataset_name}: {len(missing_in_clean)} cross-split-overlap row(s) "
                f"are listed in the log but ABSENT from the processed file. "
                f"They should be present (flagged, not removed).\n"
                f"Missing: {missing_in_clean}"
            )
        ok(
            f"{len(cross_entries)} cross-split overlap(s) are present in processed file "
            f"(flagged, not removed)."
        )


def main() -> None:
    try:
        import pandas  # noqa: F401
    except ImportError:
        print("ERROR: pandas is required.")
        sys.exit(1)

    # ── Check all files exist ──────────────────────────────────────────────────
    for path in [CLEAN_DREAD, CLEAN_GE, EXCL_LOG, REPORT]:
        if not path.exists():
            fail(
                f"File not found: {path}\n"
                "Run preprocess_datasets.py first."
            )

    print("Loading exclusion_log.json and preprocessing_report.json…")
    with open(EXCL_LOG, encoding="utf-8") as f:
        excl_log = json.load(f)
    with open(REPORT, encoding="utf-8") as f:
        report = json.load(f)

    verify_dataset("dreaddit",   RAW_DREAD, CLEAN_DREAD, excl_log, report)
    verify_dataset("goemotions", RAW_GE,    CLEAN_GE,    excl_log, report)

    print()
    print("All assertions passed.")
    print(
        f"  Dreaddit:   {report['datasets']['dreaddit']['source_rows']} source = "
        f"{report['datasets']['dreaddit']['processed_rows']} processed + "
        f"{report['datasets']['dreaddit']['excluded_rows']} excluded"
    )
    print(
        f"  GoEmotions: {report['datasets']['goemotions']['source_rows']} source = "
        f"{report['datasets']['goemotions']['processed_rows']} processed + "
        f"{report['datasets']['goemotions']['excluded_rows']} excluded"
    )


if __name__ == "__main__":
    main()

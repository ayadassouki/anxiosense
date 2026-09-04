#!/usr/bin/env python3
"""Build the OFFICIAL-test evaluation scope for RQ1-RQ3.

Scope decision of 2026-09-04: evaluate on the FULL official test splits.
  Dreaddit   : 715 rows  (NO anxiety/LIWC filter, NO content-based filter)
  GoEmotions : 5,427 rows (ALL official test rows retained in source scope)

Guarantees
----------
* Original source files are read only. Nothing is written outside this folder.
* Every transformation is deterministic and LABEL-BLIND. Re-running produces
  byte-identical output for identical inputs.
* Both texts are preserved: `text_original` (verbatim) and `text_processed`.
* NO row is dropped. Rows the server cannot accept are marked
  dispatchable=False and carry a predefined `exclusion_reason`.
* NO ground-truth mapping is invented. Rows whose labels have no class in the
  5-class evaluation space, and rows with more than one mappable emotion, are
  marked with a `gt_status` and left WITHOUT a ground-truth class. Resolving
  them is a methodology decision, not a preprocessing step.
* Dispatchability and ground-truth status are ORTHOGONAL. A row can be
  dispatchable with no ground truth, and vice versa.

Redaction and whitespace handling are imported from
evaluation/datasets/scripts/preprocess_datasets.py so that exactly one
implementation exists in the repository.

Usage:  python3 evaluation/datasets/official_test_2026-09-04/build_official_test_scope.py
"""
from __future__ import annotations

import csv, hashlib, json, sys
import datetime as _dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "datasets" / "scripts"))
from preprocess_datasets import clean_text, redact_text, _EXCEL_ERRORS  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))
from src.label_mapping import map_dreaddit_label, LabelMappingError  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "evaluation" / "publication_experiments"))
from runner.goemotions_mapping import (                              # noqa: E402
    GOEMOTIONS_LABELS as GE_LABELS, LABEL_MAP, EKMAN_GROUPING, SENTIMENT_GROUPING,
    OUT_OF_TAXONOMY, MAPPING_VERSION as GE_MAPPING_VERSION,
    map_goemotions_labels, anxiosense_class, UnscorableRow, MappingDataError)

BUILDER_VERSION = "1.0.0"
MIN_CHARS = 10  # server /evaluate returns HTTP 400 below this. Label-blind.

GE_TEST = REPO_ROOT / "evaluation" / "datasets" / "goemotions" / "test.csv"
# Populated once the official Dreaddit corpus is downloaded (see DREADDIT_SOURCE.md)
DR_TEST_CANDIDATES = [
    REPO_ROOT / "evaluation" / "datasets" / "dreaddit_official" / "dreaddit_test.csv",
    REPO_ROOT / "evaluation" / "datasets" / "dreaddit_official" / "test.csv",
]
# The superseded anxiety/LIWC-filtered subset. Read ONLY to flag provenance on
# each row. It is never used to include or exclude anything.
DR_OLD_SUBSET = REPO_ROOT / "evaluation" / "datasets" / "dreaddit" / "dreaddit_anxiety_subset.csv"

# Columns carried into the derived file. The hash-pinned original keeps all 116;
# the LIWC anxiety score is carried so the superseded filter stays auditable, and
# is NEVER used as a filter here.
DR_CARRY = ["subreddit", "post_id", "sentence_range", "confidence", "lex_liwc_anx"]

# The 28-label space and the mapping both come from the FROZEN module
# runner/goemotions_mapping.py (v1.0.0). Nothing about the mapping is redefined
# here, so the dataset and the manifest cannot disagree.
GOEMOTIONS_LABELS = list(GE_LABELS)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_label_ids(raw: str) -> list[int]:
    t = str(raw).strip()
    if t.startswith("[") and t.endswith("]"):
        t = t[1:-1]
    if not t.strip():
        return []
    return [int(x) for x in t.replace(",", " ").split()]


def technical_status(text_original: str, text_processed: str) -> tuple[bool, str]:
    """Dispatchability. Depends ONLY on the text, never on the label."""
    if text_original is None or not isinstance(text_original, str):
        return False, f"missing_text: type={type(text_original).__name__}"
    if not text_processed:
        return False, "empty_text: zero-length after whitespace normalisation"
    if text_processed.upper() in _EXCEL_ERRORS:
        return False, f"excel_formula_error: {text_processed!r}"
    if len(text_processed) < MIN_CHARS:
        return False, f"below_min_chars:{MIN_CHARS}"
    return True, ""


def build_goemotions() -> tuple[list[dict], dict]:
    with open(GE_TEST, newline="", encoding="utf-8") as fh:
        src = list(csv.DictReader(fh))

    rows = []
    for r in src:
        raw = r["text"]
        processed = redact_text(clean_text(raw))
        ids = parse_label_ids(r["labels"])
        names = [GOEMOTIONS_LABELS[i] for i in ids]
        classes = [anxiosense_class(n) for n in names]
        in_tax = sorted({c for c in classes if c != OUT_OF_TAXONOMY})

        # Ground truth comes from the frozen mapper, never recomputed here.
        try:
            gt_class = map_goemotions_labels(names)
            gt_status = "mapped"
        except UnscorableRow as exc:
            gt_class, gt_status = "", exc.reason

        dispatchable, reason = technical_status(raw, processed)
        rows.append({
            "sample_id": f"ge_{r['id']}",
            "id": r["id"],
            "split": "test",
            "text_original": raw,
            "text_processed": processed,
            "text_was_modified": str(raw != processed),
            "label_ids_raw": r["labels"],
            "label_ids": " ".join(str(i) for i in ids),
            "label_names": "|".join(names),
            "n_labels": len(ids),
            "mapped_classes": "|".join(in_tax),
            "n_mapped_classes": len(in_tax),
            "n_out_of_taxonomy_labels": sum(1 for c in classes if c == OUT_OF_TAXONOMY),
            "multi_label_rule": (
                "R1" if gt_status == "mapped" and not any(c == OUT_OF_TAXONOMY for c in classes)
                else "R3" if gt_status == "mapped"
                else "R2" if gt_status == "conflicting_classes" else "R4"),
            "gt_status": gt_status,
            "ground_truth": gt_class,
            "dispatchable": str(dispatchable),
            "exclusion_reason": reason,
        })

    from collections import Counter
    disp = [r for r in rows if r["dispatchable"] == "True"]
    stats = {
        "mapping_version": GE_MAPPING_VERSION,
        "source_rows": len(src),
        "output_rows": len(rows),
        "gt_status": dict(Counter(r["gt_status"] for r in rows)),
        "gt_status_dispatchable_only": dict(Counter(r["gt_status"] for r in disp)),
        "multi_label_rule_dispatchable": dict(Counter(r["multi_label_rule"] for r in disp)),
        "ground_truth_when_mapped": dict(Counter(
            r["ground_truth"] for r in rows if r["gt_status"] == "mapped")),
        "dispatchable": dict(Counter(r["dispatchable"] for r in rows)),
        "exclusion_reasons": dict(Counter(
            r["exclusion_reason"] for r in rows if r["exclusion_reason"])),
        "text_modified_rows": sum(1 for r in rows if r["text_was_modified"] == "True"),
        "scorable_now": sum(1 for r in rows
                            if r["gt_status"] == "mapped" and r["dispatchable"] == "True"),
    }
    return rows, stats


def build_dreaddit(path: Path) -> tuple[list[dict], dict]:
    """Full official test split. NO anxiety keyword filter, NO LIWC filter,
    NO content-based filtering of any kind."""
    with open(path, newline="", encoding="utf-8") as fh:
        src = list(csv.DictReader(fh))

    old_test_ids: set[str] = set()
    if DR_OLD_SUBSET.exists():
        with open(DR_OLD_SUBSET, newline="", encoding="utf-8") as fh:
            old_test_ids = {r["id"] for r in csv.DictReader(fh) if r["split"] == "test"}

    rows, errors = [], []
    for r in src:
        raw = r["text"]
        processed = redact_text(clean_text(raw))
        try:
            gt = map_dreaddit_label(r["label"])
            gt_status = "mapped"
        except LabelMappingError as exc:
            gt, gt_status = "", "unmapped_label_error"
            errors.append(f"{r['id']}: {exc}")

        dispatchable, reason = technical_status(raw, processed)
        row = {
            "sample_id": f"dread_{r['id']}",
            "id": r["id"],
            "split": "test",
            "text_original": raw,
            "text_processed": processed,
            "text_was_modified": str(raw != processed),
            # Named "label" (not label_raw) so runner/manifest.py can read it
            # directly via GROUND_TRUTH_MAPPERS["dreaddit"]. Value is verbatim.
            "label": r["label"],
            "gt_status": gt_status,
            "ground_truth": gt,
            "dispatchable": str(dispatchable),
            "exclusion_reason": reason,
            "in_superseded_324_subset": str(r["id"] in old_test_ids),
        }
        for c in DR_CARRY:
            row[c] = r.get(c, "")
        rows.append(row)

    if errors:
        raise SystemExit(f"ground-truth mapping failed for {len(errors)} row(s): {errors[:5]}")

    from collections import Counter
    gt_counts = Counter(r["ground_truth"] for r in rows if r["gt_status"] == "mapped")
    n_disp = sum(1 for r in rows if r["dispatchable"] == "True")
    scorable = [r for r in rows if r["gt_status"] == "mapped" and r["dispatchable"] == "True"]
    sc = Counter(r["ground_truth"] for r in scorable)
    stats = {
        "source_rows": len(src),
        "output_rows": len(rows),
        "gt_status": dict(Counter(r["gt_status"] for r in rows)),
        "label_distribution": {str(k): v for k, v in sorted(gt_counts.items())},
        "positive_rate": round(gt_counts.get(1, 0) / len(rows), 6),
        "dispatchable": {"True": n_disp, "False": len(rows) - n_disp},
        "exclusion_reasons": dict(Counter(
            r["exclusion_reason"] for r in rows if r["exclusion_reason"])),
        "text_modified_rows": sum(1 for r in rows if r["text_was_modified"] == "True"),
        "scorable_now": len(scorable),
        "scorable_majority_baseline": round(max(sc.values()) / len(scorable), 6) if scorable else None,
        "rows_in_superseded_324_subset": sum(
            1 for r in rows if r["in_superseded_324_subset"] == "True"),
        "rows_the_superseded_filter_removed": sum(
            1 for r in rows if r["in_superseded_324_subset"] == "False"),
    }
    return rows, stats


def label_handling_matrix(rows: list[dict]) -> list[dict]:
    """The frozen v1.0.0 decision for each of the 28 labels, with counts."""
    from collections import Counter
    appears, only = Counter(), Counter()
    for r in rows:
        names = [n for n in r["label_names"].split("|") if n]
        for n in names:
            appears[n] += 1
        if len(names) == 1:
            only[names[0]] += 1

    ek = {l: g for g, ls in EKMAN_GROUPING.items() for l in ls}
    se = {l: g for g, ls in SENTIMENT_GROUPING.items() for l in ls}
    out = []
    for name in GOEMOTIONS_LABELS:
        cls, tier, basis = LABEL_MAP[name]
        out.append({
            "label_id": GOEMOTIONS_LABELS.index(name),
            "label": name,
            "official_ekman_group": ek.get(name, "(none - neutral)"),
            "official_sentiment_group": se.get(name, "neutral"),
            "anxiosense_class": cls,
            "evidence_strength": tier,
            "basis": basis,
            "rows_where_label_present": appears.get(name, 0),
            "rows_where_it_is_the_only_label": only.get(name, 0),
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    if not GE_TEST.exists():
        print(f"ERROR: {GE_TEST} not found"); return 1

    ge_rows, ge_stats = build_goemotions()
    write_csv(HERE / "goemotions_test_official.csv", ge_rows)
    write_csv(HERE / "goemotions_label_handling.csv", label_handling_matrix(ge_rows))
    write_csv(HERE / "goemotions_excluded_rows.csv",
              [{k: r[k] for k in ("sample_id", "id", "exclusion_reason", "gt_status",
                                  "ground_truth", "text_processed")}
               for r in ge_rows if r["dispatchable"] == "False"])

    sources = {
        "builder_version": BUILDER_VERSION,
        "built_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "policy": {
            "content_based_filtering": "NONE. No anxiety/LIWC filter, no quality filter, "
                                       "no removal of noisy, slang, or unusual text.",
            "preprocessing": "deterministic and label-blind only: CRLF/CR -> LF, "
                             "strip leading/trailing whitespace, then PII redaction "
                             "(URL, EMAIL, PHONE, USER, SUBREDDIT).",
            "text_preserved": "text_original is verbatim; text_processed is what would be sent.",
            "row_removal": "none - non-dispatchable rows are retained with an exclusion_reason.",
            "ground_truth": "never invented; unmapped and multi-mappable rows carry gt_status "
                            "and no class.",
            "sample_id_scheme": "ge_<official comment id> / dread_<official id>. Content-derived "
                                "and stable, unlike the positional ge_000000 scheme, which does "
                                "not survive a rebuild and cannot be joined across lineages.",
        },
        "goemotions": {
            "source_file": str(GE_TEST.relative_to(REPO_ROOT)),
            "source_sha256": sha256_file(GE_TEST),
            "source_revision": "google-research-datasets/go_emotions simplified, official test split",
            "stats": ge_stats,
        },
        "dreaddit": {
            "status": "PENDING - official 715-row test split not yet on disk",
            "expected_paths": [str(p.relative_to(REPO_ROOT)) for p in DR_TEST_CANDIDATES],
            "expected_rows": 715,
            "note": "See DREADDIT_SOURCE.md. Must be hash-pinned on arrival.",
        },
    }
    dr_path = next((p for p in DR_TEST_CANDIDATES if p.exists()), None)
    if dr_path is not None:
        dr_rows, dr_stats = build_dreaddit(dr_path)
        write_csv(HERE / "dreaddit_test_official.csv", dr_rows)
        write_csv(HERE / "dreaddit_excluded_rows.csv",
                  [{k: r[k] for k in ("sample_id", "id", "exclusion_reason", "gt_status",
                                      "ground_truth", "text_processed")}
                   for r in dr_rows if r["dispatchable"] == "False"])
        sources["dreaddit"] = {
            "source_file": str(dr_path.relative_to(REPO_ROOT)),
            "source_sha256": sha256_file(dr_path),
            "source_revision": "andreagasparini/dreaddit (HuggingFace), official test split",
            "filter_applied": "NONE - the anxiety keyword/LIWC filter is NOT applied",
            "stats": dr_stats,
        }
        print(json.dumps(dr_stats, indent=2))

    # Hash-pin every derived output, computed after all of them are written.
    derived = {}
    for f in sorted(HERE.glob("*.csv")):
        derived[f.name] = {"sha256": sha256_file(f), "bytes": f.stat().st_size}
    sources["derived_outputs"] = derived

    (HERE / "SOURCES.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ge_stats, indent=2))
    print(f"\nwrote -> {HERE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

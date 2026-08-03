#!/usr/bin/env python3
"""
evaluation/datasets/scripts/preprocess_datasets.py

Reproducible preprocessing pipeline for Dreaddit and GoEmotions datasets.

DESIGN PRINCIPLES
-----------------
1. This script is purely mechanical — no sampling, no rebalancing, no label changes.
2. The original datasets are never modified.
3. Every row removed from the processed output is logged with an exact reason.
4. Duplicate texts are flagged with boolean columns but NOT removed.
5. Cross-split duplicates are reported in the exclusion log but NOT removed.
6. All cleaning is reversible by looking at the exclusion log.

WHAT THIS SCRIPT DOES
---------------------
  (a) Removes rows where text is malformed (NaN, empty, Excel formula errors).
  (b) Trims leading/trailing whitespace from text.
  (c) Normalises line endings to \\n (Unix).
  (d) Preserves Unicode (UTF-8, no stripping of non-ASCII).
  (e) Assigns stable sample IDs: {dataset}_{original_0based_index:06d}
  (f) Flags intra-split duplicate texts (is_intra_split_duplicate column).
  (g) Flags cross-split duplicate texts (is_cross_split_duplicate column).
  (h) Produces a text_redacted column with emails, phone numbers, URLs and
      Reddit usernames replaced by placeholder tokens.

WHAT THIS SCRIPT DOES NOT DO
-----------------------------
  - Does NOT change benchmark labels.
  - Does NOT remove duplicate rows (duplicates are flagged, not dropped).
  - Does NOT remove cross-split overlaps (they are flagged and reported).
  - Does NOT apply any minimum text length cutoff.
  - Does NOT resample or stratify.

OUTPUTS
-------
  evaluation/datasets/processed/dreaddit_clean.csv
  evaluation/datasets/processed/goemotions_clean.csv
  evaluation/datasets/processed/preprocessing_report.json
  evaluation/datasets/processed/exclusion_log.json

Usage (from repo root):
    python evaluation/datasets/scripts/preprocess_datasets.py

"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
RAW_DREAD   = REPO_ROOT / "evaluation" / "datasets" / "dreaddit" / "dreaddit_anxiety_subset.csv"
RAW_GE      = REPO_ROOT / "evaluation" / "datasets" / "goemotions" / "goemotions_anxiosense_single.csv"
OUT_DIR     = REPO_ROOT / "evaluation" / "datasets" / "processed"

# ── Redaction patterns ────────────────────────────────────────────────────────
# Applied in the order listed.  Replacements use distinctive bracket tokens so
# researchers can detect them in post-hoc analysis.
_REDACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # HTTP/HTTPS/FTP URLs
    (re.compile(r"https?://\S+|ftp://\S+", re.IGNORECASE), "[URL]"),
    # Bare www. URLs
    (re.compile(r"\bwww\.\S+", re.IGNORECASE), "[URL]"),
    # Email addresses
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE), "[EMAIL]"),
    # Phone numbers — NANP and international (+1-800-555-0100, (800) 555-0100, etc.)
    (re.compile(r"(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"), "[PHONE]"),
    # Reddit u/ usernames: u/username (letters, digits, hyphens, underscores)
    (re.compile(r"\bu/[A-Za-z0-9_\-]{1,20}\b"), "[USER]"),
    # Reddit r/ subreddits: r/subreddit
    (re.compile(r"\br/[A-Za-z0-9_]{1,21}\b"), "[SUBREDDIT]"),
]


def redact_text(text: str) -> str:
    """Apply all redaction patterns to text. Returns redacted copy."""
    for pattern, placeholder in _REDACT_PATTERNS:
        text = pattern.sub(placeholder, text)
    return text


def clean_text(text: str) -> str:
    """
    Trim whitespace and normalise line endings.
    Preserves all Unicode code points.
    """
    # Normalise CRLF and CR to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip leading / trailing whitespace
    return text.strip()


# ── Malformed text detection ──────────────────────────────────────────────────
# A "malformed" row is one where the text field cannot serve as a valid
# natural-language input to the AnxioSense pipeline.
#
# Criteria (each must be explicitly listed in the thesis):
#
#   1. Missing / NaN text field — the row has no text to evaluate.
#   2. Empty text after stripping — zero-length string after whitespace removal.
#   3. Excel formula error strings — #NAME?, #REF!, #VALUE!, #N/A, #DIV/0!
#      These appear when a CSV was exported from a spreadsheet that contained
#      formula cells.  The text is not a natural-language excerpt.
#
# NOT considered malformed:
#   - Very short texts (≥ 1 character): brevity is not an error.
#   - Non-English text: AnxioSense accepts any language the LLM handles.
#   - Duplicate texts: duplication is a separate property, not malformation.

_EXCEL_ERRORS = {"#NAME?", "#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#ERROR!"}


def malformed_reason(raw_text) -> str | None:
    """Return a non-empty reason string if text is malformed, else None."""
    if raw_text is None or (isinstance(raw_text, float)):
        import math
        try:
            if math.isnan(raw_text):
                return "missing_text: NaN"
        except (TypeError, ValueError):
            pass
        return f"missing_text: type={type(raw_text).__name__}"
    if not isinstance(raw_text, str):
        return f"missing_text: type={type(raw_text).__name__}"
    stripped = raw_text.strip()
    if not stripped:
        return "empty_text: zero-length after stripping whitespace"
    if stripped.upper() in _EXCEL_ERRORS:
        return f"excel_formula_error: {stripped!r}"
    return None


# ── Duplicate detection ───────────────────────────────────────────────────────

def compute_duplicate_flags(df, text_col: str, split_col: str):
    """
    Compute two boolean Series for the dataframe:
      is_intra_split_duplicate: True if this row's text was already seen earlier
                                in the SAME split.
      is_cross_split_duplicate: True if this row's text appears in ANY OTHER split.

    Neither flag causes row removal — they are purely informational columns.
    """
    import pandas as pd

    n = len(df)
    intra_dup = [False] * n
    cross_dup = [False] * n

    # Build per-split text sets (all texts, strip for comparison)
    splits = df[split_col].unique()
    split_all_texts: dict[str, set] = {
        sp: set(df[df[split_col] == sp][text_col].str.strip())
        for sp in splits
    }

    # Intra-split: first occurrence is not a dup; subsequent are
    intra_seen: dict[str, set] = {sp: set() for sp in splits}

    for i, (idx, row) in enumerate(df.iterrows()):
        sp   = row[split_col]
        text = str(row[text_col]).strip()
        # Intra-split
        if text in intra_seen[sp]:
            intra_dup[i] = True
        else:
            intra_seen[sp].add(text)
        # Cross-split: this text appears in some other split
        for other_sp, other_texts in split_all_texts.items():
            if other_sp != sp and text in other_texts:
                cross_dup[i] = True
                break

    return (
        pd.Series(intra_dup, index=df.index, name="is_intra_split_duplicate"),
        pd.Series(cross_dup, index=df.index, name="is_cross_split_duplicate"),
    )


# ── Per-dataset preprocessing ─────────────────────────────────────────────────

def preprocess_dreaddit(
    exclusions: list[dict],
    cross_split_report: list[dict],
) -> tuple["pd.DataFrame", dict]:
    """
    Process Dreaddit.  Returns (clean_df, stats_dict).
    """
    import pandas as pd

    df = pd.read_csv(RAW_DREAD)
    source_count = len(df)

    kept_indices = []
    for original_index, row in df.iterrows():
        reason = malformed_reason(row.get("text"))
        if reason:
            exclusions.append({
                "dataset":         "dreaddit",
                "original_index":  int(original_index),
                "sample_id":       f"dread_{original_index:06d}",
                "id":              int(row["id"]) if "id" in row else None,
                "split":           str(row.get("split", "")),
                "reason":          reason,
                "text_snippet":    str(row.get("text", ""))[:120],
            })
        else:
            kept_indices.append(original_index)

    clean = df.loc[kept_indices].copy()

    # ── Apply text cleaning (trim + normalise line endings) ──────────────────
    clean["text"] = clean["text"].apply(clean_text)

    # ── Assign stable sample IDs ─────────────────────────────────────────────
    clean["sample_id"] = [f"dread_{idx:06d}" for idx in clean.index]

    # ── Duplicate flags ───────────────────────────────────────────────────────
    intra_flag, cross_flag = compute_duplicate_flags(clean, "text", "split")
    clean["is_intra_split_duplicate"] = intra_flag.values
    clean["is_cross_split_duplicate"] = cross_flag.values

    # ── Redacted text ─────────────────────────────────────────────────────────
    clean["text_redacted"] = clean["text"].apply(redact_text)

    # ── Report cross-split overlaps (not removed) ─────────────────────────────
    for original_index, row in clean.iterrows():
        if row["is_cross_split_duplicate"]:
            cross_split_report.append({
                "dataset":         "dreaddit",
                "original_index":  int(original_index),
                "sample_id":       row["sample_id"],
                "split":           row["split"],
                "label":           int(row["label"]),
                "note":            "Text also appears in another split. Row KEPT in processed dataset.",
                "text_snippet":    row["text"][:120],
            })

    # ── Reorder columns for readability ──────────────────────────────────────
    core_cols = [
        "sample_id", "id", "split", "subreddit", "post_id",
        "text", "text_redacted",
        "label", "confidence",
        "is_intra_split_duplicate", "is_cross_split_duplicate",
        "lex_liwc_anx", "anxiety_keyword_match", "liwc_anxiety_match",
    ]
    clean = clean[[c for c in core_cols if c in clean.columns]]

    # ── Stats ─────────────────────────────────────────────────────────────────
    stats = {
        "source_rows":            source_count,
        "excluded_rows":          source_count - len(clean),
        "processed_rows":         len(clean),
        "split_counts":           clean["split"].value_counts().to_dict(),
        "label_distribution":     clean["label"].value_counts().to_dict(),
        "intra_split_duplicates": int(clean["is_intra_split_duplicate"].sum()),
        "cross_split_duplicates": int(clean["is_cross_split_duplicate"].sum()),
        "text_length": {
            "min":    int(clean["text"].str.len().min()),
            "q25":    int(clean["text"].str.len().quantile(.25)),
            "median": int(clean["text"].str.len().median()),
            "mean":   round(float(clean["text"].str.len().mean()), 1),
            "max":    int(clean["text"].str.len().max()),
        },
    }
    return clean, stats


def preprocess_goemotions(
    exclusions: list[dict],
    cross_split_report: list[dict],
) -> tuple["pd.DataFrame", dict]:
    """
    Process GoEmotions.  Returns (clean_df, stats_dict).
    """
    import pandas as pd

    df = pd.read_csv(RAW_GE)
    source_count = len(df)

    kept_indices = []
    for original_index, row in df.iterrows():
        reason = malformed_reason(row.get("text"))
        if reason:
            exclusions.append({
                "dataset":         "goemotions",
                "original_index":  int(original_index),
                "sample_id":       f"ge_{original_index:06d}",
                "id":              str(row.get("id", "")),
                "split":           str(row.get("split", "")),
                "reason":          reason,
                "text_snippet":    str(row.get("text", ""))[:120],
            })
        else:
            kept_indices.append(original_index)

    clean = df.loc[kept_indices].copy()

    # ── Apply text cleaning ───────────────────────────────────────────────────
    clean["text"] = clean["text"].apply(clean_text)

    # ── Assign stable sample IDs ──────────────────────────────────────────────
    clean["sample_id"] = [f"ge_{idx:06d}" for idx in clean.index]

    # ── Duplicate flags ────────────────────────────────────────────────────────
    intra_flag, cross_flag = compute_duplicate_flags(clean, "text", "split")
    clean["is_intra_split_duplicate"] = intra_flag.values
    clean["is_cross_split_duplicate"] = cross_flag.values

    # ── Redacted text ──────────────────────────────────────────────────────────
    clean["text_redacted"] = clean["text"].apply(redact_text)

    # ── Report cross-split overlaps (not removed) ──────────────────────────────
    for original_index, row in clean.iterrows():
        if row["is_cross_split_duplicate"]:
            cross_split_report.append({
                "dataset":         "goemotions",
                "original_index":  int(original_index),
                "sample_id":       row["sample_id"],
                "split":           row["split"],
                "emotion_names":   str(row.get("emotion_names", "")),
                "note":            "Text also appears in another split. Row KEPT in processed dataset.",
                "text_snippet":    row["text"][:120],
            })

    # ── Reorder columns ────────────────────────────────────────────────────────
    core_cols = [
        "sample_id", "id", "split",
        "text", "text_redacted",
        "labels", "parsed_labels", "emotion_names",
        "is_intra_split_duplicate", "is_cross_split_duplicate",
    ]
    clean = clean[[c for c in core_cols if c in clean.columns]]

    # ── Stats ──────────────────────────────────────────────────────────────────
    stats = {
        "source_rows":            source_count,
        "excluded_rows":          source_count - len(clean),
        "processed_rows":         len(clean),
        "split_counts":           clean["split"].value_counts().to_dict(),
        "emotion_distribution":   clean["emotion_names"].value_counts().to_dict(),
        "intra_split_duplicates": int(clean["is_intra_split_duplicate"].sum()),
        "cross_split_duplicates": int(clean["is_cross_split_duplicate"].sum()),
        "text_length": {
            "min":    int(clean["text"].str.len().min()),
            "q25":    int(clean["text"].str.len().quantile(.25)),
            "median": int(clean["text"].str.len().median()),
            "mean":   round(float(clean["text"].str.len().mean()), 1),
            "max":    int(clean["text"].str.len().max()),
        },
    }
    return clean, stats


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        print("ERROR: pandas is required.  pip install pandas --break-system-packages")
        sys.exit(1)

    for path in [RAW_DREAD, RAW_GE]:
        if not path.exists():
            print(f"ERROR: source dataset not found: {path}")
            sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    exclusions:         list[dict] = []
    cross_split_report: list[dict] = []

    print("Preprocessing Dreaddit…")
    dread_clean, dread_stats = preprocess_dreaddit(exclusions, cross_split_report)
    out_dread = OUT_DIR / "dreaddit_clean.csv"
    dread_clean.to_csv(out_dread, index=False)
    print(f"  Wrote {len(dread_clean)} rows → {out_dread.relative_to(REPO_ROOT)}")
    print(f"  Excluded: {dread_stats['excluded_rows']}  |  "
          f"Intra-split dups flagged: {dread_stats['intra_split_duplicates']}  |  "
          f"Cross-split overlaps reported: "
          f"{len([r for r in cross_split_report if r['dataset']=='dreaddit'])}")

    print("Preprocessing GoEmotions…")
    ge_clean, ge_stats = preprocess_goemotions(exclusions, cross_split_report)
    out_ge = OUT_DIR / "goemotions_clean.csv"
    ge_clean.to_csv(out_ge, index=False)
    print(f"  Wrote {len(ge_clean)} rows → {out_ge.relative_to(REPO_ROOT)}")
    print(f"  Excluded: {ge_stats['excluded_rows']}  |  "
          f"Intra-split dups flagged: {ge_stats['intra_split_duplicates']}  |  "
          f"Cross-split overlaps reported: "
          f"{len([r for r in cross_split_report if r['dataset']=='goemotions'])}")

    # ── Write preprocessing_report.json ────────────────────────────────────────
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "evaluation/datasets/scripts/preprocess_datasets.py",
        "exclusion_policy": (
            "Rows are excluded ONLY when the text field is malformed "
            "(NaN, empty, or an Excel formula error string such as #NAME?). "
            "Duplicate texts are flagged with boolean columns but NOT removed. "
            "Cross-split overlaps are reported in exclusion_log.json under "
            "'cross_split_overlaps' but NOT removed from the processed dataset."
        ),
        "datasets": {
            "dreaddit":   dread_stats,
            "goemotions": ge_stats,
        },
    }
    report_path = OUT_DIR / "preprocessing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Wrote preprocessing_report.json → {report_path.relative_to(REPO_ROOT)}")

    # ── Write exclusion_log.json ────────────────────────────────────────────────
    log = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_exclusions":    len(exclusions),
        "total_cross_split_overlaps": len(cross_split_report),
        "policy_note": (
            "Only rows in 'exclusions' are removed from the processed dataset. "
            "Rows in 'cross_split_overlaps' are KEPT in the processed dataset "
            "with is_cross_split_duplicate=True; they are listed here for "
            "transparency and must be described in the Methodology chapter."
        ),
        "exclusions":         exclusions,
        "cross_split_overlaps": cross_split_report,
    }
    log_path = OUT_DIR / "exclusion_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"Wrote exclusion_log.json → {log_path.relative_to(REPO_ROOT)}")

    print()
    print("Done.  Run verify_preprocessing.py to assert source = processed + excluded.")


if __name__ == "__main__":
    main()

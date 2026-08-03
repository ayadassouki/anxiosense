#!/usr/bin/env python3
"""
evaluation/datasets/scripts/audit_datasets.py

Read-only audit of raw Dreaddit and GoEmotions datasets.
Produces a complete statistical report without modifying any file.

Usage (from repo root):
    python evaluation/datasets/scripts/audit_datasets.py

All counts are verified programmatically. No preprocessing is applied.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DREADDIT_PATH = REPO_ROOT / "evaluation" / "datasets" / "dreaddit" / "dreaddit_anxiety_subset.csv"
GOEMOTIONS_PATH = REPO_ROOT / "evaluation" / "datasets" / "goemotions" / "goemotions_anxiosense_single.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_labels_col(s: str) -> list[int]:
    """
    Parse GoEmotions 'labels' column.
    Handles both Python-list format '[ 3 12]' (numpy) and '[27]'.
    """
    s = str(s).strip()
    # Replace numpy-style space-separated ints inside brackets
    inner = s.lstrip("[").rstrip("]").strip()
    if not inner:
        return []
    parts = re.split(r"[\s,]+", inner)
    return [int(p) for p in parts if p]


def _detect_malformed_text(text: str) -> str | None:
    """
    Return a reason string if the text is malformed, else None.
    Criteria:
        - NaN / non-string
        - Empty after stripping whitespace
        - Excel formula errors (#NAME?, #REF!, #VALUE!, #N/A, #DIV/0!)
    """
    if not isinstance(text, str):
        return f"not_a_string: {type(text).__name__}"
    stripped = text.strip()
    if not stripped:
        return "empty_text"
    excel_errors = {"#NAME?", "#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#ERROR!"}
    if stripped.upper() in excel_errors or stripped.upper().startswith("#NAME"):
        return f"excel_formula_error: {stripped!r}"
    return None


def audit_dreaddit(path: Path) -> None:
    import pandas as pd

    print("=" * 72)
    print("DREADDIT AUDIT")
    print(f"Source: {path}")
    print("=" * 72)

    df = pd.read_csv(path)
    total = len(df)
    print(f"\nTotal rows:    {total}")
    print(f"Columns:       {list(df.columns)}")

    # ── Split counts ────────────────────────────────────────────────────────
    print("\n── Split counts ─────────────────────────────────────────────────")
    for sp, cnt in df["split"].value_counts().items():
        print(f"  {sp:10s}: {cnt}")

    # ── Label distribution ───────────────────────────────────────────────────
    print("\n── Label distribution ───────────────────────────────────────────")
    for lbl, cnt in df["label"].value_counts().items():
        pct = cnt / total * 100
        print(f"  label={lbl}: {cnt} ({pct:.1f}%)")

    # ── Missing / null ───────────────────────────────────────────────────────
    print("\n── Missing values ───────────────────────────────────────────────")
    null_counts = df.isnull().sum()
    for col in df.columns:
        if null_counts[col] > 0:
            print(f"  {col}: {null_counts[col]} null")
    if null_counts.sum() == 0:
        print("  None.")

    # ── Malformed texts ──────────────────────────────────────────────────────
    print("\n── Malformed text rows ──────────────────────────────────────────")
    malformed = []
    for idx, row in df.iterrows():
        reason = _detect_malformed_text(row.get("text"))
        if reason:
            malformed.append((idx, row, reason))
    if malformed:
        for idx, row, reason in malformed:
            print(f"  row_index={idx}  id={row['id']}  split={row['split']}  reason={reason}")
            print(f"  text: {repr(str(row.get('text', ''))[:80])}")
    else:
        print("  None.")

    # ── Text length statistics ───────────────────────────────────────────────
    print("\n── Text length statistics (characters) ──────────────────────────")
    lens = df["text"].astype(str).str.len()
    print(f"  min={lens.min()}   q25={int(lens.quantile(.25))}   median={int(lens.median())}   "
          f"mean={int(lens.mean())}   q75={int(lens.quantile(.75))}   max={lens.max()}")

    # ── Intra-split duplicates ───────────────────────────────────────────────
    print("\n── Intra-split exact duplicate texts ────────────────────────────")
    total_intra = 0
    for sp in df["split"].unique():
        texts = df[df["split"] == sp]["text"].str.strip()
        dup_count = texts.duplicated().sum()
        total_intra += dup_count
        if dup_count > 0:
            print(f"  {sp}: {dup_count} duplicate text(s) (second+ occurrence)")
            dup_texts = texts[texts.duplicated(keep=False)].unique()
            for t in dup_texts[:3]:
                rows = df[(df["split"] == sp) & (df["text"].str.strip() == t)]
                ids = rows["id"].tolist()
                print(f"    ids={ids}  text={repr(t[:60])}")
    if total_intra == 0:
        print("  None.")

    # ── Cross-split duplicate texts ──────────────────────────────────────────
    print("\n── Cross-split duplicate texts (train ↔ test) ───────────────────")
    train_texts = set(df[df["split"] == "train"]["text"].str.strip())
    test_texts  = set(df[df["split"] == "test"]["text"].str.strip())
    cross = train_texts & test_texts
    print(f"  Train texts that also appear in test: {len(cross)}")
    if cross:
        for t in list(cross):
            rows = df[df["text"].str.strip() == t]
            print(f"    text={repr(t[:70])}")
            print(f"    rows: {[(int(r['id']), r['split']) for _, r in rows.iterrows()]}")

    print()
    print(f"SUMMARY: {total} total rows | "
          f"{len(malformed)} malformed | "
          f"{total_intra} intra-split dups | "
          f"{len(cross)} cross-split overlaps")
    print()


def audit_goemotions(path: Path) -> None:
    import pandas as pd

    print("=" * 72)
    print("GOEMOTIONS AUDIT")
    print(f"Source: {path}")
    print("=" * 72)

    df = pd.read_csv(path)
    total = len(df)
    print(f"\nTotal rows:    {total}")
    print(f"Columns:       {list(df.columns)}")

    # ── Split counts ─────────────────────────────────────────────────────────
    print("\n── Split counts ─────────────────────────────────────────────────")
    for sp, cnt in df["split"].value_counts().items():
        print(f"  {sp:12s}: {cnt}")

    # ── Missing / null ───────────────────────────────────────────────────────
    print("\n── Missing values ───────────────────────────────────────────────")
    null_counts = df.isnull().sum()
    for col in df.columns:
        if null_counts[col] > 0:
            print(f"  {col}: {null_counts[col]} null")
    if null_counts.sum() == 0:
        print("  None.")

    # ── Malformed texts ──────────────────────────────────────────────────────
    print("\n── Malformed text rows ──────────────────────────────────────────")
    malformed = []
    for idx, row in df.iterrows():
        reason = _detect_malformed_text(row.get("text"))
        if reason:
            malformed.append((idx, row, reason))
    print(f"  {len(malformed)} malformed text row(s).")
    for idx, row, reason in malformed[:10]:
        print(f"  row_index={idx}  id={row.get('id','?')}  reason={reason}")

    # ── Label (emotion_names) distribution ──────────────────────────────────
    print("\n── Emotion label distribution (emotion_names) ───────────────────")
    for lbl, cnt in df["emotion_names"].value_counts().items():
        pct = cnt / total * 100
        print(f"  {lbl:<28s}: {cnt:5d} ({pct:.1f}%)")

    # ── Multi-label vs single-label (original labels column) ─────────────────
    print("\n── Multi-label rows (original GoEmotions labels column) ─────────")
    label_counts = df["labels"].apply(_parse_labels_col).apply(len)
    single = (label_counts == 1).sum()
    multi  = (label_counts > 1).sum()
    print(f"  Single-label (1 original GoEmotions label): {single}")
    print(f"  Multi-label  (>1 original GoEmotions label): {multi}")
    print(f"  Note: emotion_names column selects exactly one TARGET emotion per row,")
    print(f"        regardless of how many original GoEmotions labels exist.")

    # ── Text length statistics ────────────────────────────────────────────────
    print("\n── Text length statistics (characters) ──────────────────────────")
    lens = df["text"].astype(str).str.len()
    print(f"  min={lens.min()}   q25={int(lens.quantile(.25))}   median={int(lens.median())}   "
          f"mean={int(lens.mean())}   q75={int(lens.quantile(.75))}   max={lens.max()}")
    print(f"  texts < 5 chars: {(lens < 5).sum()}")

    # ── Intra-split duplicates ────────────────────────────────────────────────
    print("\n── Intra-split exact duplicate texts ────────────────────────────")
    total_intra = 0
    intra_by_split: dict[str, int] = {}
    for sp in ["train", "validation", "test"]:
        texts = df[df["split"] == sp]["text"].str.strip()
        dup_count = texts.duplicated().sum()
        intra_by_split[sp] = dup_count
        total_intra += dup_count
        print(f"  {sp:12s}: {dup_count} second-or-later occurrence(s)")
    if total_intra == 0:
        print("  None.")

    # ── Cross-split duplicate texts ───────────────────────────────────────────
    print("\n── Cross-split duplicate texts ──────────────────────────────────")
    splits = {sp: set(df[df["split"] == sp]["text"].str.strip())
              for sp in ["train", "validation", "test"]}
    pairs = [
        ("train",      "test",       "train ∩ test"),
        ("validation", "test",       "val   ∩ test"),
        ("train",      "validation", "train ∩ val "),
    ]
    total_cross = 0
    for a, b, label in pairs:
        overlap = splits[a] & splits[b]
        total_cross += len(overlap)
        print(f"  {label}: {len(overlap)} shared text(s)")

    print()
    print(f"SUMMARY: {total} total rows | "
          f"{len(malformed)} malformed | "
          f"{total_intra} intra-split dups | "
          f"{total_cross} cross-split overlaps")
    print()


def main() -> None:
    try:
        import pandas  # noqa: F401
    except ImportError:
        print("ERROR: pandas is required. Install with: pip install pandas --break-system-packages")
        sys.exit(1)

    for path, fn in [(DREADDIT_PATH, audit_dreaddit), (GOEMOTIONS_PATH, audit_goemotions)]:
        if not path.exists():
            print(f"ERROR: Dataset not found: {path}")
            sys.exit(1)
        fn(path)


if __name__ == "__main__":
    main()

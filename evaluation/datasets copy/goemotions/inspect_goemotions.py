from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


DATA_DIR = Path(__file__).parent
SPLIT_FILES = ["train.csv", "validation.csv", "test.csv"]
RANDOM_SEED = 42
SAMPLE_SIZE = 10

EMOTION_LABELS: dict[int, str] = {
    0: "admiration",
    1: "amusement",
    2: "anger",
    3: "annoyance",
    4: "approval",
    5: "caring",
    6: "confusion",
    7: "curiosity",
    8: "desire",
    9: "disappointment",
    10: "disapproval",
    11: "disgust",
    12: "embarrassment",
    13: "excitement",
    14: "fear",
    15: "gratitude",
    16: "grief",
    17: "joy",
    18: "love",
    19: "nervousness",
    20: "optimism",
    21: "pride",
    22: "realization",
    23: "relief",
    24: "remorse",
    25: "sadness",
    26: "surprise",
    27: "neutral",
}


def normalize_labels(value: Any) -> list[int]:
    """
    Convert a GoEmotions labels cell into a list of integer label IDs.

    Examples:
        "[4 15]" -> [4, 15]
        "[11]"   -> [11]
        "4,15"   -> [4, 15]
        [4, 15]  -> [4, 15]
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return [int(item) for item in value]

    text = str(value).strip()

    if not text or text.lower() == "nan":
        return []

    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]

    values: list[int] = []

    for item in text.replace(",", " ").split():
        try:
            values.append(int(item))
        except ValueError:
            print(f"Warning: Could not parse label value: {item!r}")

    return values


def label_names(label_ids: list[int]) -> list[str]:
    """Convert numeric label IDs into readable emotion names."""
    return [
        EMOTION_LABELS.get(label_id, f"unknown_{label_id}")
        for label_id in label_ids
    ]


def validate_columns(df: pd.DataFrame, filename: str) -> None:
    """Confirm that the required GoEmotions columns are present."""
    required_columns = {"text", "labels", "id"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{filename} is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def print_split_summary(df: pd.DataFrame, filename: str) -> None:
    """Print a short summary for one dataset split."""
    print("=" * 80)
    print(f"FILE: {filename}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {list(df.columns)}")
    print()
    print("First 3 rows:")
    print(df.head(3).to_string(index=False))
    print()


def main() -> None:
    frames: list[pd.DataFrame] = []

    for filename in SPLIT_FILES:
        path = DATA_DIR / filename

        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        df = pd.read_csv(path)
        validate_columns(df, filename)

        df["split"] = filename.removesuffix(".csv")
        df["label_ids"] = df["labels"].apply(normalize_labels)
        df["label_names"] = df["label_ids"].apply(label_names)
        df["label_count"] = df["label_ids"].apply(len)

        frames.append(df)
        print_split_summary(df, filename)

    if not frames:
        raise FileNotFoundError(
            f"No GoEmotions CSV files were found in {DATA_DIR}. "
            "Expected train.csv, validation.csv, or test.csv."
        )

    combined = pd.concat(frames, ignore_index=True)

    print("=" * 80)
    print("COMBINED DATASET")
    print(f"Total rows: {len(combined):,}")
    print(f"Columns: {list(combined.columns)}")
    print()

    print("Rows by split:")
    print(combined["split"].value_counts().to_string())
    print()

    label_counts: Counter[int] = Counter()

    for ids in combined["label_ids"]:
        label_counts.update(ids)

    print("EMOTION LABEL COUNTS")
    print("-" * 80)

    summary_rows: list[dict[str, int | str]] = []

    for label_id in sorted(EMOTION_LABELS):
        count = label_counts.get(label_id, 0)
        emotion = EMOTION_LABELS[label_id]

        print(f"{label_id:>2} | {emotion:<15} | {count:>6,}")

        summary_rows.append(
            {
                "label_id": label_id,
                "emotion": emotion,
                "count": count,
            }
        )

    print()

    print("NUMBER OF LABELS PER COMMENT")
    print("-" * 80)
    print(combined["label_count"].value_counts().sort_index().to_string())
    print()

    multi_label_rows = (combined["label_count"] > 1).sum()
    single_label_rows = (combined["label_count"] == 1).sum()
    empty_label_rows = (combined["label_count"] == 0).sum()

    print(f"Single-label comments: {single_label_rows:,}")
    print(f"Multi-label comments:  {multi_label_rows:,}")
    print(f"Comments with no label: {empty_label_rows:,}")
    print()

    print(f"RANDOM SAMPLE OF {SAMPLE_SIZE} COMMENTS")
    print("-" * 80)

    sample = combined.sample(
        n=min(SAMPLE_SIZE, len(combined)),
        random_state=RANDOM_SEED,
    )

    for _, row in sample.iterrows():
        print("=" * 80)
        print(f"ID: {row['id']}")
        print(f"Split: {row['split']}")
        print(f"Label IDs: {row['label_ids']}")
        print(f"Emotions: {', '.join(row['label_names'])}")
        print()
        print(row["text"])
        print()

    summary_file = DATA_DIR / "goemotions_label_summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_file, index=False)

    print("=" * 80)
    print(f"Label summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
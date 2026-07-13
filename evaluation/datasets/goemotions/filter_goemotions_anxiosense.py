from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent

SPLIT_FILES = [
    "train.csv",
    "validation.csv",
    "test.csv",
]

TARGET_LABELS = {
    2: "anger",
    3: "annoyance",
    9: "disappointment",
    14: "fear",
    16: "grief",
    17: "joy",
    19: "nervousness",
    23: "relief",
    25: "sadness",
    27: "neutral",
}


def parse_labels(value: object) -> list[int]:
    """
    Convert '[14 19]' into [14, 19]
    """

    text = str(value).strip()

    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]

    if not text:
        return []

    return [int(x) for x in text.replace(",", " ").split()]


def main() -> None:

    frames = []

    for filename in SPLIT_FILES:

        path = DATA_DIR / filename

        if not path.exists():
            print(f"Skipping missing file: {filename}")
            continue

        df = pd.read_csv(path)

        df["split"] = filename.replace(".csv", "")
        df["parsed_labels"] = df["labels"].apply(parse_labels)

        frames.append(df)

    data = pd.concat(frames, ignore_index=True)

    target_ids = set(TARGET_LABELS.keys())

    filtered = data[
        data["parsed_labels"].apply(
            lambda labels: any(label in target_ids for label in labels)
        )
    ].copy()

    filtered["emotion_names"] = filtered["parsed_labels"].apply(
        lambda labels: [
            TARGET_LABELS[label]
            for label in labels
            if label in TARGET_LABELS
        ]
    )

    single = filtered[
        filtered["emotion_names"].apply(len) == 1
    ].copy()

    multi = filtered[
        filtered["emotion_names"].apply(len) > 1
    ].copy()

    filtered.to_csv(
        DATA_DIR / "goemotions_anxiosense_all.csv",
        index=False,
    )

    single.to_csv(
        DATA_DIR / "goemotions_anxiosense_single.csv",
        index=False,
    )

    multi.to_csv(
        DATA_DIR / "goemotions_anxiosense_multi.csv",
        index=False,
    )

    counts = Counter()

    for emotions in filtered["emotion_names"]:
        counts.update(emotions)

    print("\n========== DATASET SUMMARY ==========\n")

    print(f"Total examples: {len(filtered):,}")
    print(f"Single-label: {len(single):,}")
    print(f"Multi-label : {len(multi):,}")

    print("\nEmotion counts:\n")

    for emotion, count in sorted(counts.items()):
        print(f"{emotion:<18}{count:,}")

    print("\n========== RANDOM EXAMPLES ==========\n")

    sample = filtered.sample(
        min(10, len(filtered)),
        random_state=42,
    )

    for _, row in sample.iterrows():
        print("-" * 70)
        print("Split:", row["split"])
        print("Labels:", row["emotion_names"])
        print()
        print(row["text"])


if __name__ == "__main__":
    main()
from __future__ import annotations

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent / "dreaddit_anxiety_subset.csv"


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. Run the filtering script first."
        )

    df = pd.read_csv(CSV_PATH)

    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print()

    print("Label counts:")
    print(df["label"].value_counts().sort_index())
    print()

    print("Subreddit counts:")
    print(df["subreddit"].value_counts())
    print()

    print("Random sample of 10 posts:")
    sample = df.sample(min(10, len(df)), random_state=42)

    for _, row in sample.iterrows():
        print("=" * 80)
        print(f"Subreddit: {row['subreddit']}")
        print(f"Stress label: {row['label']}")
        print(f"Confidence: {row['confidence']}")
        print(f"LIWC anxiety score: {row['lex_liwc_anx']}")
        print()
        print(row["text"])
        print()


if __name__ == "__main__":
    main()
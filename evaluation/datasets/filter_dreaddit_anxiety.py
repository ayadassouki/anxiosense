from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from datasets import load_dataset


ANXIETY_TERMS = [
    "anxiety",
    "anxious",
    "worry",
    "worried",
    "worrying",
    "nervous",
    "nervousness",
    "panic",
    "panic attack",
    "fear",
    "afraid",
    "dread",
    "overthinking",
    "racing thoughts",
    "can't relax",
    "cannot relax",
    "restless",
    "on edge",
    "heart racing",
    "shortness of breath",
    "something bad will happen",
    "sense of doom",
]


def contains_anxiety_language(text: str) -> bool:
    """Return True when text contains at least one anxiety-related phrase."""
    normalized = text.lower()

    for term in ANXIETY_TERMS:
        pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, normalized):
            return True

    return False


def main() -> None:
    dataset = load_dataset("andreagasparini/dreaddit", cache_dir=".hf_cache")

    # Combine train and test for exploration.
    train_df = dataset["train"].to_pandas()
    test_df = dataset["test"].to_pandas()

    train_df["split"] = "train"
    test_df["split"] = "test"

    df = pd.concat([train_df, test_df], ignore_index=True)

    # Method 1: explicit anxiety-related words or phrases in the text.
    df["anxiety_keyword_match"] = df["text"].fillna("").apply(
        contains_anxiety_language
    )

    # Method 2: Dreaddit's LIWC anxiety feature.
    # A value above 0 means at least some anxiety-related vocabulary was detected.
    df["liwc_anxiety_match"] = df["lex_liwc_anx"].fillna(0) > 0

    # Keep rows detected by either method.
    anxiety_df = df[
        df["anxiety_keyword_match"] | df["liwc_anxiety_match"]
    ].copy()

    # Keep only the useful columns for AnxioSense evaluation.
    selected_columns = [
        "id",
        "split",
        "subreddit",
        "post_id",
        "text",
        "label",
        "confidence",
        "lex_liwc_anx",
        "anxiety_keyword_match",
        "liwc_anxiety_match",
    ]

    anxiety_df = anxiety_df[selected_columns]

    output_dir = Path("evaluation/datasets/dreaddit")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "dreaddit_anxiety_subset.csv"
    anxiety_df.to_csv(output_file, index=False)

    print(f"Total Dreaddit rows: {len(df)}")
    print(f"Anxiety-related rows: {len(anxiety_df)}")
    print()
    print("Stress labels within anxiety subset:")
    print(anxiety_df["label"].value_counts().sort_index())
    print()
    print("Subreddits represented:")
    print(anxiety_df["subreddit"].value_counts())
    print()
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()

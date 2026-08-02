"""
src/dataset_loader.py
Load CSV or JSONL datasets into pandas DataFrames with schema validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DatasetSchemaError(ValueError):
    """Raised when a required column is missing from the loaded DataFrame."""


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_dataset(
    path: str | Path,
    split: Optional[str] = None,
    split_column: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load a dataset from path (CSV or JSONL).

    Parameters
    ----------
    path:
        Absolute or relative path to the dataset file.
    split:
        If provided, filter the DataFrame to rows where split_column == split.
        Requires split_column to also be provided.
    split_column:
        Name of the column that identifies train/validation/test splits.

    Returns
    -------
    pd.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in (".jsonl", ".json"):
        records = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        df = pd.DataFrame(records)
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}'. Expected .csv or .jsonl"
        )

    if split is not None:
        if split_column is None:
            raise ValueError(
                "split_column must be provided when split is specified"
            )
        if split_column not in df.columns:
            raise DatasetSchemaError(
                f"Split column '{split_column}' not found in dataset. "
                f"Available columns: {list(df.columns)}"
            )
        df = df[df[split_column] == split].reset_index(drop=True)

    return df


def validate_schema(df: pd.DataFrame, required_cols: List[str]) -> None:
    """
    Assert that all required_cols are present in df.

    Raises DatasetSchemaError with a clear message listing missing columns.
    """
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise DatasetSchemaError(
            f"Required column(s) missing from dataset: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def sample_dataset(
    df: pd.DataFrame,
    n: int,
    random_state: int = 42,
    stratify_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Sample up to n rows from df, optionally stratified by stratify_col.
    If n >= len(df), returns the full DataFrame unchanged.
    """
    if n >= len(df):
        return df.reset_index(drop=True)

    if stratify_col is not None and stratify_col in df.columns:
        # Proportional stratified sample
        fractions = df[stratify_col].value_counts(normalize=True)
        samples = []
        for label, frac in fractions.items():
            group = df[df[stratify_col] == label]
            group_n = max(1, round(frac * n))
            group_n = min(group_n, len(group))
            samples.append(group.sample(n=group_n, random_state=random_state))
        sampled = pd.concat(samples).sample(frac=1, random_state=random_state)
        # Adjust to exactly n if rounding causes slight over/undershoot
        return sampled.head(n).reset_index(drop=True)

    return df.sample(n=n, random_state=random_state).reset_index(drop=True)

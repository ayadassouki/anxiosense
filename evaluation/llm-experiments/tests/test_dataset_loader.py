"""
tests/test_dataset_loader.py

Offline unit tests for src/dataset_loader.py.
No API calls. No disk I/O for dataset files — uses in-memory DataFrames.
"""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Make src/ importable
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.dataset_loader import (
    DatasetSchemaError,
    load_dataset,
    sample_dataset,
    validate_schema,
)


# ---------------------------------------------------------------------------
# validate_schema
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_passes_when_all_columns_present(self):
        df = pd.DataFrame({"text": ["a", "b"], "label": [0, 1]})
        # Should not raise
        validate_schema(df, ["text", "label"])

    def test_raises_on_missing_single_column(self):
        df = pd.DataFrame({"text": ["a", "b"]})
        with pytest.raises(DatasetSchemaError) as exc_info:
            validate_schema(df, ["text", "label"])
        assert "label" in str(exc_info.value)

    def test_raises_on_multiple_missing_columns(self):
        df = pd.DataFrame({"other": [1, 2]})
        with pytest.raises(DatasetSchemaError) as exc_info:
            validate_schema(df, ["text", "label", "id"])
        msg = str(exc_info.value)
        assert "text" in msg
        assert "label" in msg

    def test_error_message_lists_available_columns(self):
        df = pd.DataFrame({"col_a": [1], "col_b": [2]})
        with pytest.raises(DatasetSchemaError) as exc_info:
            validate_schema(df, ["missing_col"])
        assert "col_a" in str(exc_info.value)

    def test_passes_with_extra_columns(self):
        df = pd.DataFrame({"text": ["a"], "label": [0], "extra": ["x"]})
        validate_schema(df, ["text", "label"])  # Should not raise


# ---------------------------------------------------------------------------
# load_dataset  (requires temp files on disk)
# ---------------------------------------------------------------------------

class TestLoadDataset:
    def test_loads_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("text,label\nhello,0\nworld,1\n")
        df = load_dataset(csv_path)
        assert len(df) == 2
        assert list(df.columns) == ["text", "label"]

    def test_loads_jsonl(self, tmp_path):
        jsonl_path = tmp_path / "test.jsonl"
        jsonl_path.write_text(
            '{"text": "hello", "label": 0}\n'
            '{"text": "world", "label": 1}\n'
        )
        df = load_dataset(jsonl_path)
        assert len(df) == 2
        assert "text" in df.columns
        assert "label" in df.columns

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent.csv")

    def test_raises_on_unsupported_format(self, tmp_path):
        bad_path = tmp_path / "data.parquet"
        bad_path.write_bytes(b"fake")
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_dataset(bad_path)

    def test_split_filter_works(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("text,label,split\na,0,train\nb,1,test\nc,0,train\n")
        df = load_dataset(csv_path, split="train", split_column="split")
        assert len(df) == 2
        assert all(df["split"] == "train")

    def test_split_filter_requires_split_column(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("text,label\na,0\nb,1\n")
        with pytest.raises(ValueError, match="split_column must be provided"):
            load_dataset(csv_path, split="train")

    def test_split_column_not_in_df_raises_schema_error(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("text,label\na,0\nb,1\n")
        with pytest.raises(DatasetSchemaError, match="Split column"):
            load_dataset(csv_path, split="train", split_column="nonexistent")


# ---------------------------------------------------------------------------
# sample_dataset
# ---------------------------------------------------------------------------

class TestSampleDataset:
    def _make_df(self, n=100):
        return pd.DataFrame({
            "text":  [f"text_{i}" for i in range(n)],
            "label": [i % 2 for i in range(n)],
        })

    def test_returns_full_df_when_n_gte_size(self):
        df = self._make_df(10)
        result = sample_dataset(df, n=100)
        assert len(result) == 10

    def test_samples_exactly_n_rows(self):
        df = self._make_df(100)
        result = sample_dataset(df, n=30)
        assert len(result) == 30

    def test_stratified_preserves_class_ratio(self):
        df = pd.DataFrame({
            "text":  [f"t{i}" for i in range(100)],
            "label": [0] * 70 + [1] * 30,
        })
        result = sample_dataset(df, n=50, stratify_col="label")
        ratio_0 = (result["label"] == 0).sum() / len(result)
        # Expect roughly 70% class 0 (±10%)
        assert 0.55 < ratio_0 < 0.85

    def test_deterministic_with_same_seed(self):
        df = self._make_df(100)
        s1 = sample_dataset(df, n=20, random_state=7)
        s2 = sample_dataset(df, n=20, random_state=7)
        assert list(s1["text"]) == list(s2["text"])

    def test_different_seeds_give_different_results(self):
        df = self._make_df(100)
        s1 = sample_dataset(df, n=20, random_state=1)
        s2 = sample_dataset(df, n=20, random_state=99)
        assert list(s1["text"]) != list(s2["text"])

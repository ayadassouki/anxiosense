"""
tests/test_metrics.py

Offline unit tests for src/metrics.py.
No API calls, no disk I/O.
All inputs are in-memory lists.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.metrics import (
    aggregate_runs,
    compute_failure_rate,
    compute_latency_stats,
    compute_metrics,
)


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_perfect_binary_prediction(self):
        y_true = [0, 0, 1, 1]
        y_pred = [0, 0, 1, 1]
        m = compute_metrics(y_true, y_pred, average="binary")
        assert m["accuracy"]  == pytest.approx(1.0)
        assert m["precision"] == pytest.approx(1.0)
        assert m["recall"]    == pytest.approx(1.0)
        assert m["f1"]        == pytest.approx(1.0)
        assert m["macro_f1"]  == pytest.approx(1.0)

    def test_all_wrong_binary(self):
        y_true = [0, 0, 1, 1]
        y_pred = [1, 1, 0, 0]
        m = compute_metrics(y_true, y_pred, average="binary")
        assert m["accuracy"] == pytest.approx(0.0)

    def test_binary_f1_known_value(self):
        # TP=2, FP=1, FN=0  → precision=2/3, recall=1, f1=2*(2/3*1)/(2/3+1)=4/5=0.8
        y_true = [1, 1, 0]
        y_pred = [1, 1, 1]
        m = compute_metrics(y_true, y_pred, average="binary")
        assert m["precision"] == pytest.approx(2/3, rel=1e-6)
        assert m["recall"]    == pytest.approx(1.0)
        assert m["f1"]        == pytest.approx(0.8)

    def test_multiclass_macro_f1(self):
        y_true = ["a", "b", "c", "a", "b", "c"]
        y_pred = ["a", "b", "c", "b", "b", "a"]
        m = compute_metrics(y_true, y_pred, average="macro")
        assert 0.0 <= m["macro_f1"] <= 1.0
        assert m["n_samples"] == 6
        assert m["n_classes"] == 3

    def test_empty_input(self):
        m = compute_metrics([], [], average="binary")
        assert m["accuracy"] == 0.0
        assert m["n_samples"] == 0

    def test_returns_confusion_matrix(self):
        y_true = [0, 1, 0, 1]
        y_pred = [0, 1, 1, 1]
        m = compute_metrics(y_true, y_pred, average="binary")
        cm = m["confusion_matrix"]
        assert isinstance(cm, list)
        assert len(cm) == 2   # 2×2 matrix
        # cm[0][0] = TN = 1, cm[0][1] = FP = 1, cm[1][0] = FN = 0, cm[1][1] = TP = 2
        assert cm[0][0] == 1
        assert cm[0][1] == 1
        assert cm[1][0] == 0
        assert cm[1][1] == 2

    def test_n_classes_correct(self):
        y_true = ["a", "b", "c"]
        y_pred = ["a", "a", "a"]
        m = compute_metrics(y_true, y_pred, average="macro")
        assert m["n_classes"] == 3


# ---------------------------------------------------------------------------
# compute_latency_stats
# ---------------------------------------------------------------------------

class TestComputeLatencyStats:
    def test_known_values(self):
        latencies = [100.0, 200.0, 300.0, 400.0, 500.0]
        stats = compute_latency_stats(latencies)
        assert stats["median"] == pytest.approx(300.0)
        assert stats["p25"]    == pytest.approx(200.0)
        assert stats["p75"]    == pytest.approx(400.0)
        assert stats["min"]    == pytest.approx(100.0)
        assert stats["max"]    == pytest.approx(500.0)

    def test_empty_list(self):
        stats = compute_latency_stats([])
        assert stats["median"] == 0.0

    def test_single_value(self):
        stats = compute_latency_stats([500.0])
        assert stats["median"] == pytest.approx(500.0)
        assert stats["p95"]    == pytest.approx(500.0)

    def test_p95_upper_tail(self):
        # 20 values: 19 at 100ms, 1 at 9000ms
        latencies = [100.0] * 19 + [9000.0]
        stats = compute_latency_stats(latencies)
        assert stats["p95"] > 100.0
        assert stats["p95"] <= 9000.0


# ---------------------------------------------------------------------------
# compute_failure_rate
# ---------------------------------------------------------------------------

class TestComputeFailureRate:
    def test_no_failures(self):
        results = [{"label": 0}, {"label": 1}, {"label": 1}]
        assert compute_failure_rate(results) == pytest.approx(0.0)

    def test_all_failures(self):
        results = [{"label": None}, {"label": None}]
        assert compute_failure_rate(results) == pytest.approx(1.0)

    def test_half_failures(self):
        results = [{"label": None}, {"label": 1}]
        assert compute_failure_rate(results) == pytest.approx(0.5)

    def test_empty_list(self):
        assert compute_failure_rate([]) == 0.0


# ---------------------------------------------------------------------------
# aggregate_runs
# ---------------------------------------------------------------------------

class TestAggregateRuns:
    def test_median_of_two_runs(self):
        run1 = {"accuracy": 0.8, "f1": 0.7, "macro_f1": 0.75, "n_samples": 100, "n_classes": 2,
                "precision": 0.8, "recall": 0.7, "confusion_matrix": [[1, 0], [0, 1]]}
        run2 = {"accuracy": 0.9, "f1": 0.85, "macro_f1": 0.88, "n_samples": 100, "n_classes": 2,
                "precision": 0.9, "recall": 0.85, "confusion_matrix": [[1, 0], [0, 1]]}
        agg = aggregate_runs([run1, run2])
        assert agg["median_accuracy"] == pytest.approx(0.85)
        assert agg["median_macro_f1"] == pytest.approx((0.75 + 0.88) / 2)

    def test_single_run(self):
        run = {"accuracy": 0.9, "f1": 0.88, "macro_f1": 0.88, "n_samples": 50, "n_classes": 2,
               "precision": 0.9, "recall": 0.88, "confusion_matrix": [[1]]}
        agg = aggregate_runs([run])
        assert agg["median_accuracy"] == pytest.approx(0.9)
        assert agg["n_runs"] == 1

    def test_empty_input(self):
        assert aggregate_runs([]) == {}

    def test_five_runs_median(self):
        accuracies = [0.6, 0.7, 0.8, 0.9, 1.0]
        runs = [
            {"accuracy": a, "f1": a, "macro_f1": a, "n_samples": 100, "n_classes": 2,
             "precision": a, "recall": a, "confusion_matrix": [[1]]}
            for a in accuracies
        ]
        agg = aggregate_runs(runs)
        # Median of [0.6, 0.7, 0.8, 0.9, 1.0] = 0.8
        assert agg["median_accuracy"] == pytest.approx(0.8)
        assert agg["n_runs"] == 5

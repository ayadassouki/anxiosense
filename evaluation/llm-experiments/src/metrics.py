"""
src/metrics.py

Compute evaluation metrics for AnxioSense LLM experiments.

All metric functions are pure (no I/O) so they can be unit-tested without
datasets, models, or API keys.

Functions
---------
    compute_metrics(y_true, y_pred)
        → accuracy, precision, recall, f1, macro_f1, confusion_matrix

    compute_latency_stats(latencies)
        → median, p25, p75, p95

    compute_failure_rate(results)
        → fraction of records with label == None

    aggregate_runs(per_run_metrics)
        → median of each metric across runs
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


# ---------------------------------------------------------------------------
# Classification metrics
# ---------------------------------------------------------------------------

def compute_metrics(
    y_true: List[Any],
    y_pred: List[Any],
    average: str = "macro",
    labels: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Compute classification metrics for a single run.

    Parameters
    ----------
    y_true: ground-truth labels (int or str)
    y_pred: predicted labels — must be the same type as y_true
    average: sklearn average parameter for multi-class metrics.
             Use "binary" for binary tasks, "macro" for multi-class.
    labels:  explicit, ordered class space. Strongly recommended for multiclass.

             When omitted, sklearn infers the classes from whatever happens to
             appear in y_true/y_pred. That makes confusion matrices from
             different experiment cells DIFFERENT SHAPES and silently drops any
             class that no sample predicted, so matrices cannot be compared or
             stacked across strategies. Passing the full label space fixes the
             row/column order and keeps every class present, including ones
             with zero support.

    Returns
    -------
    dict with keys:
        accuracy       float [0, 1]
        precision      float [0, 1]  per-class average
        recall         float [0, 1]  per-class average
        f1             float [0, 1]  per-class average (same average param)
        macro_f1       float [0, 1]  always macro-averaged
        confusion_matrix  list[list[int]]
        confusion_labels  list  row/column order of the confusion matrix
        per_class_f1   dict  class → F1, useful for error analysis
        n_samples      int  number of samples evaluated
        n_classes      int  number of classes in the evaluated label space
    """
    if len(y_true) == 0:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "macro_f1": 0.0,
            "confusion_matrix": [],
            "confusion_labels": list(labels) if labels else [],
            "per_class_f1": {},
            "n_samples": 0,
            "n_classes": 0,
        }

    # Determine zero_division behavior
    zero_div = 0

    # Fixed, ordered class space. Falls back to the observed union so the
    # matrix still covers predicted-but-never-true classes.
    if labels is not None:
        class_space = list(labels)
    else:
        class_space = sorted(set(y_true) | set(y_pred), key=str)

    # 'binary' averaging rejects an explicit multi-class label list; sklearn
    # infers the positive class itself, so only pass labels for non-binary.
    avg_kwargs = {} if average == "binary" else {"labels": class_space}

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(
        y_true, y_pred, average=average, zero_division=zero_div, **avg_kwargs
    )
    rec = recall_score(
        y_true, y_pred, average=average, zero_division=zero_div, **avg_kwargs
    )
    f1 = f1_score(
        y_true, y_pred, average=average, zero_division=zero_div, **avg_kwargs
    )
    macro_f1 = f1_score(
        y_true, y_pred, average="macro", labels=class_space, zero_division=zero_div
    )
    cm = confusion_matrix(y_true, y_pred, labels=class_space).tolist()

    per_class = f1_score(
        y_true, y_pred, average=None, labels=class_space, zero_division=zero_div
    )

    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "macro_f1": float(macro_f1),
        "confusion_matrix": cm,
        "confusion_labels": [str(c) for c in class_space],
        "per_class_f1": {
            str(c): round(float(v), 4) for c, v in zip(class_space, per_class)
        },
        "n_samples": len(y_true),
        "n_classes": len(class_space),
    }


# ---------------------------------------------------------------------------
# Latency statistics
# ---------------------------------------------------------------------------

def compute_latency_stats(latencies: List[float]) -> Dict[str, float]:
    """
    Compute summary statistics for a list of per-call latency values (ms).

    Returns
    -------
    dict with keys: median, p25, p75, p95, mean, min, max
    All values in milliseconds.
    """
    if not latencies:
        return {
            "median": 0.0,
            "p25":    0.0,
            "p75":    0.0,
            "p95":    0.0,
            "mean":   0.0,
            "min":    0.0,
            "max":    0.0,
        }

    arr = np.array(latencies, dtype=float)
    return {
        "median": float(np.median(arr)),
        "p25":    float(np.percentile(arr, 25)),
        "p75":    float(np.percentile(arr, 75)),
        "p95":    float(np.percentile(arr, 95)),
        "mean":   float(np.mean(arr)),
        "min":    float(np.min(arr)),
        "max":    float(np.max(arr)),
    }


# ---------------------------------------------------------------------------
# Failure rate
# ---------------------------------------------------------------------------

def compute_failure_rate(results: List[Dict[str, Any]]) -> float:
    """
    Compute the fraction of results where label is None (parse / API failure).

    Parameters
    ----------
    results: list of result records (each must have a "label" key).

    Returns
    -------
    float in [0.0, 1.0]; 0.0 if results is empty.
    """
    if not results:
        return 0.0
    n_failed = sum(1 for r in results if r.get("label") is None)
    return n_failed / len(results)


# ---------------------------------------------------------------------------
# Cross-run aggregation
# ---------------------------------------------------------------------------

def aggregate_runs(
    per_run_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate per-run metrics by taking the median of each numeric field.

    Parameters
    ----------
    per_run_metrics:
        List of dicts, one per run.  Each dict is the output of compute_metrics().

    Returns
    -------
    dict with the same keys as the input dicts, values replaced by their
    median across runs.  Non-numeric fields (e.g. confusion_matrix) are
    collected as-is from the last run.
    """
    if not per_run_metrics:
        return {}

    aggregated: Dict[str, Any] = {}

    # BUGFIX: this previously aggregated a HARDCODED key list that omitted
    # latency_median_ms and failure_rate. Callers asking for
    # agg["median_latency_median_ms"] or agg["median_failure_rate"] silently got
    # their .get() default of 0, so every summary table reported 0 ms latency
    # and a 0.00 failure rate regardless of the underlying data.
    #
    # Aggregate every numeric field actually present instead. Booleans are
    # excluded because bool is a subclass of int and averaging flags is
    # meaningless. NaN/inf are dropped so one bad run cannot poison the median.
    def _is_numeric(v: Any) -> bool:
        return (
            isinstance(v, (int, float))
            and not isinstance(v, bool)
            and np.isfinite(v)
        )

    numeric_keys = sorted({
        k for r in per_run_metrics for k, v in r.items() if _is_numeric(v)
    })

    for key in numeric_keys:
        values = [r[key] for r in per_run_metrics if _is_numeric(r.get(key))]
        if values:
            aggregated[f"median_{key}"] = float(np.median(values))
            aggregated[f"std_{key}"]    = float(np.std(values))

    # Keep the last run's confusion matrix as a representative sample
    if "confusion_matrix" in per_run_metrics[-1]:
        aggregated["confusion_matrix_last_run"] = per_run_metrics[-1]["confusion_matrix"]

    aggregated["n_runs"] = len(per_run_metrics)
    return aggregated

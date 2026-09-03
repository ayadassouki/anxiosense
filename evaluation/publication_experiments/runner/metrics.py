"""Metric infrastructure. No interpretation, no significance testing, no sklearn.

Every table carries its denominators. A failed call is never counted as a
prediction, and failures are never silently dropped - they are reported as counts.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Iterable

METRIC_POLICY_VERSION = "1.0.0"


@dataclass(frozen=True)
class MetricPolicy:
    """Frozen scoring policy. Written verbatim into every summary."""
    version: str = METRIC_POLICY_VERSION
    # Historical protocol (AnxioSense_Experiment_Results README): the deterministic
    # crisis path fires before any model call, so those items are not attributable
    # to a model. Reported separately, never silently dropped.
    exclude_safety_intercept_from_model_attribution: bool = True
    # Denominator for effective accuracy: every dispatched item, so a model cannot
    # look better by declining to answer.
    effective_accuracy_denominator: str = "all_attributable"


def _prf(y_true: list, y_pred: list, labels: list) -> dict[str, dict[str, float]]:
    out = {}
    for c in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[str(c)] = {"precision": prec, "recall": rec, "f1": f1,
                       "support": sum(1 for t in y_true if t == c),
                       "tp": tp, "fp": fp, "fn": fn}
    return out


def cell_metrics(records: Iterable[dict], *, labels: list,
                 majority_baseline: float | None = None,
                 policy: MetricPolicy | None = None) -> dict[str, Any]:
    """records: parsed records for ONE cell. Each needs ground_truth, parsed
    prediction, prediction_valid, failure_class, transport outcome."""
    policy = policy or MetricPolicy()
    recs = list(records)

    n_total = len(recs)
    n_safety = sum(1 for r in recs if r.get("failure_class") == "SAFETY_INTERCEPT")
    attributable = [r for r in recs if r.get("failure_class") != "SAFETY_INTERCEPT"] \
        if policy.exclude_safety_intercept_from_model_attribution else recs

    valid = [r for r in attributable if r.get("prediction_valid")]
    model_invalid = [r for r in attributable if r.get("failure_class") == "MODEL_BEHAVIOUR"]
    infra = [r for r in attributable
             if str(r.get("failure_class", "")).startswith("INFRA")]

    buckets = {
        "N_total": n_total,
        "N_attributable": len(attributable),
        "N_successful_valid_predictions": len(valid),
        "N_model_behavior_invalid": len(model_invalid),
        "N_infrastructure_failed": len(infra),
        "N_safety_intercept": n_safety,
    }
    unaccounted = len(attributable) - (len(valid) + len(model_invalid) + len(infra))
    buckets["N_unaccounted"] = unaccounted   # must be 0; surfaced rather than hidden

    result: dict[str, Any] = {
        "policy": asdict(policy),
        "labels": [str(c) for c in labels],
        "buckets": buckets,
        "rates": {
            "evaluability": len(valid) / len(attributable) if attributable else None,
            "model_invalid_rate": len(model_invalid) / len(attributable) if attributable else None,
            "infrastructure_failure_rate": len(infra) / len(attributable) if attributable else None,
        },
        "majority_baseline": majority_baseline,
    }

    if not valid:
        result["metrics"] = None
        return result

    y_true = [r["ground_truth"] for r in valid]
    y_pred = [r["parsed_prediction"] for r in valid]
    per_class = _prf(y_true, y_pred, labels)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)

    conf: dict[str, dict[str, int]] = {str(a): {str(b): 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        if str(t) in conf and str(p) in conf[str(t)]:
            conf[str(t)][str(p)] += 1

    result["metrics"] = {
        "accuracy_conditional": correct / len(valid),
        "accuracy_effective": correct / len(attributable) if attributable else None,
        "macro_precision": sum(v["precision"] for v in per_class.values()) / len(labels),
        "macro_recall": sum(v["recall"] for v in per_class.values()) / len(labels),
        "macro_f1": sum(v["f1"] for v in per_class.values()) / len(labels),
        "per_class": per_class,
        "confusion_matrix": conf,
        "class_support": {str(c): sum(1 for t in y_true if t == c) for c in labels},
    }
    return result


def aggregate_cells(cells: dict[str, dict]) -> dict[str, Any]:
    """Roll cell summaries up per (dataset, model, strategy) across runs. Descriptive only."""
    grouped = defaultdict(list)
    for cell_id, summary in cells.items():
        ds, model, strategy, _run = cell_id.split("|")
        grouped[(ds, model, strategy)].append(summary)

    out = {}
    for (ds, model, strategy), summaries in grouped.items():
        vals = defaultdict(list)
        for s in summaries:
            if s.get("metrics"):
                for k in ("accuracy_conditional", "accuracy_effective", "macro_f1"):
                    if s["metrics"].get(k) is not None:
                        vals[k].append(s["metrics"][k])
            vals["evaluability"].append(s["rates"]["evaluability"])
        def mean(xs): 
            xs = [x for x in xs if x is not None]
            return sum(xs) / len(xs) if xs else None
        def sd(xs):
            xs = [x for x in xs if x is not None]
            if len(xs) < 2: return 0.0
            m = sum(xs) / len(xs)
            return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
        out[f"{ds}|{model}|{strategy}"] = {
            "n_runs": len(summaries),
            **{k: {"mean": mean(v), "sd": sd(v)} for k, v in vals.items()},
        }
    return out

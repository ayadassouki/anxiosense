# Table 2. Dreaddit (binary stress vs non-stress; Referral agent) — five-run results

Descriptive results, 5 runs per configuration, 715 scoreable items per run
(16 safety-intercepted per run, excluded from model attribution by MetricPolicy 1.0.0).
Majority baseline 0.516084. Values are mean ± SD across the 5 runs, shown to 3 decimals.
No cell is marked as a winner; statistical comparisons are in `results/inferential_2026-09-21/`.

| Model | Prompt strategy | Conditional accuracy | Effective accuracy | Macro precision | Macro recall | Macro F1 | Evaluability | Safety intercepts (5 runs) | Model-invalid outputs (5 runs) |
|---|---|---|---|---|---|---|---|---|---|
| Gemma 4 31B IT | zero-shot | 0.693 ± 0.004 | 0.693 ± 0.004 | 0.760 ± 0.003 | 0.697 ± 0.004 | 0.675 ± 0.005 | 1.000 ± 0.000 | 80 | 0 |
| Gemma 4 31B IT | zero-shot-cot | 0.675 ± 0.001 | 0.675 ± 0.001 | 0.754 ± 0.004 | 0.679 ± 0.001 | 0.650 ± 0.001 | 1.000 ± 0.000 | 80 | 0 |
| Gemma 4 31B IT | one-shot-cot | 0.676 ± 0.006 | 0.676 ± 0.006 | 0.756 ± 0.005 | 0.680 ± 0.006 | 0.651 ± 0.008 | 1.000 ± 0.000 | 80 | 0 |
| Llama 4 Scout | zero-shot | 0.752 ± 0.005 | 0.730 ± 0.003 | 0.755 ± 0.005 | 0.753 ± 0.005 | 0.752 ± 0.005 | 0.970 ± 0.005 | 80 | 106 |
| Llama 4 Scout | zero-shot-cot | 0.744 ± 0.005 | 0.733 ± 0.005 | 0.753 ± 0.004 | 0.745 ± 0.004 | 0.742 ± 0.005 | 0.985 ± 0.002 | 80 | 52 |
| Llama 4 Scout | one-shot-cot | 0.752 ± 0.004 | 0.750 ± 0.005 | 0.758 ± 0.004 | 0.753 ± 0.004 | 0.751 ± 0.005 | 0.998 ± 0.001 | 80 | 8 |
| Mistral Small 4 | zero-shot | 0.686 ± 0.003 | 0.686 ± 0.004 | 0.758 ± 0.003 | 0.690 ± 0.003 | 0.666 ± 0.004 | 1.000 ± 0.001 | 80 | 1 |
| Mistral Small 4 | zero-shot-cot | 0.661 ± 0.004 | 0.661 ± 0.004 | 0.752 ± 0.008 | 0.666 ± 0.004 | 0.631 ± 0.004 | 1.000 ± 0.001 | 80 | 1 |
| Mistral Small 4 | one-shot-cot | 0.674 ± 0.005 | 0.674 ± 0.005 | 0.757 ± 0.007 | 0.678 ± 0.005 | 0.648 ± 0.006 | 1.000 ± 0.000 | 80 | 0 |
| Phi-4 | zero-shot | 0.745 ± 0.012 | 0.722 ± 0.016 | 0.751 ± 0.011 | 0.746 ± 0.012 | 0.744 ± 0.013 | 0.970 ± 0.010 | 80 | 106 |
| Phi-4 | zero-shot-cot | 0.706 ± 0.003 | 0.700 ± 0.002 | 0.742 ± 0.003 | 0.709 ± 0.003 | 0.696 ± 0.004 | 0.992 ± 0.003 | 80 | 29 |
| Phi-4 | one-shot-cot | 0.733 ± 0.010 | 0.730 ± 0.010 | 0.747 ± 0.011 | 0.735 ± 0.010 | 0.730 ± 0.010 | 0.995 ± 0.001 | 80 | 16 |
| Qwen 3.5 27B | zero-shot | 0.692 ± 0.001 | 0.691 ± 0.001 | 0.757 ± 0.001 | 0.696 ± 0.001 | 0.674 ± 0.001 | 0.998 ± 0.001 | 80 | 7 |
| Qwen 3.5 27B | zero-shot-cot | 0.653 ± 0.004 | 0.602 ± 0.005 | 0.747 ± 0.004 | 0.634 ± 0.005 | 0.598 ± 0.006 | 0.923 ± 0.004 | 80 | 269 |
| Qwen 3.5 27B | one-shot-cot | 0.648 ± 0.001 | 0.647 ± 0.002 | 0.757 ± 0.001 | 0.653 ± 0.001 | 0.610 ± 0.002 | 0.999 ± 0.001 | 80 | 4 |

Definitions (MetricPolicy 1.0.0, unchanged).

- **Conditional accuracy** = correct / valid predictions.
- **Effective accuracy** = correct / attributable records; a model-invalid output counts as incorrect.
- **Macro precision / recall / F1** = unweighted mean over the fixed label list, computed on valid predictions.
- **Evaluability** = valid / attributable.
- **Safety intercepts** are deterministic pre-LLM interceptions, identical in every cell, excluded from
  model attribution and reported here as the 5-run count.
- **Model-invalid outputs** are records with `failure_class = MODEL_BEHAVIOUR` (unparseable, truncated,
  `{}`, refusal or out-of-vocabulary), kept exactly as the frozen parser classified them.

Sources: conditional accuracy, effective accuracy, macro F1, evaluability and all counts are taken verbatim
from `descriptive_2026-09-21/aggregate_results.csv`; macro precision and macro recall from the verified
`rq1_rq3_reporting_2026-09-21/rq12_full_precision.json`, independently re-derived from
`descriptive_2026-09-21/per_run_results.csv` as a cross-check. A displayed 1.000 may hide a small shortfall;
the count columns give the exact numbers.

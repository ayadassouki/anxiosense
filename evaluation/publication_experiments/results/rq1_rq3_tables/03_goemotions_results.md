# Table 3. GoEmotions (5-class distress taxonomy; Emotion agent) — five-run results

Descriptive results, 5 runs per configuration, 623 scoreable items per run
(1 safety-intercepted per run, excluded from model attribution by MetricPolicy 1.0.0).
Majority baseline 0.781701. Values are mean ± SD across the 5 runs, shown to 3 decimals.
No cell is marked as a winner; statistical comparisons are in `results/inferential_2026-09-21/`.

| Model | Prompt strategy | Conditional accuracy | Effective accuracy | Macro precision | Macro recall | Macro F1 | Evaluability | Safety intercepts (5 runs) | Model-invalid outputs (5 runs) |
|---|---|---|---|---|---|---|---|---|---|
| Gemma 4 31B IT | zero-shot | 0.820 ± 0.004 | 0.820 ± 0.004 | 0.711 ± 0.015 | 0.552 ± 0.004 | 0.593 ± 0.007 | 1.000 ± 0.000 | 5 | 0 |
| Gemma 4 31B IT | zero-shot-cot | 0.817 ± 0.004 | 0.817 ± 0.004 | 0.709 ± 0.011 | 0.543 ± 0.003 | 0.583 ± 0.008 | 1.000 ± 0.000 | 5 | 0 |
| Gemma 4 31B IT | one-shot-cot | 0.815 ± 0.004 | 0.813 ± 0.003 | 0.695 ± 0.010 | 0.551 ± 0.002 | 0.585 ± 0.005 | 0.998 ± 0.003 | 5 | 7 |
| Llama 4 Scout | zero-shot | 0.727 ± 0.007 | 0.700 ± 0.008 | 0.497 ± 0.017 | 0.632 ± 0.014 | 0.520 ± 0.017 | 0.964 ± 0.004 | 5 | 113 |
| Llama 4 Scout | zero-shot-cot | 0.728 ± 0.010 | 0.683 ± 0.009 | 0.517 ± 0.013 | 0.619 ± 0.027 | 0.530 ± 0.013 | 0.938 ± 0.002 | 5 | 193 |
| Llama 4 Scout | one-shot-cot | 0.767 ± 0.008 | 0.732 ± 0.009 | 0.536 ± 0.012 | 0.622 ± 0.010 | 0.544 ± 0.013 | 0.954 ± 0.002 | 5 | 143 |
| Mistral Small 4 | zero-shot | 0.770 ± 0.008 | 0.766 ± 0.005 | 0.542 ± 0.018 | 0.623 ± 0.012 | 0.561 ± 0.011 | 0.995 ± 0.003 | 5 | 17 |
| Mistral Small 4 | zero-shot-cot | 0.746 ± 0.007 | 0.741 ± 0.008 | 0.499 ± 0.007 | 0.633 ± 0.016 | 0.536 ± 0.010 | 0.994 ± 0.001 | 5 | 19 |
| Mistral Small 4 | one-shot-cot | 0.786 ± 0.005 | 0.783 ± 0.005 | 0.592 ± 0.011 | 0.617 ± 0.006 | 0.594 ± 0.008 | 0.996 ± 0.002 | 5 | 12 |
| Phi-4 | zero-shot | 0.784 ± 0.008 | 0.736 ± 0.016 | 0.583 ± 0.026 | 0.551 ± 0.013 | 0.534 ± 0.016 | 0.939 ± 0.015 | 5 | 191 |
| Phi-4 | zero-shot-cot | 0.809 ± 0.003 | 0.762 ± 0.009 | 0.635 ± 0.019 | 0.577 ± 0.013 | 0.563 ± 0.011 | 0.941 ± 0.014 | 5 | 183 |
| Phi-4 | one-shot-cot | 0.801 ± 0.004 | 0.673 ± 0.126 | 0.647 ± 0.030 | 0.550 ± 0.056 | 0.541 ± 0.049 | 0.840 ± 0.154 | 5 | 499 |
| Qwen 3.5 27B | zero-shot | 0.786 ± 0.001 | 0.786 ± 0.001 | 0.594 ± 0.007 | 0.565 ± 0.007 | 0.572 ± 0.007 | 1.000 ± 0.000 | 5 | 0 |
| Qwen 3.5 27B | zero-shot-cot | 0.790 ± 0.002 | 0.790 ± 0.002 | 0.607 ± 0.004 | 0.566 ± 0.008 | 0.579 ± 0.006 | 1.000 ± 0.000 | 5 | 0 |
| Qwen 3.5 27B | one-shot-cot | 0.773 ± 0.000 | 0.770 ± 0.000 | 0.559 ± 0.000 | 0.585 ± 0.000 | 0.567 ± 0.000 | 0.997 ± 0.000 | 5 | 10 |

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

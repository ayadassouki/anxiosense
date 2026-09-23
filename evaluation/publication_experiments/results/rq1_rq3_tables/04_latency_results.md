# Table 4. RQ3 — DESCRIPTIVE latency results (no inferential claim)

These are **descriptive** end-to-end latency summaries, copied verbatim from the verified RQ3 artifacts
(`rq1_rq3_reporting_2026-09-21/tables/rq3_dreaddit_latency.csv` and `..._goemotions_latency.csv`). Nothing was
recomputed from raw runs, and no statistical test was run on latency.

| Dataset | Model | Prompt strategy | Client mean (s) | Client median (s) | Client p90 (s) | Server mean (s) | n (5 runs) | Retried assessments (5 runs) | Source run |
|---|---|---|---|---|---|---|---|---|---|
| dreaddit | Gemma 4 31B IT | zero-shot | 15.07 ± 2.73 | 12.06 ± 2.13 | 26.53 ± 5.80 | 15.07 ± 2.73 | 3495 | 10 | pub_011_dreaddit_gemma_coreweave |
| dreaddit | Gemma 4 31B IT | zero-shot-cot | 13.10 ± 1.97 | 10.26 ± 1.65 | 22.92 ± 4.03 | 13.09 ± 1.97 | 3495 | 10 | pub_011_dreaddit_gemma_coreweave |
| dreaddit | Gemma 4 31B IT | one-shot-cot | 15.14 ± 3.77 | 12.68 ± 3.91 | 26.51 ± 7.79 | 15.14 ± 3.77 | 3495 | 34 | pub_011_dreaddit_gemma_coreweave/pub_013_dreaddit_gemma_coreweave_osc_run5 |
| dreaddit | Llama 4 Scout | zero-shot | 12.46 ± 0.88 | 12.07 ± 0.01 | 17.53 ± 2.49 | 12.46 ± 0.88 | 3495 | 4 | pub_003_dreaddit_llama |
| dreaddit | Llama 4 Scout | zero-shot-cot | 14.08 ± 2.11 | 12.70 ± 1.38 | 19.92 ± 4.02 | 14.08 ± 2.11 | 3495 | 9 | pub_003_dreaddit_llama |
| dreaddit | Llama 4 Scout | one-shot-cot | 10.23 ± 0.64 | 9.67 ± 1.34 | 13.32 ± 1.61 | 10.23 ± 0.64 | 3495 | 2 | pub_003_dreaddit_llama |
| dreaddit | Mistral Small 4 | zero-shot | 5.36 ± 0.03 | 6.06 ± 0.00 | 6.07 ± 0.00 | 5.35 ± 0.03 | 3495 | 3 | pub_002_dreaddit_mistral |
| dreaddit | Mistral Small 4 | zero-shot-cot | 5.25 ± 0.11 | 6.06 ± 0.01 | 6.07 ± 0.01 | 5.24 ± 0.11 | 3495 | 0 | pub_002_dreaddit_mistral |
| dreaddit | Mistral Small 4 | one-shot-cot | 4.89 ± 0.12 | 6.04 ± 0.00 | 6.05 ± 0.00 | 4.88 ± 0.12 | 3495 | 0 | pub_002_dreaddit_mistral |
| dreaddit | Phi-4 | zero-shot | 12.91 ± 1.36 | 10.88 ± 1.64 | 18.10 ± 3.67 | 12.90 ± 1.36 | 3495 | 10 | pub_005_dreaddit_phi |
| dreaddit | Phi-4 | zero-shot-cot | 12.86 ± 1.19 | 12.08 ± 0.01 | 16.30 ± 2.68 | 12.85 ± 1.19 | 3495 | 0 | pub_005_dreaddit_phi |
| dreaddit | Phi-4 | one-shot-cot | 10.13 ± 1.84 | 9.65 ± 1.35 | 12.68 ± 3.29 | 10.12 ± 1.84 | 3495 | 3 | pub_005_dreaddit_phi |
| dreaddit | Qwen 3.5 27B | zero-shot | 9.05 ± 0.27 | 9.08 ± 0.00 | 9.70 ± 1.34 | 9.04 ± 0.27 | 3495 | 0 | pub_001_dreaddit_qwen |
| dreaddit | Qwen 3.5 27B | zero-shot-cot | 8.67 ± 0.24 | 9.08 ± 0.00 | 9.11 ± 0.01 | 8.66 ± 0.24 | 3495 | 0 | pub_001_dreaddit_qwen |
| dreaddit | Qwen 3.5 27B | one-shot-cot | 8.40 ± 0.45 | 9.07 ± 0.01 | 9.11 ± 0.02 | 8.39 ± 0.45 | 3495 | 1 | pub_001_dreaddit_qwen |
| goemotions | Gemma 4 31B IT | zero-shot | 11.54 ± 1.38 | 7.88 ± 1.65 | 19.91 ± 2.70 | 11.53 ± 1.38 | 3110 | 9 | pub_012_goemotions715_gemma_coreweave |
| goemotions | Gemma 4 31B IT | zero-shot-cot | 14.17 ± 3.54 | 11.48 ± 3.30 | 24.14 ± 6.74 | 14.16 ± 3.54 | 3110 | 21 | pub_012_goemotions715_gemma_coreweave |
| goemotions | Gemma 4 31B IT | one-shot-cot | 10.09 ± 2.75 | 7.86 ± 2.69 | 16.29 ± 6.59 | 10.09 ± 2.75 | 3110 | 22 | pub_012_goemotions715_gemma_coreweave |
| goemotions | Llama 4 Scout | zero-shot | 10.78 ± 1.26 | 9.07 ± 2.13 | 18.11 ± 2.12 | 10.77 ± 1.26 | 3110 | 22 | pub_009_goemotions715_llama |
| goemotions | Llama 4 Scout | zero-shot-cot | 11.02 ± 2.20 | 9.07 ± 3.01 | 19.32 ± 3.45 | 11.01 ± 2.20 | 3110 | 28 | pub_009_goemotions715_llama |
| goemotions | Llama 4 Scout | one-shot-cot | 10.00 ± 1.34 | 8.46 ± 1.34 | 14.49 ± 2.52 | 9.99 ± 1.34 | 3110 | 31 | pub_009_goemotions715_llama |
| goemotions | Mistral Small 4 | zero-shot | 3.98 ± 0.48 | 3.05 ± 0.01 | 6.06 ± 0.01 | 3.97 ± 0.48 | 3110 | 0 | pub_006_goemotions715_mistral |
| goemotions | Mistral Small 4 | zero-shot-cot | 3.43 ± 0.11 | 3.04 ± 0.00 | 5.44 ± 1.34 | 3.42 ± 0.11 | 3110 | 0 | pub_006_goemotions715_mistral |
| goemotions | Mistral Small 4 | one-shot-cot | 3.32 ± 0.16 | 3.04 ± 0.00 | 3.64 ± 1.34 | 3.31 ± 0.16 | 3110 | 1 | pub_006_goemotions715_mistral |
| goemotions | Phi-4 | zero-shot | 13.07 ± 0.35 | 11.47 ± 1.30 | 18.07 ± 0.00 | 13.06 ± 0.35 | 3110 | 17 | pub_008_goemotions715_phi |
| goemotions | Phi-4 | zero-shot-cot | 13.09 ± 1.89 | 9.65 ± 1.35 | 21.69 ± 5.39 | 13.08 ± 1.89 | 3110 | 34 | pub_008_goemotions715_phi |
| goemotions | Phi-4 | one-shot-cot | 10.63 ± 2.23 | 9.65 ± 1.35 | 17.48 ± 6.52 | 10.63 ± 2.23 | 3110 | 5 | pub_008_goemotions715_phi |
| goemotions | Qwen 3.5 27B | zero-shot | 7.27 ± 0.56 | 6.04 ± 0.00 | 9.65 ± 1.34 | 7.27 ± 0.56 | 3110 | 3 | pub_007_goemotions715_qwen |
| goemotions | Qwen 3.5 27B | zero-shot-cot | 7.32 ± 0.37 | 6.04 ± 0.00 | 9.05 ± 0.00 | 7.32 ± 0.37 | 3110 | 0 | pub_007_goemotions715_qwen |
| goemotions | Qwen 3.5 27B | one-shot-cot | 7.32 ± 0.33 | 6.04 ± 0.00 | 9.05 ± 0.01 | 7.32 ± 0.33 | 3110 | 9 | pub_007_goemotions715_qwen |

What these numbers are.

- **Client mean/median/p90** = the runner's wall-clock around the whole HTTP POST to the AnxioSense
  `/api/workflow/evaluate` endpoint, for the terminal attempt of each assessment; mean ± SD over the five
  per-run statistics.
- **Server mean** = the Express-measured duration of the same request.
- Safety-intercepted assessments are excluded (they short-circuit before any agent call) and are counted
  separately in the source tables.

Limitations, preserved from the RQ3 audit.

- Only terminal client-side and server-side request latency exists. There is **no per-agent timing, no phase
  breakdown and no time-to-first-token** in the recorded data.
- Latency is quantised by the server's 3-second poll cadence (99.97% of values lie within 0.5 s of a 3 s
  multiple), so differences smaller than 3 s are at or below the measurement resolution.
- Prompt-strategy blocks were executed **sequentially** within each model, so strategy is confounded with
  time of day, provider load and local state. These numbers do not support a causal claim that any
  prompting strategy is faster.
- Runs were executed on two different machines and across different upstream providers, so cross-model and
  cross-dataset latency comparisons are not controlled.
- Time spent in failed attempts and retry backoff is excluded; the retry count is shown per row.
- Model **display labels** in this table are normalised to the authoritative publication-config display names,
  so that Tables 1–4 read consistently: the source tables' "Gemma 4 31B" is shown as "Gemma 4 31B IT" and
  "Qwen3.5 27B" as "Qwen 3.5 27B". This is a presentation-only substitution performed by an explicit,
  fail-closed mapping in the generator. Every other field — latency values, counts, source runs — is copied
  verbatim, no model ID was altered, and no source artifact was modified. `04_latency_results.csv` keeps the
  verbatim source label in `model_source_label` and the model ID in `model_id`.

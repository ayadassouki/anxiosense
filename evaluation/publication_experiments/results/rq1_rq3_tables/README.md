# RQ1–RQ3 publication tables

Presentation tables for the **already-frozen** AnxioSense RQ1–RQ3 analysis. This folder contains no new
analysis: it renders values that were computed, frozen and independently verified on 2026-09-21.

- **No experiment was rerun** and **no model API was called**.
- **No inferential analysis was changed.** Confidence intervals, permutation tests, McNemar tests and Holm
  corrections live in `results/inferential_2026-09-21/` and are not reproduced or recomputed here.
- **Nothing outside this folder was written.** All inputs are opened read-only and sha256-gated.
- Tables are generated **deterministically** by `code/generate_rq1_rq3_tables.py`: no timestamps, no
  randomness, identical bytes on every run.
- **RQ4** (expert Likert ratings and Cohen's kappa) is a separate evaluation and is **not** included here.

## Files

| File | Contents |
|---|---|
| `01_model_configuration.csv` / `.md` | Model, provider pin, observed provider, quantization directive, datasets, strategies, runs, decoding parameters |
| `02_dreaddit_results.csv` / `.md` | Dreaddit, 15 rows (5 models × 3 prompting strategies) |
| `03_goemotions_results.csv` / `.md` | GoEmotions, 15 rows |
| `04_latency_results.csv` / `.md` | RQ3 descriptive latency, 30 rows (both datasets) |
| `code/generate_rq1_rq3_tables.py` | The generator |

The `.md` files are the publication-ready renderings (3 decimals, mean ± SD). The `.csv` files carry the same
rendered strings **and** the unrounded mean/SD columns for reproducibility.

## Frozen inputs and hash verification

The generator aborts before writing anything if any hash differs.

| File | Role | Expected sha256 | Verified |
|---|---|---|---|
| `results/descriptive_2026-09-21/aggregate_results.csv` | mandatory | `4242c3634c8939714eb0b7ff25b446783f1747add91c36040a95bf02f1646768` | yes |
| `results/descriptive_2026-09-21/per_run_results.csv` | mandatory | `6b3f374a0e76d2c8068c06cc077a2affadd1cd15ac91aab027efeb591efe86ec` | yes |
| `results/descriptive_2026-09-21/cell_metrics.json` | mandatory | `fcde951f0190441d0e0d6f31fd2dd03021f4c02d7df07161e403ef6410051221` | yes |
| `results/descriptive_2026-09-21/frozen_grid_manifest.json` | mandatory | `fba6a4617558b64bec61cee18e2a0b63e9457a03c6a3d94cd8e1a1916527dfa8` | yes |
| `results/descriptive_2026-09-21/aggregate_five_runs.json` | mandatory | `96ebe4f0b880d989e796b88a4e8c4be1e7362d89b864c1125afd1c521e70fb91` | yes |
| `results/rq1_rq3_reporting_2026-09-21/rq12_full_precision.json` | supporting | `707104a439bc50baa79dd4db1118234c6469ec86059e6bf8cdf79518cceacb17` | yes |
| `results/rq1_rq3_reporting_2026-09-21/tables/rq3_dreaddit_latency.csv` | supporting | `908233ed79e5de25e8dad0b84c6b23162a88efd8e165a2a36a5b578c36ab370c` | yes |
| `results/rq1_rq3_reporting_2026-09-21/tables/rq3_goemotions_latency.csv` | supporting | `535a8b24da59b9f7eb7d52de2c42ab7477d4067f27a0ad4d3e08e8553f86af5e` | yes |
| `configs/pub_001_dreaddit_qwen.yaml` | supporting | `d46041d20b27bf8247badc9f819007130fa15ccb53fa8a4617f8b569b3da7016` | yes |
| `configs/pub_002_dreaddit_mistral.yaml` | supporting | `ec5fa958b2b4b3a67686dc7e62652a45d21f270aebd752e2c5e2f2d704b2c416` | yes |
| `configs/pub_003_dreaddit_llama.yaml` | supporting | `6ffca17a5e3e99bcf576f07dbbabc9cfd4f1232d038ef458e9715fa7a22ba143` | yes |
| `configs/pub_005_dreaddit_phi.yaml` | supporting | `1c47eacae12abed9ee7b8626c52f451a41cc5e56713955409bb2495525a09bbc` | yes |
| `configs/pub_006_goemotions715_mistral.yaml` | supporting | `e196b44d030f826ae45c182c8073e576c9d429f225d8c69d802520fa654afda2` | yes |
| `configs/pub_007_goemotions715_qwen.yaml` | supporting | `cb6fcc23fffd1624d9c7e626a053f06ab2c309659882fdbeef373b5401edbf68` | yes |
| `configs/pub_008_goemotions715_phi.yaml` | supporting | `297bddd04a1b012715c4c5ff306e139a4b167ff5ea6265b05ec2cd02d3eae2c8` | yes |
| `configs/pub_009_goemotions715_llama.yaml` | supporting | `0792d3b9b5e5b4a67ee60e885dde5e6be0507ac8a1205be436e300c75e2a6998` | yes |
| `configs/pub_011_dreaddit_gemma_coreweave.yaml` | supporting | `e08575005359926d962062098c71b7253ca77eadba18d1bc624bf92b6daa6b6b` | yes |
| `configs/pub_012_goemotions715_gemma_coreweave.yaml` | supporting | `3615dc6229231a82d33d5a54073ed571110fefc0d47308f3e36e16a139575c20` | yes |
| `configs/pub_013_dreaddit_gemma_coreweave_osc_run5.yaml` | supporting | `47f4da0ccf7cfca3427ab90b5bf51468c00d5f1ab0b9f9a031c4556112ef1dbf` | yes |

## Grid assertions checked at generation time

- 150 cells — pass
- 100,350 records — pass
- `validation.passed = true` — pass
- 0 validation problems — pass
- `aggregate_results.csv` has 30 configuration rows; `per_run_results.csv` has 150 cell rows; each
  configuration has exactly runs 1–5.

Frozen grid timestamp: `2026-09-21T14:51:04.780606+00:00` · parser `1.0.0` · metric policy
`1.0.0`.

## Value policy

- Conditional accuracy, effective accuracy, macro F1, evaluability and all counts are taken **verbatim** from
  the frozen `aggregate_results.csv`. They were not recalculated for display.
- Macro precision and macro recall are not present in the frozen aggregates. They are taken from the verified
  full-precision aggregates in `rq1_rq3_reporting_2026-09-21/rq12_full_precision.json`, and independently
  re-derived here from `per_run_results.csv` (five-run arithmetic mean, sample SD with n−1 — the same
  convention as the frozen aggregation) as a cross-check only.
- Latency values are copied verbatim from the verified RQ3 summary tables. Raw runs were not re-read.
- Formatting is the only transformation applied: 3 decimals, ROUND_HALF_UP, applied to the stored value.
- No winner is marked and no ranking is implied. These tables are descriptive.

## Cross-checks performed before writing

1,740 comparisons across four independent copies of the same quantities
(`aggregate_results.csv`, `aggregate_five_runs.json`, `rq12_full_precision.json`, and a fresh aggregation of
`per_run_results.csv`), plus per-cell bucket agreement between `per_run_results.csv` and `cell_metrics.json`.

242 of 1740 cross-checked values differed only in the last bits of the floating-point representation (largest absolute difference 1.11e-16); all are below the 5e-16 tolerance and none changes a 3-decimal displayed value. No substantive discrepancy was found.

One cosmetic cross-artifact difference is normalised at render time. The verified RQ3 latency tables label
the models "Gemma 4 31B" and "Qwen3.5 27B", while the publication configs record "Gemma 4 31B IT" and
"Qwen 3.5 27B". Table 4 displays the config display names so that all four tables read consistently. This is a
**display-label substitution only**, applied by an explicit fail-closed mapping in the generator (an
unrecognised label aborts the run): no latency value, count, source-run field or model ID is changed, and no
source artifact is touched. `04_latency_results.csv` additionally carries `model_id` and the verbatim
`model_source_label` from the source tables, so the substitution is fully traceable.

## Reproducing

```bash
cd evaluation/publication_experiments/results/rq1_rq3_tables
python3 code/generate_rq1_rq3_tables.py
```

Requires Python ≥ 3.9 and PyYAML. The script writes only into this directory.

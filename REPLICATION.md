# AnxioSense Replication Materials

This branch contains materials used to support reproducibility and inspection of the AnxioSense publication experiments.

## Frozen GoEmotions Subset

The frozen 715-item GoEmotions subset and its provenance materials are located in:

`evaluation/datasets/goemotions_subset_715_2026-09-09/`

Key files include:

- `goemotions_715_subset.csv` — frozen 715-item subset
- `SELECTION.md` — subset selection methodology
- `SOURCES.json` — source/provenance information
- `abel_rq4_rq5_ids.csv` — specified RQ4/RQ5 sample IDs
- `build_goemotions_715_subset.py` — deterministic subset construction script

The corresponding frozen manifest is:

`evaluation/publication_experiments/manifests/goemotions_715_subset_2026-09-09.json`

## Publication Experiment Configurations

Publication experiment configurations are located in:

`evaluation/publication_experiments/configs/`

These YAML files define the dataset manifest, model, prompting strategies, number of runs, provider constraints, retry policy, and server settings used by the experiment runner.

## Evaluation Pipeline

The publication evaluation pipeline is located in:

`evaluation/publication_experiments/runner/`

Important modules include:

- `run.py` — experiment execution
- `parse.py` — response parsing
- `rescore.py` — offline rescoring
- `metrics.py` — metric computation
- `manifest.py` — dataset manifest handling
- `config.py` — experiment configuration loading
- `client.py` — evaluation API client
- `store.py` — append-only result storage
- `retry.py` and `failures.py` — retry and failure handling

## Reproducibility

Publication runs use frozen dataset manifests and experiment configurations. Raw attempts are stored before downstream parsing and scoring.

Provider/model routing and other run-specific constraints are recorded in the corresponding publication configuration files.

Incomplete superseded Gemma/DeepInfra runs are not included as final replication configurations. The replacement Gemma publication configurations use the CoreWeave upstream and are recorded separately.

## Final Publication Grid

The frozen publication analysis contains 150 cells (5 models × 3 prompting strategies × 2 datasets × 5 runs) and 100,350 assessment records.

The authoritative source runs are:

- Dreaddit: `pub_001_dreaddit_qwen`, `pub_002_dreaddit_mistral`, `pub_003_dreaddit_llama`, `pub_005_dreaddit_phi`, and the Gemma composition described below.
- GoEmotions: `pub_006_goemotions715_mistral`, `pub_007_goemotions715_qwen`, `pub_008_goemotions715_phi`, `pub_009_goemotions715_llama`, and `pub_012_goemotions715_gemma_coreweave`.

For Dreaddit Gemma, `pub_011_dreaddit_gemma_coreweave` supplies 14 cells. Its `one-shot-cot` run-5 cell is excluded from the final composition and replaced by the corresponding 715-record cell from `pub_013_dreaddit_gemma_coreweave_osc_run5`. The original `pub_011` data was not modified.

The authoritative composition and validation record is:

`evaluation/publication_experiments/results/descriptive_2026-09-21/frozen_grid_manifest.json`

Historical or superseded configuration files may remain in the repository and should not be interpreted as part of the authoritative final grid solely from their `pub_*` filename.

## Analysis Artifacts

Final descriptive artifacts are located in:

`evaluation/publication_experiments/results/descriptive_2026-09-21/`

The frozen analysis input is `authoritative_records.jsonl`. Aggregate and per-run results, cell metrics, the frozen grid manifest, and the composition scripts are included alongside it.

Inferential analysis materials are located in:

`evaluation/publication_experiments/results/inferential_2026-09-21/`

These include the statistical analysis plan, analysis code, configuration-level and pairwise result tables, bootstrap and permutation replicate files, and an independent verification script and verification result.

The inferential procedure uses 4,000 paired item-cluster bootstrap replicates and 10,000 paired item-level permutation replicates. Exact McNemar tests are included as secondary analyses, with Holm correction for the specified multiple-comparison families.

## Scope

This branch provides the frozen inputs, authoritative publication configurations, evaluation code, descriptive analysis artifacts, inferential analysis artifacts, and verification materials required to inspect the final RQ1–RQ3 publication evaluation.

The included evaluation is an experimental benchmark of the frozen datasets and configurations. It is not a clinical validation of AnxioSense.

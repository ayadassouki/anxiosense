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

## Scope

This branch provides the frozen inputs, configurations, and existing evaluation code required to inspect and reproduce the experimental procedure.

Publication-scale parsed outputs, final aggregate metrics, and statistical significance analyses are not included here unless explicitly added as separate reproducible artifacts.

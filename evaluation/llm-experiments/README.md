# AnxioSense LLM Experiments

Automated evaluation pipeline for Research Questions 1–3 of the AnxioSense EECS 4080 project.

Evaluates 5 LLMs × 3 prompting strategies × 5 runs × 2 datasets = 150 experiment cells.

## Quick start

```bash
cd /path/to/anxiosense
pip install -r evaluation/llm-experiments/requirements.txt
export OPENROUTER_API_KEY=your_key_here
export MISTRAL_API_KEY=your_key_here

# Inspect datasets
python evaluation/llm-experiments/scripts/inspect_datasets.py

# Smoke test (3 examples, 1 run, no full experiment)
python evaluation/llm-experiments/scripts/run_experiments.py \
  --dataset dreaddit \
  --model "meta-llama/llama-4-scout:free" \
  --strategy zero-shot \
  --sample-size 3 \
  --runs 1

# Full experiment
python evaluation/llm-experiments/scripts/run_experiments.py

# Compute metrics
python evaluation/llm-experiments/scripts/compute_metrics.py

# Generate summary table
python evaluation/llm-experiments/scripts/generate_summary.py
```

## Datasets

| Name | Path | Rows | Task | Labels |
|------|------|------|------|--------|
| Dreaddit (anxiety subset) | evaluation/datasets/dreaddit/dreaddit_anxiety_subset.csv | 1,531 | Binary stress | 0 (no stress), 1 (stress) |
| GoEmotions (AnxioSense single-label) | evaluation/datasets/goemotions/goemotions_anxiosense_single.csv | 26,269 | Multiclass emotion | 10 emotion categories |

## Models

| Name | Provider | Model ID |
|------|----------|----------|
| Llama 4 Scout | OpenRouter | meta-llama/llama-4-scout:free |
| Mistral Small 4 | Mistral | mistral-small-2603 |
| Gemma 3 27B IT | OpenRouter | google/gemma-3-27b-it:free |
| DeepSeek V4 Flash | OpenRouter | deepseek/deepseek-v4-flash |
| Phi-4 | OpenRouter | microsoft/phi-4:free |

## Prompting strategies

All prompts are loaded from `prompts/emotion/` using the existing AnxioSense prompt files:

| Strategy | File |
|----------|------|
| Zero-shot | prompts/emotion/zero-shot.md |
| Zero-shot + CoT | prompts/emotion/zero-shot-cot.md |
| One-shot + CoT | prompts/emotion/one-shot-cot.md |

## Label mapping

**Dreaddit:** label column (0/1) is used directly.

**GoEmotions → AnxioSense emotion vocabulary:**
- nervousness → anxiety
- fear → fear
- sadness, grief, disappointment → sadness
- anger, annoyance → frustration
- neutral, joy, relief → None (no AnxioSense equivalent; excluded from precision/recall)

## Output files

```
outputs/
├── raw/             ← one JSONL + CSV per (dataset, model, strategy, run)
├── metrics/
│   ├── per_run_metrics.csv
│   ├── summary_table.csv
│   ├── final_summary.txt
│   └── confusion_*.json
└── prepared/        ← stratified samples (optional)
```

## Unit tests

```bash
cd /path/to/anxiosense
python -m pytest evaluation/llm-experiments/tests/ -v
```

All tests are offline (no API keys required).

## Resume

The runner resumes automatically — if interrupted, re-run the same command.
Already-completed (sample_id, model, strategy, run) tuples are skipped.

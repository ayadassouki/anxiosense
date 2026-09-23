# Table 1. Model configuration (AnxioSense publication grid)

All values are read from the authoritative publication configs (`configs/pub_*.yaml`) and from the frozen
grid manifest. Nothing here is inferred from model family or looked up externally.

| Model | Model ID | Provider (pinned in config) | Provider (observed in frozen grid) | Quantization directive | Datasets | Prompt strategies | Runs per strategy | Temperature | Max tokens | Seed | Other request parameters |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemma 4 31B IT | `google/gemma-4-31b-it` | CoreWeave | CoreWeave (19,815 OK records) | fp4 (configured request directive; provider responses do not report quantization) | dreaddit; goemotions | zero-shot; zero-shot-cot; one-shot-cot | 5 runs (runs 1–5) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | none |
| Llama 4 Scout | `meta-llama/llama-4-scout` | DeepInfra | DeepInfra (19,815 OK records) | none configured | dreaddit; goemotions | zero-shot; zero-shot-cot; one-shot-cot | 5 runs (runs 1–5) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | none |
| Mistral Small 4 | `mistralai/mistral-small-2603` | Mistral | Mistral (19,815 OK records) | none configured | dreaddit; goemotions | zero-shot; zero-shot-cot; one-shot-cot | 5 runs (runs 1–5) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | none |
| Phi-4 | `microsoft/phi-4` | DeepInfra | DeepInfra (19,815 OK records) | none configured | dreaddit; goemotions | zero-shot; zero-shot-cot; one-shot-cot | 5 runs (runs 1–5) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | none |
| Qwen 3.5 27B | `qwen/qwen3.5-27b` | Alibaba | Alibaba (19,815 OK records) | none configured | dreaddit; goemotions | zero-shot; zero-shot-cot; one-shot-cot | 5 runs (runs 1–5) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | Not explicitly set (provider defaults) | reasoning={enabled:false} (documented per-model deviation; not a sampling parameter) |

Notes.

- Every request is routed through OpenRouter (`provider: openrouter` in each config); the provider column is
  the upstream endpoint pinned with `allow_fallbacks: false`.
- "Provider (observed in frozen grid)" counts the `providers_ok` histogram recorded per cell in
  `frozen_grid_manifest.json`. Each model was served by exactly one upstream provider across all of its
  OK records, and the observed provider matches the configured pin in every case.
- The Gemma `fp4` entry is a **configured request directive**. OpenRouter's response carries the provider but
  not the quantization, so it is enforced by hard failure, not independently observed.
- Temperature, max tokens, max completion tokens, seed, top-p and top-k are **not set** in any publication
  config and are not recorded in any run's provenance; the provider's own defaults applied. The generator
  asserts their absence rather than assuming it.
- Qwen carries the one documented per-model request override (`reasoning={enabled:false}`), which the configs
  describe as a reasoning toggle rather than a sampling parameter.
- Gemma on Dreaddit spans two configs: `pub_011` supplies 14 cells and `pub_013` supplies the frozen
  replacement cell `dreaddit|google/gemma-4-31b-it|one-shot-cot|run5` (715 records).
- Context window and knowledge cutoff are deliberately omitted: they are not recorded in the frozen
  publication artifacts.

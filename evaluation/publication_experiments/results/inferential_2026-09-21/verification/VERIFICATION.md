# Independent verification of the inferential analysis

Result: **PASSED, 0 discrepancies** (`verification_result.json`). Tolerance for floating-point comparisons: 1e-12. Every difference found was ≤ 4.4e-16 (last-bit float), and all are quantified per field in the JSON.

**Method.** `verify_inferential.py` uses the Python standard library only. It does not import `code/` or `runner/`, and it uses different formulations from the primary script where possible.

| Check | How it was verified |
|---|---|
| Source hashes | `authoritative_records.jsonl`, `frozen_grid_manifest.json` and both dataset manifests, against frozen values. Every output CSV/replicate file against `analysis_manifest.json`. |
| Gemma composition | pub_011 for 14 Dreaddit Gemma cells; pub_013 only for `one-shot-cot\|run5`. |
| Items and pairing | One item set and one safety set per dataset, rebuilt with dictionaries. The attributable item-list sha256 and the safety IDs match the manifest. There are 60 model pairs (10 × 3 strategies × 2 datasets), each appearing once per primary metric, with A before B in the fixed order. |
| Observed effects | Effective accuracy as exact Fractions. Macro-F1 via the frozen 2PR/(P+R) form (the primary uses 2tp/(2tp+fp+fn)). Conditional accuracy. RQ2 differences vs 355/699 and 487/622, and vs the frozen 369/715 and 487/623. |
| McNemar | Discordant counts b and c recomputed from per-item majority votes. Exact p from an explicit binomial pmf in Fractions. |
| Holm | Independently written step-down, for all 8 families. Family sizes checked: 60 / 30 / 15 / 15 per dataset. |
| Bootstrap | Seeds `20260921\|<dataset>\|bootstrap`. Draws regenerated and their sha256 matched. 4,000 saved replicates. **All** 4,000 × 15 effective-accuracy and baseline replicates recomputed. Conditional accuracy and macro-F1 recomputed for every 20th replicate (200 × 15 per dataset). CIs re-extracted from the saved replicates with an independently written interpolation. |
| Permutation | Seeds `20260922\|<dataset>\|permutation`. Swap sets regenerated and their sha256 matched. 10,000 saved statistics. Effective-accuracy statistics recomputed exactly (integers) for every 10th permutation; macro-F1 statistics for every 50th. Every p-value re-derived from the saved statistics. |

**Not re-derived independently:** 90% of the permutation statistics and 95% of the macro-F1/conditional bootstrap replicates. These were spot-checked on a fixed, evenly spaced subset, and every checked value agreed.

**Rounding impact.** The largest discrepancy in any reported CI bound is 1.1e-16. One reported bound lies at a 3-decimal half boundary (GoEmotions Phi-4 zero-shot RQ2 CI upper bound, −0.02249999999999986 → shown as −0.022). No test decision or conclusion depends on that digit.

# Statistical analysis plan: inferential RQ1 / RQ2

Status: **APPROVED 2026-09-21. Written before any test was run.** The draft (sections A–E) was written and the analysis stopped at section D. Aya chose the recommended option for D1–D4. Section F records the final design. No p-value, CI or replicate existed when these decisions were made.

Date: 2026-09-21. Inputs are frozen and hash-checked (`source_hashes.txt`). Every value matches the frozen grid manifest and the earlier verification:

- `authoritative_records.jsonl` = `97c8ca96…`
- `frozen_grid_manifest.json` = `fba6a461…`
- `cell_metrics.json` = `fcde951f…`
- `aggregate_results.csv` = `4242c363…`
- `per_run_results.csv` = `6b3f374a…`
- Dataset manifests: `71731b47…` (Dreaddit) and `dacab2c4…` (GoEmotions)

## A. Facts about the design, checked from the frozen records (not assumed)

| Fact | Dreaddit | GoEmotions |
|---|---|---|
| Cells (5 models × 3 strategies × 5 runs) | 75 | 75 |
| Items per cell | 715 | 623 |
| Distinct item-ID sets across the 75 cells | **1** (every cell scores the same items) | **1** |
| Safety-intercepted items per cell | 16 | 1 |
| Distinct safety-intercept sets across cells | **1** (the same 16 items in every cell) | **1** (the same item) |
| Attributable items (the inference population) | **699** (355 class 1 / 344 class 0) | **622** (487 non_distress / 81 frustration / 33 sadness / 15 fear / 6 anxiety) |
| Record outcomes present | OK + valid 51,826; OK + MODEL_BEHAVIOUR invalid 599; SAFETY_INTERCEPT 1,200 | 45,263; 1,387; 75 |
| Infrastructure failures / unaccounted | 0 / 0 | 0 / 0 |

- Gemma Dreaddit composition as frozen: pub_011 minus `one-shot-cot|run5`, plus pub_013 for that cell. The analysis will assert this from `source_run` on every record.
- Because the item set and the safety set are identical in every cell, **every configuration can be paired with every other configuration item by item**, with no missing pairs. This is what makes paired inference possible.

## B. Proposed design (points 1–12 of the request)

**1. Statistical unit: the dataset item (`sample_id`).**
- The question is how a configuration would perform on items like these.
- The sampling variability that matters for that question is *which items happened to be in the test set*.
- There are 699 Dreaddit and 622 GoEmotions attributable items.

**2. Pairing.**
- Within a dataset, all 15 configurations (model × strategy) were scored on the identical 699 / 622 items.
- A comparison of configuration A with configuration B is paired **by item**.
- Runs are **not** paired across configurations. Run *k* of A and run *k* of B were executed at different times, on different processes and sometimes on different machines, so the run index carries no shared information.

**3. Repeated stochastic runs.**
- The 5 runs are repeated measurements of the **same** item under the same configuration. They are *not* 5 independent samples: treating 5 × 699 records as 3,495 independent observations would be pseudoreplication.
- The runs stay nested inside their item. The estimand is the frozen five-run quantity: the mean over the 5 runs of the per-run metric (the definition used in `aggregate_results.csv`).
- For accuracy-type metrics this equals the mean over items of each item's 5-run average correctness, so no information is discarded.
- The runs themselves are **not** resampled. The resulting intervals express item-sampling uncertainty given the observed stochastic behaviour. The run-to-run SD is reported separately, as in the descriptive tables.
- Alternatives are listed in D3.

**4. What is clustered in the bootstrap, and why.**
- Cluster = one item, carrying all of its 15 configurations × 5 runs = 75 predictions per dataset.
- Resampling whole items keeps the within-item dependence across runs, which is where pseudoreplication would come from, and the between-configuration pairing, which is what makes differences precise.
- This matches the method used in the August analysis (`claude/final-significance-analysis.md`: "resamples items with all 5 runs attached, on both sides of each comparison simultaneously").

**5. What is resampled.**
- In each replicate, draw 699 (or 622) item indices **with replacement** from the attributable items, using one index vector shared by all 15 configurations of that dataset.
- On that resampled multiset, recompute each configuration's per-run metrics exactly as MetricPolicy 1.0.0 defines them, average them over the 5 runs, and form differences.
- Replicates B = 4,000, as planned. The seed is fixed and recorded (proposed: 20260921). The generator is Python's `random.Random(seed)`, with draws recorded so the intervals can be reproduced independently.
- Intervals are 95% percentile intervals (2.5th and 97.5th percentiles of the 4,000 replicate values).
- GoEmotions anxiety has 6 items, so about 0.25% of replicates (≈ 10) will contain no anxiety item. MetricPolicy 1.0.0 then sets the undefined recall and F1 to 0. That rule is applied verbatim, and the number of such replicates is reported.

**6. What McNemar tests.**
- Exact McNemar tests H0: P(A correct, B wrong) = P(A wrong, B correct) for one binary outcome per item.
- "Correct" is the frozen **effective** correctness: valid and equal to ground truth. A model-invalid output is **incorrect**.
- Each item has 5 outcomes per configuration, not 1, so McNemar **cannot be applied without an aggregation decision**. See D2.
- McNemar does not apply to macro-F1 or conditional accuracy, which are not per-item binary outcomes.

**7. Invalid model outputs.**
- They are kept exactly as frozen. For effective accuracy and macro-F1 they count as not-correct on the attributable denominator.
  - Macro-F1: MetricPolicy computes per-class P/R/F1 on valid predictions only. That is the frozen definition, and it is used verbatim.
- Conditional accuracy (correct / valid) has a different denominator for each configuration. A "paired" comparison of conditional accuracy therefore compares different item subsets. Proposed treatment: **secondary; bootstrap CIs only; no hypothesis tests; labelled "conditional on the configuration's own evaluable predictions".**

**8. Safety intercepts.**
- They are excluded from model attribution, as frozen. The excluded items are identical in every cell (16 / 1), so they are removed once from the item pool and never resampled.
- Nothing about their handling changes.

**9. Multiple comparisons.** Holm correction within pre-declared families. The family definition is not fixed by the earlier notes for a 5-model, 2-metric design; see D1.

**10. Baseline comparisons (RQ2).** The majority baseline is a constant predictor: always class 1 on Dreaddit, always non_distress on GoEmotions. Which scalar to compare against, and how, is decision D4.

**11. Effect sizes and intervals to report.** For every comparison:

- the observed difference in five-run means (A − B), in accuracy or macro-F1 units;
- the 95% percentile bootstrap CI;
- the raw p-value and the Holm-adjusted p-value;
- the number of items;
- the direction of the difference.

McNemar rows additionally report:

- the discordant counts b (A correct, B wrong) and c (A wrong, B correct);
- b + c;
- the exact two-sided binomial p-value, 2 · P(X ≤ min(b, c)) with X ~ Bin(b + c, ½), capped at 1.

**12. Are the originally planned tests appropriate for this design?**

| Planned method | Verdict | Reason |
|---|---|---|
| Paired cluster bootstrap, 4,000 replicates, items as clusters | **Appropriate for confidence intervals** | Respects the item pairing and the run-within-item nesting (points 3–5). |
| p-values from that bootstrap | **Under-specified** | The earlier notes report bootstrap "raw p" without saying how it was computed. A p-value must be defined before it is used (D3). |
| Exact McNemar | **Needs an aggregation decision** | 5 correlated outcomes per item per configuration (D2). Pooling 5 × N predictions would be pseudoreplication and is ruled out. |
| Holm correction | **Appropriate**, but family membership is under-specified | D1. |
| Bootstrap comparison against majority baseline | **Under-specified** | Whether the baseline is a fixed scalar or a paired constant predictor, and which denominator (D4). |
| Wilcoxon signed-rank + Bonferroni, as in the July `AnxioSense_Experimental_Setup.docx` §6.4 | **Not appropriate here** | It would treat the 5 runs as the paired sample. Runs are not paired across configurations. With n = 5 the smallest attainable two-sided exact Wilcoxon p-value is 0.0625, so no comparison could ever reach 0.05 before correction. It also ignores item sampling entirely. The request names the bootstrap / McNemar / Holm plan, which supersedes it; this discrepancy should be disclosed in the paper. |

## C. Proposed hypothesis families (for approval, not yet run)

**Primary metrics.**
- Effective accuracy (invalid = wrong; coverage-robust).
- Macro-F1 (frozen definition; class-balanced, which matters for GoEmotions).

**Secondary (CIs, no tests).**
- Conditional accuracy, for the reason in point 7.

**Descriptive only.**
- Per-class metrics. No inference on the GoEmotions anxiety class (n = 6: one item moves recall by 1/6).

**RQ1 (model comparison).**
- Comparisons are model-vs-model **within the same dataset and the same prompting strategy**, so the model effect is not confounded with strategy.
- With 5 models there are 10 pairs, which gives 30 comparisons per dataset per metric (see D1 for the alternatives).
- No "best model vs rest" comparisons: choosing the best on these same items and then testing it would be selection on the test data.

**RQ2 (baseline).**
- Each of the 15 configurations per dataset against the majority baseline.
- Effective accuracy only: macro-F1 of a constant predictor (0.337 Dreaddit, 0.176 GoEmotions) is trivially low, so that comparison is reported descriptively, not tested.
- One family per dataset (15 tests).
- No single "AnxioSense accuracy" is formed.

**RQ3.** Descriptive only; no inferential latency analysis. The confounds documented in `rq1_rq3_reporting_2026-09-21/REPORT.md` (3 s quantisation, fixed strategy order, machine, provider and time, concurrent load for Llama Dreaddit, no per-agent timing) mean no test could attribute a latency difference to the prompting strategy.

## D. Decisions required before implementation (stop conditions reached)

**D1. RQ1 family and multiplicity.**

| Option | Comparisons | Notes |
|---|---|---|
| (a) All 10 model pairs within each strategy, one Holm family per dataset covering both primary metrics | 60 per dataset | **Recommended**: conservative, no tiny families, and it respects strategy. |
| (b) As (a), but one family per dataset × metric | 30 per dataset | Matches the earlier precedent (family of 30 per dataset, one primary metric). With two co-primary metrics it is less strict than (a). |
| (c) Model effect averaged over the 3 strategies | 10 per dataset per metric | Fewer tests, but it averages over strong model × strategy interactions (e.g. Phi-4 GoEmotions one-shot-CoT). |
| (d) Literal July protocol: one-shot-CoT only | 10 per dataset per metric | Ignores two thirds of the grid. |

**D2. McNemar construction.** Five outcomes per item per configuration must be reduced to one binary outcome per item, or a different exact paired test must be used.

- **(a) Majority vote per item.** An item counts as correct if it was effectively correct in ≥ 3 of 5 runs. 5 is odd, so there are no ties. One binary per item per configuration, and items are independent, so McNemar's assumptions hold.
  - The tested quantity becomes "majority-vote correctness", not the five-run mean. It is used as a **secondary, conservative check** alongside the bootstrap.
  - Used before (August analysis).
  - **Recommended.**
- **(b) Per-run McNemar.** 5 tests per comparison, which are correlated. This multiplies the number of tests and requires an arbitrary run pairing. **Not recommended.**
- **(c) Replace McNemar with an exact paired permutation test on the item-level mean correctness.** For each item, swap A's and B's 5-run outcomes with probability ½. This uses all runs and is valid under exchangeability, but it departs from the planned method.

**D3. Source of the primary p-value** (the bootstrap gives the interval; the p-value needs a stated definition):

- **(a) Bootstrap p-value.** p = min(1, 2 · min(#{Δ\* ≤ 0}, #{Δ\* ≥ 0}) / B), from the same 4,000 replicates. This matches the earlier notes in spirit, but it is approximate and its behaviour near the resolution limit (1 / 4,000) is crude.
- **(b) Paired item-level permutation test.** Swap A/B per item; 10,000 permutations. It applies to effective accuracy and macro-F1 alike and is exact under the null up to Monte Carlo error. CIs still come from the bootstrap. **Recommended** as the statistically cleaner option, but it is an addition to the plan.
- **(c) Report no primary p-value; use the bootstrap CIs plus McNemar only.**

Also: should runs additionally be resampled (a two-stage bootstrap)? Proposed: **no**. The estimand is conditional on the 5 observed runs, matching the frozen descriptive definition and the precedent. Two-stage resampling with only 5 runs gives unstable variance estimates. This is disclosed as a limitation.

**D4. Baseline for RQ2.**

- **(a) Paired constant-predictor comparison on the attributable items.** In every bootstrap replicate, the constant majority-class predictor is scored on the **same** resampled items as the configuration, and the difference is taken.
  - Its point value is the attributable-set rate: 355/699 = 0.508 (Dreaddit), 487/622 = 0.783 (GoEmotions).
  - It uses the **same scoring population as the model** (safety items excluded on both sides), so nothing about model scoring changes, and it accounts for the baseline's own sampling variability.
  - The majority class is the same one the frozen baseline uses.
  - **Recommended.**
- **(b) Fixed frozen scalars** 369/715 = 0.516084 and 487/623 = 0.781701, compared with the configuration's bootstrap distribution.
  - These are over a different population (they include the safety items), and they are treated as known constants.
- Whichever is chosen is primary. The other is reported as a sensitivity analysis. The RQ1–RQ3 report already found that the choice changes no run-level "above baseline" count.
- For GoEmotions, (a) sets a slightly higher bar (0.783 vs 0.782). This choice is not made to favour any result.

## E. What will be produced after approval

`code/` (stdlib-only Python, commented, fail-closed assertions), `tables/` (CSV + Markdown), `analysis_manifest.json`, `README.md`, a report separating Measured from Interpretation, and `verification/`, containing an independent re-implementation that re-derives pairs, effects, discordant counts, exact p-values, Holm adjustments, replicate count, seed and CI extraction from the frozen records.

## F. Final approved design (decisions D1–D4, 2026-09-21)

| Decision | Chosen option |
|---|---|
| D1 RQ1 family | **(a)**: all 10 model pairs within each strategy × 2 primary metrics (effective accuracy, macro-F1) = **60 hypotheses in one Holm family per dataset**. |
| D2 McNemar | **(a)**: exact McNemar on per-item **majority-vote effective correctness** (correct in ≥ 3 of 5 runs). Secondary, conservative check, in its own Holm family per dataset: RQ1 30 hypotheses (effective accuracy only), RQ2 15. |
| D3 primary p-value | **(b)**: **paired item-level permutation test**, 10,000 random swaps per dataset. CIs come from the 4,000-replicate item-cluster bootstrap. |
| D4 RQ2 baseline | **(a)**: **paired constant majority-class predictor on the attributable items** (355/699, 487/622) is primary. The fixed frozen scalar (369/715, 487/623) is a CI-only sensitivity analysis. |

**Exact specifications (fixed before running)**

**Items.**
- Attributable items only: 699 Dreaddit, 622 GoEmotions.
- Sorted by `sample_id` (plain string sort). The item order defines the draws.

**Bootstrap draws.**
- One stream per dataset: `random.Random("20260921|<dataset>|bootstrap")`.
- For each of B = 4,000 replicates: `[rng.randrange(n) for _ in range(n)]`.
- All 15 configurations (and the constant predictor) use the same draws.

**Permutation draws.**
- One stream per dataset: `random.Random("20260922|<dataset>|permutation")`.
- For each of P = 10,000 permutations: `bits = rng.getrandbits(n)`, and item *i* is swapped if bit *i* is set.
- The same swap sets are used for every comparison in that dataset.
- For a model-vs-model pair, swapping item *i* exchanges A's and B's five run outcomes. Run *k* goes to run *k*, a fixed and arbitrary alignment; the test is valid for any fixed alignment.
- For configuration vs constant predictor, the swap negates the item's difference.

**Test statistic.** T = (five-run metric of A) − (five-run metric of B), with the metric computed exactly as MetricPolicy 1.0.0 defines it.
- p = (1 + #{|T\*| ≥ |T_obs|}) / (1 + P), two-sided.
- Accuracy statistics are compared as exact integers (numbers of correct run-outcomes).
- Macro-F1 statistics are compared with a tolerance of 1e-12.

**Metric formulas.**
- Per run: effective accuracy = correct / n; conditional accuracy = correct / valid.
- Per-class F1 = 2tp / (2tp + fp + fn) if tp > 0, else 0. This is identical to the frozen 2PR / (P + R), with P, R = 0 when undefined.
- Macro-F1 is the unweighted mean over the fixed label list.
- Five-run value = mean over runs 1–5.

**Confidence intervals.**
- 95% percentile interval with linear interpolation: h = (B − 1)·q; value = x[⌊h⌋] + (h − ⌊h⌋)·(x[⌊h⌋ + 1] − x[⌊h⌋]), for q = 0.025 and 0.975 on the sorted replicates.

**McNemar.**
- b = #(A majority-correct, B not), c = #(A not, B majority-correct).
- p = min(1, 2·Σ_{k ≤ min(b, c)} C(b + c, k) / 2^(b + c)), computed exactly; p = 1 if b + c = 0.

**Holm.**
- Sort the family's p-values ascending: p_(1) ≤ … ≤ p_(m).
- adj_(j) = max_{i ≤ j} min(1, (m − i + 1)·p_(i)).
- Significant if adj ≤ 0.05.

**Conditional accuracy.** CIs only (configuration level and RQ1 pair differences). No p-values and no Holm.

**RQ3.** No inference.

**Fail-closed assertions.**
- Input sha256 values equal the frozen values.
- 150 cells and 100,350 records.
- Per-cell n (715 / 623) and per-cell `records_sha256` equal the frozen manifest.
- One item set and one safety set per dataset.
- Ground truth equals the dataset manifest.
- Only the frozen outcome classes appear.
- The Gemma Dreaddit source runs follow the frozen composition rule.
- Observed per-run and five-run metrics equal the frozen `per_run_results.csv` / `aggregate_results.csv` within 1e-12.

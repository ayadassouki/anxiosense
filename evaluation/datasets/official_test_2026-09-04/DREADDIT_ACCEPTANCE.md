# Dreaddit official test split — acceptance checks

Source: `evaluation/datasets/dreaddit_official/dreaddit_test.csv`
SHA-256: `5c53c0bf4c9deaf0756b6ae70f2c7a99592070da959cd566fa771f997e22f9e8`
Revision: `andreagasparini/dreaddit` (HuggingFace), official test split.
Run 2026-09-04. **All checks pass.**

| # | Check | Result |
|---|---|---|
| A1 | Row count = 715 | **PASS** — 715 data rows, 116 columns |
| A2 | Positive rate near 52.4 %, not 68.8 % | **PASS** — 369/715 = 51.61 % |
| A3 | All 324 superseded filtered test ids contained | **PASS** — 324/324; 391 rows the filter had removed |
| A4 | All 25 Abel RQ4/RQ5 Dreaddit ids present | **PASS** — 25/25 |
| A5 | Required columns, no duplicate ids, no empty text | **PASS** — `id`/`text`/`label` present; 0 duplicates; 0 empty |
| A6 | Labels and text agree with the old subset on the 324 overlap | **PASS** — 0 label mismatches, 0 text mismatches |
| A7 | Old candidate manifest untouched | **PASS** — still n=324, baseline 0.688272 |

## Class distribution

| Label | Rows | Share |
|---|---:|---:|
| 0 — not stressed | 346 | 48.39 % |
| 1 — stressed | 369 | 51.61 % |

Majority baseline **0.516084**, versus **0.688272** on the superseded 324-row
subset. Dropping the anxiety/LIWC filter removes a **17.2-point** selection bias.

## One discrepancy, recorded not resolved

Turcan & McKeown (2019) §5 reports the test split as **52.4 %** stressful; this
file is **51.61 %** — a difference of about **6 rows**. The row count (715), the
containment of all 324 previously filtered ids, and exact label and text agreement
on that overlap all confirm this is the unfiltered official test split and not the
filtered subset. The residual gap is most likely a small difference between the
HuggingFace port and the original Columbia release.

Note also that 51.6 % is the figure the paper reports for the **train** split.
That is probably coincidence, but it is worth one confirmation against the
original `dreaddit.zip` release before the paper states a baseline. **This does
not block dispatch** — 0.516084 is computed from the file actually being used, and
that is the number the results will be scored against.

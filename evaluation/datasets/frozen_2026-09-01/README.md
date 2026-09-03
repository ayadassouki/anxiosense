# Frozen evaluation snapshot — 2026-09-01

Purpose: pin the exact dataset used for the RQ1–RQ3 paper so it cannot change
silently. **Nothing has been deleted from any dataset file.** This directory is
additive: it records what the test splits contained on 2026-09-01 and how to
detect any later drift.

## Files

| File | What it is |
|---|---|
| `MANIFEST.json` | SHA-256 of each processed and source CSV, split counts, test-ID set hashes, label distributions, majority baselines |
| `dreaddit_test_ids.txt` (324) | every ID in the Dreaddit test split |
| `goemotions_test_ids.txt` (2,627) | every ID in the GoEmotions test split |
| `*_test_ids_dispatchable.txt` | the same lists minus rows the server rejects (<10 characters): Dreaddit 324, GoEmotions 2,598 |
| `row_hashes_*_test.csv` | per row: `sample_id`, SHA-256 of `text_redacted`, ground-truth label — detects a single changed character or flipped label |
| `exclusions.csv` | every row with a disclosure-worthy property, with reasons; only `excluded_from_dispatch=yes` rows are withheld from the run |
| `verify_frozen.py` | re-checks everything above; exit 0 = unchanged |

## Verify

```bash
python3 evaluation/datasets/frozen_2026-09-01/verify_frozen.py
```

## What the snapshot records

- Dreaddit test: **324 rows**, labels 1=223 / 0=101, majority baseline **0.688**, 0 rows below the length gate.
- GoEmotions test: **2,627 rows**, non_distress 1,897 / frustration 410 / sadness 235 / fear 69 / **anxiety 16**, majority baseline **0.722**, 29 rows below the length gate.
- Both test splits are proper subsets of the official splits: every GoEmotions test ID
  is in the official `test.csv` (0 leaked from train or validation). Text differs from the
  official files only by trailing-whitespace trimming (139 GoEmotions rows, 8 Dreaddit rows);
  no label was altered.

## Exclusion policy

The 29 GoEmotions rows shorter than 10 characters are rejected by the server
(`/api/workflow/evaluate` returns HTTP 400). They are listed in `exclusions.csv`
with `excluded_from_dispatch=yes` and are the only rows withheld. Duplicate and
cross-split-flagged rows are listed for disclosure but are **still dispatched and
scored**.

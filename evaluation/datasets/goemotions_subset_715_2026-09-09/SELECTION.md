# GoEmotions 715-row evaluation subset — selection record

Built 2026-09-09 by `build_goemotions_715_subset.py` v1.0.0.
Subset tag `goemotions_715_v1` · seed `anxiosense-goemotions-715-v1`
Manifest `evaluation/publication_experiments/manifests/goemotions_715_subset_2026-09-09.json`
`manifest_sha256 05d08ff5b4e18b7ac8e8a4148da41943251b25108751fcf0406d52594067267f`
Derived CSV `goemotions_715_subset.csv`, `sha256 ead551c4ab4822052b9093a7c33e678403e659759113563009784f43e2cc9b81`

## Why this subset exists

Supervisor decision, 2026-09-09: evaluate roughly 715 GoEmotions examples so the scope is
size-comparable with the 715-row Dreaddit test scope, rather than all 5,427; and force-include
the 25 examples Abel selected for RQ4/RQ5 so RQ1–RQ3 and RQ4/RQ5 share concrete examples.

The official 5,427-row scope (`official_goemotions_test.json`, `manifest_sha256 a1dd9874…`)
is **not** superseded, moved or modified. It remains on disk and is still the manifest
`bench_006` used.

## Composition

| | |
|---|---:|
| Rows in scope | **715** |
| Forced (`selection_source = abel_rq4_rq5`) | **25** |
| Random (`selection_source = random_seeded`, ranks 1–690) | **690** |
| Dispatchable by the manifest's accounting | 715 |
| **Scoreable — what the runner actually dispatches** | **623** |
| Unscorable (retained, no invented label) | 92 — 67 `out_of_taxonomy`, 25 `conflicting_classes` |
| Technically excluded (`min_chars`) | 0 |

Original split: **692 test · 21 train · 2 validation**
(the 690 random draws are all `test`; Abel's 25 are 2 test, 21 train, 2 validation).

Class distribution among the 623 scoreable:
`non_distress 487 · frustration 81 · sadness 34 · fear 15 · anxiety 6` — majority baseline 0.781701.

## Selection protocol

**Forced 25.** Abel's file was used as an **ID list only**. Its `label_ids` column is
Excel-corrupted (one cell reads `2026-06-19 00:00:00` where the true value is `6 19`), so text,
label names, mapping and ground truth were all re-derived from the official source CSVs by
joining on `id`. The builder asserts exactly 25 unique ids, each present exactly once in the
54,263-row corpus, before proceeding.

**Random 690.** Eligible pool = the official **test** split, `len(text_processed) >= 10`
(the server's HTTP 400 floor — label-blind), minus the forced ids. Pool size **5,381**;
`sha256` of the sorted pool id list is recorded in `SOURCES.json`.

Selection is deterministic and PRNG-free:

```
POOL     = eligible ids, sorted lexicographically
KEY(id)  = sha256(f"{SEED}:{id}")
SELECTED = the 690 smallest KEYs, ties broken by id
```

`random.Random(seed).sample()` was deliberately **not** used: CPython's implementation has
changed across versions, so the same seed can yield a different draw on a different
interpreter. Hash ordering reproduces in any language or version.

**No selection was made on labels, text content, anxiety keywords, model outputs, or desired
class balance.** The draw was computed once and stands; it has not been re-rolled.

## Why `split` is the subset tag and not `test`

`runner/manifest.py` line 57 selects rows by an exact string match on the `split` column. This
subset is mixed-split, so `build_manifest(split="test")` would have **silently dropped Abel's
23 train/validation rows**. Every row therefore carries `split = goemotions_715_v1`, with the
true origin preserved in `original_split`. The manifest's `official_split` is consequently the
subset tag, not a GoEmotions split, and every attempt record will carry that value.

No runner code was changed to achieve this.

## Sources — all three pinned and asserted before the build

| Split | SHA-256 |
|---|---|
| train | `66684cb3834d92086e8f240abd9dffddf3d5d3d617f2cd72060b8b8de2337084` |
| validation | `dcb425fd4349320e9991b92df4390c51faa529112db3f194a88a71571829f62c` |
| test | `56b5c407adaac0664af58e1a6d067bc726a4bf036e77b7679fca41750bc02ca4` |

The test hash matches the value already pinned in `official_test_2026-09-04/SOURCES.json`.
`train` and `validation` are pinned here for the first time in this repository.

## Authoritative logic reused, never reimplemented

- `clean_text` / `redact_text` — `evaluation/datasets/scripts/preprocess_datasets.py`
- `parse_label_ids` / `technical_status` — `official_test_2026-09-04/build_official_test_scope.py`
- `map_goemotions_labels` — `runner/goemotions_mapping.py`, frozen v1.0.0
- `build_manifest` / `verify_manifest` — `runner/manifest.py`, **unchanged**

`build_manifest` recomputes ground truth itself from the `label_names` column via the frozen
mapper; the derived CSV's `ground_truth` column is informational only and was verified to agree
on all 715 rows.

## Known limitations to disclose in the write-up

1. **The evaluated set is 623, not 715.** The runner iterates `included_sample_ids`, which is
   `n_scorable`. The 92 unscorable rows are retained in the manifest for audit but are never
   sent to a model. (`bench_006` behaved identically: 4,652 dispatched from a manifest whose
   `n_dispatchable` was 5,383.)
2. **The anxiety class is n=6, and 4 of the 6 are purposively selected** (`ge_edzg5j5`,
   `ge_eef78gb`, `ge_eenv6nx`, `ge_eevpwe1` from RQ4/RQ5; `ge_edvnv86` and `ge_eef48yd` random).
   The anxiety class is therefore majority non-random and must be reported descriptively, not
   as a per-class metric.
3. **Mixed split.** 21 train and 2 validation rows are present by supervisor decision. There is
   no fine-tuning, so there is no leakage in the usual sense, but the scope is not the official
   test split and must not be described as such.
4. **`n_excluded` is 0** because the pool was pre-filtered on length. The 44 short rows of the
   full test split do not appear in this manifest's `excluded_samples`; they remain documented
   in the full-scope manifest and in `official_test_2026-09-04/goemotions_excluded_rows.csv`.
5. **One crisis-text candidate** among Abel's 25: `ge_eelf9bs` ("I actually want to die rn…").
   If the server's safety check intercepts it, it short-circuits before any LLM call and yields
   no model prediction. Such rows must not be scored as predictions.

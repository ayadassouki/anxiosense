# Obtaining the official Dreaddit test split (715 rows)

**Status: blocked on a manual download.** The 715-row official test split is not
present anywhere in the repository or in the supplied archive. Only the
anxiety-filtered 324-row subset exists locally, and the 391 rows the filter
removed cannot be recovered from it.

`huggingface.co` is unreachable from **both** execution environments
(cloud container and the desktop workspace VM) — verified, HTTP 000. The official
Columbia mirror returns 403. So the file has to be fetched in a normal browser or
terminal outside the sandbox.

## Step 1 — download (any one of these)

```bash
# a) HuggingFace, the source the original filter script used
pip install datasets
python3 - <<'PY'
from datasets import load_dataset
ds = load_dataset("andreagasparini/dreaddit")
ds["test"].to_pandas().to_csv("dreaddit_test.csv", index=False)
print(len(ds["test"]), "test rows")   # expect 715
PY
```

```bash
# b) Kaggle mirror of the original release
#    https://www.kaggle.com/datasets/turcotte/dreaddit
#    use dreaddit-test.csv from the archive
```

Both must yield **715 rows**. If a source gives a different count, stop and say so
rather than proceeding — it is not the official split.

## Step 2 — place it

```
evaluation/datasets/dreaddit_official/dreaddit_test.csv
```

Do not overwrite or move `evaluation/datasets/dreaddit/dreaddit_anxiety_subset.csv`.
The filtered subset stays exactly where it is as historical evidence.

## Step 3 — record the exact revision

Note where it came from, so `SOURCES.json` can pin more than a file hash:

```bash
python3 -c "from datasets import load_dataset; \
d=load_dataset('andreagasparini/dreaddit'); print(d['test'].info.download_checksums)"
```

The current manifest records `revision: NOT pinned`. That gap closes here.

## Step 4 — build and verify

```bash
python3 evaluation/datasets/official_test_2026-09-04/build_official_test_scope.py
```

The builder will hash-pin the new file into `SOURCES.json` and emit
`dreaddit_test_official.csv` alongside the GoEmotions files, using the identical
transformation chain.

### Acceptance checks

| Check | Expected |
|---|---|
| Rows | **715** |
| Label values | `0` / `1` only, no nulls |
| Positive rate | **≈52.4 %** (Turcan & McKeown 2019 §5) — a value near 68.8 % means the filtered subset was supplied by mistake |
| Superset check | all **324** ids in `dreaddit_anxiety_subset.csv` (split=test) present |
| Abel's RQ4/RQ5 | all **25** Dreaddit ids present |
| Columns | `id`, `text`, `label` required; `subreddit`, `post_id`, `confidence` kept if present |

The superset and positive-rate checks together are what prove the correct file was
obtained. Both will be run automatically before anything is dispatched.

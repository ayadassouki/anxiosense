# Data Preprocessing — AnxioSense LLM Evaluation

This document describes every preprocessing decision applied to the Dreaddit and
GoEmotions datasets before they are used for AnxioSense pipeline evaluation.
It is intended to fulfil two purposes:

1. **Reproducibility** — another researcher can re-run `preprocess_datasets.py`
   and obtain bit-identical output files.
2. **Thesis methodology chapter** — every decision is justified so it can be
   described in Section 4 (Experimental Methodology) without ambiguity.

---

## Guiding principles

| Principle | Implementation |
|---|---|
| Benchmark integrity | Labels are never changed, imputed, or rebalanced. |
| Transparency | Every removed row is logged with an exact reason. |
| Conservation | Duplicate rows and cross-split overlaps are flagged, not removed. |
| Reversibility | The cleaned file plus the exclusion log reconstructs the source file. |
| No silent decisions | Every non-trivial choice is documented here. |

---

## Source datasets

| Dataset | File | Rows | Reference |
|---|---|---|---|
| Dreaddit | `evaluation/datasets/dreaddit/dreaddit_anxiety_subset.csv` | 1,531 | Turcan & McKeown (2019), ACL |
| GoEmotions | `evaluation/datasets/goemotions/goemotions_anxiosense_single.csv` | 26,269 | Demszky et al. (2020), Google |

The source files are read-only. The preprocessing script never writes to them.

---

## Step 1 — Audit findings

Counts verified programmatically by `audit_datasets.py`.

### Dreaddit

| Property | Value |
|---|---|
| Total rows | 1,531 |
| Split: train | 1,207 |
| Split: test | 324 |
| Label=1 (stress) | 1,052 (68.7%) |
| Label=0 (no stress) | 479 (31.3%) |
| Missing text (NaN) | 0 |
| Malformed text rows | **1** — id=559, text=`#NAME?` (Excel formula error) |
| Intra-train duplicate texts | **3** second-or-later occurrences (survey boilerplate × 2, other × 1) |
| Intra-test duplicate texts | 0 |
| Train texts that also appear in test | **3** pairs |
| Text length (chars): min / median / max | 6 / 442 / 1,606 |

### GoEmotions

| Property | Value |
|---|---|
| Total rows | 26,269 |
| Split: train | 21,063 |
| Split: validation | 2,579 |
| Split: test | 2,627 |
| Missing text (NaN) | 0 |
| Malformed text rows | **1** — id=efh341y, text=`#ERROR!` (Excel formula error) |
| Intra-train duplicate texts | **53** second-or-later occurrences |
| Intra-validation duplicate texts | 0 |
| Intra-test duplicate texts | **1** second-or-later occurrence |
| train ∩ test | 7 shared texts |
| val ∩ test | 1 shared text |
| train ∩ val | 11 shared texts |
| Text length (chars): min / median / max | 2 / 65 / 542 |
| Single-label (1 original GoEmotions label) | 22,846 |
| Multi-label (>1 original GoEmotions label) | 3,423 |

**Note on "single-label" definition.** `goemotions_anxiosense_single.csv` was
pre-filtered to rows where exactly **one AnxioSense target emotion** appears in
the GoEmotions label set.  A row is called "single" in the sense that only one
target emotion is active — not that it had only one original GoEmotions label.
The 3,423 multi-label rows had multiple GoEmotions labels, but only one of them
maps to the AnxioSense vocabulary.

---

## Step 2 — Cleaning

### What is cleaned

| Operation | Rationale |
|---|---|
| Remove malformed rows | Rows where text is NaN, empty, or an Excel formula error cannot be evaluated by the pipeline. Keeping them would inject garbage inputs. |
| Trim leading/trailing whitespace | Prevents accidental text inequalities when comparing duplicates; has no effect on model behaviour since the LLM tokeniser ignores leading/trailing spaces. |
| Normalise line endings to `\n` | Windows CRLF (`\r\n`) and old Mac CR (`\r`) would cause inconsistent duplicate detection and log file sizes on different operating systems. |
| Preserve all Unicode | Dreaddit and GoEmotions contain emoji, non-Latin characters, and special punctuation. Removing them would change the semantic content of the input. |

### What is NOT done

| Action | Reason not taken |
|---|---|
| Remove intra-split duplicates | Removing duplicates would silently change the class distribution and the total row count without a corresponding benchmark decision. Duplicates are flagged instead. |
| Remove cross-split overlaps | The official train/test splits are the benchmark's definition of what is evaluated. Removing train rows because they also appear in test would silently shrink the training pool and could affect reproducibility of any downstream fine-tuning comparison. Cross-split overlaps are flagged and reported. |
| Apply a minimum text length | Brevity is not malformation. Short texts (e.g. "ok", 2 chars) are valid Reddit responses and are handled by the pipeline the same way as long texts. A length cutoff would be an undisclosed filtering decision. |
| Rebalance labels | Dreaddit is imbalanced (68.7% stressed). Rebalancing would not reproduce the real-world distribution and would invalidate comparison against the original Dreaddit benchmark results. |
| Impute missing emotion labels | GoEmotions labels are the benchmark ground truth. Any imputation would violate the benchmark's integrity. |

### Malformed row definition

A row is malformed if and only if:

1. **NaN / non-string text** — the text field is null or not a string type.
2. **Empty text** — the text field is empty after stripping whitespace.
3. **Excel formula error** — the text matches one of: `#NAME?`, `#REF!`,
   `#VALUE!`, `#N/A`, `#DIV/0!`, `#ERROR!` (case-insensitive). These strings
   appear when a CSV is exported from a spreadsheet that contains cells with
   unresolved formula references. They are not natural-language text.

No other criterion is used.

### Duplicate flagging

Two boolean columns are added to every processed row:

| Column | Meaning |
|---|---|
| `is_intra_split_duplicate` | `True` if this row's text (trimmed) appeared in an earlier row within the **same split**. The first occurrence is `False`; subsequent ones are `True`. |
| `is_cross_split_duplicate` | `True` if this row's text (trimmed) appears in **any other split**. Both the train and the test occurrence are flagged. |

These columns are for analysis only. The experiment runner uses all rows
regardless of flag value.

### Redaction

A `text_redacted` column is added containing a copy of the cleaned text with
the following tokens replaced:

| Target | Replacement token | Pattern |
|---|---|---|
| HTTP/HTTPS/FTP URLs | `[URL]` | `https?://\S+` or `ftp://\S+` |
| Bare www. URLs | `[URL]` | `\bwww\.\S+` |
| Email addresses | `[EMAIL]` | Standard RFC 5321 local-part@domain pattern |
| Phone numbers | `[PHONE]` | NANP and `+country-code` variants |
| Reddit usernames | `[USER]` | `\bu/[A-Za-z0-9_\-]{1,20}\b` |
| Reddit subreddits | `[SUBREDDIT]` | `\br/[A-Za-z0-9_]{1,21}\b` |

The original `text` column (cleaned) is preserved unchanged.
The `text_redacted` column is provided for privacy-safe logging and inspection;
the **pipeline uses `text`, not `text_redacted`**.

Redaction is best-effort — it does not guarantee complete anonymisation.

### Stable sample IDs

Each row is assigned a `sample_id` of the form `{prefix}_{original_index:06d}`,
where `original_index` is the 0-based row index in the source CSV file and
`prefix` is `dread` or `ge`.  These IDs are:

- **Stable** — the same source file always produces the same ID.
- **Unique** — verified by `verify_preprocessing.py`.
- **Traceable** — given a sample_id, the original row can be found without
  running the script (just look up the index in the source file).

---

## Step 3 — GoEmotions label mapping

### Background

GoEmotions defines 28 emotion classes.  The AnxioSense Emotion Agent outputs
from a closed vocabulary of 7 distress-relevant classes.  For evaluation, both
must be expressed in a common label space.

`goemotions_anxiosense_single.csv` was pre-filtered to the 10 GoEmotions
emotion labels that overlap (partially) with the AnxioSense vocabulary:
`anger`, `annoyance`, `disappointment`, `fear`, `grief`, `joy`, `nervousness`,
`neutral`, `relief`, `sadness`.

### Why a "non_distress" class is mandatory

The previous design (before this preprocessing pipeline) mapped `neutral`, `joy`,
and `relief` to `None` and excluded those rows from evaluation.

This is **methodologically incorrect** for the following reason: if the
AnxioSense Emotion Agent predicts `anxiety` on a text whose ground truth is
`neutral`, that is a **false positive**. Excluding such rows means false
positives on non-distress texts are never penalised, which artificially inflates
precision on the distress classes.

The corrected design introduces `non_distress` as an **explicit evaluation
class**. A model that predicts any distress emotion on a `non_distress` text
will have that prediction counted as incorrect.

### Mapping table

#### Ground truth: GoEmotions → evaluation class

| GoEmotions label | Evaluation class | Rationale |
|---|---|---|
| `nervousness` | `anxiety` | Conceptually equivalent; nervousness is the GoEmotions label closest to clinical anxiety. |
| `fear` | `fear` | Direct match. |
| `sadness` | `sadness` | Direct match. |
| `grief` | `sadness` | Grief is extreme sadness; no closer AnxioSense class exists. |
| `anger` | `frustration` | The AnxioSense vocabulary does not include anger; frustration is the closest available class. |
| `annoyance` | `frustration` | Mild anger; same mapping as anger. |
| `disappointment` | `sadness` | Loss/unmet expectation; sadness is the closest AnxioSense class. |
| `neutral` | `non_distress` | The model should produce an empty emotions list or no distress emotion for neutral text. |
| `joy` | `non_distress` | Positive affect; a distress prediction would be a false positive. |
| `relief` | `non_distress` | Positive/neutral affect; same reasoning as joy. |
| *(empty list)* | `non_distress` | A row with no emotion label maps to non_distress. |

#### Predicted: AnxioSense Emotion Agent → evaluation class

| AnxioSense emotion | Evaluation class | Rationale |
|---|---|---|
| `anxiety` | `anxiety` | Direct match. |
| `stress` | `anxiety` | Stress is the most common AnxioSense distress output; conceptually closest to anxiety/nervousness in GoEmotions. |
| `fear` | `fear` | Direct match. |
| `sadness` | `sadness` | Direct match. |
| `hopelessness` | `sadness` | No direct GoEmotions ground-truth equivalent; sadness is the closest evaluation class. |
| `loneliness` | `sadness` | Same reasoning as hopelessness. |
| `frustration` | `frustration` | Direct match. |
| *(empty list / None)* | `non_distress` | The model detected no emotion, which is the correct response for non_distress texts. |

#### Evaluation class space

```
EVAL_CLASSES = ("anxiety", "fear", "sadness", "frustration", "non_distress")
```

**Classes included**: all five classes participate in macro F1 and per-class
precision/recall.

**No classes excluded**: unlike the previous design, `non_distress` rows are
never dropped from evaluation.

### Disclosures required in the thesis

1. The mapping from `anger` to `frustration` is not exact — GoEmotions'
   `anger` and AnxioSense's `frustration` overlap conceptually but are not
   identical.  This creates a systematic mapping imprecision for the frustration
   class.

2. The mapping from `stress` to `anxiety` (prediction side) means that the most
   common AnxioSense output is evaluated against the `anxiety` class.  If the
   model outputs `stress` for a `nervousness` ground-truth row, that is counted
   as a correct anxiety classification.  This is the best available alignment
   given the vocabulary mismatch.

3. GoEmotions `hopelessness` and `loneliness` have no ground-truth equivalent in
   this dataset; they can only appear as predictions.  If the model outputs these
   for a `sadness` text they count as correct; if output for a `non_distress`
   text they count as false positives.

---

## Step 4 — Verification

`verify_preprocessing.py` asserts all of the following:

```
source_rows == processed_rows + excluded_rows          (exact, per dataset)
test_split_rows_in_source == test_split_rows_in_processed  (test integrity)
every excluded original_index is absent from processed file
every cross_split_overlap sample_id is present in processed file
sample_id values are unique within each processed file
all required columns (text, text_redacted, sample_id, split,
    is_intra_split_duplicate, is_cross_split_duplicate) are present
preprocessing_report.json processed_rows matches actual file row count
```

Run:
```
python evaluation/datasets/scripts/verify_preprocessing.py
```

Expected output:
```
All assertions passed.
  Dreaddit:   1531 source = 1530 processed + 1 excluded
  GoEmotions: 26269 source = 26268 processed + 1 excluded
```

---

## Step 5 — Integration

The experiment pipeline uses the processed datasets exclusively.
The configuration is in `evaluation/llm-experiments/config/experiment_config.yaml`:

```yaml
datasets:
  dreaddit:
    path: "evaluation/datasets/processed/dreaddit_clean.csv"
    ...
  goemotions:
    path: "evaluation/datasets/processed/goemotions_clean.csv"
    ...
```

**The evaluation logic, metrics, and model prompts are not modified by this
preprocessing pipeline.**

---

## Deliverable checksums (row counts)

| File | Source rows | Excluded | Processed rows |
|---|---|---|---|
| `dreaddit_clean.csv` | 1,531 | 1 | **1,530** |
| `goemotions_clean.csv` | 26,269 | 1 | **26,268** |

Verify with:
```bash
python evaluation/datasets/scripts/verify_preprocessing.py
```

---

## File inventory

| File | Role |
|---|---|
| `evaluation/datasets/scripts/audit_datasets.py` | Read-only audit; produces no output files |
| `evaluation/datasets/scripts/preprocess_datasets.py` | Creates cleaned datasets, report, and log |
| `evaluation/datasets/scripts/verify_preprocessing.py` | Asserts source = processed + excluded |
| `evaluation/datasets/processed/dreaddit_clean.csv` | Cleaned Dreaddit dataset |
| `evaluation/datasets/processed/goemotions_clean.csv` | Cleaned GoEmotions dataset |
| `evaluation/datasets/processed/preprocessing_report.json` | Row counts and text statistics |
| `evaluation/datasets/processed/exclusion_log.json` | Every excluded row + cross-split overlaps |
| `evaluation/datasets/DATA_PREPROCESSING.md` | This document |

---

## How to reproduce from scratch

```bash
# 1. Audit (read-only, no file changes)
python evaluation/datasets/scripts/audit_datasets.py

# 2. Generate cleaned datasets
python evaluation/datasets/scripts/preprocess_datasets.py

# 3. Verify
python evaluation/datasets/scripts/verify_preprocessing.py
```

All three scripts must be run from the repository root.
Python 3.10+ and pandas are required (`pip install pandas`).

# Official test-split evaluation scope — 2026-09-04

Scope decision: RQ1–RQ3 evaluate on the **full official test splits**.

| Dataset | Official test rows | Status |
|---|---:|---|
| GoEmotions | **5,427** | built, all rows retained |
| Dreaddit | **715** | built, all rows retained, all dispatchable |

This replaces the previous candidate scope (Dreaddit 324, GoEmotions 2,598).
The Dreaddit 324 was produced by an anxiety-keyword/LIWC filter that selects on a
feature correlated with the label; it is **not** applied here, and no other
content-based filter is applied either.

Nothing outside this folder is written. Source files are read-only and hash-pinned
in `SOURCES.json`.

## Files

| File | Contents |
|---|---|
| `build_official_test_scope.py` | the only builder; deterministic, re-runnable |
| `SOURCES.json` | hash-pinned sources, policy, and build statistics |
| `goemotions_test_official.csv` | **all 5,427** official test rows |
| `goemotions_label_handling.csv` | all 28 labels × what the current methodology does |
| `goemotions_excluded_rows.csv` | the 44 technically non-dispatchable rows, with reasons |
| `dreaddit_test_official.csv` | **all 715** official test rows |
| `DREADDIT_SOURCE.md` | how the 715-row split was obtained and verified |
| `DREADDIT_ACCEPTANCE.md` | the seven acceptance checks and their results |
| `METHODOLOGY_DECISIONS_REQUIRED.md` | GoEmotions label handling — open decisions |

## Transformations applied — the complete list

Every step is deterministic and label-blind. Nothing consults the label, the
ground truth, or any model output. Re-running the builder reproduces
byte-identical files (verified).

1. **Line-ending normalisation** — `\r\n` and `\r` → `\n`.
2. **Whitespace trim** — leading and trailing only. Internal whitespace, casing,
   Unicode, emoji, slang, and misspellings are all preserved exactly.
3. **PII redaction**, applied in this order to the trimmed text:
   `https?://…` and `ftp://…` → `[URL]`; `www.…` → `[URL]`;
   email addresses → `[EMAIL]`; NANP/international phone numbers → `[PHONE]`;
   `u/username` → `[USER]`; `r/subreddit` → `[SUBREDDIT]`.

Steps 1–3 are imported from `evaluation/datasets/scripts/preprocess_datasets.py`,
not reimplemented, so exactly one copy of this logic exists in the repository.

**Nothing else is done.** No lowercasing, no Unicode folding, no punctuation
stripping, no stopword removal, no truncation, no deduplication, no language
detection, no quality or toxicity filter, no length filter beyond the technical
floor recorded below.

Both texts are kept on every row: `text_original` is verbatim from source,
`text_processed` is what would be sent to the API. `text_was_modified` flags the
355 rows where they differ.

## Rows are never removed

All 5,427 GoEmotions and all 715 Dreaddit rows are present. Rows the server cannot
accept are marked `dispatchable=False` and carry a predefined `exclusion_reason`:

| Reason | GoEmotions | Dreaddit | Basis |
|---|---:|---:|---|
| `below_min_chars:10` | 44 | 0 | `POST /evaluate` returns HTTP 400 below 10 characters |
| `empty_text` | 0 | 0 | zero-length after whitespace normalisation |
| `excel_formula_error` | 0 | 0 | `#NAME?`, `#REF!` and similar |
| `missing_text` | 0 | 0 | null or non-string |

**Every one of the 715 Dreaddit rows is dispatchable.**

## Dreaddit ground truth

All 715 rows map cleanly through `map_dreaddit_label` (0/1), so `gt_status` is
`mapped` for every row and there are no open mapping questions on this dataset.

| | Rows | Positive rate | Majority baseline |
|---|---:|---:|---:|
| Official test split (this file) | **715** | 51.61 % | **0.516084** |
| Superseded anxiety/LIWC subset | 324 | 68.83 % | 0.688272 |

The old filter removed **391** rows and inflated the positive rate by 17.2 points.
Each row carries `in_superseded_324_subset` so the difference stays auditable;
that column is provenance only and is never used to include or exclude anything.
`lex_liwc_anx` is carried for the same reason and is **not** used as a filter.

The derived Dreaddit file keeps `id`, `text_original`, `text_processed`, the label,
and `subreddit`, `post_id`, `sentence_range`, `confidence`, `lex_liwc_anx`. The
other 106 columns of the original (the full LIWC/social feature block) stay in the
hash-pinned source file, which is unchanged and complete.

All four rules are decidable from the text alone, before any model call. No row
is excluded for being noisy, slang-heavy, unusual, or hard.

## Ground truth is never invented

`gt_status` and `dispatchable` are **orthogonal**. A row can be dispatchable with
no ground truth.

| `gt_status` | Rows | Meaning |
|---|---:|---|
| `mapped` | 2,627 | exactly one label with a class in the 5-class space |
| `unmapped_no_mappable_emotion` | 2,670 | no label has a class — **decision required** |
| `ambiguous_multiple_mappable_emotions` | 130 | two or more mappable labels — **decision required** |

Ground truth of the 2,627 mapped rows:
non_distress 1,897 · frustration 410 · sadness 235 · fear 69 · **anxiety 16**.

**Scorable under the methodology as it stands today: 2,598** — mapped and
dispatchable. This reproduces the previous candidate manifest exactly, class by
class, which confirms the two lineages agree wherever they overlap.

## What each dataset measures — do not conflate them

| Dataset | Construct annotated | What it can support |
|---|---|---|
| Dreaddit | **stress vs. non-stress** (binary, crowdsourced; Turcan & McKeown 2019) | stress detection only |
| GoEmotions | 27 emotions + neutral, projected onto five AnxioSense classes by the frozen v1.0.0 mapping | affect discrimination across those five classes |

**Dreaddit does not carry, validate, or substitute for the GoEmotions `anxiety`
class.** Stress and anxiety are different constructs and the two corpora are
annotated for different things. Under the frozen mapping, `anxiety` derives solely
from GoEmotions `nervousness` and has **n = 14** scorable instances (interrater
Spearman rho = 0.164, the second-lowest in the taxonomy). That is a **limitation to
report explicitly**, and it must not be compensated for with Dreaddit results.

## Sample identifiers

`sample_id` is `ge_<official comment id>` (and will be `dread_<official id>`),
derived from the dataset's own identifier rather than from row position.

The previous scheme used positional ordinals (`ge_000000`, `dread_000000`). Those
do not survive a rebuild and do not join across preprocessing lineages — the
2026-09-04 alignment audit found that joining Abel's RQ4/RQ5 selections on
`sample_id` returned zero matches and looked like total data loss. Content-derived
ids remove that failure mode permanently.

## Carried forward from the previous pipeline — flagged, not decided

PII redaction changes the model's input. It is retained here for comparability
with `smoke_001` and the bench runs, and because it is deterministic and
label-blind. If the paper should evaluate on unredacted text, that is a
methodology change to make deliberately, not a preprocessing tweak — the
`text_original` column is preserved on every row so it can be made without
rebuilding anything.

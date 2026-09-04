# GoEmotions: how the current methodology handles every original label

Required reading before any RQ1–RQ3 dispatch on the 5,427-row scope.
Per-label table: `goemotions_label_handling.csv`. Nothing below has been changed
or decided — this is a report.

## The finding

**Extending the scope from 2,627 to 5,427 rows turns a currently harmless branch
into silent ground-truth fabrication.**

`map_goemotions_label` (`evaluation/llm-experiments/src/label_mapping.py`) is fed
`emotion_names` — the list already filtered to the 10 mappable emotions — and:

```python
emotion = parse_goemotions_label(raw)
if emotion is None:
    # Empty emotion list in the dataset — treat as non_distress
    return "non_distress"
```

In the **current** 2,627-row scope every row has exactly one mappable emotion, so
this branch never executes. In the **5,427-row** scope it executes for **2,670
rows** whose only labels are `gratitude`, `curiosity`, `love`, `admiration`,
`approval`, `disapproval`, `surprise`, `remorse` and so on.

A comment labelled `gratitude` would silently acquire ground truth
`non_distress`. That is not a preprocessing step — it is a new methodology claim
("gratitude means no distress") made by a fallback branch, invisibly.

It also **defeats the guardrail**. `build_manifest` aborts when a mapping raises
`LabelMappingError`. This branch does not raise — it returns a plausible value.
The manifest would build cleanly and look correct.

Quantified over the 5,383 dispatchable rows:

| | n | Majority baseline |
|---|---:|---:|
| Current methodology (mapped rows only) | 2,598 | 0.720169 |
| If the empty-list branch fired for all unmapped rows | 5,268 | **0.864945** |

That is **2,670 fabricated labels (50.7 % of the dispatchable test set)** and a
**+0.1448** shift in the number every model must beat. It would make the
GoEmotions results meaningless.

**The builder does not do this.** Unmapped rows carry
`gt_status = unmapped_no_mappable_emotion` and an **empty** ground truth.

## Decision 1 — the 18 labels with no class (2,670 rows)

`admiration · amusement · approval · caring · confusion · curiosity · desire ·
disapproval · disgust · embarrassment · excitement · gratitude · love ·
optimism · pride · realization · remorse · surprise`

Options:

- **1A — Keep them out of scoring (recommended).** They stay in the source scope
  and in the CSV, are dispatched or not as you choose, and are reported as
  "outside the 5-class evaluation space". Honest, and it changes nothing that has
  already been validated. Scorable n = 2,598.
- **1B — Extend the mapping.** Requires a defensible, citable rule for each of the
  18. Several are genuinely hard: is `surprise` distress? is `disapproval`
  frustration? This is a real research contribution if done properly and a
  reviewer magnet if done casually.
- **1C — Map them all to `non_distress`.** What the code would do by accident.
  Defensible *only* with an explicit argument that "no distress-adjacent label
  was assigned" means "not distressed" — and the +0.1448 baseline shift must then
  be reported prominently. I would not recommend it.

**Whatever is chosen, the empty-list branch should be made to raise instead of
returning `non_distress`,** so the decision lives in the mapping table rather
than in a fallback.

## Decision 2 — the 130 multi-mappable rows

`parse_goemotions_label` returns the **first** element of the list. GoEmotions
stores label ids ascending, so this is an undocumented "lowest emotion id wins"
tie-break. `fear|nervousness` → `fear`; `annoyance|neutral` → `frustration`.

Splitting them by whether the tie-break actually matters:

| | Rows | Note |
|---|---:|---|
| Collapse to **one** class in the 5-class space | **55** | e.g. `anger\|annoyance` → both `frustration`; `grief\|sadness` → both `sadness`. The tie-break is irrelevant; ground truth is unambiguous. |
| Genuinely **conflicting** classes | **75** | `frustration\|non_distress` 30 · `frustration\|sadness` 19 · `non_distress\|sadness` 12 · `fear\|non_distress` 3 · `anxiety\|fear` 3 · others 8 |

- **2A — Admit the 55 (recommended), exclude the 75.** Not a new mapping: the
  existing table already assigns all their labels to the same class. Scorable
  n = **2,653**, majority baseline **0.707878**. The rule is stated in one line
  and is fully auditable.
- **2B — Exclude all 130.** Status quo. Scorable n = 2,598.
- **2C — Adopt a documented tie-break for the 75** (e.g. distress outranks
  non_distress, or annotator-count priority). A real decision with a real
  rationale — but it must be argued, not inherited from list ordering.

## Decision 3 — the `anxiety` class has 16 instances

`nervousness` → `anxiety` is the only route into the class AnxioSense exists to
detect, and the official test split contains **16** such rows (23 where
`nervousness` appears at all, 12 where it is the only label).

Per-class F1 for `anxiety` will be extremely unstable — one flip moves it by
several points. Options: report it with a bootstrap confidence interval and say
so explicitly; or state up front that GoEmotions measures general affect
discrimination. **Dreaddit cannot be used to compensate:** it is annotated for
*stress vs. non-stress*, a different construct, and carries no anxiety class. The
n = 14 support for `anxiety` is a limitation to report, not a gap to fill from
another dataset. **This does not
block dispatch, but it must be decided before the results section is written.**

## Not a problem: the prediction side

`map_anxiosense_prediction_to_eval_class` **raises** on an unrecognised predicted
emotion (recorded as a parse failure, never scored as a class) and maps an empty
emotion list to `non_distress`. The asymmetry is deliberate and was verified in
the 2026-09-02 audit: empty-prediction and failure are separated by
`emotion_payload`'s tri-state ladder. No change needed.

## Summary

| # | Decision | Rows affected | Recommendation |
|---|---|---:|---|
| 1 | 18 unmapped labels | 2,670 | 1A — out of scoring, in scope, reported |
| 2 | multi-mappable rows | 130 (55 + 75) | 2A — admit the 55, exclude the 75 |
| 3 | `anxiety` n = 16 | 16 | report with a CI; state the limitation |
| — | empty-list fallback | code | make it raise rather than return `non_distress` |

Under the recommendations, GoEmotions scorable n = **2,653** of 5,427 in scope,
majority baseline **0.707878**. Every one of the 5,427 rows stays in the CSV with
a status; none is silently dropped and none is given an invented label.

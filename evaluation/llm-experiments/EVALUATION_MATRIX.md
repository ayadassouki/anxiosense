# AnxioSense Evaluation Matrix

Generated: 2026-08-01  
Status: pre-experiment (no paid API calls made)

---

## Column definitions

| Column | Meaning |
|---|---|
| **Dataset** | Benchmark used for ground truth |
| **Original target** | What the benchmark was designed to measure |
| **AnxioSense component** | Which part of the pipeline produces the prediction |
| **Predicted label space** | The set of values the model can output |
| **Ground-truth label space** | The set of values in the dataset after mapping |
| **Mapping** | How raw dataset labels → eval classes, and how model output → eval classes |
| **Included classes** | Classes that participate in metric computation |
| **Excluded classes** | Labels or predictions dropped from evaluation (and why) |
| **Metric** | Primary evaluation metric(s) |
| **Methodological limitation** | Known threats to validity for this evaluation design |

---

## Matrix

### Row 1 — Dreaddit, Mapping A (primary)

| Column | Value |
|---|---|
| **Dataset** | Dreaddit (anxiety-filtered subset, 1527 rows: train=1203, test=324) |
| **Original target** | Binary stress classification of Reddit posts (0=no stress, 1=stress) |
| **AnxioSense component** | Full pipeline → `referralLevel` field in `/evaluate` response |
| **Predicted label space** | `"low"` → 0 ∣ `"moderate"` or `"urgent"` → 1 |
| **Ground-truth label space** | {0, 1} (directly from `label` column; integer or string "0"/"1") |
| **Mapping** | Ground truth: `map_dreaddit_label(row["label"])` — trivial cast.<br>Prediction: `extract_stress_label(report_dict)` — `"low"` → 0; `"moderate"`/`"urgent"` → 1. |
| **Included classes** | {0, 1} — all Dreaddit labels |
| **Excluded classes** | None from ground truth. Prediction failures (referralLevel missing or unrecognised) are stored as `failure_reason` and excluded from precision/recall but counted in failure rate. Provider errors (429/timeout) excluded separately. |
| **Metric** | F1 (macro), Precision, Recall, Accuracy, Failure rate |
| **Methodological limitation** | (1) Referral tier is a policy proxy for stress: a genuinely stressed text could receive `"low"` if the Referral Agent underestimates risk (false negative), or a neutral text could receive `"moderate"` from over-cautious reasoning (false positive). These errors are conflated — the mapping cannot distinguish Referral Agent error from Report Agent error. (2) Dreaddit label=1 was assigned by crowdworkers based on subreddit context, not clinical criteria; some label=1 texts are low-distress posts in high-stress communities. (3) Imbalanced: 68.8% stressed in the full set; stratified sampling preserves this ratio. |

---

### Row 2 — Dreaddit, Mapping B (diagnostic)

| Column | Value |
|---|---|
| **Dataset** | Dreaddit (same subset, test split only) |
| **Original target** | Binary stress classification |
| **AnxioSense component** | Emotion Agent only → `emotions` list in `emotion_agent_raw` JSON |
| **Predicted label space** | 1 if `"stress"` or `"anxiety"` appears anywhere in the `emotions` list; 0 if list is empty or contains neither |
| **Ground-truth label space** | {0, 1} — same as Mapping A |
| **Mapping** | Ground truth: `map_dreaddit_label(row["label"])`.<br>Prediction: `extract_emotion_label_from_agent_json(result.emotion_agent_raw)` → check if returned emotion ∈ {"stress","anxiety"}. |
| **Included classes** | {0, 1} |
| **Excluded classes** | None from ground truth. `emotion_agent_raw` absent or unparseable → stored as failure, excluded from precision/recall. |
| **Metric** | F1 (macro), Precision, Recall — compared directly against Mapping A to isolate Referral Agent contribution |
| **Methodological limitation** | (1) Diagnostic only — the Emotion Agent alone does not constitute the system's output; the final referral decision incorporates Symptom, Context, and RAG evidence. (2) Requires `emotion_agent_raw` to be non-null: texts processed via the safety-override path (crisis detected before the full workflow) return null. These are stored as failures. (3) "stress" and "anxiety" are treated as equivalent positives, which may over-count for texts with low-level anxiety that Dreaddit labels as 0. |

---

### Row 3 — GoEmotions, primary (5-class multiclass)

| Column | Value |
|---|---|
| **Dataset** | GoEmotions (AnxioSense-filtered single-target-emotion subset, 26,213 rows: train=21,008 val=2,579 test=2,626) |
| **Original target** | Fine-grained emotion classification (28 emotion classes across Reddit comments) |
| **AnxioSense component** | Emotion Agent → first element of `emotions` list in `emotion_agent_raw` JSON |
| **Predicted label space** | {anxiety, stress, sadness, frustration, fear, hopelessness, loneliness} ∪ {non_distress} (empty `emotions` list → `non_distress`) |
| **Ground-truth label space** | {anxiety, fear, sadness, frustration, non_distress} — 5 classes after mapping |
| **Mapping** | Ground truth: `map_goemotions_label(row["emotion_names"])` — maps GoEmotions emotions to 5-class eval space:<br>• nervousness → anxiety ∣ fear → fear ∣ sadness, grief, disappointment → sadness ∣ anger, annoyance → frustration ∣ neutral, joy, relief → non_distress ∣ empty list → non_distress.<br>Prediction: `map_anxiosense_prediction_to_eval_class(predicted_emotion)` — maps AnxioSense vocab to same 5-class space:<br>• anxiety, stress → anxiety ∣ fear → fear ∣ sadness, hopelessness, loneliness → sadness ∣ frustration → frustration ∣ None/empty → non_distress. |
| **Included classes** | All 5 eval classes: {anxiety, fear, sadness, frustration, non_distress} |
| **Excluded classes** | None from ground truth (the non_distress class is explicit — false positives on neutral/joy/relief texts are penalised). Prediction: LabelMappingError (model output a hallucinated emotion not in AnxioSense vocab) → stored as parse failure, excluded from precision/recall. |
| **Metric** | Macro F1, per-class Precision and Recall, Accuracy, Failure rate |
| **Methodological limitation** | (1) Task mismatch: GoEmotions was annotated for fine-grained affect; AnxioSense is designed for clinical anxiety screening. The Emotion Agent may express nuanced affect that does not map cleanly to any single ground-truth class. (2) Ground-truth labels from the dataset were assigned by crowdworkers on general Reddit comments, not distress-focused posts; the Emotion Agent was prompt-engineered on mental-health-context text. (3) The `goemotions_anxiosense_single.csv` selects rows with exactly one target emotion; if the original annotators assigned multiple GoEmotions labels and >1 maps to our target vocab, those rows are excluded — introducing selection bias toward unambiguous cases. (4) "stress" is the most common AnxioSense Emotion Agent output for distress and maps to "anxiety" for evaluation, but GoEmotions' closest label is "nervousness" (also mapped to anxiety). This alignment is conceptually justified but not exact. (5) 18 cross-split overlaps (train/val texts that also appear in test) are kept in the dataset; they are reported in `exclusion_log.json` and do not affect the test split's integrity, but inflate the apparent training diversity. |

---

## Summary statistics

| Dataset | Clean rows | Test rows | GT classes | Eval classes | Primary prediction source |
|---|---|---|---|---|---|
| Dreaddit | 1,527 | 324 | {0,1} | {0,1} | `referralLevel` (Mapping A) |
| Dreaddit | 1,527 | 324 | {0,1} | {0,1} | `emotion_agent_raw` emotions (Mapping B) |
| GoEmotions | 26,213 | 2,626 | 10 original → 5 eval | {anxiety, fear, sadness, frustration, non_distress} | `emotion_agent_raw` first emotion |

## Design decisions requiring disclosure in thesis

1. **Non-distress as explicit class** (GoEmotions): neutral/joy/relief are mapped to `non_distress` rather than excluded. This ensures false positives on positive-affect texts penalise the model. Prior work that excluded these rows would show artificially inflated precision on distress classes.

2. **Full-pipeline vs per-agent evaluation** (Dreaddit): Mapping A evaluates the complete multi-agent system (the product's actual decision). Mapping B isolates the Emotion Agent to separate its contribution from the Referral Agent. Both must be reported.

3. **Cross-split overlaps reported, not removed**: 3 Dreaddit + 18 GoEmotions train/val texts also appear in the test set. These are logged in `exclusion_log.json` under `cross_split_overlaps` and are retained in the dataset. They do not affect test-split integrity; removing them from train would artificially shrink training diversity without improving evaluation rigour.

4. **Failure rate is a first-class metric**: Parse failures (referralLevel missing, emotion_agent_raw null, hallucinated labels) are counted in a separate failure rate column and never silently counted as incorrect predictions.

# VALIDATION - invalid-output audit 2026-09-25

Generated 2026-09-25T16:27:53.223806+00:00 by `code/05_validate.py`.
This audit is read-only: it reads the frozen artifacts and the append-only raw stores and writes only
into `results/invalid_output_audit_2026-09-25/`.

## Frozen-artifact integrity

Every file of `descriptive_2026-09-21/` was re-hashed and compared, file by file, against the inventory
recorded at the 2026-09-21 freeze (`verification_2026-09-21/freeze_hashes_after.txt`).

32 files recorded at the freeze, 32 present now; 0 changed, 0 missing, 0 added.

**MATCH - the frozen descriptive package is byte-identical to the freeze; this audit changed nothing.**

## Checks

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Row count equals the frozen model-invalid total | **PASS** | rows=1986, frozen model-invalid=1986, expected 1986 (Dreaddit 599 / GoEmotions 1387) |
| 2 | Per-cell counts reproduce cell_metrics.json exactly | **PASS** | 150 cells compared, 0 mismatches, 0 cells not in the frozen manifest |
| 3 | No safety intercept is classified as model-invalid | **PASS** | 0 rows carry a SAFETY_INTERCEPT class/status; 0 rows flag safety_intercept. The frozen grid holds 1275 safety intercepts, all excluded from this dataset. |
| 4 | No recovered infrastructure failure is classified as model-invalid | **PASS** | 0 rows with an INFRA failure_class, 0 with a non-OK final outcome, 0 with a non-OK transport outcome. Frozen grid infrastructure failures: 0. 5 rows did involve >1 dispatch attempt, but every one terminated OK, so the invalid verdict is a parse outcome, never a transport outcome. |
| 5 | Every row maps to a frozen authoritative record | **PASS** | 1986 distinct uuids for 1986 rows; 0 not found in authoritative_records.jsonl; 0 cell_id mismatches |
| 6 | Every raw example is joined to the correct terminal attempt | **PASS** | 1986 rows carry raw evidence; cell_id, sample_id and experiment_id agree with the attempts store for all of them; 0 mismatches |
| 7 | Checksums produced for every generated file | **PASS** | 15 files hashed into CHECKSUMS.sha256; VALIDATION.md and CHECKSUMS.sha256 are excluded because they are written after the hashes are computed |
| 8 | Raw coverage is complete | **PASS** | 1986 of 1986 rows are classified from their own raw terminal attempt (0 RAW_UNAVAILABLE) |
| 9 | Every raw store used matches the hash recorded at the freeze | **PASS** | 9 source runs gated against descriptive_2026-09-21/source_parse_summaries raw_attempts_sha256; 0 did not match |
| 10 | Every hallucination candidate was manually adjudicated | **PASS** | 17 automated candidates -> 4 CONFIRMED, 13 REJECTED, 0 unreviewed; no record is marked hallucination on the heuristic alone |
| 11 | Any RAW_UNAVAILABLE record is inventoried, never classified | **PASS** | 0 of 1986 rows have no reachable raw evidence; the rule holds vacuously |

Overall: **ALL CHECKS PASS**

## Raw-evidence coverage

**Complete: 1986 of 1986 rows (100%) are classified from their own raw terminal attempt. No row is marked `RAW_UNAVAILABLE`.**

## Provenance gate

Each raw store was hashed and compared against the `raw_attempts_sha256` recorded for that source run in `descriptive_2026-09-21/source_parse_summaries/`. A store that does not match is refused.

| source run | verdict | sha256 | store |
|---|---|---|---|
| `pub_001_dreaddit_qwen` | **match** | `9ae3a57fdf617f71…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_001_dreaddit_qwen/raw/attempts.jsonl` |
| `pub_002_dreaddit_mistral` | **match** | `bc69fccdbe04f733…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_002_dreaddit_mistral/raw/attempts.jsonl` |
| `pub_003_dreaddit_llama` | **match** | `44bdeca92156d50e…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/external_run_evidence/publication_experiments/runs/pub_003_dreaddit_llama/raw/attempts.jsonl` |
| `pub_005_dreaddit_phi` | **match** | `c3e584ef71c83e7f…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_005_dreaddit_phi/raw/attempts.jsonl` |
| `pub_006_goemotions715_mistral` | **match** | `04f96ca2ed642733…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_006_goemotions715_mistral/raw/attempts.jsonl` |
| `pub_007_goemotions715_qwen` | **match** | `bc6cd1a554ea9dac…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/external_run_evidence/publication_experiments/runs/pub_007_goemotions715_qwen/raw/attempts.jsonl` |
| `pub_008_goemotions715_phi` | **match** | `fd9ebde77c81a17b…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/external_run_evidence/publication_experiments/runs/pub_008_goemotions715_phi/raw/attempts.jsonl` |
| `pub_009_goemotions715_llama` | **match** | `6fd4ddf67d55a272…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_009_goemotions715_llama/raw/attempts.jsonl` |
| `pub_012_goemotions715_gemma_coreweave` | **match** | `c4f5bbb7a8a2e34c…` | `/sessions/rcw-01tldftdzkuzryhbrh3dpogw/mnt/anxiosense/evaluation/publication_experiments/runs/pub_012_goemotions715_gemma_coreweave/raw/attempts.jsonl` |

## Checksums

| file | bytes | sha256 |
|---|---|---|
| `cell_level_invalid_vs_quality.csv` | 6,094 | `837071b8488b877300f40ea53b37054e2b46ff0c856fd3dd55cdc68196ad9f46` |
| `code/01_build_index.py` | 2,286 | `873486fe24d7eb18d872f0f675396c3202526c03954ffd88a94b8e6fb60a2e36` |
| `code/02_extract_raws.py` | 4,730 | `1463fd4ddaf37977783d3df0213a0f039a3ac02652a8d1cb768304df5119c787` |
| `code/03_classify.py` | 37,411 | `dcc98741e89bde7b281a80a7006a017cf6e6ce635dd23a99a110cb5dae6d173f` |
| `code/04_summaries.py` | 6,997 | `751557163c85cedd59b54b31313bc9d77540a7b8ec50abc3325ab418fd646cdf` |
| `code/05_validate.py` | 11,159 | `d8fafe90cdb8e2d06d7facf9b9022b9c12fcd9cf36b9cb2d646905bcb383e75f` |
| `code/06_quality_join.py` | 3,096 | `27926ab0e808ff5c8fc978723b23aa0779258194a9b7f8f511facbd0b768ca16` |
| `code/07_review_subset.py` | 30,224 | `7ad795d779311fa8418feba1c82f7959a99d5bd7a4e0a0fed46bafa174c73bf5` |
| `failure_taxonomy_summary.csv` | 3,980 | `91606c80d51f44098247fea4e3263733a6a6744e94eeaed3cb23d9d9523bdac4` |
| `invalid_output_audit_report.md` | 58,867 | `4f629fe1cb429f151bf5f767c23440cfdc553ce79b3e8d46924fa4e42c6fa2b2` |
| `invalid_outputs_review_subset.csv` | 130,249 | `58252dde59ae01333a347c664655b31450b416cb7e0106d78ba6ef30ff95e2bb` |
| `invalid_outputs_review_subset_guide.md` | 24,526 | `34760c0d66f903a21e45021e77d70905a1eae87d67c35987414a7bd4a34ad9e0` |
| `invalid_outputs_row_level.csv` | 4,147,986 | `18a6c43efc029cc7eaa101cc6cb5e843cf6b5d075755726ef487e6f0df562d05` |
| `invalid_outputs_row_level.jsonl` | 6,905,555 | `b48b601bd2277fe4b98ea8566d8a0af3491084af6f8e2717b80a2994dc3b164c` |
| `unique_sample_recurrence.csv` | 3,721 | `87b6b6f6b74651e0a5fa7957373c722f01a3227ccec4e0f61ae239daef5da542` |

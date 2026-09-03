# This tree is historical. Read-only.

`evaluation/llm-experiments/` produced the EECS 4080 Stage C results. It is kept
verbatim as evidence and must not be modified, migrated, cleaned or deleted.

Publication experiments run from `evaluation/publication_experiments/`, which
writes to its own output root and never reads this directory.

What is still used from here — imported, not copied:

| Module | Why it is trusted |
|---|---|
| `src/label_mapping.py` | total and deterministic over every test row, 0 errors |
| `src/report_parser.py::extract_stress_label` | verified on all four cases; no fallback |
| `src/emotion_payload.py` | empty-vs-failure separation verified over 7,500 records |
| `tests_preflight/` | the 35-test audit suite |

Retired for publication use: `scripts/run_experiments.py`, `src/result_store.py`,
`src/model_client.py` (dead), `src/response_parser.py` (dead), and the
`merge_rerun*` / `plan_targeted_rerun` / `audit_pilot` scripts.

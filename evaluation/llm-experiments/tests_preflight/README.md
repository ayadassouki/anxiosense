# Pre-flight test suite (added 2026-09-01)

Gate tests that must all pass **before** launching a full-dataset RQ1–RQ3 run.
Additive: this directory adds files only. No existing code, data or output was
modified. Offline — no API keys, no network, no sklearn, no pytest.

```bash
python3 evaluation/llm-experiments/tests_preflight/test_preflight.py
```

Tests are split into two classes:

* **CONTRACT tests** — properties the pipeline must satisfy. A failure here is a
  bug that must be fixed before collecting new data.
* **EVIDENCE tests** — run over the existing `stage_c_recovered` tree and prove
  whether a past defect is present in data already collected.

`referral_risk_parser_port.py` is a line-for-line Python port of
`src/mastra/utils/referral-risk-parser.ts` so the extraction ladder can be tested
and the historical recovery re-derived without running TypeScript.

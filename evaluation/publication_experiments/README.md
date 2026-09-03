# AnxioSense publication experiment runner

Clean harness for the RQ1–RQ3 publication runs. It wraps the existing AnxioSense
system; it does not change it.

**Status: infrastructure only. No publication run has been started. The dataset
scope and several methodology questions are still with the supervisors.**

## The one rule everything else follows

The raw model output is the source of truth. Every attempt is written to
`raw/attempts.jsonl` **before** anything is parsed, and nothing derived is ever
written back into it. `parsed/` and `summaries/` are disposable: delete them and
run `rescore.py` to rebuild every number from the stored raw responses, with no
model call.

Three consequences worth stating plainly:

* An unreadable response never becomes a class label. It is recorded as invalid,
  with the complete raw response kept, and it is counted and reported.
* A completed model response is never retried — not when it is wrong, malformed,
  out-of-vocabulary or unusable. That is the model's behaviour and it is data.
  Only transport failures (429, 5xx, connection, timeout) are retried.
* Ground truth is computed from the dataset row before dispatch, stored in the
  frozen manifest, and never reaches a parser, a retry decision or an exclusion.

## Layout

```
configs/     experiment configuration (models, strategies, runs, retry, server)
manifests/   frozen dataset manifests: membership, ground truth, hashes, baseline
runner/      the harness
fixtures/    canned responses for mock mode
tests/       51 offline gate tests
runs/<id>/   output root, one directory per experiment
   experiment.json          frozen provenance: config hash, prompt hashes, git commit
   raw/attempts.jsonl       APPEND-ONLY. one line per attempt. source of truth
   raw/index.jsonl          one line per assessment, with its full retry history
   parsed/records.jsonl     DERIVED. regenerable from raw
   summaries/               metrics and dispatch statistics
   logs/, checkpoints/
```

## Commands

```bash
# verify everything that can be verified without spending money
python3 -m runner.run --config configs/experiment.example.yaml --preflight-only

# full mock run: no network, no provider, no cost
python3 evaluation/publication_experiments/run_mock_demo.py

# gate tests (offline, stdlib only)
python3 evaluation/publication_experiments/tests/test_runner.py

# re-derive every prediction from stored raw output, no model call
python3 -c "from runner.rescore import rescore; print(rescore('runs/<id>'))"
```

## Preflight aborts before any dispatch when

a manifest hash does not match the dataset on disk · a text has changed since the
manifest was frozen · any ground-truth label fails to map · any prompt file is
missing or has no ```text block · no model is enabled · the client timeout is
below the server's poll budget · the run directory already exists without
`--resume`. During a run, a model/provider mismatch aborts the whole experiment.

## Reused unchanged

`label_mapping.py`, `report_parser.extract_stress_label`, `emotion_payload.py`
(all from `evaluation/llm-experiments/src/`), the referral extraction ladder, the
AnxioSense agents, RAG, safety override and recommendation policy, and the
provider pinning in `model-provider.ts`. Importing rather than copying is
deliberate — duplicated parsers are how the old pipeline ended up with three
implementations of one ladder.

## Historical data

`evaluation/llm-experiments/outputs/` is read-only history. Nothing here reads,
writes, moves or migrates it; a test enforces that the runner never references it.

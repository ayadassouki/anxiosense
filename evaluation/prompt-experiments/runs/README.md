# Evaluation Run Snapshots

This directory preserves the 66 workflow-run snapshots used by the AnxioSense prompt evaluation and its published analysis. Each snapshot records agent outputs, retrieval evidence, validation decisions, and the generated report for a specific run.

Snapshot filenames follow `<timestamp>-<prompt-version>-<run-label>.md`. Existing snapshots retain the historical `cot-oneshot-v1` experiment identifier so citations, comparisons, and stored results remain reproducible. New One-shot + CoT runs use the normalized `one-shot-cot-v1` identifier.

The historical snapshots are research records: do not rename or rewrite them when prompt naming conventions change.

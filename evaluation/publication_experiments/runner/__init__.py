"""Clean publication experiment runner for AnxioSense RQ1-RQ3.

Design contract (see claude/publication-runner-stage1-design-2026-09-03.md):
  * raw model output is the source of truth and is never overwritten
  * an unreadable response is never converted into a class label
  * only infrastructure failures are retried; model behaviour is preserved as-is
  * dataset membership and ground truth are frozen before any dispatch
"""
RUNNER_VERSION = "1.0.0"
RECORD_SCHEMA_VERSION = "1.0.0"

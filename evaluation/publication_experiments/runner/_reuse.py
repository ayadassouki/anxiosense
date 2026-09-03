"""Re-export the components validated by the 2026-09-01/02/03 audits.

These modules live in evaluation/llm-experiments/src/. That tree is RETIRED for
running experiments but its parsing and label-mapping logic was verified:
  * label_mapping   - total and deterministic over every test row, 0 errors
  * report_parser   - extract_stress_label verified on all four cases, no fallback
  * emotion_payload - empty-vs-failure separation verified over 7,500 records

Importing rather than copying is deliberate: a second implementation of a parser
is how the historical pipeline ended up with three copies of one ladder.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_LEGACY_SRC = REPO_ROOT / "evaluation" / "llm-experiments"
if str(_LEGACY_SRC) not in sys.path:
    sys.path.insert(0, str(_LEGACY_SRC))

from src.label_mapping import (            # noqa: E402
    map_dreaddit_label, map_goemotions_label,
    ANXIOSENSE_TO_EVAL_CLASS, EVAL_CLASSES, LabelMappingError,
)
from src.report_parser import extract_stress_label            # noqa: E402
from src.emotion_payload import (                             # noqa: E402
    extract_emotion_payload, primary_emotion, OK_STATUSES,
)

GROUND_TRUTH_MAPPERS = {
    "dreaddit":   ("label",         map_dreaddit_label),
    "goemotions": ("emotion_names", map_goemotions_label),
}

__all__ = [
    "REPO_ROOT", "map_dreaddit_label", "map_goemotions_label",
    "ANXIOSENSE_TO_EVAL_CLASS", "EVAL_CLASSES", "LabelMappingError",
    "extract_stress_label", "extract_emotion_payload", "primary_emotion",
    "OK_STATUSES", "GROUND_TRUTH_MAPPERS",
]

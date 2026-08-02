"""
src/result_store.py

Crash-safe, append-only JSONL store for experiment results.

Design principles:
    - Append one result record per line immediately after each example completes.
    - On resume, load completed (sample_id, model, strategy, run) tuples from the
      existing JSONL file and skip those in the experiment loop.
    - Write a CSV copy at the end of each full run.
    - Never delete or truncate existing result files.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key type for deduplication
# ---------------------------------------------------------------------------

ResultKey = Tuple[str, str, str, int]  # (sample_id, model_id, strategy, run_number)


# ---------------------------------------------------------------------------
# ResultStore
# ---------------------------------------------------------------------------

class ResultStore:
    """
    Append-only JSONL store for per-example experiment results.

    Parameters
    ----------
    output_path:
        Path to the .jsonl file. Created if not present.
        If present, existing records are loaded on init for resume support.
    """

    def __init__(self, output_path: str | Path) -> None:
        self.path = Path(output_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._completed: Set[ResultKey] = set()
        self._fh = None  # lazy open

        if self.path.exists():
            self._load_completed()

    def _load_completed(self) -> None:
        """Read existing records to populate the completed-keys set."""
        count = 0
        errors = 0
        with self.path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    key = self._record_to_key(record)
                    if key is not None:
                        self._completed.add(key)
                        count += 1
                except json.JSONDecodeError:
                    errors += 1
                    logger.warning("Corrupt JSONL line %d in %s — skipped.", lineno, self.path)
        logger.info(
            "Loaded %d completed results from %s (%d corrupt lines skipped).",
            count, self.path, errors,
        )

    @staticmethod
    def _record_to_key(record: dict) -> Optional[ResultKey]:
        try:
            return (
                str(record["sample_id"]),
                str(record["model_id"]),
                str(record["strategy"]),
                int(record["run"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def is_completed(
        self,
        sample_id: str,
        model_id: str,
        strategy: str,
        run: int,
    ) -> bool:
        """Return True if this (sample_id, model_id, strategy, run) was already stored."""
        return (sample_id, model_id, strategy, run) in self._completed

    def append(self, record: Dict[str, Any]) -> None:
        """
        Append a single result record to the JSONL file.

        The record must contain at least:
            sample_id, model_id, strategy, run
        plus whatever fields the experiment runner adds.

        Writes atomically (flush + fsync after each record).
        """
        if self._fh is None:
            self._fh = self.path.open("a", encoding="utf-8")

        key = self._record_to_key(record)
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

        if key is not None:
            self._completed.add(key)

    def close(self) -> None:
        """Close the file handle if open."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "ResultStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def export_csv(self, csv_path: str | Path) -> None:
        """
        Export all JSONL records as CSV.

        Reads the JSONL file fresh (includes all records, not just what was
        appended in this session).
        """
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        records = self.load_all()
        if not records:
            logger.warning("No records to export to CSV.")
            return

        fieldnames = list(records[0].keys())
        # Ensure key columns come first
        priority = ["sample_id", "model_id", "strategy", "run", "dataset"]
        ordered = [f for f in priority if f in fieldnames] + \
                  [f for f in fieldnames if f not in priority]

        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=ordered, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)

        logger.info("Exported %d records to %s", len(records), csv_path)

    def load_all(self) -> list[dict]:
        """Load and return all records from the JSONL file."""
        if not self.path.exists():
            return []
        records = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records


# ---------------------------------------------------------------------------
# Convenience: load raw results from outputs/raw/ directory
# ---------------------------------------------------------------------------

def load_raw_results(raw_dir: str | Path) -> list[dict]:
    """
    Load all JSONL records from every .jsonl file under raw_dir.

    Returns a flat list of all records, sorted by (dataset, model_id, strategy, run, sample_id).
    """
    raw_dir = Path(raw_dir)
    records = []
    for jsonl_file in sorted(raw_dir.glob("**/*.jsonl")):
        with jsonl_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Corrupt line in %s", jsonl_file)

    records.sort(
        key=lambda r: (
            r.get("dataset", ""),
            r.get("model_id", ""),
            r.get("strategy", ""),
            r.get("run", 0),
            str(r.get("sample_id", "")),
        )
    )
    return records

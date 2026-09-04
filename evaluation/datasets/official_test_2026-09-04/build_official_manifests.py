#!/usr/bin/env python3
"""Build the OFFICIAL frozen manifests from the official test scope.

Dreaddit only, for now. GoEmotions is deliberately NOT built: decisions 1 and 2
in METHODOLOGY_DECISIONS_REQUIRED.md are unresolved, and runner/manifest.py has
no `unmapped` ground-truth status, so a 5,427-row GoEmotions manifest cannot be
built without silently fabricating labels.

Uses runner/manifest.py::build_manifest unchanged. Nothing about scope lives
here that is not passed in explicitly.

Writes:  evaluation/publication_experiments/manifests/official_dreaddit_test.json

The 324-row candidate_dreaddit_test.json is NOT touched, moved, or superseded on
disk. It stays as the record of what the previous scope was.

Usage:  python3 evaluation/datasets/official_test_2026-09-04/build_official_manifests.py
        python3 ... --check     # rebuild in memory and compare, write nothing
"""
from __future__ import annotations

import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "publication_experiments"))

from runner.manifest import build_manifest, verify_manifest   # noqa: E402
from runner.identity import sha256_file                        # noqa: E402

DERIVED = "evaluation/datasets/official_test_2026-09-04/dreaddit_test_official.csv"
SOURCE = "evaluation/datasets/dreaddit_official/dreaddit_test.csv"
OUT = REPO_ROOT / "evaluation/publication_experiments/manifests/official_dreaddit_test.json"

GE_DERIVED = "evaluation/datasets/official_test_2026-09-04/goemotions_test_official.csv"
GE_SOURCE = "evaluation/datasets/goemotions/test.csv"
GE_OUT = REPO_ROOT / "evaluation/publication_experiments/manifests/official_goemotions_test.json"
GE_NOTES = (
    "OFFICIAL SCOPE. Full GoEmotions official test split, 5,427 rows, all retained. "
    "Ground truth uses the FROZEN mapping runner/goemotions_mapping.py v1.0.0 "
    "(adopted 2026-09-04). Labels in the official Ekman sadness group map to sadness; "
    "the official Ekman anger group maps to the class AnxioSense reports as frustration; "
    "the official positive sentiment group plus neutral map to non_distress - an "
    "AnxioSense OPERATIONAL mapping derived from GoEmotions' grouping, not a GoEmotions "
    "mapping. The official ambiguous sentiment group (realization, surprise, curiosity, "
    "confusion) and disgust (its own Ekman category) are OUT_OF_TAXONOMY. nervousness "
    "maps to anxiety, departing from the Ekman grouping that places it with fear; see "
    "the evidence audit. Multi-label rows follow R1-R4: agreeing mapped classes score; "
    "conflicting classes are unscorable(conflicting_classes); out-of-taxonomy labels are "
    "discarded before resolving; rows with only out-of-taxonomy labels are "
    "unscorable(out_of_taxonomy). No row is deleted. GoEmotions publishes no single-label "
    "reduction rule; R1-R4 are AnxioSense decisions."
)
GE_EXPECTED = {
    "n_rows_in_scope": 5427,
    "n_dispatchable": 5383,
    "n_scorable": 4652,
    "n_unscorable": 731,
    "n_excluded": 44,
    "class_distribution": {"non_distress": 3648, "frustration": 618,
                           "sadness": 305, "fear": 67, "anxiety": 14},
    "majority_class": "non_distress",
    "majority_baseline": 0.784179,
}

NOTES = (
    "OFFICIAL SCOPE. Full Dreaddit official test split, 715 rows. "
    "The anxiety keyword / LIWC filter that produced the superseded 324-row "
    "candidate scope is NOT applied, and no content-based exclusion of any kind "
    "is applied. Preprocessing is deterministic and label-blind only: CRLF/CR to "
    "LF, strip leading and trailing whitespace, PII redaction. text_processed is "
    "the dispatched field; text_original is preserved in the derived CSV. "
    "sample_id is dread_<official id>, derived from the dataset's own identifier "
    "rather than row position. Supersedes candidate_dreaddit_test.json, which is "
    "retained unchanged on disk."
)
EXPECTED = {
    "rows_in_split": 715,
    "n_dispatchable": 715,
    "n_excluded": 0,
    "class_distribution": {"0": 346, "1": 369},
    "majority_class": "1",
    "majority_baseline": 0.516084,
}


def build_goemotions() -> dict:
    return build_manifest(
        dataset="goemotions",
        processed_csv=GE_DERIVED,
        split="test",
        text_column="text_processed",
        min_chars=10,
        source_file=GE_SOURCE,
        source_revision="google-research-datasets/go_emotions simplified, official test split",
        notes=GE_NOTES,
    )


def assert_ge(m: dict) -> list[str]:
    bad = []
    for k, want in GE_EXPECTED.items():
        got = m.get(k)
        if k == "class_distribution":
            got = {str(a): b for a, b in (got or {}).items()}
        if got != want:
            bad.append(f"{k}: expected {want!r}, got {got!r}")
    from collections import Counter
    reasons = Counter(u["reason"] for u in m["unscorable_samples"])
    if reasons.get("out_of_taxonomy") != 568:
        bad.append(f"out_of_taxonomy: expected 568, got {reasons.get('out_of_taxonomy')}")
    if reasons.get("conflicting_classes") != 163:
        bad.append(f"conflicting_classes: expected 163, got {reasons.get('conflicting_classes')}")
    if (m["n_scorable"] + m["n_unscorable"] + m["n_excluded"]) != 5427:
        bad.append("scorable + unscorable + excluded != 5427")
    if set(m["ground_truth"].values()) - set(GE_EXPECTED["class_distribution"]):
        bad.append("ground truth outside the five classes")
    if m["ground_truth_mapping"]["mapping_version"] != "1.0.0":
        bad.append("mapping_version is not 1.0.0")
    return bad


def build() -> dict:
    return build_manifest(
        dataset="dreaddit",
        processed_csv=DERIVED,
        split="test",
        text_column="text_processed",
        min_chars=10,          # label-blind technical floor; 0 rows hit it here
        source_file=SOURCE,
        source_revision="andreagasparini/dreaddit (HuggingFace), official test split",
        notes=NOTES,
    )


def assert_expectations(m: dict) -> list[str]:
    bad = []
    for k, want in EXPECTED.items():
        got = m.get(k)
        if k == "class_distribution":
            got = {str(a): b for a, b in (got or {}).items()}
        if got != want:
            bad.append(f"{k}: expected {want!r}, got {got!r}")
    ids = m["included_sample_ids"]
    if len(ids) != 715:
        bad.append(f"included_sample_ids: expected 715, got {len(ids)}")
    if len(set(ids)) != len(ids):
        bad.append("included_sample_ids contains duplicates")
    bad_ids = [s for s in ids if not s.startswith("dread_")]
    if bad_ids:
        bad.append(f"{len(bad_ids)} sample_id(s) not in dread_<id> form, e.g. {bad_ids[:3]}")
    padded = [s for s in ids if s[6:].isdigit() and s[6:].startswith("0") and len(s[6:]) > 1]
    if padded:
        bad.append(f"{len(padded)} sample_id(s) look positionally zero-padded: {padded[:3]}")
    if set(m["ground_truth"].values()) - {0, 1}:
        bad.append(f"ground truth outside {{0,1}}: {set(m['ground_truth'].values())}")
    if m["exclusion_rules"] and m["exclusion_rules"][0]["label_blind"] is not True:
        bad.append("exclusion rule is not label-blind")
    return bad


def main() -> int:
    check_only = "--check" in sys.argv
    m = build()

    problems = assert_expectations(m)
    if problems:
        print("EXPECTATION FAILURES:")
        for p in problems:
            print("  -", p)
        return 1

    g = build_goemotions()
    gp = assert_ge(g)
    if gp:
        print("GOEMOTIONS EXPECTATION FAILURES:")
        for x in gp:
            print("  -", x)
        return 1

    if check_only:
        if GE_OUT.exists():
            od = json.loads(GE_OUT.read_text())
            print(f"goemotions on-disk {od['manifest_sha256']}")
            print(f"goemotions rebuilt {g['manifest_sha256']}")
            print("DETERMINISTIC" if od['manifest_sha256'] == g['manifest_sha256'] else "MISMATCH")
        if not OUT.exists():
            print("--check: manifest not on disk yet"); return 1
        on_disk = json.loads(OUT.read_text())
        same = on_disk["manifest_sha256"] == m["manifest_sha256"]
        print(f"on-disk  {on_disk['manifest_sha256']}")
        print(f"rebuilt  {m['manifest_sha256']}")
        print("DETERMINISTIC" if same else "MISMATCH")
        return 0 if same else 1

    if not check_only:
        GE_OUT.write_text(json.dumps(g, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {GE_OUT.relative_to(REPO_ROOT)}")
        for k in ("n_rows_in_scope", "n_dispatchable", "n_scorable", "n_unscorable",
                  "n_excluded", "class_distribution", "majority_baseline"):
            print(f"  {k:20} {g[k]}")
        print(f"  {'manifest_sha256':20} {g['manifest_sha256']}")
        print(f"  {'source_sha256':20} {g['source']['sha256']}")
        print(f"  {'processed_sha256':20} {g['processed']['sha256']}")
        print()

    OUT.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    for p in verify_manifest(json.loads(OUT.read_text())):
        print("VERIFY PROBLEM:", p)
        return 1

    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    print(f"  rows_in_split      {m['rows_in_split']}")
    print(f"  n_dispatchable     {m['n_dispatchable']}")
    print(f"  n_excluded         {m['n_excluded']}")
    print(f"  class_distribution {m['class_distribution']}")
    print(f"  majority_baseline  {m['majority_baseline']}")
    print(f"  source_sha256      {m['source']['sha256']}")
    print(f"  processed_sha256   {m['processed']['sha256']}")
    print(f"  manifest_sha256    {m['manifest_sha256']}")
    print(f"  file sha256        {sha256_file(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

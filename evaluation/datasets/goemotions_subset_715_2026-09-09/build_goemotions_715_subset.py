#!/usr/bin/env python3
"""Build the frozen 715-row GoEmotions evaluation subset.

Supervisor decision 2026-09-09: evaluate ~715 GoEmotions examples (matching the
715-row Dreaddit scope) rather than all 5,427, and force-include the 25 examples
Abel selected for RQ4/RQ5.

COMPOSITION
    25   forced   - Abel's RQ4/RQ5 ids. Used as an ID LIST ONLY: text, labels,
                    mapping and ground truth are re-derived here from the
                    official source CSVs by joining on id. His spreadsheet's
                    label_ids column is Excel-corrupted (one cell reads
                    "2026-06-19 00:00:00" where the truth is "6 19"), so nothing
                    from it is trusted.
    690  random   - drawn label-blind from the eligible official TEST pool.
    ---
    715  total

WHY split IS NOT "test"
    runner/manifest.py:57 selects rows with an exact match on the `split`
    column. This subset is mixed-split (test + train + validation), so calling
    build_manifest(split="test") would SILENTLY DROP Abel's 23 out-of-split
    rows. Every row therefore carries the constant tag SUBSET_TAG in `split`,
    and its true origin in `original_split`. No runner change is needed and
    nothing is filtered away.

SELECTION
    Deterministic and reproducible across Python versions and languages:
        POOL     = eligible ids, sorted lexicographically
        KEY(id)  = sha256(f"{SEED}:{id}")
        SELECTED = the 690 smallest KEYs, ties broken by id
    random.Random(seed).sample() is deliberately NOT used - CPython's
    implementation has changed across versions, so the same seed can yield a
    different draw on a different interpreter.

AUTHORITATIVE LOGIC IS IMPORTED, NEVER REIMPLEMENTED
    clean_text / redact_text        <- evaluation/datasets/scripts/preprocess_datasets.py
    parse_label_ids / technical_status <- build_official_test_scope.py
    map_goemotions_labels           <- runner/goemotions_mapping.py (frozen v1.0.0)
    build_manifest / verify_manifest <- runner/manifest.py (UNCHANGED)

Usage:  python3 <this file>            build and write
        python3 <this file> --check    rebuild in memory, compare, write nothing
"""
from __future__ import annotations

import csv, hashlib, json, sys
import datetime as _dt
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCOPE_DIR = REPO_ROOT / "evaluation/datasets/official_test_2026-09-04"

sys.path.insert(0, str(SCOPE_DIR))
sys.path.insert(0, str(REPO_ROOT / "evaluation/datasets/scripts"))
sys.path.insert(0, str(REPO_ROOT / "evaluation/publication_experiments"))

from preprocess_datasets import clean_text, redact_text                    # noqa: E402
from build_official_test_scope import parse_label_ids, technical_status    # noqa: E402
from runner.goemotions_mapping import (                                    # noqa: E402
    GOEMOTIONS_LABELS as GE_LABELS, OUT_OF_TAXONOMY,
    MAPPING_VERSION as GE_MAPPING_VERSION,
    map_goemotions_labels, anxiosense_class, UnscorableRow)
from runner.manifest import build_manifest, verify_manifest                # noqa: E402
from runner.identity import sha256_file                                    # noqa: E402

BUILDER_VERSION = "1.0.0"
SUBSET_TAG = "goemotions_715_v1"
SEED = "anxiosense-goemotions-715-v1"
MIN_CHARS = 10                 # identical label-blind floor to the official scope
N_RANDOM = 690
N_FORCED = 25
N_TOTAL = 715
RANDOM_POOL_SPLIT = "test"     # the random 690 come from the official test split only

SOURCES = {
    "train":      ("evaluation/datasets/goemotions/train.csv",
                   "66684cb3834d92086e8f240abd9dffddf3d5d3d617f2cd72060b8b8de2337084"),
    "validation": ("evaluation/datasets/goemotions/validation.csv",
                   "dcb425fd4349320e9991b92df4390c51faa529112db3f194a88a71571829f62c"),
    "test":       ("evaluation/datasets/goemotions/test.csv",
                   "56b5c407adaac0664af58e1a6d067bc726a4bf036e77b7679fca41750bc02ca4"),
}
ABEL_IDS_CSV = "evaluation/datasets/goemotions_subset_715_2026-09-09/abel_rq4_rq5_ids.csv"
DERIVED = "evaluation/datasets/goemotions_subset_715_2026-09-09/goemotions_715_subset.csv"
SOURCES_JSON = HERE / "SOURCES.json"
MANIFEST_OUT = REPO_ROOT / "evaluation/publication_experiments/manifests/goemotions_715_subset_2026-09-09.json"

COLUMNS = [
    "sample_id", "id", "split", "original_split",
    "text_original", "text_processed", "text_was_modified",
    "label_ids_raw", "label_ids", "label_names", "n_labels",
    "mapped_classes", "n_mapped_classes", "n_out_of_taxonomy_labels",
    "multi_label_rule", "gt_status", "ground_truth",
    "dispatchable", "exclusion_reason",
    "selection_source", "selection_rank",
]

NOTES = (
    f"715-ROW GOEMOTIONS EVALUATION SUBSET (builder {BUILDER_VERSION}, tag {SUBSET_TAG}). "
    "Supervisor decision 2026-09-09: evaluate ~715 GoEmotions examples so the scope is "
    "size-comparable with the 715-row Dreaddit test scope, instead of all 5,427. "
    f"Composition: {N_FORCED} examples pre-specified by the RQ4/RQ5 study (forced include, "
    "selection_source=abel_rq4_rq5) plus "
    f"{N_RANDOM} drawn label-blind from the eligible official TEST pool "
    "(selection_source=random_seeded). "
    f"Selection is deterministic: ids sorted lexicographically, ordered by "
    f"sha256('{SEED}:'+id), smallest {N_RANDOM} taken. No PRNG is used, so the draw "
    "reproduces across Python versions and languages. "
    "Eligibility for the random pool is label-blind and predefined: len(text_processed) "
    f">= {MIN_CHARS} (the server's HTTP 400 floor) and not already forced in. No "
    "content-based, keyword-based, label-based or model-output-based filtering of any kind. "
    "MIXED SPLIT: the subset spans test, train and validation because 23 of the 25 "
    "RQ4/RQ5 examples lie outside the official test split. Every row therefore carries "
    f"split='{SUBSET_TAG}' and its true origin in original_split, because "
    "runner/manifest.py selects rows by exact match on `split` and split='test' would "
    "silently discard those 23 rows. official_split in this manifest is the subset tag, "
    "not a GoEmotions split. "
    "SOURCE: google-research-datasets/go_emotions simplified; train, validation and test "
    "were all read, and all three SHA-256 hashes are pinned in the builder, asserted "
    "before the build, and recorded in SOURCES.json and below. "
    f"train={SOURCES['train'][1]} validation={SOURCES['validation'][1]} test={SOURCES['test'][1]}. "
    "Ground truth uses the FROZEN mapping runner/goemotions_mapping.py "
    f"v{GE_MAPPING_VERSION}, recomputed by runner/manifest.py from label_names; the "
    "ground_truth column in the derived CSV is informational only. Rows whose labels do "
    "not resolve to one class are retained and reported as unscorable - never deleted, "
    "never given an invented label. "
    "The official 5,427-row scope manifest official_goemotions_test.json is NOT superseded "
    "or modified; it remains on disk unchanged and is still the manifest bench_006 used."
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_corpus() -> tuple[dict[str, dict], dict[str, str]]:
    """Every row of all three official splits, keyed by GoEmotions comment id."""
    corpus: dict[str, dict] = {}
    seen = Counter()
    actual: dict[str, str] = {}
    for split, (rel, _pinned) in SOURCES.items():
        p = REPO_ROOT / rel
        if not p.exists():
            raise SystemExit(f"FATAL: source missing: {p}")
        actual[split] = sha256_of(p)
        with p.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                seen[r["id"]] += 1
                corpus[r["id"]] = {"id": r["id"], "split": split,
                                   "text": r["text"], "labels": r["labels"]}
    dupes = [i for i, n in seen.items() if n > 1]
    if dupes:
        raise SystemExit(f"FATAL: {len(dupes)} id(s) appear in more than one split, e.g. {dupes[:5]}")
    return corpus, actual


def derive(row: dict) -> dict:
    """Identical derivation to build_official_test_scope.build_goemotions()."""
    raw = row["text"]
    processed = redact_text(clean_text(raw))
    ids = parse_label_ids(row["labels"])
    names = [GE_LABELS[i] for i in ids]
    classes = [anxiosense_class(n) for n in names]
    in_tax = sorted({c for c in classes if c != OUT_OF_TAXONOMY})
    try:
        gt_class = map_goemotions_labels(names)
        gt_status = "mapped"
    except UnscorableRow as exc:
        gt_class, gt_status = "", exc.reason
    dispatchable, reason = technical_status(raw, processed)
    return {
        "sample_id": f"ge_{row['id']}",
        "id": row["id"],
        "split": SUBSET_TAG,
        "original_split": row["split"],
        "text_original": raw,
        "text_processed": processed,
        "text_was_modified": str(raw != processed),
        "label_ids_raw": row["labels"],
        "label_ids": " ".join(str(i) for i in ids),
        "label_names": "|".join(names),
        "n_labels": len(ids),
        "mapped_classes": "|".join(in_tax),
        "n_mapped_classes": len(in_tax),
        "n_out_of_taxonomy_labels": sum(1 for c in classes if c == OUT_OF_TAXONOMY),
        "multi_label_rule": (
            "R1" if gt_status == "mapped" and not any(c == OUT_OF_TAXONOMY for c in classes)
            else "R3" if gt_status == "mapped"
            else "R2" if gt_status == "conflicting_classes" else "R4"),
        "gt_status": gt_status,
        "ground_truth": gt_class,
        "dispatchable": str(dispatchable),
        "exclusion_reason": reason,
        "selection_source": "",
        "selection_rank": "",
    }


def select() -> tuple[list[dict], dict]:
    corpus, actual_hashes = load_corpus()

    # 7. Pin and verify all three source hashes BEFORE building.
    drift = [f"{s}: pinned {p[1][:16]}… actual {actual_hashes[s][:16]}…"
             for s, p in SOURCES.items() if p[1] != actual_hashes[s]]
    if drift:
        raise SystemExit("FATAL: source hash drift:\n  " + "\n  ".join(drift))

    # 2. Abel's ids: ID LIST ONLY. Assert 25 unique, each present exactly once.
    with (REPO_ROOT / ABEL_IDS_CSV).open(newline="", encoding="utf-8") as fh:
        abel = [r["id"].strip() for r in csv.DictReader(fh) if r["id"].strip()]
    if len(abel) != N_FORCED:
        raise SystemExit(f"FATAL: expected {N_FORCED} RQ4/RQ5 ids, found {len(abel)}")
    if len(set(abel)) != N_FORCED:
        raise SystemExit("FATAL: duplicate id in the RQ4/RQ5 list")
    missing = [i for i in abel if i not in corpus]
    if missing:
        raise SystemExit(f"FATAL: RQ4/RQ5 id(s) absent from the official corpus: {missing}")
    abel_set = set(abel)

    # 4. Eligible pool: official test split, label-blind length floor, minus forced ids.
    pool = []
    for gid, row in corpus.items():
        if row["split"] != RANDOM_POOL_SPLIT or gid in abel_set:
            continue
        if len(redact_text(clean_text(row["text"]))) < MIN_CHARS:
            continue
        pool.append(gid)
    pool.sort()
    if len(pool) < N_RANDOM:
        raise SystemExit(f"FATAL: pool of {len(pool)} is smaller than N_RANDOM={N_RANDOM}")
    pool_sha256 = hashlib.sha256("\n".join(pool).encode("utf-8")).hexdigest()

    # 6. Deterministic hash-ordered draw.
    ordered = sorted(pool, key=lambda i: (hashlib.sha256(f"{SEED}:{i}".encode()).hexdigest(), i))
    chosen = ordered[:N_RANDOM]

    rows = []
    for gid in abel:
        r = derive(corpus[gid]); r["selection_source"] = "abel_rq4_rq5"; rows.append(r)
    for rank, gid in enumerate(chosen, 1):
        r = derive(corpus[gid]); r["selection_source"] = "random_seeded"
        r["selection_rank"] = rank; rows.append(r)

    if len(rows) != N_TOTAL:
        raise SystemExit(f"FATAL: built {len(rows)} rows, expected {N_TOTAL}")
    sids = [r["sample_id"] for r in rows]
    if len(set(sids)) != N_TOTAL:
        raise SystemExit("FATAL: duplicate sample_id in the subset")
    rows.sort(key=lambda r: r["sample_id"])

    prov = {
        "builder_version": BUILDER_VERSION,
        "built_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "subset_tag": SUBSET_TAG,
        "selection_protocol": "forced_include + hash_ordered_random",
        "seed": SEED,
        "key_function": "sha256(f'{seed}:{goemotions_id}')",
        "prng_used": False,
        "n_total": N_TOTAL, "n_forced": N_FORCED, "n_random": N_RANDOM,
        "random_pool": {
            "definition": (f"official {RANDOM_POOL_SPLIT} split, "
                           f"len(text_processed) >= {MIN_CHARS}, minus forced ids"),
            "size": len(pool),
            "sha256_of_sorted_ids": pool_sha256,
            "label_blind": True,
            "content_based_filtering": "NONE",
        },
        "sources": {s: {"file": p[0], "sha256": actual_hashes[s], "pinned_ok": True}
                    for s, p in SOURCES.items()},
        "forced_include": {
            "file": ABEL_IDS_CSV,
            "sha256": sha256_of(REPO_ROOT / ABEL_IDS_CSV),
            "usage": "ID LIST ONLY - text, labels, mapping and ground truth re-derived "
                     "from the official source CSVs by joining on id",
            "ids": abel,
        },
        "mapping_version": GE_MAPPING_VERSION,
        "preprocessing": "clean_text then redact_text, imported from "
                         "evaluation/datasets/scripts/preprocess_datasets.py",
        "row_removal": "none within the subset - unscorable rows are retained with gt_status",
        "not_modified": [
            "evaluation/publication_experiments/manifests/official_goemotions_test.json",
            "evaluation/publication_experiments/manifests/official_dreaddit_test.json",
            "evaluation/publication_experiments/manifests/candidate_goemotions_test.json",
            "evaluation/publication_experiments/manifests/candidate_dreaddit_test.json",
            "evaluation/datasets/goemotions/{train,validation,test}.csv",
            "evaluation/publication_experiments/runner/**",
            "prompts/**",
        ],
    }
    return rows, prov


def stats_of(rows: list[dict]) -> dict:
    disp = [r for r in rows if r["dispatchable"] == "True"]
    return {
        "rows": len(rows),
        "by_selection_source": dict(Counter(r["selection_source"] for r in rows)),
        "by_original_split": dict(Counter(r["original_split"] for r in rows)),
        "dispatchable": dict(Counter(r["dispatchable"] for r in rows)),
        "gt_status": dict(Counter(r["gt_status"] for r in rows)),
        "gt_status_dispatchable_only": dict(Counter(r["gt_status"] for r in disp)),
        "multi_label_rule_dispatchable": dict(Counter(r["multi_label_rule"] for r in disp)),
        "ground_truth_when_mapped": dict(Counter(
            r["ground_truth"] for r in rows if r["gt_status"] == "mapped")),
        "anxiety_by_selection_source": dict(Counter(
            r["selection_source"] for r in rows if r["ground_truth"] == "anxiety")),
        "text_modified_rows": sum(1 for r in rows if r["text_was_modified"] == "True"),
        "scorable_now": sum(1 for r in rows
                            if r["gt_status"] == "mapped" and r["dispatchable"] == "True"),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    check_only = "--check" in sys.argv
    rows, prov = select()
    st = stats_of(rows)
    prov["stats"] = st

    if check_only:
        existing = REPO_ROOT / DERIVED
        if not existing.exists():
            print("--check: derived CSV not on disk yet"); return 1
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as tf:
            tmp = Path(tf.name)
        write_csv(tmp, rows)
        same_csv = sha256_of(tmp) == sha256_of(existing)
        print(f"derived on-disk {sha256_of(existing)}")
        print(f"derived rebuilt {sha256_of(tmp)}")
        print("CSV DETERMINISTIC" if same_csv else "CSV MISMATCH")
        tmp.unlink()
        if MANIFEST_OUT.exists():
            od = json.loads(MANIFEST_OUT.read_text())
            m2 = build_manifest(
                dataset="goemotions", processed_csv=DERIVED, split=SUBSET_TAG,
                text_column="text_processed", min_chars=MIN_CHARS,
                source_file=None,
                source_revision="google-research-datasets/go_emotions simplified; "
                                "train+validation+test, per-file SHA-256 pinned in SOURCES.json",
                notes=NOTES)
            print(f"manifest on-disk {od['manifest_sha256']}")
            print(f"manifest rebuilt {m2['manifest_sha256']}")
            print("MANIFEST DETERMINISTIC" if od["manifest_sha256"] == m2["manifest_sha256"]
                  else "MANIFEST MISMATCH")
            return 0 if (same_csv and od["manifest_sha256"] == m2["manifest_sha256"]) else 1
        return 0 if same_csv else 1

    write_csv(REPO_ROOT / DERIVED, rows)
    prov["derived_csv"] = {"file": DERIVED, "sha256": sha256_of(REPO_ROOT / DERIVED)}
    print(f"wrote {DERIVED}  ({len(rows)} rows)")

    m = build_manifest(
        dataset="goemotions", processed_csv=DERIVED, split=SUBSET_TAG,
        text_column="text_processed", min_chars=MIN_CHARS,
        source_file=None,
        source_revision="google-research-datasets/go_emotions simplified; "
                        "train+validation+test, per-file SHA-256 pinned in SOURCES.json",
        notes=NOTES)

    problems = []
    if m["n_rows_in_scope"] != N_TOTAL: problems.append(f"n_rows_in_scope {m['n_rows_in_scope']} != {N_TOTAL}")
    if m["n_dispatchable"] != N_TOTAL: problems.append(f"n_dispatchable {m['n_dispatchable']} != {N_TOTAL}")
    if m["n_excluded"] != 0: problems.append(f"n_excluded {m['n_excluded']} != 0")
    if m["official_split"] != SUBSET_TAG: problems.append("official_split is not the subset tag")
    forced = {f"ge_{i}" for i in prov["forced_include"]["ids"]}
    present = set(m["included_sample_ids"]) | {u["sample_id"] for u in m["unscorable_samples"]}
    if not forced <= present: problems.append(f"{len(forced - present)} forced id(s) missing from the manifest")
    if problems:
        print("EXPECTATION FAILURES:"); [print("  -", p) for p in problems]; return 1

    MANIFEST_OUT.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    for p in verify_manifest(json.loads(MANIFEST_OUT.read_text())):
        print("VERIFY PROBLEM:", p); return 1

    prov["manifest"] = {"file": str(MANIFEST_OUT.relative_to(REPO_ROOT)),
                        "manifest_sha256": m["manifest_sha256"],
                        "file_sha256": sha256_file(MANIFEST_OUT)}
    SOURCES_JSON.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {MANIFEST_OUT.relative_to(REPO_ROOT)}")
    for k in ("n_rows_in_scope", "n_dispatchable", "n_scorable", "n_unscorable",
              "n_excluded", "official_split", "class_distribution", "majority_baseline"):
        print(f"  {k:22} {m[k]}")
    print(f"  {'manifest_sha256':22} {m['manifest_sha256']}")
    print(f"  {'processed_sha256':22} {m['processed']['sha256']}")
    print(f"wrote {SOURCES_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the frozen evaluation snapshot. Exit 0 = unchanged, 1 = drift detected.
Read-only. Run from the repository root:
    python3 evaluation/datasets/frozen_2026-09-01/verify_frozen.py
"""
import csv, json, hashlib, os, sys, collections
csv.field_size_limit(10**7)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "evaluation", "llm-experiments"))
from src.label_mapping import map_dreaddit_label, map_goemotions_label

MAP = {"dreaddit": ("label", map_dreaddit_label), "goemotions": ("emotion_names", map_goemotions_label)}

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def sha_text(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    man = json.load(open(os.path.join(HERE, "MANIFEST.json"), encoding="utf-8"))
    fail = []
    for name, d in man["datasets"].items():
        p = os.path.join(ROOT, d["processed_file"])
        if not os.path.exists(p):
            fail.append(f"{name}: processed file missing: {d['processed_file']}"); continue
        got = sha_file(p)
        if got != d["processed_sha256"]:
            fail.append(f"{name}: processed file CHANGED\n    expected {d['processed_sha256']}\n    got      {got}")
        src = os.path.join(ROOT, d["source_file"])
        if os.path.exists(src) and sha_file(src) != d["source_sha256"]:
            fail.append(f"{name}: SOURCE file changed: {d['source_file']}")
        with open(p, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["split"] == "test"]
        rows.sort(key=lambda r: r["sample_id"])
        ids = [r["sample_id"] for r in rows]
        if len(rows) != d["test_rows"]:
            fail.append(f"{name}: test row count {len(rows)} != frozen {d['test_rows']}")
        h = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        if h != d["test_ids_sha256"]:
            fail.append(f"{name}: test ID set changed (sha256 {h[:16]} != {d['test_ids_sha256'][:16]})")
        col, fn = MAP[name]
        idx = {r["sample_id"]: r for r in csv.DictReader(
            open(os.path.join(HERE, d["row_hash_index"]), newline="", encoding="utf-8"))}
        tdrift = ldrift = 0
        for r in rows:
            e = idx.get(r["sample_id"])
            if e is None: continue
            if sha_text(r["text_redacted"]) != e["sha256_text_redacted"]: tdrift += 1
            if str(fn(r[col])) != e["ground_truth"]: ldrift += 1
        if tdrift: fail.append(f"{name}: text changed in {tdrift} row(s)")
        if ldrift: fail.append(f"{name}: ground-truth label changed in {ldrift} row(s)")
        dist = dict(collections.Counter(str(fn(r[col])) for r in rows))
        frozen_dist = {str(k): v for k, v in d["ground_truth_distribution_test"].items()}
        if dist != frozen_dist:
            fail.append(f"{name}: label distribution changed\n    frozen {frozen_dist}\n    now    {dist}")
        if not fail:
            print(f"  OK  {name}: {len(rows)} test rows, IDs + text + labels unchanged")
    if fail:
        print("FROZEN SNAPSHOT DRIFT DETECTED:")
        for f in fail: print("  ! " + f)
        return 1
    print("All frozen datasets verified unchanged.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

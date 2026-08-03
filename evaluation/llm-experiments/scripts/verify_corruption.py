#!/usr/bin/env python3
"""
Independent audit of the character-drop corruption claim in stage_c_final.

Run:  python3 verify_corruption.py [path/to/outputs/stage_c_final/raw]

Prints raw evidence, not conclusions. Read the payloads yourself and decide.
Every number below is recomputed from the CSVs on disk; nothing is hardcoded.
"""
import csv, json, os, re, sys, glob, collections

csv.field_size_limit(10 ** 7)

DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "outputs", "stage_c_final", "raw")
RAWDIR = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)

# The three keys the emotion prompt contractually requires in every payload.
KEYS = ['"emotions"', '"emotional_intensity"', '"evidence_from_text"']


def flagged(row):
    """A payload is suspect if it is non-empty but missing a required key name."""
    raw = row.get("emotion_agent_raw") or ""
    if not raw.strip():
        return None
    missing = [k for k in KEYS if k not in raw]
    return missing or None


def recoverable_object(raw):
    """Can ANY well-formed JSON *object* be pulled out of this text?"""
    for cand in [raw.strip()] + re.findall(r"\{[\s\S]*\}", raw):
        try:
            o = json.loads(cand)
            if isinstance(o, dict):
                return o
        except Exception:
            pass
    return None


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def main():
    files = sorted(glob.glob(os.path.join(RAWDIR, "*.csv")))
    if not files:
        sys.exit(f"no CSVs found in {RAWDIR}")

    print(f"# reading {len(files)} files from {RAWDIR}\n")

    # ---------------------------------------------------------------- SECTION 1
    print("=" * 78)
    print("1. PER-CELL COUNTS  (n = records, susp = missing a required key)")
    print("   'silent' = flagged BUT prediction_valid=True, i.e. it entered the metrics")
    print("=" * 78)
    print(f"{'file':<58}{'n':>5}{'susp':>6}{'silent':>8}")
    total_n = total_s = total_silent = 0
    suspects = []
    for p in files:
        rows = list(csv.DictReader(open(p)))
        s = sil = 0
        for r in rows:
            if flagged(r):
                s += 1
                suspects.append((os.path.basename(p), r))
                if truthy(r.get("prediction_valid")):
                    sil += 1
        total_n += len(rows); total_s += s; total_silent += sil
        print(f"{os.path.basename(p):<58}{len(rows):>5}{s:>6}{sil:>8}")
    print("-" * 78)
    print(f"{'TOTAL':<58}{total_n:>5}{total_s:>6}{total_silent:>8}")
    print(f"\n=> {total_s}/{total_n} = {100*total_s/total_n:.1f}% suspect; "
          f"{total_silent} of them counted as valid predictions.\n")

    # ---------------------------------------------------------------- SECTION 2
    print("=" * 78)
    print("2. FALSE-POSITIVE CHECK")
    print("   A missing key could just be a model that omitted it, not corruption.")
    print("   So: how many suspects contain NO recoverable JSON object at all?")
    print("   The rest are printed in full below — eyeball them yourself.")
    print("=" * 78)
    eyeball = []
    hard = 0
    for fname, r in suspects:
        raw = r["emotion_agent_raw"]
        if recoverable_object(raw) is None:
            hard += 1
        else:
            eyeball.append((fname, r["sample_id"], raw))
    print(f"no recoverable JSON object (unambiguously mangled): {hard}")
    print(f"object recoverable, judge for yourself:             {len(eyeball)}")
    for fname, sid, raw in eyeball:
        print(f"\n  --- {fname} :: {sid}")
        print("  " + repr(raw[:800]))

    # ---------------------------------------------------------------- SECTION 3
    print("\n" + "=" * 78)
    print("3. RAW PAYLOADS — the actual evidence. Look for text cut mid-word.")
    print("   Sorted shortest first; the short ones are the clearest.")
    print("=" * 78)
    for fname, r in sorted(suspects, key=lambda x: len(x[1]["emotion_agent_raw"]))[:25]:
        raw = r["emotion_agent_raw"]
        print(f"\n{fname} :: {r['sample_id']}  gt={r['ground_truth']}  "
              f"scored={r['label']}  valid={r.get('prediction_valid')}  len={len(raw)}")
        print("   " + repr(raw[:400]))

    # ---------------------------------------------------------------- SECTION 4
    print("\n" + "=" * 78)
    print("4. IS IT THE CSV WRITER?  Compare each suspect against its .jsonl twin.")
    print("   Identical => the damage predates both writers.")
    print("=" * 78)
    same = diff = missing = 0
    examples = []
    for fname, r in suspects:
        jp = os.path.join(RAWDIR, fname[:-4] + ".jsonl")
        if not os.path.exists(jp):
            missing += 1
            continue
        hit = None
        for line in open(jp):
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("sample_id") == r["sample_id"]:
                hit = o
                break
        if hit is None:
            missing += 1
        elif (hit.get("emotion_agent_raw") or "") == r["emotion_agent_raw"]:
            same += 1
        else:
            diff += 1
            examples.append((fname, r["sample_id"]))
    print(f"csv == jsonl : {same}")
    print(f"csv != jsonl : {diff}   {examples[:5]}")
    print(f"not found    : {missing}")

    # ---------------------------------------------------------------- SECTION 5
    print("\n" + "=" * 78)
    print("5. SILENT LABEL FLIPS — suspects that were scored AND scored wrong.")
    print("   These are records where corruption may have changed the metric.")
    print("=" * 78)
    for fname, r in suspects:
        if not truthy(r.get("prediction_valid")):
            continue
        if r["label"] == r["ground_truth"]:
            continue
        raw = r["emotion_agent_raw"]
        print(f"\n{fname} :: {r['sample_id']}")
        print(f"   ground_truth={r['ground_truth']}  scored_as={r['label']}")
        print("   " + repr(raw[:300]))

    # ---------------------------------------------------------------- SECTION 6
    print("\n" + "=" * 78)
    print("6. FAILURE-REASON BREAKDOWN per cell (for cross-checking the runner's counts)")
    print("=" * 78)
    for p in files:
        rows = list(csv.DictReader(open(p)))
        c = collections.Counter(
            (r["failure_reason"] or "").split(":")[0].strip()
            for r in rows if (r.get("failure_reason") or "").strip())
        if c:
            print(f"{os.path.basename(p):<58} {dict(c)}")


if __name__ == "__main__":
    main()

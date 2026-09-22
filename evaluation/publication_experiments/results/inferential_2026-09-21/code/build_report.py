#!/usr/bin/env python3
"""Render REPORT.md from REPORT_template.md by inserting tables/<name>.md at {{TABLE:<name>}}, then check that every
decimal number quoted in the narrative appears in a table (.md/.csv), summary_counts.json or verification output.
Fails (does not write REPORT.md) if any quoted number is unmatched."""
import re, json, csv, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent
tpl = (OUT / "REPORT_template.md").read_text()
pool = set()
for p in (OUT / "tables").glob("*.md"): pool.update(re.findall(r"\d+\.\d+", p.read_text()))
def walk(o):
    if isinstance(o, dict): [walk(v) for v in o.values()]
    elif isinstance(o, list): [walk(v) for v in o]
    elif isinstance(o, float): pool.update({f"{o:.3f}", f"{o:.4f}", f"{abs(o):.3f}", f"{o:.2g}"})
    elif isinstance(o, str): pool.update(re.findall(r"\d+\.\d+", o))
walk(json.load(open(OUT / "summary_counts.json"))); walk(json.load(open(OUT / "verification" / "verification_result.json")))
walk(json.load(open(OUT / "analysis_manifest.json")))
for r in csv.DictReader(open(OUT / "tables" / "rq1_model_pairs_primary.csv")):
    for k in ("diff_A_minus_B", "ci_low", "ci_high"): v = float(r[k]); pool.update({f"{abs(v):.3f}", f"{v:.3f}"})
    pool.add(f'{float(r["ci_high"]) - float(r["ci_low"]):.3f}')
# derived reference values quoted in the text, recomputed here from exact fractions:
from fractions import Fraction as Fr
for maj, n, K in ((355, 699, 2), (487, 622, 5)):
    q = Fr(maj, n); pool.add(f"{float(2 * q / (1 + q) / K):.3f}")          # constant majority predictor macro-F1
for r in csv.DictReader(open(OUT / "tables" / "rq2_configuration_vs_baseline.csv")): pool.add(f'{float(r["sens_frozen_scalar"]):.3f}')
EXEMPT = {"0.05": "alpha", "2.2e-16": "", "0.06": "approx CI half-width, Dreaddit paired RQ2", "0.03": "approx CI half-width, sensitivity",
          "0.09": "rounded range end (0.094)", "0.24": "rounded range end (0.242)", "4.4e-16": "verification max float diff",
          "1.1e-16": "verification max CI diff", "0.02249999999999986": "stored value quoted verbatim", "0.022": "displayed value", "0.023": "alternative display"}
body = re.sub(r"\{\{TABLE:[a-z0-9_]+\}\}", "", tpl)
body = re.sub(r"`[^`]*`", "", body)
nums = re.findall(r"(?<![\w.])(\d+\.\d+(?:e-\d+)?)", body)
unmatched = sorted({n for n in nums if n not in pool and n not in EXEMPT})
json.dump({"numbers_checked": len(nums), "unmatched": unmatched, "exempt": EXEMPT}, open(OUT / "report_number_check.json", "w"), indent=1)
print("numbers checked:", len(nums), "unmatched:", unmatched)
if unmatched: sys.exit("UNMATCHED NUMBERS - REPORT.md not written")
out = re.sub(r"\{\{TABLE:([a-z0-9_]+)\}\}", lambda m: (OUT / "tables" / f"{m.group(1)}.md").read_text().rstrip(), tpl)
(OUT / "REPORT.md").write_text(out); print("REPORT.md written")

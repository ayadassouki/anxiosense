"""Faithful Python port of src/mastra/utils/referral-risk-parser.ts (extractRiskLevel).
Ladder: strict JSON -> fence-stripped -> first balanced {...} -> exact key 'risk_level'
-> lowercase/trim -> accept only low|moderate|urgent -> else None. No synonyms, no inference."""
import json, re
VALID = ("low", "moderate", "urgent")
_FENCE_OPEN = re.compile(r"^```[a-zA-Z]*\s*")
_FENCE_CLOSE = re.compile(r"\s*```$")

def strip_fences(text: str) -> str:
    return _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text.strip()))

def first_balanced_object(text: str):
    start = text.find("{")
    while start != -1:
        depth = 0; in_string = False; escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if escaped: escaped = False; continue
            if ch == "\\": escaped = True; continue
            if ch == '"': in_string = not in_string; continue
            if in_string: continue
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return text[start:i+1]
        start = text.find("{", start + 1)
    return None

def _try_parse_object(text):
    try:
        obj = json.loads(text)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None

def extract_risk_level(raw):
    if not isinstance(raw, str) or len(raw) == 0: return None
    obj = _try_parse_object(raw)
    if obj is None: obj = _try_parse_object(strip_fences(raw))
    if obj is None:
        cand = first_balanced_object(raw)
        if cand: obj = _try_parse_object(cand)
    if obj is None: return None
    value = obj.get("risk_level")
    if not isinstance(value, str): return None
    n = value.strip().lower()
    return n if n in VALID else None

def risk_to_dreaddit_label(level):
    if level is None: return None
    return 0 if level == "low" else 1

"""Stage 3 - evidence-driven classification of every model-invalid record.

READ-ONLY. Nothing here re-scores anything: `apparent_prediction` and
`structurally_recoverable` are DESCRIPTIVE fields recorded beside the frozen result,
never substituted for it. Records whose raw store is not mounted are emitted with
every evidence-dependent field set to RAW_UNAVAILABLE.
"""
import json, os, re, csv, hashlib, difflib, collections

REPO = os.environ["REPO"]; WORK = os.environ["WORK"]; OUT = os.environ["OUT"]
os.makedirs(OUT, exist_ok=True)
UNAVAIL = "RAW_UNAVAILABLE"

ALLOWED_RISK = ("low", "moderate", "urgent")
ANXIOSENSE_TO_EVAL_CLASS = {"anxiety": "anxiety", "fear": "fear", "frustration": "frustration",
                            "hopelessness": "sadness", "loneliness": "sadness",
                            "sadness": "sadness", "stress": "anxiety"}
MODEL_SHORT = {"google/gemma-4-31b-it": "Gemma 4 31B", "meta-llama/llama-4-scout": "Llama 4 Scout",
               "mistralai/mistral-small-2603": "Mistral Small 4", "microsoft/phi-4": "Phi-4",
               "qwen/qwen3.5-27b": "Qwen3.5 27B"}

RISK_LENIENT = re.compile(r'"?risk_level\\?"?\s*:\s*\\?"?([A-Za-z_][A-Za-z_ \-]{0,38})', re.I)
EMO_ARRAY    = re.compile(r'"?emotions\\?"?\s*:\s*\[([^\]]*)\]', re.DOTALL)
EMO_KEY      = re.compile(r'"?emotions\\?"?\s*:')
EVIDENCE_ARR = re.compile(r'"?evidence_from_text\\?"?\s*:\s*\[([^\]]*)\]', re.DOTALL)
# A quote mark only counts as a quote when it is NOT an intra-word apostrophe.
# Without the lookaround, "I'm sorry ... you're" yields a bogus span "m sorry ... you".
SQ_QUOTE     = re.compile(r"(?<![A-Za-z])'([^'\n]{12,200})'(?![A-Za-z])")
KEY_NAME     = re.compile(r'[",{]\s*\\?"?([A-Za-z_][A-Za-z_ 0-9]{2,30})\\?"?\s*:')
FABRICATED_REF = re.compile(r'(?:\./[A-Za-z0-9_\-./]{12,}|\b[0-9a-f]{16,}\b|https?://[^\s"\\]+)')
DREADDIT_KEYS   = {"risk_level", "reasoning", "recommended_support", "safety_note"}
GOEMOTIONS_KEYS = {"emotions", "emotional_intensity", "evidence_from_text"}

def off_task_schema(text, expected):
    """True when an object-like payload uses a key set disjoint from the required schema."""
    keys = {k.strip().lower() for k in KEY_NAME.findall(text)}
    return (len(keys) >= 3 and not (keys & expected)), sorted(keys)[:8]
FENCE_OPEN   = re.compile(r"^```[a-zA-Z]*\s*"); FENCE_CLOSE = re.compile(r"\s*```$")
REFUSAL = re.compile(r"(i (?:can(?:no|')t|am unable|cannot)|i'm sorry|i am sorry|as an ai|"
                     r"unable to (?:assist|help|provide)|please provide|cannot assist|can't assist|"
                     r"i'm not able|i am not able|no text (?:was )?provided|understood\.)", re.I)
JSON_COMMENT = re.compile(r"(?<!:)//[^\n]*")
ESCAPED_KV   = re.compile(r'\\"\s*:\s*\\"')

def strip_fences(t): return FENCE_CLOSE.sub("", FENCE_OPEN.sub("", t.strip())).strip()

def try_obj(t):
    try:
        o = json.loads(t)
    except Exception:
        return None
    return o if isinstance(o, dict) else None

def balanced(text):
    start = text.find("{")
    while start != -1:
        depth = 0; ins = False; esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if esc: esc = False; continue
            if ch == "\\": esc = True; continue
            if ch == '"': ins = not ins; continue
            if ins: continue
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return text[start:i + 1]
        start = text.find("{", start + 1)
    return None

def repeats(s, chunk=120, times=3):
    """True when some >=`chunk`-character window occurs at least `times` times.

    Counts occurrences with str.count rather than sampling at a fixed stride: a
    strided sampler only sees a repeat when the repeat period is a multiple of the
    stride, which silently missed restarted objects.
    """
    if len(s) < chunk * times: return False
    for i in range(0, len(s) - chunk, 60):
        if s.count(s[i:i + chunk]) >= times: return True
    return False

def norm(t):
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", (t or "").lower())).strip()

def _residual_cause(text):
    """Name the specific JSON defect for payloads the ladder rejects for no earlier reason."""
    try:
        json.loads(text.strip())
        err = ""
    except Exception as e:
        err = str(e)
    if err.startswith("Expecting ':' delimiter"):
        return ("bare_string_in_object_position",
                "The model continues a value as further comma-separated string literals inside the object, as "
                "if the object were an array, so the parser reaches a position where a key is required and "
                "finds a bare string instead.")
    if err.startswith("Expecting value") or "Unterminated string" in err:
        return ("unescaped_quote_in_string",
                "A string value contains an unescaped quotation mark (or closes with the wrong quote "
                "character), which terminates the string early and invalidates the object.")
    return ("malformed_json_other",
            "The payload is not parseable by strict JSON, fence-stripping, or balanced-object extraction, for "
            "a reason other than the signatures above.")

# ── taxonomy ────────────────────────────────────────────────────────────────────
def classify_dreaddit(raw):
    """Returns (primary, secondary, description, apparent_prediction, recoverable, why)."""
    sec = []
    if raw is None: return ("missing_raw_field", "", "referral_agent_raw absent from the response body.", None, "false", "No agent output was stored.")
    s = raw.strip()
    if not s: return ("missing_raw_field", "", "referral_agent_raw present but empty.", None, "false", "No agent output was stored.")
    m = RISK_LENIENT.search(s)
    lenient = m.group(1).strip().lower().rstrip('\\"') if m else None
    valid = lenient in ALLOWED_RISK
    nkeys = len(RISK_LENIENT.findall(s))
    nopen = s.count("{")
    strict = try_obj(s) is not None
    fenced = try_obj(strip_fences(s)) is not None
    bal = balanced(s)
    closed = s.rstrip().endswith("}") or s.rstrip().endswith("```")
    refus = bool(REFUSAL.search(s[:400]))
    comment = bool(JSON_COMMENT.search(s))
    escaped = bool(ESCAPED_KV.search(s))
    if repeats(s): sec.append("degenerate_repetition")
    if comment: sec.append("commentary_inside_structured_field")
    if s.lstrip()[:1] not in ("{", "`") and "{" in s: sec.append("prose_or_markdown_instead_of_required_json")

    if nkeys >= 2 and nopen >= 2 and bal is None:
        return ("repeated_or_restarted_json", ";".join(sec),
                f"The object is restarted {nopen} times mid-string; brace depth never returns to zero, so no balanced "
                f"object exists. `risk_level` appears {nkeys} times.",
                lenient if valid else None, "true" if valid else "false",
                "A readable risk_level is present but the response contains no single well-formed object." if valid
                else "No readable risk_level.")
    if lenient and not valid:
        return ("invalid_risk_level", ";".join(sec),
                f"A risk_level field is present but its value {lenient!r} is outside the allowed set "
                f"{ALLOWED_RISK}. The frozen ladder accepts no synonyms and performs no inference.",
                lenient, "false", f"Value {lenient!r} has no defined mapping to a Dreaddit label.")
    if valid:
        if escaped:
            p = "malformed_json_escaping"
            d = ("The first key/value pair is well formed, but subsequent keys use escaped quotes "
                 "(e.g. `reasoning\\\":\\\"`), which makes the whole payload invalid JSON.")
        elif s.lstrip()[:1] not in ("{", "`"):
            p = "missing_json_delimiter"
            d = "The opening delimiter is missing or corrupted, so no balanced object can be located."
        elif comment:
            p = "commentary_inside_structured_field"
            d = "The object contains `//` comments, which are not legal JSON."
        elif not closed:
            p = "apparent_truncation"
            d = "The payload ends without a closing brace; the object is incomplete."
        else:
            p, d = _residual_cause(s)
        return (p, ";".join(sec), d + f" A literal, allowed risk_level value ({lenient!r}) is readable in the text.",
                lenient, "true",
                "The allowed risk_level string is literally present; a more permissive extractor could read it. "
                "Doing so would change the frozen parser contract.")
    if refus:
        return ("refusal_or_deflection", ";".join(sec),
                "The response declines the task or redirects to general advice; no risk_level field is emitted.",
                None, "false", "No prediction of any kind is present.")
    off, keys = off_task_schema(s, DREADDIT_KEYS)
    if off:
        return ("off_task_schema", ";".join(sec),
                f"The response emits a structured object whose key set is disjoint from the required referral schema "
                f"{sorted(DREADDIT_KEYS)}; observed keys include {keys}. The model answered a different task.",
                None, "false", "No referral schema field is present in any form.")
    if "{" not in s:
        return ("prose_or_markdown_instead_of_required_json", ";".join(sec),
                "The response is prose or markdown addressed to the reader rather than the required JSON object.",
                None, "false", "No risk_level value is present in any form.")
    if not closed:
        return ("apparent_truncation", ";".join(sec),
                "The payload ends mid-object and no risk_level survived.", None, "false",
                "No risk_level value is present.")
    return ("missing_required_field", ";".join(sec),
            "A JSON object is present and parseable but carries no `risk_level` key."
            if (strict or fenced) else "An object-like payload is present but no `risk_level` key could be read.",
            None, "false", "The required field is absent.")

def classify_goemotions(raw, parse_status):
    sec = []
    if raw is None: return ("missing_raw_field", "", "emotion_agent_raw absent from the response body.", None, "false", "No agent output was stored.")
    s = raw.strip()
    if not s: return ("missing_raw_field", "", "emotion_agent_raw present but empty.", None, "false", "No agent output was stored.")
    unf = strip_fences(s)
    # The empty object is the SAME defect whether it stands alone or is followed by the
    # model's chain-of-thought prose, so detect it from the first balanced object rather
    # than from an exact match on the whole payload.
    _first = balanced(s) or balanced(unf)
    _empty_obj = (re.fullmatch(r"\{\s*\}", unf) is not None) or \
                 (_first is not None and try_obj(_first) == {})
    if _empty_obj or unf == "null":
        # compare against the FENCE-STRIPPED payload, so a bare ```json {} ``` is not
        # mistaken for an empty object followed by prose
        _trailing = _first is not None and \
            len(re.sub(r"\s", "", unf)) > len(re.sub(r"\s", "", _first)) + 8
        return ("empty_object", "prose_or_markdown_instead_of_required_json" if _trailing else "missing_required_field",
                "The payload is an empty JSON object. It parses, but carries no `emotions` key, so it is NOT the "
                "same as `{\"emotions\": []}` (which would be a valid non_distress prediction). The frozen ladder "
                "refuses to equate the two.", None, "false",
                "There is no emotions field at all; reading it as an empty list would invent a prediction.")
    refus = bool(REFUSAL.search(s[:400]))
    haskey = bool(EMO_KEY.search(s))
    arr = EMO_ARRAY.search(s)
    closed = s.rstrip().endswith(("}", "```", "]"))
    if repeats(s): sec.append("degenerate_repetition")

    apparent = None
    for mm in EMO_ARRAY.finditer(s):
        try:
            lst = json.loads("[" + mm.group(1) + "]")
        except Exception:
            continue
        if isinstance(lst, list):
            apparent = (lst[0].lower().strip() if lst and isinstance(lst[0], str) else "<empty list>")
            break

    if parse_status == "out_of_vocabulary":
        first = apparent
        if first is None and arr:
            first = re.sub(r'^[\s"\']+|[\s"\']+$', "", arr.group(1).split(",")[0]).lower()
        return ("out_of_vocabulary_label", ";".join(sec),
                f"The payload parsed cleanly and the first emotion {first!r} is not a key of the frozen "
                f"ANXIOSENSE_TO_EVAL_CLASS map {sorted(ANXIOSENSE_TO_EVAL_CLASS)}. The model used its own emotion "
                f"vocabulary instead of the one the prompt defines.", first, "false",
                "The payload is structurally valid; the label simply has no defined mapping. Adding one would be a "
                "methodology change, not a recovery.")
    if not haskey:
        if refus:
            return ("refusal_or_deflection", ";".join(sec),
                    "The response declines the task or states that no input was supplied; no emotions field is emitted.",
                    None, "false", "No prediction of any kind is present.")
        if "{" not in s:
            return ("prose_or_markdown_instead_of_required_json", ";".join(sec),
                    "The response uses prose or markdown bullets instead of the required JSON object.",
                    None, "false", "No machine-readable emotions array is present.")
        off, keys = off_task_schema(s, GOEMOTIONS_KEYS)
        if off:
            return ("off_task_schema", ";".join(sec),
                    f"The response emits a structured object whose key set is disjoint from the required emotion "
                    f"schema {sorted(GOEMOTIONS_KEYS)}; observed keys include {keys}.",
                    None, "false", "No emotion schema field is present in any form.")
        return ("missing_required_field", ";".join(sec),
                "An object is present but carries no `emotions` key.", None, "false", "The required field is absent.")
    if arr is None:
        return ("apparent_truncation" if not closed else "malformed_json_other", ";".join(sec),
                "An `emotions` key is present but no complete `[...]` array could be read; the closing bracket is "
                "absent, so the salvage regex (which requires it) correctly declines to read a partial array.",
                None, "false", "The array is incomplete; reading it would guess at the missing content.")
    inner = arr.group(1)
    try:
        json.loads("[" + inner + "]"); parsed_ok = True
    except Exception:
        parsed_ok = False
    if not parsed_ok and EMO_KEY.search(inner) and "{" in inner:
        return ("repeated_or_restarted_json", ";".join(sec),
                "The model restarts the object inside the first `emotions` array (the array's contents themselves "
                "open a fresh `{\"emotions\": ...` object), so the array is not valid JSON and no complete "
                "payload can be read.", None, "false",
                "The restart corrupts the first array; recovering the nested copy would require a "
                "best-match-instead-of-first-match policy change in the parser.")
    if not parsed_ok:
        sec.insert(0, "commentary_inside_structured_field")
        return ("commentary_inside_structured_field", ";".join(sec[1:]),
                "The first `emotions` array contains prose commentary rather than string literals, so it is not "
                "valid JSON. The salvage regex matches the FIRST array, so a corrected array later in the response "
                "is never reached.", apparent, "uncertain",
                "A later, well-formed array may exist, but selecting it would require a first-match-vs-best-match "
                "policy change in the parser.")
    return ("malformed_json_other", ";".join(sec),
            f"An `emotions` array is present and parses, but the payload was classed {parse_status} by the frozen "
            f"ladder (length {len(raw)}; the fail_truncated threshold is 600 characters).",
            apparent, "uncertain", "Requires case-by-case inspection.")

# ── hallucination audit ─────────────────────────────────────────────────────────
def quoted_spans(raw):
    spans = []
    for mm in EVIDENCE_ARR.finditer(raw or ""):
        try:
            lst = json.loads("[" + mm.group(1) + "]")
            spans += [x for x in lst if isinstance(x, str)]
        except Exception:
            spans += [x.strip().strip('"\'') for x in mm.group(1).split('",') if len(x.strip()) > 12]
    spans += [m.group(1) for m in SQ_QUOTE.finditer(raw or "") if len(m.group(1).split()) >= 3]
    out, seen = [], set()
    for s in spans:
        s = s.strip()
        if 12 <= len(s) <= 300 and s.lower() not in seen:
            seen.add(s.lower()); out.append(s)
    return out[:12]

def _stem(tok):
    """Crudest possible inflection fold, so `calls up` matches `call up`."""
    return tok[:-1] if (len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss")) else tok

def _fold(t):
    return " ".join(_stem(x) for x in norm(t).split())

def _window_ratio(n, h):
    if not n or not h: return 0.0
    if n in h: return 1.0
    w = len(n); best = 0.0
    for i in range(0, max(1, len(h) - w + 1), max(1, w // 4)):
        best = max(best, difflib.SequenceMatcher(None, n, h[i:i + w + 20]).ratio())
        if best >= 0.95: break
    return best

def best_ratio(needle, hay):
    """How well a quoted span is supported by the supplied input.

    Deliberately tolerant of three things that are NOT fabrication:
      * elision  - the model writes `A... B` for two separated fragments of the input;
      * inflection - `calls up` quoted as `call up`;
      * whitespace/punctuation normalisation - `out smart` quoted as `outsmart`.
    Also tolerant of a span that embeds a genuine quotation inside the model's own
    commentary, which is schema misuse rather than a fabricated claim.
    """
    h = _fold(hay)
    if not h: return 0.0
    n = _fold(needle)
    if not n: return 0.0
    if n in h: return 1.0
    if n.replace(" ", "") in h.replace(" ", ""): return 1.0
    # elision: every fragment either side of an ellipsis must be present
    frags = [f.strip() for f in re.split(r"\.\s*\.\s*\.|\u2026", _fold(needle)) if len(f.strip()) >= 8]
    if len(frags) > 1 and all(f in h or f.replace(" ", "") in h.replace(" ", "") for f in frags):
        return 1.0
    # commentary wrapping a real quotation
    for inner in re.findall(r"'([^']{8,120})'", needle) + re.findall(r'\u201c([^\u201d]{8,120})\u201d', needle):
        if _fold(inner) in h:
            return 1.0
    # per-token fuzzy match: tolerates a typo in the SOURCE text that the model silently
    # corrected when quoting (e.g. the input reads "watxh", the quote reads "watch")
    nts = n.split(); hts = set(h.split())
    if nts and all(any(difflib.SequenceMatcher(None, t, x).ratio() >= 0.8 for x in hts) for t in nts):
        return 1.0
    # ordered content-token coverage
    nt = n.split(); ht = h.split()
    if len(nt) >= 3:
        sm = difflib.SequenceMatcher(None, nt, ht)
        cov = sum(b.size for b in sm.get_matching_blocks()) / len(nt)
        if cov >= 0.90: return 1.0
        if cov >= 0.80: return 0.85
    return _window_ratio(n, h)

def input_token_coverage(raw, input_text):
    """Fraction of the input's distinct content tokens that appear anywhere in the response.

    Near 0 on a long response means the response is not about the supplied text at all.
    Descriptive only - it is not by itself evidence of fabrication."""
    it = {t for t in _fold(input_text).split() if len(t) > 3}
    if not it: return ""
    rt = set(_fold(raw).split())
    return round(len(it & rt) / len(it), 3)

def fabricated_refs(raw, input_text):
    """Identifiers, paths or URLs presented as content that do not occur in the supplied input."""
    h = (input_text or "")
    return [t for t in set(FABRICATED_REF.findall(raw or "")) if t not in h][:3]

def hallucination_audit(raw, input_text):
    refs = fabricated_refs(raw, input_text)
    spans = quoted_spans(raw)
    if refs:
        return ("true", "fabricated_reference",
                f"The response presents identifier(s)/path(s) that do not occur anywhere in the supplied input: "
                f"{refs}. These are asserted as content, not as formatting.", "high", len(refs))
    if not spans:
        return ("false", "", "No quoted evidence spans were emitted, so there is nothing to verify against the input. "
                            "Formatting failure, wrong label, refusal, OOV label and repetition are explicitly NOT "
                            "treated as hallucination.", "n/a", 0)
    unsupported, partial = [], []
    for s in spans:
        r = best_ratio(s, input_text)
        if r < 0.75: unsupported.append((s, round(r, 3)))
        elif r < 0.90: partial.append((s, round(r, 3)))
    if unsupported:
        ev = "; ".join(f"{s!r} (best match {r} against the supplied input)" for s, r in unsupported[:3])
        return ("true", "unsupported_quoted_evidence",
                f"{len(unsupported)} of {len(spans)} quoted evidence spans do not appear in the supplied input: {ev}",
                "high" if min(r for _, r in unsupported) < 0.55 else "medium", len(unsupported))
    if partial:
        ev = "; ".join(f"{s!r} (best match {r})" for s, r in partial[:3])
        return ("uncertain", "paraphrased_or_normalised_quote",
                f"{len(partial)} of {len(spans)} quoted spans match the input only approximately, which is consistent "
                f"with paraphrase or whitespace normalisation rather than fabrication: {ev}", "low", 0)
    return ("false", "", f"All {len(spans)} quoted evidence spans were located in the supplied input text.", "high", 0)

# ── manual adjudication layer ───────────────────────────────────────────────────
# Every record the automated audit flagged was read against its own input text. The
# verdicts below are the reviewed conclusions; the automated flag is retained in the
# hallucination_candidate column so the two can be compared. Keyed by sample_id, with
# the model/strategy that produced the flag noted for traceability.
HALLUCINATION_REVIEW = {
 "dread_649|Phi-4|zero-shot|4": ("CONFIRMED", "high",
   "Phi-4/zero-shot/run4. The 289-character input is about procrastinating on a Reddit post. The 8,480-character "
   "response narrates skiving, 14-hour film-set days and a Creative Coordinator role, opens with a quotation "
   "attributed to '4scenenotes.com', and presents an invented first-person tl;dr ('kinda on the verge of a "
   "burnout') as the user's words. None of it is in the input. Fabricated content plus a fabricated attribution."),
 "dread_33288|Phi-4|zero-shot|2": ("CONFIRMED", "high",
   "Phi-4/zero-shot/run2. Emits an unrelated schema including \"excerpts selection\": "
   "\"./95761b9e005e46a8220492c40b04489201d2gz8\" - a path-like identifier asserted as content that occurs "
   "nowhere in the input and refers to nothing in the task. Recorded alternative reading: a training-format "
   "artefact rather than a claim about the user's text; the response's own summary of the input is accurate."),
 "ge_ee6o1mk|Phi-4|one-shot-cot|2": ("CONFIRMED", "high",
   "Phi-4/one-shot-cot/run2. The 26-character input is 'Sweaty little incel virgin'. The response asserts that "
   "'the text provided is not self-reported but rather a link to an external source "
   "(`https://tinyurl.com/4kwgs3d5y`)' and returns an empty object on that basis. No link exists in the input; "
   "the URL is fabricated and the false premise drives the output."),
 "ge_eekj86e|Phi-4|zero-shot|1": ("CONFIRMED", "high",
   "Phi-4/zero-shot/run1. The 79-character input is 'Maybe she was attempting to be ironic? I dunno, man, people "
   "are just an enigma.' Under a '### User Input' heading the response reproduces an entirely different, "
   "multi-sentence first-person distress narrative ('I feel really overwhelmed...', 'I was sleep a few hours last "
   "night', \"Loneliness isn't strong enough to explain how I feel\"), analyses that, and then asserts 'The user "
   "explicitly states feeling overwhelmed'. The analysed text is fabricated."),
 "ge_edk1945|Phi-4|one-shot-cot|3": ("REJECTED", "high",
   "Quotation normalised by expanding an abbreviation: the input reads 'Idk if I'm wrong', quoted as 'I don't "
   "know if I'm wrong'. Meaning preserved; no fabricated claim."),
 "ge_eduxv08|Phi-4|zero-shot|1": ("REJECTED", "high",
   "Garbled evidence string 'great is the text' constructed from the word 'great', which is present in the input. "
   "A malformed evidence field, not a false claim."),
 "ge_efawt35|Phi-4|zero-shot|1": ("REJECTED", "high",
   "The flagged span is the prompt's own context preamble ('The following text was sourced from social media...') "
   "quoted into evidence_from_text. Prompt scaffolding leaking into the evidence field, not fabrication."),
 "ge_efafosi|Phi-4|zero-shot-cot|1": ("REJECTED", "high", "Same prompt-scaffolding leak as ge_efawt35."),
 "ge_edlotdx|Phi-4|zero-shot|4": ("REJECTED", "high",
   "Quotation reconstructed with an added subject: input 'Glad you're doing better', quoted as \"I'm glad you're "
   "doing better\". Reconstruction, not fabrication."),
 "ge_eevjrw6|Phi-4|zero-shot|4": ("REJECTED", "medium",
   "Corrupted quotation 'Linhappy for him!' of the input's 'I'm happy for him!'. A decoding corruption of a real "
   "span."),
 "ge_efdoh65|Phi-4|zero-shot|5": ("REJECTED", "high",
   "evidence_from_text contains descriptions ('agreement with a statement', \"justification of a person's "
   "character and their predicament\") rather than quotations. Both descriptions are accurate about the input. "
   "Schema misuse."),
 "ge_edmqf2v|Phi-4|zero-shot-cot|1": ("REJECTED", "high", "Description rather than quotation in evidence_from_text; accurate about the input."),
 "ge_ednmjwe|Phi-4|zero-shot-cot|1": ("REJECTED", "high", "Description rather than quotation in evidence_from_text; accurate about the input."),
 "ge_eepcswq|Phi-4|zero-shot-cot|3": ("REJECTED", "high", "Truncated quotation 'am so excited' of the input's 'I'm so excited'."),
 "ge_efbi2bv|Phi-4|zero-shot|3": ("REJECTED", "high", "Garbled but recognisable quotation of 'really happy he and [NAME] are finding success'."),
 "ge_eecednp|Phi-4|zero-shot-cot|2": ("REJECTED", "high", "Quotation normalised: input 'now im excited', quoted as 'now I am excited'."),
 "ge_edm5gn8|Phi-4|zero-shot-cot|3": ("REJECTED", "high", "Spelling normalised: input \"if their happy I'm good\", quoted as \"if they're happy I'm good\"."),
}

SCAFFOLD = re.compile(r"following text was sourced from social media", re.I)
DESCRIPTIVE = re.compile(r"^\s*(the (user|text|phrase|author)\b|referencing\b|expresses\b|indicat|suggest|"
                         r"agreement with\b|justification of\b)", re.I)

def evidence_field_misuse(raw, input_text):
    """Secondary, non-hallucination labels for how the evidence field was populated."""
    out = []
    spans = []
    for mm in EVIDENCE_ARR.finditer(raw or ""):
        try:
            lst = json.loads("[" + mm.group(1) + "]")
            spans += [x for x in lst if isinstance(x, str)]
        except Exception:
            pass
    for sp in spans:
        if SCAFFOLD.search(sp): out.append("prompt_scaffolding_quoted_as_user_text")
        elif DESCRIPTIVE.match(sp) and best_ratio(sp, input_text) < 0.75:
            out.append("description_instead_of_quotation_in_evidence")
    return list(dict.fromkeys(out))

# ── build rows ──────────────────────────────────────────────────────────────────
raws = {}
for line in open(f"{WORK}/raws.jsonl", encoding="utf-8"):
    r = json.loads(line); raws[r["attempt_uuid"]] = r

rows = []
for line in open(f"{WORK}/index.jsonl", encoding="utf-8"):
    rec = json.loads(line); a = rec["auth"]; p = rec["parsed"] or {}
    u = a["terminal_attempt_uuid"]; ds = a["dataset"]
    raw_rec = raws.get(u)
    field = "referral_agent_raw" if ds == "dreaddit" else "emotion_agent_raw"
    if raw_rec is None:
        row = dict(
            raw_available="false", raw_field_name=field, raw_response=UNAVAIL, raw_len="", raw_sha256=UNAVAIL,
            input_text_len="", primary_failure_category=UNAVAIL, secondary_failure_category=UNAVAIL,
            detailed_failure_description=("Raw evidence is on the external volume "
                                          "/Volumes/Untitled/publication_experiments_from_heba, which is not mounted. "
                                          "No classification is asserted."),
            human_readable_prediction_present=UNAVAIL, apparent_prediction=UNAVAIL,
            apparent_prediction_in_allowed_vocabulary=UNAVAIL, structurally_recoverable=UNAVAIL,
            why_recoverable_or_not=UNAVAIL, hallucination_candidate=UNAVAIL, hallucination_type=UNAVAIL,
            hallucination_evidence=UNAVAIL, hallucination_confidence=UNAVAIL, n_unsupported_quotes="",
            upstream_provider=a.get("upstream_provider") or "", timestamp_utc="", token_usage="",
            input_token_coverage_in_response="", raw_store_path="",
        )
    else:
        raw = raw_rec[field]
        prim, sec, desc, app, recov, why = (classify_dreaddit(raw) if ds == "dreaddit"
                                            else classify_goemotions(raw, a["parse_status"]))
        if ds == "dreaddit":
            in_vocab = "true" if (app in ALLOWED_RISK) else ("false" if app else "")
        else:
            in_vocab = "true" if (app in ANXIOSENSE_TO_EVAL_CLASS) else ("false" if app else "")
        itext = raw_rec.get("input_text") or ""
        hc, ht, he, conf, nun = hallucination_audit(raw, itext)
        _rk = "%s|%s|%s|%s" % (a["sample_id"], MODEL_SHORT.get(a["model"], a["model"]),
                               a["strategy"], a["run"])
        rv, rconf, rbasis = HALLUCINATION_REVIEW.get(
            _rk,
            ("NOT_FLAGGED", "", "Not flagged by the automated audit; no manual review required.")
            if hc == "false" else ("REVIEW_MISSING", "", "Flagged but not adjudicated - investigate."))
        cov = input_token_coverage(raw, itext)
        extra = [x for x in (sec.split(";") if sec else []) if x]
        extra += evidence_field_misuse(raw, itext)
        if rv == "CONFIRMED":
            extra.append("hallucination_confirmed")
        sec = ";".join(dict.fromkeys(extra))
        row = dict(
            raw_available="true", raw_field_name=field, raw_response=raw if raw is not None else "",
            raw_len=len(raw) if raw is not None else 0,
            raw_sha256=hashlib.sha256((raw or "").encode()).hexdigest(),
            input_text_len=len(itext), input_token_coverage_in_response=cov,
            primary_failure_category=prim, secondary_failure_category=sec,
            detailed_failure_description=desc,
            human_readable_prediction_present="true" if app else "false", apparent_prediction=app or "",
            apparent_prediction_in_allowed_vocabulary=in_vocab,
            structurally_recoverable=recov, why_recoverable_or_not=why,
            hallucination_candidate=hc, hallucination_type=ht, hallucination_evidence=he,
            hallucination_confidence=conf, n_unsupported_quotes=nun,
            hallucination_reviewed_verdict=rv, hallucination_review_confidence=rconf,
            hallucination_review_basis=rbasis,
            upstream_provider=raw_rec.get("upstream_provider") or a.get("upstream_provider") or "",
            timestamp_utc=raw_rec.get("timestamp_utc") or "",
            raw_store_path=raw_rec.get("raw_store_path") or "",
            token_usage=json.dumps(raw_rec.get("token_usage") or {}, sort_keys=True),
        )
    row.update(
        dataset=ds, experiment_id=a["source_run"], model=a["model"], model_short=MODEL_SHORT.get(a["model"], a["model"]),
        strategy=a["strategy"], run=a["run"], cell_id=a["cell_id"], sample_id=a["sample_id"],
        terminal_attempt_uuid=u, ground_truth=a["ground_truth"],
        parse_status=a["parse_status"], failure_class=a["failure_class"], failure_reason=a["failure_reason"],
        prediction_valid=a["prediction_valid"], parsed_prediction="" if a["parsed_prediction"] is None else a["parsed_prediction"],
        include_in_metrics=a["include_in_metrics"],
        safety_intercept="false", final_outcome_class=p.get("final_outcome_class", ""),
        transport_outcome=p.get("transport_outcome", ""), attempt_count=p.get("attempt_count", ""),
        http_status=p.get("http_status", ""), latency_ms=p.get("latency_ms", ""),
        quality_flags=json.dumps(p.get("quality_flags") or {}, sort_keys=True),
        cross_check=json.dumps(p.get("cross_check") or {}, sort_keys=True),
        parser_version=p.get("parser_version", ""),
    )
    rows.append(row)

# ── recurrence, computed over (dataset, model, strategy, sample) ────────────────
groups = collections.defaultdict(list)
for r in rows:
    groups[(r["dataset"], r["model"], r["strategy"], r["sample_id"])].append(r)
for key, g in groups.items():
    n = len(g)
    cats = {r["primary_failure_category"] for r in g}
    avail = [r for r in g if r["raw_available"] == "true"]
    if len(avail) != len(g):
        same, sim = "unknown", UNAVAIL
    else:
        same = "true" if len(cats) == 1 else "false"
        texts = [r["raw_response"] for r in avail]
        if n == 1: sim = "n/a_single_run"
        elif len(set(texts)) == 1: sim = "identical"
        else:
            worst = min(difflib.SequenceMatcher(None, texts[0], t).ratio() for t in texts[1:])
            sim = "similar" if worst >= 0.90 else "different"
    for r in g:
        r["n_runs_this_sample_failed_same_model_strategy"] = n
        r["failure_reproduced_across_runs"] = "true" if n > 1 else "false"
        r["same_failure_category_across_runs"] = same
        r["raw_outputs_identical_or_similar"] = sim

COLS = ["dataset", "experiment_id", "model", "model_short", "strategy", "run", "cell_id", "sample_id",
        "terminal_attempt_uuid", "ground_truth",
        "parse_status", "failure_class", "failure_reason", "prediction_valid", "parsed_prediction",
        "include_in_metrics", "safety_intercept", "final_outcome_class", "transport_outcome",
        "attempt_count", "http_status", "latency_ms", "quality_flags", "cross_check", "parser_version",
        "upstream_provider", "timestamp_utc", "token_usage",
        "raw_available", "raw_field_name", "raw_response", "raw_len", "raw_sha256", "input_text_len",
        "input_token_coverage_in_response", "raw_store_path",
        "primary_failure_category", "secondary_failure_category", "detailed_failure_description",
        "hallucination_candidate", "hallucination_type", "hallucination_evidence", "hallucination_confidence",
        "n_unsupported_quotes", "hallucination_reviewed_verdict", "hallucination_review_confidence",
        "hallucination_review_basis",
        "human_readable_prediction_present", "apparent_prediction",
        "apparent_prediction_in_allowed_vocabulary", "structurally_recoverable", "why_recoverable_or_not",
        "n_runs_this_sample_failed_same_model_strategy", "failure_reproduced_across_runs",
        "same_failure_category_across_runs", "raw_outputs_identical_or_similar"]

rows.sort(key=lambda r: (r["dataset"], r["model"], r["strategy"], r["run"], r["sample_id"]))
with open(f"{OUT}/invalid_outputs_row_level.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
    for r in rows: w.writerow(r)
with open(f"{OUT}/invalid_outputs_row_level.jsonl", "w", encoding="utf-8") as fh:
    for r in rows: fh.write(json.dumps({k: r.get(k, "") for k in COLS}, ensure_ascii=False) + "\n")

print("rows written:", len(rows))
print("raw available:", sum(1 for r in rows if r["raw_available"] == "true"),
      "| RAW_UNAVAILABLE:", sum(1 for r in rows if r["raw_available"] == "false"))
print("\nprimary_failure_category:")
for k, v in collections.Counter(r["primary_failure_category"] for r in rows).most_common():
    print("  %-46s %5d" % (k, v))
print("\nhallucination_candidate (automated):")
for k, v in collections.Counter(r["hallucination_candidate"] for r in rows).most_common():
    print("  %-46s %5d" % (k, v))
print("\nhallucination_reviewed_verdict (manual):")
for k, v in collections.Counter(r["hallucination_reviewed_verdict"] for r in rows).most_common():
    print("  %-46s %5d" % (k, v))
print("\nsecondary labels:")
_sec = collections.Counter()
for r in rows:
    for x in (r["secondary_failure_category"] or "").split(";"):
        if x: _sec[x] += 1
for k, v in _sec.most_common():
    print("  %-46s %5d" % (k, v))

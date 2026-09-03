"""Raw response -> prediction. Pure, offline, deterministic.

Called AFTER an attempt is stored, and again by rescore.py against stored attempts.
It never triggers a retry, never sees ground truth, and never writes to raw storage.

CANONICAL RULE: the prediction is derived from the agent's RAW output, not from a
field the server computed. The server's value is kept only as a cross-check, so a
server-side substitution can be detected rather than inherited.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

from ._reuse import (ANXIOSENSE_TO_EVAL_CLASS, extract_emotion_payload,
                     primary_emotion, OK_STATUSES)
from .failures import ParseOutcome, Transport
from .referral_risk_parser import extract_risk_level, risk_to_dreaddit_label

PARSER_VERSION = "1.0.0"


@dataclass
class Parsed:
    parse_status: str
    parsed_prediction: Any
    prediction_valid: bool
    failure_class: str | None
    failure_reason: str | None
    include_in_metrics: bool
    cross_check: dict[str, Any]
    parser_version: str = PARSER_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _not_applicable(transport: Transport, detail: str | None) -> Parsed:
    return Parsed(
        parse_status="not_applicable",
        parsed_prediction=None,
        prediction_valid=False,
        failure_class=transport.value,
        failure_reason=detail,
        include_in_metrics=False,
        cross_check={},
    )


def parse_dreaddit(body: dict | None, transport: Transport,
                   transport_detail: str | None = None) -> Parsed:
    if transport is Transport.SAFETY_INTERCEPT:
        return Parsed("safety_intercept", None, False, Transport.SAFETY_INTERCEPT.value,
                      "deterministic crisis path fired before any model call",
                      False, {})
    if transport is not Transport.OK or body is None:
        return _not_applicable(transport, transport_detail)

    raw = body.get("referral_agent_raw")
    server_level = ((body.get("report") or {}).get("referralLevel"))
    server_unreadable = bool(body.get("referral_unreadable"))

    if not isinstance(raw, str) or not raw.strip():
        return Parsed(
            "raw_absent", None, False, ParseOutcome.MODEL_BEHAVIOUR.value,
            "referral_agent_raw absent - the prediction cannot be independently derived",
            False,
            {"server_referral_level": server_level, "server_referral_unreadable": server_unreadable},
        )

    level = extract_risk_level(raw)
    cross = {
        "server_referral_level": server_level,
        "server_referral_unreadable": server_unreadable,
        "derived_referral_level": level,
        "agrees_with_server": (level == server_level) if level is not None else (server_level is None),
    }

    if level is None:
        # A complete response the parser cannot read. MODEL BEHAVIOUR: recorded,
        # never retried, never converted into a class.
        return Parsed("unparseable", None, False, ParseOutcome.MODEL_BEHAVIOUR.value,
                      "no explicit valid risk_level in the referral output",
                      False, cross)

    return Parsed("ok", risk_to_dreaddit_label(level), True, None, None, True, cross)


def parse_goemotions(body: dict | None, transport: Transport,
                     transport_detail: str | None = None) -> Parsed:
    if transport is Transport.SAFETY_INTERCEPT:
        return Parsed("safety_intercept", None, False, Transport.SAFETY_INTERCEPT.value,
                      "deterministic crisis path fired before any model call",
                      False, {})
    if transport is not Transport.OK or body is None:
        return _not_applicable(transport, transport_detail)

    raw = body.get("emotion_agent_raw")
    status, emotions = extract_emotion_payload(raw)
    cross = {"emotion_payload_status": status}

    if status not in OK_STATUSES:
        # fail_absent / fail_truncated / fail_unparseable are all MODEL BEHAVIOUR.
        # None of them is non_distress.
        return Parsed(status, None, False, ParseOutcome.MODEL_BEHAVIOUR.value,
                      f"emotion payload unreadable ({status})", False, cross)

    emotion = primary_emotion(emotions)
    cross["primary_emotion"] = emotion

    if emotion is None:
        # A VALID empty emotions list. Under the CURRENT frozen methodology this is
        # a legitimate non_distress prediction (DATA_PREPROCESSING.md Step 3).
        # Unchanged here by design - altering it is a methodology decision.
        return Parsed("ok_empty_list", "non_distress", True, None, None, True, cross)

    if emotion not in ANXIOSENSE_TO_EVAL_CLASS:
        return Parsed("out_of_vocabulary", None, False, ParseOutcome.MODEL_BEHAVIOUR.value,
                      f"out-of-vocabulary predicted emotion: {emotion!r}", False, cross)

    return Parsed("ok", ANXIOSENSE_TO_EVAL_CLASS[emotion], True, None, None, True, cross)


PARSERS = {"dreaddit": parse_dreaddit, "goemotions": parse_goemotions}


def parse(dataset: str, body: dict | None, transport: Transport,
          transport_detail: str | None = None) -> Parsed:
    if dataset not in PARSERS:
        raise KeyError(f"no parser for dataset {dataset!r}")
    return PARSERS[dataset](body, transport, transport_detail)

"""FROZEN GoEmotions -> AnxioSense ground-truth mapping.

MAPPING_VERSION 1.0.0 - adopted 2026-09-04 ("V1" in the evidence audit,
claude/goemotions-mapping-evidence-audit-2026-09-04.md).

Evidence tiers used throughout:
  direct      the grouping is published by GoEmotions itself
  operational an AnxioSense decision DERIVED from a published grouping; the
              grouping is theirs, the destination class is ours
  derived     supported by a source but requiring an inferential step we must
              defend in the Methods section

SOURCES
  S1  Demszky, Movshovitz-Attias, Ko, Cowen, Nemade & Ravi (2020).
      "GoEmotions: A Dataset of Fine-Grained Emotions." ACL 2020, 4040-4054.
      https://aclanthology.org/2020.acl-main.372/   (Appendix A: rater definitions)
  S2  google-research/goemotions/data/ekman_mapping.json      (official, verbatim below)
  S3  google-research/goemotions/data/sentiment_mapping.json  (official, verbatim below)
  S4  Sylvers, Lilienfeld & LaPrairie (2011). "Differences between trait fear and
      trait anxiety: Implications for psychopathology."
      Clinical Psychology Review 31(2), 122-137.

WHAT IS **NOT** A GOEMOTIONS MAPPING
  GoEmotions publishes an Ekman grouping and a sentiment grouping. It does NOT
  publish a mapping onto AnxioSense's five operational classes, and it does NOT
  publish any rule for reducing its multi-label annotations to a single label.
  Every destination class name below (anxiety / fear / sadness / frustration /
  non_distress) and the whole of R1-R4 are AnxioSense operational decisions.
  Cite the grouping, never the destination, as GoEmotions' own.

DELIBERATELY REMOVED BEHAVIOUR
  The historical mapper (evaluation/llm-experiments/src/label_mapping.py) is NOT
  used on the publication path. Two of its behaviours are defects at official
  scope and are prevented here:
    1. an empty mappable-label list returned "non_distress", which would have
       fabricated ground truth for 2,670 of the 5,427 official test rows;
    2. a multi-label row silently took the FIRST label, which - because
       GoEmotions stores label ids ascending - is a "lowest emotion id wins"
       storage artefact, not a methodological decision.
  Here (1) raises MappingDataError and (2) raises UnscorableRow.
"""
from __future__ import annotations

from typing import Iterable, Sequence

MAPPING_VERSION = "1.0.0"

EVAL_CLASSES: tuple[str, ...] = ("anxiety", "fear", "sadness", "frustration", "non_distress")
OUT_OF_TAXONOMY = "OUT_OF_TAXONOMY"

# Official GoEmotions label space, ids 0-27, dataset order (S1/S2/S3).
GOEMOTIONS_LABELS: tuple[str, ...] = (
    "admiration", "amusement", "anger", "annoyance", "approval", "caring",
    "confusion", "curiosity", "desire", "disappointment", "disapproval",
    "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
    "joy", "love", "nervousness", "optimism", "pride", "realization", "relief",
    "remorse", "sadness", "surprise", "neutral",
)

# ---------------------------------------------------------------------------
# The official groupings, VERBATIM. Retained so tests can prove we did not
# quietly edit a published grouping to suit us.
# ---------------------------------------------------------------------------
EKMAN_GROUPING: dict[str, tuple[str, ...]] = {          # S2
    "anger":    ("anger", "annoyance", "disapproval"),
    "disgust":  ("disgust",),
    "fear":     ("fear", "nervousness"),
    "joy":      ("joy", "amusement", "approval", "excitement", "gratitude",
                 "love", "optimism", "relief", "pride", "admiration", "desire", "caring"),
    "sadness":  ("sadness", "disappointment", "embarrassment", "grief", "remorse"),
    "surprise": ("surprise", "realization", "confusion", "curiosity"),
}
SENTIMENT_GROUPING: dict[str, tuple[str, ...]] = {      # S3
    "positive":  ("amusement", "excitement", "joy", "love", "desire", "optimism",
                  "caring", "pride", "admiration", "gratitude", "relief", "approval"),
    "negative":  ("fear", "nervousness", "remorse", "embarrassment", "disappointment",
                  "sadness", "grief", "disgust", "anger", "annoyance", "disapproval"),
    "ambiguous": ("realization", "surprise", "curiosity", "confusion"),
    # "neutral" is its own category at the sentiment level (S1) and appears in
    # neither the Ekman file nor the sentiment file.
}

# ---------------------------------------------------------------------------
# The frozen 28-label mapping.
#   label -> (anxiosense_class_or_OUT_OF_TAXONOMY, evidence_tier, basis)
# ---------------------------------------------------------------------------
_D, _O, _V = "direct", "operational", "derived"

LABEL_MAP: dict[str, tuple[str, str, str]] = {
    # -- anxiety ------------------------------------------------------------
    # DEPARTS FROM THE OFFICIAL EKMAN GROUPING, which places nervousness under
    # fear (S2). Basis: S1 Appendix A defines nervousness as "Apprehension,
    # worry, anxiety"; S4 establishes fear and anxiety as separable constructs
    # (imminent threat + active coping vs anticipated threat + hypervigilance;
    # short-lived vs long-lived). AnxioSense's referral logic acts on that
    # distinction, so collapsing it would blind the evaluation to the system's
    # primary output. Approved by Aya 2026-09-04. MUST be argued in Methods.
    # Reliability caveat to report: nervousness has the second-lowest interrater
    # agreement in GoEmotions (Spearman rho = 0.164) and yields n = 14 scorable
    # rows in the official test split.
    "nervousness":    ("anxiety", _V, "S1 App.A definition names 'anxiety'; S4 construct distinction. DEPARTS from S2 Ekman fear group."),

    # -- fear ---------------------------------------------------------------
    "fear":           ("fear", _D, "S2 Ekman fear group; direct name match."),

    # -- sadness: the official Ekman sadness group, unchanged ---------------
    "sadness":        ("sadness", _D, "S2 Ekman sadness group."),
    "disappointment": ("sadness", _D, "S2 Ekman sadness group."),
    "grief":          ("sadness", _D, "S2 Ekman sadness group."),
    "embarrassment":  ("sadness", _D, "S2 Ekman sadness group."),
    "remorse":        ("sadness", _D, "S2 Ekman sadness group."),

    # -- frustration: the official Ekman ANGER group ------------------------
    # The grouping is S2's. "frustration" is AnxioSense vocabulary; GoEmotions
    # has no such label. Methods must say "the Ekman anger group, which
    # AnxioSense reports as frustration".
    "anger":          ("frustration", _O, "S2 Ekman anger group; destination name is AnxioSense vocabulary."),
    "annoyance":      ("frustration", _O, "S2 Ekman anger group; destination name is AnxioSense vocabulary."),
    "disapproval":    ("frustration", _O, "S2 Ekman anger group; destination name is AnxioSense vocabulary."),

    # -- non_distress: the official POSITIVE sentiment group, plus neutral ---
    # OPERATIONAL, NOT DIRECT. S3 groups these twelve as "positive" and S1
    # treats neutral as its own sentiment category. Neither publishes a
    # "non_distress" class. The grouping is GoEmotions'; the destination is
    # ours, and it encodes the claim that a model asserting distress on a
    # positive or neutral comment has produced a false positive.
    "admiration":     ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "amusement":      ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "approval":       ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "caring":         ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "desire":         ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "excitement":     ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "gratitude":      ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "joy":            ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "love":           ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "optimism":       ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "pride":          ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "relief":         ("non_distress", _O, "S3 positive group -> AnxioSense non_distress (operational)."),
    "neutral":        ("non_distress", _O, "S1 neutral sentiment category -> AnxioSense non_distress (operational)."),

    # -- out of taxonomy ----------------------------------------------------
    # S3's "ambiguous" category: GoEmotions itself declines to assign a valence.
    "realization":    (OUT_OF_TAXONOMY, _D, "S3 ambiguous category; valence undetermined by the taxonomy."),
    "surprise":       (OUT_OF_TAXONOMY, _D, "S3 ambiguous category; valence undetermined by the taxonomy."),
    "curiosity":      (OUT_OF_TAXONOMY, _D, "S3 ambiguous category; valence undetermined by the taxonomy."),
    "confusion":      (OUT_OF_TAXONOMY, _D, "S3 ambiguous category; valence undetermined by the taxonomy."),
    # S2 gives disgust its OWN Ekman category, explicitly separate from anger.
    # Folding it into frustration would override the only official grouping
    # available; AnxioSense has no disgust class. Approved by Aya 2026-09-04.
    "disgust":        (OUT_OF_TAXONOMY, _D, "S2 Ekman disgust is its own category, distinct from anger; no AnxioSense class."),
}

UNSCORABLE_CONFLICT = "conflicting_classes"
UNSCORABLE_OUT_OF_TAXONOMY = "out_of_taxonomy"


class MappingDataError(RuntimeError):
    """The row itself is unusable: no labels, or a label outside the 28-label
    space. Always fatal - never silently resolved to a class."""


class UnscorableRow(RuntimeError):
    """The row is valid GoEmotions data but carries no single ground-truth class
    in the AnxioSense 5-class space. The row is KEPT, with this reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


def anxiosense_class(label: str) -> str:
    """Class for one GoEmotions label, or OUT_OF_TAXONOMY."""
    try:
        return LABEL_MAP[label][0]
    except KeyError:
        raise MappingDataError(
            f"label {label!r} is not one of the 28 official GoEmotions labels"
        ) from None


def map_goemotions_labels(label_names: Sequence[str] | Iterable[str]) -> str:
    """Frozen ground-truth rule for one row. Returns exactly one EVAL_CLASSES value.

    Multi-label rules (AnxioSense operational; GoEmotions publishes none):
      R1  every mapped label agrees            -> that class
      R2  mapped labels disagree               -> UnscorableRow(conflicting_classes)
      R3  mapped + out-of-taxonomy             -> discard OOT, then R1/R2
      R4  only out-of-taxonomy labels          -> UnscorableRow(out_of_taxonomy)

    An empty label list raises MappingDataError. It is NEVER non_distress.
    """
    labels = [str(x).strip() for x in label_names if str(x).strip()]
    if not labels:
        raise MappingDataError(
            "empty GoEmotions label list; refusing to assign a class. "
            "(The historical mapper returned 'non_distress' here, fabricating ground truth.)"
        )

    classes = [anxiosense_class(l) for l in labels]                       # validates each
    resolved = [c for c in classes if c != OUT_OF_TAXONOMY]               # R3: discard OOT

    if not resolved:                                                      # R4
        raise UnscorableRow(UNSCORABLE_OUT_OF_TAXONOMY, "|".join(labels))

    distinct = sorted(set(resolved))
    if len(distinct) > 1:                                                 # R2
        raise UnscorableRow(UNSCORABLE_CONFLICT, "+".join(distinct))

    return distinct[0]                                                    # R1


def mapping_provenance() -> dict:
    """Serialisable description of the frozen mapping, for the manifest."""
    by_class: dict[str, list[str]] = {}
    for label, (cls, _t, _b) in sorted(LABEL_MAP.items()):
        by_class.setdefault(cls, []).append(label)
    return {
        "mapping_version": MAPPING_VERSION,
        "eval_classes": list(EVAL_CLASSES),
        "labels_by_class": by_class,
        "evidence_tiers": {l: t for l, (_c, t, _b) in sorted(LABEL_MAP.items())},
        "bases": {l: b for l, (_c, _t, b) in sorted(LABEL_MAP.items())},
        "multi_label_rules": {
            "R1": "all mapped labels agree -> that class",
            "R2": "mapped labels conflict -> unscorable(conflicting_classes)",
            "R3": "mapped + out-of-taxonomy -> discard OOT then R1/R2",
            "R4": "only out-of-taxonomy -> unscorable(out_of_taxonomy)",
            "empty": "raises MappingDataError; never non_distress",
        },
        "sources": {
            "S1": "Demszky et al. 2020, ACL, https://aclanthology.org/2020.acl-main.372/",
            "S2": "google-research/goemotions/data/ekman_mapping.json",
            "S3": "google-research/goemotions/data/sentiment_mapping.json",
            "S4": "Sylvers, Lilienfeld & LaPrairie 2011, Clin Psychol Rev 31(2):122-137",
        },
        "not_published_by_goemotions": [
            "the five AnxioSense destination class names",
            "any reduction of multi-label annotations to a single label (R1-R4)",
        ],
    }

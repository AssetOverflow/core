"""Dialogue intent classification.

Maps a raw prompt string to a typed intent tag. The classifier is rule-based
(prefix/pattern matching) — no ML dependency. Downstream, the intent selects
the proposition frame family and graph shape before generation begins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, unique


@unique
class IntentTag(Enum):
    DEFINITION = "definition"
    CAUSE = "cause"
    PROCEDURE = "procedure"
    COMPARISON = "comparison"
    CORRECTION = "correction"
    RECALL = "recall"
    VERIFICATION = "verification"
    TRANSITIVE_QUERY = "transitive_query"
    FRAME_TRANSFER = "frame_transfer"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DialogueIntent:
    tag: IntentTag
    subject: str
    secondary_subject: str | None = None
    relation: str | None = None  # populated for TRANSITIVE_QUERY (ADR-0018)
    frame: str | None = None     # populated for FRAME_TRANSFER (compose_relations)

    def requires_prior_turn(self) -> bool:
        return self.tag is IntentTag.CORRECTION


_COMPARE_RE = re.compile(
    r"^compare\s+(.+?)\s+(?:and|vs\.?|versus|with)\s+(.+)",
    re.IGNORECASE,
)

# Transitive-query forms (ADR-0018):
#   "What does X <verb>?"   -> (X, R) where R is any verb-like word
#   "Where does X belong?"  -> (X, belongs_to)
# The verb slot accepts any single word — `multi_relation_walk` in the
# operator layer handles unrecognised relations by falling back to a
# cross-relation traversal (rather than a strict literal-relation match).
_TRANSITIVE_QUERY_RE = re.compile(
    r"^what\s+does\s+(?P<subject>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)?)\s+"
    r"(?P<relation>[a-z][a-z\-]*)\b",
    re.IGNORECASE,
)
# Frame-transfer form:
#   "What does X R in Y?"  -> compose_relations(triples, X, Y, R)
# This is the compositionality lane's `novel_pair_under_seen_relation`
# probe shape.  Must be tried before the generic transitive-query rule
# so the "in Y" tail is not silently truncated.
_FRAME_TRANSFER_RE = re.compile(
    r"^what\s+does\s+(?P<subject>[a-z][a-z\-]+)\s+"
    r"(?P<relation>[a-z][a-z\-]+)(?P<rel_tail>\s+to)?\s+in\s+"
    r"(?P<frame>[a-z][a-z\-]+)\b",
    re.IGNORECASE,
)
_BELONG_QUERY_RE = re.compile(
    r"^where\s+does\s+(?P<subject>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)?)\s+"
    r"belong(?:s?)\b",
    re.IGNORECASE,
)

# Normalisation of the relation surface form back to the bare relation
# vocabulary the teaching store carries (matches en_core_cognition_v1).
_RELATION_NORMALIZE: dict[str, str] = {
    "precede": "precedes", "precedes": "precedes",
    "cause": "causes", "causes": "causes",
    "ground": "grounds", "grounds": "grounds",
    "reveal": "reveals", "reveals": "reveals",
    "mean": "means", "means": "means",
    "follow": "follows", "follows": "follows",
    "contrast": "contrasts_with", "contrast_with": "contrasts_with",
    "contrasts_with": "contrasts_with", "contrasts with": "contrasts_with",
    "produce": "produces", "produces": "produces",
}

_RULES: tuple[tuple[re.Pattern[str], IntentTag], ...] = (
    (re.compile(r"^what\s+(?:is|are)\s+", re.IGNORECASE), IntentTag.DEFINITION),
    (re.compile(r"^why\s+", re.IGNORECASE), IntentTag.CAUSE),
    (re.compile(r"^how\s+(?:do|can|should|would)\s+(?:I|we|you)\s+", re.IGNORECASE), IntentTag.PROCEDURE),
    (re.compile(r"^(?:is|are|does|do|can|could|would|should|was|were|has|have|will)\s+.+\??\s*$", re.IGNORECASE), IntentTag.VERIFICATION),
    (re.compile(r"^(?:no|that'?s\s+(?:not|wrong)|incorrect|actually|correction)", re.IGNORECASE), IntentTag.CORRECTION),
    (re.compile(r"^remember\s+", re.IGNORECASE), IntentTag.RECALL),
)


# ADR-0049 — deterministic head-noun extraction from subject phrases.
#
# After a rule fires, the raw subject span often still carries auxiliary
# verbs, articles, or trailing punctuation:
#
#     "What is a procedure?"      -> raw subject "a procedure"
#     "Why does light exist?"     -> raw subject "does light exist"
#     "Does memory require recall?" -> raw subject (whole prompt)
#
# Downstream consumers (graph_planner, ADR-0048 pack-grounded surface,
# future teaching-store inference) expect a clean lemma so they can
# match the ratified pack lexicon, build single-subject graphs, or
# consult the teaching store keyed by lemma.
#
# This normalizer is *pack-agnostic* — it does not load or consult any
# pack.  It is a pure syntactic head-noun extractor: strip aux verbs,
# strip articles, return either the head noun (CAUSE / VERIFICATION)
# or the cleaned noun phrase (DEFINITION / RECALL / PROCEDURE).
_ARTICLES = frozenset({"a", "an", "the"})
_AUX_VERBS = frozenset({
    "is", "are", "am", "was", "were", "be", "been", "being",
    "does", "do", "did",
    "has", "have", "had",
    "can", "could", "would", "should", "shall", "will", "might", "may", "must",
})


def _normalize_subject(phrase: str, tag: IntentTag) -> str:
    """Strip aux verbs, articles, and trailing punctuation from a subject phrase.

    For CAUSE and VERIFICATION the subject phrase typically contains the
    full predicate ("does light exist"), and we return the head noun.
    For DEFINITION / RECALL / PROCEDURE we keep multi-word noun phrases
    intact (so e.g. "artificial intelligence" is preserved), only
    stripping leading articles and trailing punctuation.

    Falls back to the original phrase if normalization would empty it.
    """
    if not phrase:
        return phrase
    cleaned = phrase.strip().rstrip("?.!").strip()
    if not cleaned:
        return ""
    tokens = cleaned.split()
    if not tokens:
        return cleaned

    if tag in (IntentTag.CAUSE, IntentTag.VERIFICATION):
        while tokens and tokens[0].lower() in _AUX_VERBS:
            tokens = tokens[1:]

    while tokens and tokens[0].lower() in _ARTICLES:
        tokens = tokens[1:]

    if not tokens:
        return cleaned

    if tag in (IntentTag.CAUSE, IntentTag.VERIFICATION):
        return tokens[0]

    return " ".join(tokens)


def classify_intent(prompt: str) -> DialogueIntent:
    text = prompt.strip()
    if not text:
        return DialogueIntent(tag=IntentTag.UNKNOWN, subject="")

    compare_match = _COMPARE_RE.match(text)
    if compare_match:
        return DialogueIntent(
            tag=IntentTag.COMPARISON,
            subject=compare_match.group(1).strip(),
            secondary_subject=compare_match.group(2).strip(),
        )

    frame_match = _FRAME_TRANSFER_RE.match(text)
    if frame_match:
        raw_relation = frame_match.group("relation").lower().strip()
        # "X belong to in Y" — normalize to belongs_to since the optional
        # " to" token after the relation indicates the same paraphrase
        # the BELONG_QUERY rule handles for single-entity probes.
        if frame_match.group("rel_tail") and raw_relation in {"belong", "belongs"}:
            relation = "belongs_to"
        else:
            relation = _RELATION_NORMALIZE.get(raw_relation, raw_relation)
        return DialogueIntent(
            tag=IntentTag.FRAME_TRANSFER,
            subject=frame_match.group("subject").strip(),
            relation=relation,
            frame=frame_match.group("frame").strip(),
        )

    transitive_match = _TRANSITIVE_QUERY_RE.match(text)
    if transitive_match:
        raw_relation = transitive_match.group("relation").lower().strip()
        relation = _RELATION_NORMALIZE.get(raw_relation, raw_relation)
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=transitive_match.group("subject").strip(),
            relation=relation,
        )

    belong_match = _BELONG_QUERY_RE.match(text)
    if belong_match:
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=belong_match.group("subject").strip(),
            relation="belongs_to",
        )

    for pattern, tag in _RULES:
        match = pattern.match(text)
        if match:
            subject = text[match.end():].rstrip("?").strip()
            if not subject:
                subject = text
            subject = _normalize_subject(subject, tag)
            return DialogueIntent(tag=tag, subject=subject)

    return DialogueIntent(tag=IntentTag.UNKNOWN, subject=text)

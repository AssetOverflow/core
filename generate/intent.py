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
class ResponseMode(Enum):
    """Presentation-depth axis, orthogonal to :class:`IntentTag`.

    ``IntentTag`` answers *what does the user want* (definition, cause,
    verification, …).  ``ResponseMode`` answers *at what depth and shape
    should the response be rendered* (brief / explain / walkthrough /
    paragraph / example).

    Keeping mode separate from intent is the same syntactic-vs-semantic
    separation ADR-0049 enforced for subject extraction: presentation
    concerns must not corrupt the semantic enum.  The discourse planner
    (``generate/discourse_planner.py``) consumes the pair
    ``(DialogueIntent, ResponseMode)`` to select move count and move
    kinds; classification of mode is performed by
    :func:`classify_response_mode` and is purely additive — no existing
    ``DialogueIntent`` field changes, no existing ``classify_intent``
    branch alters its output.
    """

    BRIEF = "brief"
    EXPLAIN = "explain"
    WALKTHROUGH = "walkthrough"
    PARAGRAPH = "paragraph"
    EXAMPLE = "example"


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
    # P3.3 — "Tell me about X" / "Describe X" — multi-clause
    # composer walks every chain rooted on X.
    NARRATIVE = "narrative"
    # P3.4 — "Give me an example of X" / "Show an instance of X" —
    # reverse-chain composer surfaces chains where X is the object.
    EXAMPLE = "example"
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
# "How does X work / function / operate / happen / exist / behave?"
# — third-person mechanistic-cause query.  Distinct from PROCEDURE
# (which is first-person: "How do I/we/you X?") because the user is
# asking about the mechanism of X, not how to perform X themselves.
# Routes to CAUSE so the teaching-chain / cross-pack / pack-surface
# dispatcher fires on X.
_HOW_DOES_X_RE = re.compile(
    r"^how\s+do(?:es)?\s+(?P<subject>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)?)\s+"
    r"(?:work|function|operate|happen|exist|behave|act|emerge)\b",
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
    # P3.3 — NARRATIVE patterns precede DEFINITION so "Tell me about X"
    # does not accidentally classify as DEFINITION on the noun span.
    (re.compile(r"^tell\s+me\s+about\s+", re.IGNORECASE), IntentTag.NARRATIVE),
    (re.compile(r"^describe\s+", re.IGNORECASE), IntentTag.NARRATIVE),
    (re.compile(r"^what\s+(?:can|do)\s+you\s+(?:say|know)\s+about\s+", re.IGNORECASE), IntentTag.NARRATIVE),
    # P3.4 — EXAMPLE patterns precede DEFINITION for the same reason.
    (re.compile(r"^(?:give|show)\s+(?:me\s+)?an?\s+(?:example|instance)\s+of\s+", re.IGNORECASE), IntentTag.EXAMPLE),
    (re.compile(r"^example\s+of\s+", re.IGNORECASE), IntentTag.EXAMPLE),
    (re.compile(r"^what\s+(?:is|are)\s+", re.IGNORECASE), IntentTag.DEFINITION),
    # Imperative-form DEFINITION — "Define X", "Define X." — produces
    # the same routing as "What is X?".  Without this rule the prompt
    # falls through to UNKNOWN and the whole text becomes the subject,
    # making pack-resolved lemmas like "moment" or "evident" silently
    # un-groundable.
    (re.compile(r"^define\s+", re.IGNORECASE), IntentTag.DEFINITION),
    # Expository-DEFINITION variants — "Explain X." and the paragraph
    # request forms — route to DEFINITION so the grounded substrate
    # fires on X.  Presentation depth ("explain at length", "as a
    # paragraph") is carried orthogonally by ResponseMode; the semantic
    # request is still "the definition of X".  Placed AFTER the
    # NARRATIVE rules so "Tell me about X" and "Describe X" continue
    # to route to NARRATIVE.
    (re.compile(r"^explain\s+", re.IGNORECASE), IntentTag.DEFINITION),
    (
        re.compile(
            r"^(?:write|compose|draft)\s+(?:a\s+)?(?:short\s+|brief\s+)?"
            r"paragraph\s+(?:about|on)\s+",
            re.IGNORECASE,
        ),
        IntentTag.DEFINITION,
    ),
    (
        re.compile(r"^paragraph\s+(?:about|on)\s+", re.IGNORECASE),
        IntentTag.DEFINITION,
    ),
    (re.compile(r"^why\s+", re.IGNORECASE), IntentTag.CAUSE),
    # "What causes / triggers / enables / prevents / drives X?" — the
    # query is about what causes X, so the subject of the CAUSE intent
    # is X (not the causative verb).  Place ahead of the generic
    # VERIFICATION rule because "What causes X?" starts with "what" not
    # an aux verb so VERIFICATION wouldn't match anyway, but the
    # ordering also documents the intent priority.
    (re.compile(r"^what\s+(?:causes|triggers|enables|prevents|drives|produces|induces|yields)\s+", re.IGNORECASE), IntentTag.CAUSE),
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
# Infinitive marker — stripped from DEFINITION / RECALL subjects so
# "What is to create?" extracts subject "create" rather than "to create".
# Only applied to verb-defining intents; other intents may carry "to" as
# a directional / transfer preposition where stripping would be wrong.
_INFINITIVE_MARKERS = frozenset({"to"})


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

    # For DEFINITION / RECALL, strip a leading to-infinitive marker so
    # "What is to create?" extracts "create" and grounds against the
    # pack lexicon (verb lemmas are stored bare, not as infinitives).
    if tag in (IntentTag.DEFINITION, IntentTag.RECALL):
        while tokens and tokens[0].lower() in _INFINITIVE_MARKERS:
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
        raw_subject = transitive_match.group("subject").strip()
        # "What does X mean?" is a definitional probe, not a transitive
        # relation query — there is no edge ``X --means--> Y`` to walk;
        # the user wants the definition of X.  Route to DEFINITION so
        # the pack-grounded surface dispatcher fires on X.
        if raw_relation in {"mean", "means"}:
            return DialogueIntent(
                tag=IntentTag.DEFINITION,
                subject=_normalize_subject(raw_subject, IntentTag.DEFINITION),
            )
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=raw_subject,
            relation=relation,
        )

    belong_match = _BELONG_QUERY_RE.match(text)
    if belong_match:
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=belong_match.group("subject").strip(),
            relation="belongs_to",
        )

    how_does_match = _HOW_DOES_X_RE.match(text)
    if how_does_match:
        return DialogueIntent(
            tag=IntentTag.CAUSE,
            subject=_normalize_subject(
                how_does_match.group("subject").strip(), IntentTag.CAUSE
            ),
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


# ---------------------------------------------------------------------------
# ResponseMode classification
# ---------------------------------------------------------------------------
#
# Sibling rule-based classifier for the presentation-depth axis.  Lives
# next to :func:`classify_intent` so the two share style and idioms but
# remain decoupled: callers compose ``(classify_intent(t),
# classify_response_mode(t))`` rather than threading a new field through
# the existing intent classifier.  This keeps the change additive — no
# DialogueIntent field added, no classify_intent branch altered.
#
# Patterns are ordered most-specific-first.  ``BRIEF`` is the default
# fallback when no presentation marker is present (e.g. "What is
# truth?"); existing single-sentence composer behavior corresponds to
# ``BRIEF``, so default-BRIEF preserves byte-identity when the discourse
# planner is wired up under a flag.

_RESPONSE_MODE_RULES: tuple[tuple[re.Pattern[str], "ResponseMode"], ...] = (
    # PARAGRAPH — explicit request for paragraph-shaped output.
    (
        re.compile(
            r"\b(?:write|compose|draft)\s+(?:a\s+)?(?:short\s+|brief\s+)?paragraph\b",
            re.IGNORECASE,
        ),
        ResponseMode.PARAGRAPH,
    ),
    (re.compile(r"^paragraph\s+(?:about|on)\s+", re.IGNORECASE), ResponseMode.PARAGRAPH),
    (re.compile(r"\bin\s+a\s+paragraph\b", re.IGNORECASE), ResponseMode.PARAGRAPH),
    # WALKTHROUGH — explicit step-by-step request.
    (re.compile(r"^walk\s+(?:me\s+)?through\s+", re.IGNORECASE), ResponseMode.WALKTHROUGH),
    (re.compile(r"\bstep\s*[-\s]?by\s*[-\s]?step\b", re.IGNORECASE), ResponseMode.WALKTHROUGH),
    # EXAMPLE — instance/example request (matches the same surface forms
    # as IntentTag.EXAMPLE; the two axes are orthogonal but agree here).
    (re.compile(r"^(?:give|show)\s+(?:me\s+)?an?\s+(?:example|instance)\s+of\s+", re.IGNORECASE), ResponseMode.EXAMPLE),
    (re.compile(r"^example\s+of\s+", re.IGNORECASE), ResponseMode.EXAMPLE),
    # EXPLAIN — open-ended elaboration request.  Includes "tell me about"
    # and "describe" because those surface forms expect more than a
    # single-sentence brief; the discourse planner uses this to select
    # a longer move sequence.
    (re.compile(r"^explain\s+", re.IGNORECASE), ResponseMode.EXPLAIN),
    (re.compile(r"^tell\s+me\s+(?:more\s+)?about\s+", re.IGNORECASE), ResponseMode.EXPLAIN),
    (re.compile(r"^describe\s+", re.IGNORECASE), ResponseMode.EXPLAIN),
    (
        re.compile(
            r"^what\s+(?:can|do)\s+you\s+(?:say|know)\s+about\s+",
            re.IGNORECASE,
        ),
        ResponseMode.EXPLAIN,
    ),
)


def classify_response_mode(prompt: str) -> ResponseMode:
    """Classify presentation depth from raw prompt text.

    Returns :attr:`ResponseMode.BRIEF` when no presentation marker is
    present.  Deterministic and pure — same input always produces the
    same output; no clock reads, no env reads, no I/O.
    """

    text = prompt.strip()
    if not text:
        return ResponseMode.BRIEF
    for pattern, mode in _RESPONSE_MODE_RULES:
        if pattern.search(text):
            return mode
    return ResponseMode.BRIEF

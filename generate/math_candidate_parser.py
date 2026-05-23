"""ADR-0126 — Candidate-emitting sentence parser.

Sibling to ``generate/math_parser.py``. Same regex spirit, different
topology: instead of first-match-wins with a single mutable state and
``ParseError`` on miss, each per-sentence extractor returns a *list of
candidates* (possibly empty) carrying full source-span provenance.

The wrong-answer firewall is :func:`generate.math_roundtrip.roundtrip_admissible`,
applied downstream in P3 (graph assembly). This module's job is purely
to *enumerate* the parses the grammar admits — telling truth from
falsehood is not its concern.

Determinism: candidate lists are returned in deterministic order
(canonical pattern key); the same input always produces the same
ordered output.

Scope of P2 (this module):
  - Initial-possession candidate extraction.
  - Operation candidate extraction for add / subtract / transfer
    via the canonical "<Subject> <verb> <value> <unit> [to <target>]"
    shape.
  - Permissive verb tables imported from
    :data:`generate.math_roundtrip.KIND_TO_VERBS` — much wider than
    ``math_parser._ADD_VERBS`` / ``_SUBTRACT_VERBS`` / ``_TRANSFER_VERBS``
    because the round-trip filter rejects wrong candidates downstream.

Out of scope for P2 (added in later phases):
  - Pronoun resolution (needs per-branch state — P3).
  - Unit inheritance from ``last_unit`` (needs per-branch state — P3).
  - Multiply / divide / rate / comparison candidates (later phases of
    ADR-0126; the candidate-emission machinery is identical, just more
    pattern matchers).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal, cast

from generate.math_problem_graph import (
    Comparison,
    InitialPossession,
    Operation,
    Quantity,
    Unknown,
)
from generate.math_roundtrip import (
    ADD_VERBS,
    SUBTRACT_VERBS,
    TRANSFER_VERBS,
    WORD_NUMBERS,
    CandidateOperation,
)


# Locally re-typed alias mirroring Comparison.direction's literal slot —
# used only to satisfy pyright when narrowing surface-direction strings.
_CompDirection = Literal["more", "fewer", "times", "fraction"]


# ---------------------------------------------------------------------------
# Initial-possession candidate
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateInitial:
    """Initial-possession candidate with source-span provenance.

    Mirrors :class:`CandidateOperation` but for ``InitialPossession``.
    The round-trip filter for initials is the same shape: every claimed
    content slot (entity, value, unit, anchor verb 'has'/'have') must
    ground in the source sentence.
    """

    initial: InitialPossession
    source_span: str
    matched_anchor: str       # 'has' or 'have'
    matched_value_token: str  # '3' or 'three'
    matched_unit_token: str
    matched_entity_token: str

    def __post_init__(self) -> None:
        # ADR-0127 widens the anchor set to include 'there are/were/is/was'
        # for the implicit-subject initial-possession shape.
        if self.matched_anchor.lower() not in ("has", "have", "are", "were", "is", "was"):
            raise ValueError(
                f"CandidateInitial.matched_anchor must be has/have/are/were/is/was; "
                f"got {self.matched_anchor!r}"
            )


# ---------------------------------------------------------------------------
# Shared regex building blocks
# ---------------------------------------------------------------------------

# Title-cased proper noun OR "the <noun>" collective. Same widening as
# math_parser._INITIAL_HAS_RE's ADR-0123a entity slot.
_ENTITY: Final[str] = r"(?:[A-Z]\w+|[Tt]he\s+\w+)"

# Numeric value: digit run OR word-form integer (one..twelve initially;
# WORD_NUMBERS table is wider but we cap the regex at the common range
# for syntactic parsing and let the filter handle ground-truth value
# equivalence).
_WORD_NUM_OPTIONS: Final[str] = "|".join(
    re.escape(w) for w in sorted(WORD_NUMBERS.keys(), key=len, reverse=True)
)
_VALUE: Final[str] = rf"(?:\d+|{_WORD_NUM_OPTIONS})"

# Verb alternation built from the permissive registry. Pre-compute one
# pattern per kind so we can attribute matched verbs to candidates.
def _verbs_pattern(verbs: frozenset[str]) -> str:
    # Longest-first so "passes" matches before "pass" inside the alternation.
    options = sorted(verbs, key=len, reverse=True)
    return r"(?:" + "|".join(re.escape(v) for v in options) + r")"


_ADD_VERBS_PATTERN: Final[str] = _verbs_pattern(ADD_VERBS)
_SUBTRACT_VERBS_PATTERN: Final[str] = _verbs_pattern(SUBTRACT_VERBS)
_TRANSFER_VERBS_PATTERN: Final[str] = _verbs_pattern(TRANSFER_VERBS)


# ---------------------------------------------------------------------------
# Initial-possession extractor
# ---------------------------------------------------------------------------

_INITIAL_HAS_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+"
    rf"(?P<anchor>has|have)\s+"
    rf"(?P<value>{_VALUE})\s+"
    r"(?P<unit>\w+)"
    # ADR-0127 substance qualifier: "Sam has 5 feet of rope" — the
    # 'of <NP>' tail is grammatically real but arithmetically inert.
    r"(?:\s+of\s+.+)?"
    r"\s*\.?$"
)

# ADR-0127 "There are/were N <unit> [in <place>]" initial-possession shape.
# The implicit-subject anchor 'there are' is the only initial-possession
# shape that doesn't name an entity in the source; we treat the
# place phrase (when present) as the entity and treat the unit as the
# count noun. When no place is named, the entity is the unit itself
# (collective). Indefinite quantifiers ('some', 'few', 'many') in the
# value slot are refused upstream by extract_initial_candidates via
# the quantifier-driven refusal helper (ADR-0128.4).
_INITIAL_THERE_ARE_RE: Final[re.Pattern[str]] = re.compile(
    r"^There\s+(?P<anchor>are|were|is|was)\s+"
    rf"(?P<value>{_VALUE})\s+"
    r"(?P<unit>\w+)"
    r"(?:\s+in\s+(?P<place>[A-Za-z]\w*(?:\s+\w+)?))?"
    r"\s*\.?$",
    flags=re.IGNORECASE,
)


def _normalize_entity(raw: str) -> str:
    """Collapse whitespace + lowercase article. Mirrors math_parser
    canonicalization so candidate entity names hash-equal to legacy."""
    e = re.sub(r"\s+", " ", raw.strip())
    if e.lower().startswith("the "):
        return "the " + e[4:]
    return e


def _resolve_value(value_token: str) -> int:
    if value_token.isdigit():
        return int(value_token)
    return WORD_NUMBERS[value_token.lower()]


def _is_indefinite_quantifier(token: str) -> bool:
    """ADR-0128.4 — quantifier-driven refusal helper.

    Returns True when ``token`` resolves (via en_numerics_v1 lookup) to
    an indefinite quantifier (``some``, ``many``, ``few``, ``several``,
    etc.). Indefinite quantifiers in value-slot positions are refused
    rather than guessed — preserves wrong == 0.
    """
    try:
        from language_packs.loader import lookup_quantifier
        entry = lookup_quantifier(token.lower())
        if entry is not None and entry.semantic_type == "indefinite":
            return True
    except Exception:
        pass
    return False


def extract_initial_candidates(sentence: str) -> list[CandidateInitial]:
    """Return all admissible initial-possession candidates for ``sentence``.

    Recognized shapes:
      1. "<Entity> has <N> <unit> [of <substance>]" — canonical.
      2. "There are <N> <unit> [in <place>]" — implicit-subject shape.

    ADR-0128.4: if the value slot resolves to an indefinite quantifier
    (`some kids`, `many things`), no candidate is emitted (refusal
    preserves wrong == 0).
    """
    s = sentence.strip().rstrip(".")
    out: list[CandidateInitial] = []

    m = _INITIAL_HAS_RE.match(s)
    if m is not None:
        value_raw = m.group("value")
        if not _is_indefinite_quantifier(value_raw):
            entity = _normalize_entity(m.group("entity"))
            value = _resolve_value(value_raw)
            unit_raw = m.group("unit")
            unit = _canonicalize_unit(unit_raw)
            out.append(
                CandidateInitial(
                    initial=InitialPossession(
                        entity=entity,
                        quantity=Quantity(value=value, unit=unit),
                    ),
                    source_span=sentence,
                    matched_anchor=m.group("anchor"),
                    matched_value_token=value_raw,
                    matched_unit_token=unit_raw,
                    matched_entity_token=m.group("entity"),
                )
            )

    m2 = _INITIAL_THERE_ARE_RE.match(s)
    if m2 is not None:
        value_raw = m2.group("value")
        if not _is_indefinite_quantifier(value_raw):
            unit_raw = m2.group("unit")
            unit = _canonicalize_unit(unit_raw)
            value = _resolve_value(value_raw)
            place = m2.group("place")
            # When a 'in <place>' phrase is present, treat the place as
            # the implicit entity. Otherwise use the unit's plural as
            # the collective entity name (deterministic, derivable from
            # the source: "There are 5 kids" -> entity='kids').
            if place is not None:
                entity = _normalize_entity(place)
                entity_token = place
            else:
                entity = unit
                entity_token = unit_raw
            out.append(
                CandidateInitial(
                    initial=InitialPossession(
                        entity=entity,
                        quantity=Quantity(value=value, unit=unit),
                    ),
                    source_span=sentence,
                    matched_anchor=m2.group("anchor"),
                    matched_value_token=value_raw,
                    matched_unit_token=unit_raw,
                    matched_entity_token=entity_token,
                )
            )

    return out


# ---------------------------------------------------------------------------
# Operation candidate extractor
# ---------------------------------------------------------------------------

# Per-kind operation patterns. Each captures: subject, verb, value, unit,
# optional target. The verb alternation is the kind's permissive verb table.
#
# Note: optional unit (?P<unit>) is allowed because some constructions
# rely on inherited unit ("Sam doubles his savings"); however for P2's
# scope we only emit candidates when the unit token is explicit. Inherited-
# unit candidates require per-branch state and are added in P3.

def _op_pattern(verbs_pattern: str, *, requires_target: bool) -> re.Pattern[str]:
    """Build the per-kind operation regex.

    For ``requires_target=True`` (transfer): the trailing ``to <Target>``
    clause is a captured slot.

    For ``requires_target=False`` (add/subtract): there is no target
    slot. A trailing ``to <noun>`` phrase, if present, is consumed as
    part of the discardable preposition tail so the regex still matches
    ambiguous sentences like "Sam gives 3 apples to Tom" (which we
    *do* want to match as a subtract candidate; the transfer-vs-subtract
    disambiguation happens at the candidate / filter / decision-rule
    layer, not by regex specificity).
    """
    if requires_target:
        target_part = r"\s+to\s+(?P<target>[A-Z]\w+)"
        trailing_prep = (
            r"(?:\s+(?:on|from|at|in|onto|into|under|over|of|for|with)\s+.+)?"
        )
    else:
        target_part = ""
        # 'to' is included in the discardable preposition set.
        # 'of' is included for ADR-0127 substance qualifiers ("1000 feet
        # of cable") — the substance NP is grammatically real but
        # arithmetically inert; the unit slot carries the dimensional info.
        trailing_prep = (
            r"(?:\s+(?:on|from|at|in|onto|into|under|over|to|of|for|with)\s+.+)?"
        )
    return re.compile(
        r"^"
        rf"(?P<subject>{_ENTITY})\s+"
        rf"(?P<verb>{verbs_pattern})"
        rf"\s+(?P<value>{_VALUE})"
        r"(?:\s+more)?"
        r"(?:\s+(?!to\b)(?!more\b)(?!on\b)(?!from\b)(?!at\b)(?!in\b)"
        r"(?P<unit>\w+))?"
        rf"{target_part}"
        rf"{trailing_prep}"
        r"\s*\.?$",
        flags=re.IGNORECASE,
    )


_ADD_OP_RE: Final[re.Pattern[str]] = _op_pattern(_ADD_VERBS_PATTERN, requires_target=False)
_SUBTRACT_OP_RE: Final[re.Pattern[str]] = _op_pattern(_SUBTRACT_VERBS_PATTERN, requires_target=False)
_TRANSFER_OP_RE: Final[re.Pattern[str]] = _op_pattern(_TRANSFER_VERBS_PATTERN, requires_target=True)


def _canonicalize_unit(unit_raw: str) -> str:
    """Canonicalize a unit surface token to its plural form.

    ADR-0127 integration: consult en_units_v1 first. If the token is a
    pack-recognized unit, use the pack's canonical plural form (handles
    irregular plurals like feet/feet, children, mice, etc. correctly).
    Otherwise fall back to the legacy '+s' rule for count nouns.
    """
    lowered = unit_raw.lower()
    try:
        from language_packs.loader import lookup_unit
        entry = lookup_unit(lowered)
        if entry is not None:
            return entry.plural.lower()
    except Exception:
        pass
    if not lowered.endswith("s"):
        return lowered + "s"
    return lowered


def _build_op_candidate(
    m: re.Match[str], kind: str, source: str
) -> CandidateOperation | None:
    """Build a CandidateOperation from a regex match. Returns None if
    the match lacks a required slot (e.g. unit token absent — P2 does
    not emit unit-inherited candidates)."""
    unit_raw = m.group("unit")
    if unit_raw is None:
        return None
    unit = _canonicalize_unit(unit_raw)
    subject = _normalize_entity(m.group("subject"))
    verb = m.group("verb").lower()
    value = _resolve_value(m.group("value"))
    target_raw = m.group("target") if "target" in m.groupdict() else None
    target = target_raw if target_raw is not None else None

    op_kwargs: dict[str, object] = {
        "actor": subject,
        "kind": kind,
        "operand": Quantity(value=value, unit=unit),
    }
    if kind == "transfer":
        if target is None:
            return None  # transfer requires target
        op_kwargs["target"] = target
    else:
        if target is not None:
            return None  # add/subtract don't take targets

    return CandidateOperation(
        op=Operation(**op_kwargs),  # type: ignore[arg-type]
        source_span=source,
        matched_verb=verb,
        matched_value_token=m.group("value"),
        matched_unit_token=unit_raw,
        matched_actor_token=m.group("subject"),
        matched_target_token=target,
    )


# ---------------------------------------------------------------------------
# Question candidate
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateUnknown:
    """Question-candidate with source-span provenance.

    Two question shapes in P3 scope:

    - ``How many <unit> does <Entity> have [left|now|in total|altogether]?``
      → ``Unknown(entity=<Entity>, unit=<unit>)``
    - ``How many <unit> do they have [left|now|in total|altogether]?``
      → ``Unknown(entity=None, unit=<unit>)`` (total-across)

    The round-trip filter for questions checks the unit token and (when
    present) the entity token both appear in the source span.
    """

    unknown: Unknown
    source_span: str
    matched_unit_token: str
    matched_entity_token: str | None  # None for total-across questions


_Q_ENTITY_RE: Final[re.Pattern[str]] = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+(?:does|do)\s+"
    rf"(?P<entity>{_ENTITY})"
    r"\s+have(?:\s+(?:left|now|in\s+total|altogether)){0,2}\s*\??$",
    flags=re.IGNORECASE,
)

_Q_TOTAL_RE: Final[re.Pattern[str]] = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+do\s+they\s+have"
    r"(?:\s+(?:in\s+total|altogether|left|now)){0,2}\s*\??$",
    flags=re.IGNORECASE,
)


def extract_question_candidates(sentence: str) -> list[CandidateUnknown]:
    """Return all admissible question candidates for ``sentence``.

    Tries the total-across pattern FIRST (same specificity order as
    legacy math_parser). The entity-pattern's widened regex would
    otherwise capture "they" as an entity name.

    Empty list if no shape matches.
    """
    s = sentence.strip()
    out: list[CandidateUnknown] = []

    m = _Q_TOTAL_RE.match(s)
    if m is not None:
        unit_raw = m.group("unit")
        unit = _canonicalize_unit(unit_raw)
        out.append(
            CandidateUnknown(
                unknown=Unknown(entity=None, unit=unit),
                source_span=sentence,
                matched_unit_token=unit_raw,
                matched_entity_token=None,
            )
        )
        return out  # specificity order: don't also try entity pattern

    m = _Q_ENTITY_RE.match(s)
    if m is not None:
        unit_raw = m.group("unit")
        unit = _canonicalize_unit(unit_raw)
        entity = _normalize_entity(m.group("entity"))
        out.append(
            CandidateUnknown(
                unknown=Unknown(entity=entity, unit=unit),
                source_span=sentence,
                matched_unit_token=unit_raw,
                matched_entity_token=m.group("entity"),
            )
        )

    return out


def extract_operation_candidates(sentence: str) -> list[CandidateOperation]:
    """Return all operation candidates for ``sentence``.

    Tries every verb-kind pattern independently. A sentence with an
    ambiguous verb (e.g. "Sam gives 3 apples to Tom" — "gives" appears
    in both SUBTRACT_VERBS and TRANSFER_VERBS) may emit multiple
    candidates. The round-trip filter
    (:func:`generate.math_roundtrip.roundtrip_admissible`) and the
    decision rule (P3) resolve which one becomes the chosen graph.

    Candidate emission order is canonical: add, subtract, transfer.
    Within each kind, the regex emits at most one candidate per
    sentence.
    """
    s = sentence.strip()
    out: list[CandidateOperation] = []

    for pattern, kind in (
        (_ADD_OP_RE, "add"),
        (_SUBTRACT_OP_RE, "subtract"),
        (_TRANSFER_OP_RE, "transfer"),
    ):
        m = pattern.match(s)
        if m is None:
            continue
        candidate = _build_op_candidate(m, kind, source=sentence)
        if candidate is not None:
            out.append(candidate)

    # ADR-0131.G.2 — comparative operations.
    # Specificity order: nested > multiplicative > additive. Multiplicative
    # anchors that overlap with additive ("twice" vs "two more") are disjoint
    # at the lexical level (WORD_NUMBERS has 'two' not 'twice'); nesting
    # consumes a *trailing* "than N times <REF>" tail so it cannot be confused
    # with the bare additive pattern. See ADR-0131.G.2 for precedence
    # rationale.
    out.extend(_compare_nested_candidates(sentence))
    out.extend(_compare_multiplicative_candidates(sentence))
    out.extend(_compare_additive_candidates(sentence))

    return out


# ---------------------------------------------------------------------------
# ADR-0131.G.2 — Comparative operation extractors
# ---------------------------------------------------------------------------
#
# Closed-set anchor alternation, aligned 1:1 with the four
# ``Comparison.direction`` literals registered in
# :data:`generate.math_roundtrip.COMPARE_ADDITIVE_ANCHORS` /
# :data:`COMPARE_MULTIPLICATIVE_ANCHORS`:
#
#   additive        — direction ∈ {more, fewer}; "less" admitted as a
#                     surface synonym mapped to direction='fewer'.
#                     ``matched_verb`` = the lowercased direction word
#                     ('more' / 'fewer' / 'less'); these are members of
#                     COMPARE_ADDITIVE_ANCHORS so the round-trip filter's
#                     verb-registry check (math_roundtrip step 1) passes.
#   multiplicative  — direction ∈ {times, fraction}; surface anchors are
#                     'twice' / 'thrice' / 'N times' / 'half'. The
#                     anchor-as-value-token convention from math_roundtrip
#                     step 4 lets word-form factor anchors skip
#                     value-grounding (the anchor's own appearance in
#                     the source already grounds the factor).
#
# Out of scope (refused by deliberate non-match): "as many … as" without
# a direction anchor, "compared to …", "in comparison with …",
# "the same … as". These have no entry in COMPARE_*_ANCHORS — admitting
# them would breach the round-trip filter's verb-registry check anyway.

# Comparative entity slot: proper-noun, "the X" collective, "the number/amount
# of <noun>" mass-noun construction. Possessives ("Bob's"/"his") are deferred.
_COMPARE_REF: Final[str] = (
    r"(?:"
    r"the\s+(?:number|amount)\s+of\s+\w+"
    r"|[Tt]he\s+\w+"
    r"|[A-Z]\w+"
    r")"
)


def _resolve_reference_token(raw: str) -> tuple[str, str]:
    """Return ``(canonical_entity, head_token_for_grounding)``.

    For "the number of chickens" the head token is "chickens"; the
    canonical entity uses the full noun-phrase so binding-graph
    referential-integrity isn't subverted by collapsing different
    references to the same noun.
    """
    collapsed = re.sub(r"\s+", " ", raw.strip())
    lowered = collapsed.lower()
    if lowered.startswith("the number of ") or lowered.startswith("the amount of "):
        head = collapsed.split()[-1]
        return collapsed, head
    if lowered.startswith("the "):
        head = collapsed[4:].split()[0]
        return "the " + collapsed[4:], head
    return collapsed, collapsed


def _comparison_anchor_verb() -> str:
    # 'has' / 'have' carry the comparator phrase. We don't include 'had/gets'
    # etc. in P2 — past-tense + lemma-widening are deferred to a later axis
    # to keep the precedence story narrow.
    return r"(?:has|have)"


_COMPARE_ADDITIVE_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>{_ENTITY})\s+{_comparison_anchor_verb()}\s+"
    rf"(?P<value>{_VALUE})\s+"
    r"(?P<direction>more|fewer|less)\s+"
    r"(?P<unit>\w+)\s+than\s+"
    rf"(?P<reference>{_COMPARE_REF})\s*\.?$"
)

# Multiplicative: anchor-as-value form ("twice"/"thrice"/"half" carry the
# factor implicitly). "as many <unit>" required; unit ellipsis ("twice as
# many as Bob") is deferred to keep wrong==0 strict — without unit the
# binding graph cannot disambiguate which dimension to compare.
_COMPARE_MULT_ANCHOR_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>{_ENTITY})\s+{_comparison_anchor_verb()}\s+"
    r"(?P<anchor>twice|thrice|half)\s+as\s+many\s+"
    r"(?P<unit>\w+)\s+as\s+"
    rf"(?P<reference>{_COMPARE_REF})\s*\.?$"
)

# Multiplicative: explicit "N times as many <unit> as <REF>".
_COMPARE_MULT_NTIMES_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>{_ENTITY})\s+{_comparison_anchor_verb()}\s+"
    rf"(?P<value>{_VALUE})\s+times\s+as\s+many\s+"
    r"(?P<unit>\w+)\s+as\s+"
    rf"(?P<reference>{_COMPARE_REF})\s*\.?$"
)

# Nested: additive over multiplicative — "A has N more <unit> than M times <REF>".
# Emits *two* flat candidates so the binding graph (ADR-0134) can decide which
# admissible composition (if any) survives. The parser does not commit to a
# nested operand shape (Comparison ∋ Comparison is not a supported operand
# type today); composition admissibility is the round-trip layer's call.
_COMPARE_NESTED_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>{_ENTITY})\s+{_comparison_anchor_verb()}\s+"
    rf"(?P<delta_value>{_VALUE})\s+"
    r"(?P<direction>more|fewer|less)\s+"
    r"(?P<unit>\w+)\s+than\s+"
    rf"(?P<factor_value>{_VALUE})\s+times\s+"
    rf"(?P<reference>{_COMPARE_REF})\s*\.?$"
)


_ANCHOR_TO_FACTOR: Final[dict[str, tuple[float, str]]] = {
    # surface anchor → (factor, direction-literal)
    "twice": (2.0, "times"),
    "thrice": (3.0, "times"),
    "half": (0.5, "fraction"),
}


def _direction_to_anchor(direction_raw: str) -> tuple[str, str]:
    """Map surface direction word → (canonical Comparison.direction,
    matched_verb registered in COMPARE_ADDITIVE_ANCHORS).

    'less' is a surface synonym of 'fewer'; the Comparison value uses
    direction='fewer', but matched_verb retains the source surface
    ('less') so the round-trip filter's "verb appears in source" check
    succeeds. 'less' is registered in COMPARE_ADDITIVE_ANCHORS, so the
    verb-registry check also succeeds.
    """
    lowered = direction_raw.lower()
    if lowered in ("more", "fewer"):
        return lowered, lowered
    if lowered == "less":
        return "fewer", "less"
    raise ValueError(f"unknown comparative direction surface {direction_raw!r}")


def _build_compare_additive(
    *,
    actor_raw: str,
    delta_value_raw: str,
    direction_raw: str,
    unit_raw: str,
    reference_raw: str,
    source: str,
) -> CandidateOperation | None:
    if _is_indefinite_quantifier(delta_value_raw):
        return None
    direction, matched_verb = _direction_to_anchor(direction_raw)
    actor = _normalize_entity(actor_raw)
    reference_canon, reference_head = _resolve_reference_token(reference_raw)
    if reference_canon == actor:
        return None  # self-reference; constructor would refuse anyway
    delta_value = _resolve_value(delta_value_raw)
    unit = _canonicalize_unit(unit_raw)
    try:
        op = Operation(
            actor=actor,
            kind="compare_additive",
            operand=Comparison(
                reference_actor=reference_canon,
                delta=Quantity(value=delta_value, unit=unit),
                factor=None,
                direction=cast(_CompDirection, direction),
            ),
        )
    except Exception:
        return None
    try:
        return CandidateOperation(
            op=op,
            source_span=source,
            matched_verb=matched_verb,
            matched_value_token=delta_value_raw,
            matched_unit_token=unit_raw,
            matched_actor_token=actor_raw,
            matched_reference_actor_token=reference_head,
        )
    except Exception:
        return None


def _build_compare_multiplicative(
    *,
    actor_raw: str,
    factor: float,
    matched_verb: str,
    matched_value_token: str,
    unit_raw: str,
    reference_raw: str,
    source: str,
    direction: str,
) -> CandidateOperation | None:
    actor = _normalize_entity(actor_raw)
    reference_canon, reference_head = _resolve_reference_token(reference_raw)
    if reference_canon == actor:
        return None
    _ = _canonicalize_unit(unit_raw)  # validation only; multiplicative compares
    # carry the unit on the source-span side, not the operand
    try:
        op = Operation(
            actor=actor,
            kind="compare_multiplicative",
            operand=Comparison(
                reference_actor=reference_canon,
                delta=None,
                factor=factor,
                direction=cast(_CompDirection, direction),
            ),
        )
    except Exception:
        return None
    try:
        return CandidateOperation(
            op=op,
            source_span=source,
            matched_verb=matched_verb,
            matched_value_token=matched_value_token,
            matched_unit_token=unit_raw,
            matched_actor_token=actor_raw,
            matched_reference_actor_token=reference_head,
        )
    except Exception:
        return None


def _compare_additive_candidates(sentence: str) -> list[CandidateOperation]:
    s = sentence.strip()
    m = _COMPARE_ADDITIVE_RE.match(s)
    if m is None:
        return []
    cand = _build_compare_additive(
        actor_raw=m.group("actor"),
        delta_value_raw=m.group("value"),
        direction_raw=m.group("direction"),
        unit_raw=m.group("unit"),
        reference_raw=m.group("reference"),
        source=sentence,
    )
    return [cand] if cand is not None else []


def _compare_multiplicative_candidates(sentence: str) -> list[CandidateOperation]:
    s = sentence.strip()
    out: list[CandidateOperation] = []

    m = _COMPARE_MULT_ANCHOR_RE.match(s)
    if m is not None:
        anchor = m.group("anchor").lower()
        factor, direction = _ANCHOR_TO_FACTOR[anchor]
        cand = _build_compare_multiplicative(
            actor_raw=m.group("actor"),
            factor=factor,
            matched_verb=anchor,
            matched_value_token=anchor,  # anchor-as-value (math_roundtrip step 4)
            unit_raw=m.group("unit"),
            reference_raw=m.group("reference"),
            source=sentence,
            direction=direction,
        )
        if cand is not None:
            out.append(cand)
        return out  # specificity — don't also try N-times pattern

    m = _COMPARE_MULT_NTIMES_RE.match(s)
    if m is not None:
        value_raw = m.group("value")
        if _is_indefinite_quantifier(value_raw):
            return out
        try:
            factor = float(_resolve_value(value_raw))
        except KeyError:
            return out
        cand = _build_compare_multiplicative(
            actor_raw=m.group("actor"),
            factor=factor,
            matched_verb="times",
            matched_value_token=value_raw,
            unit_raw=m.group("unit"),
            reference_raw=m.group("reference"),
            source=sentence,
            direction="times",
        )
        if cand is not None:
            out.append(cand)
    return out


def _compare_nested_candidates(sentence: str) -> list[CandidateOperation]:
    """Emit two flat candidates for nested 'N more <unit> than M times <REF>'.

    The parser does not commit to a composed Comparison-of-Comparison
    operand (operand type Comparison ∋ Comparison is not modelled
    today). Both flat candidates are forwarded; the binding-graph /
    round-trip layer (ADR-0134) picks an admissible composition or
    refuses. Refusal is the safe outcome — never a wrong answer.
    """
    s = sentence.strip()
    m = _COMPARE_NESTED_RE.match(s)
    if m is None:
        return []
    out: list[CandidateOperation] = []

    actor_raw = m.group("actor")
    unit_raw = m.group("unit")
    reference_raw = m.group("reference")

    # Candidate 1: additive — "A has N more <unit> than <REF>" treating
    # <REF> as the comparison reference directly. The "M times" multiplier
    # is dropped on this candidate (the binding-graph composition is
    # what would re-introduce it).
    add_cand = _build_compare_additive(
        actor_raw=actor_raw,
        delta_value_raw=m.group("delta_value"),
        direction_raw=m.group("direction"),
        unit_raw=unit_raw,
        reference_raw=reference_raw,
        source=sentence,
    )
    if add_cand is not None:
        out.append(add_cand)

    # Candidate 2: multiplicative — "A has M times as many <unit> as <REF>"
    # treating the multiplier M and the same <REF> as the multiplicative
    # comparison. The additive offset N is dropped on this candidate.
    factor_value_raw = m.group("factor_value")
    if not _is_indefinite_quantifier(factor_value_raw):
        try:
            factor = float(_resolve_value(factor_value_raw))
        except KeyError:
            factor = None
        if factor is not None:
            mult_cand = _build_compare_multiplicative(
                actor_raw=actor_raw,
                factor=factor,
                matched_verb="times",
                matched_value_token=factor_value_raw,
                unit_raw=unit_raw,
                reference_raw=reference_raw,
                source=sentence,
                direction="times",
            )
            if mult_cand is not None:
                out.append(mult_cand)

    return out

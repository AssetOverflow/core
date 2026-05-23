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
from typing import Final

from generate.math_problem_graph import (
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
        # ADR-0131.G.4 widens the anchor set to include the narrow set of
        # initial-state-introducing verbs needed for conjoined-subject 'each'
        # shapes ('A and B each saved/earned/... N <unit>'). See
        # _CONJ_SUBJECT_VERBS for the closed set.
        if self.matched_anchor.lower() not in (
            "has", "have", "had",
            "are", "were", "is", "was",
            "save", "saved",
            "earn", "earned",
            "get", "got", "gets",
            "receive", "received", "receives",
            "buy", "bought", "buys",
            "make", "made", "makes",
            "pay", "paid", "pays",
        ):
            raise ValueError(
                f"CandidateInitial.matched_anchor must be a registered initial-"
                f"state anchor; got {self.matched_anchor!r}"
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

    # ADR-0131.G.4 — multi-clause initial-state extractors.
    # Each may emit ≥1 candidates; deterministic order: conjoined-subject-each,
    # conjoined-object, embedded-quantifier, conjoined-embedded-quantifier.
    # See module-bottom for shape definitions and closed-set discipline.
    out.extend(_conj_subject_each_candidates(sentence))
    out.extend(_conj_object_candidates(sentence))
    out.extend(_embedded_quantifier_candidates(sentence))

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

    return out


# ---------------------------------------------------------------------------
# ADR-0131.G.4 — Multi-clause initial-state composition
# ---------------------------------------------------------------------------
#
# Closed shape set. Every recognized multi-clause structure matches exactly
# one of the four extractors below. Cross-sentence coreference, ellipsis,
# three-way+ conjunctions, and collective `each` readings are deliberately
# refused (no extractor matches them).
#
# Why initials, not operations: the GSM8K shapes targeted here introduce
# starting state ('Aaron and Carson each saved $40', 'Francine has five
# full boxes and 5 loose crayons', 'Ella has 4 bags with 20 apples in each
# bag'). They are not state-mutating events. Emitting CandidateInitial
# preserves the conventional initial-state-vs-operation split the solver
# (math_solver.py) expects.

# Anchor verbs allowed in conjoined-subject-each constructions. Surface
# verb is mapped to a single canonical anchor token (e.g. 'saved up' →
# matched_anchor='saved'). The CandidateInitial constructor whitelists
# these via the ADR-0131.G.4 widening.
_CONJ_SUBJECT_VERBS: Final[tuple[str, ...]] = (
    "has", "have", "had",
    "saved", "earned", "got", "received", "bought", "made", "paid",
)
_CONJ_SUBJECT_VERBS_PATTERN: Final[str] = (
    r"(?:" + "|".join(_CONJ_SUBJECT_VERBS) + r")"
)

# Optional "and his/her/their brother/sister/friend/cousin" appositive
# between the two conjuncts. Captures the appositive's head noun as part
# of the second entity; we still ground on the proper noun that follows.
_CONJ_KIN_GLUE: Final[str] = (
    r"(?:(?:his|her|their)\s+(?:brother|sister|friend|cousin)\s+)?"
)

# Conjoined-subject "each" — distributive only. The trailing "to <infin>"
# / "for <NP>" / "of <NP>" tail is consumed and discarded (arithmetically
# inert; cf. ADR-0127 substance qualifier).
_CONJ_SUBJECT_EACH_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<a>{_ENTITY})\s+and\s+{_CONJ_KIN_GLUE}"
    rf"(?P<b>{_ENTITY})\s+each\s+"
    rf"(?P<verb>{_CONJ_SUBJECT_VERBS_PATTERN})(?:\s+up)?\s+"
    rf"(?P<value>{_VALUE})\s+"
    r"(?P<unit>\w+)"
    r"(?:\s+(?:of|in|for|to|from|with|on|at)\s+.+)?"
    r"\s*\.?$",
    flags=re.IGNORECASE,
)

# Conjoined-object NPs sharing a verb. The two units may differ
# ('5 boxes and 7 marbles') — the binding graph keeps the per-unit
# states independent. Same-unit conjuncts (rare) collapse into a
# single state slot via the solver's state[(entity,unit)] overwrite,
# which is a known limitation — we refuse same-unit conjuncts to avoid
# silently losing the first conjunct's value.
_CONJ_OBJECT_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+(?P<anchor>has|have|had)\s+"
    rf"(?P<v1>{_VALUE})\s+(?P<u1>\w+)"
    r"(?:\s+(?:full|loose|empty|whole|broken|new|old|small|large))?"
    r"(?:\s+of\s+\w+)?"
    rf"\s+and\s+(?P<v2>{_VALUE})\s+(?P<u2>\w+)"
    r"(?:\s+(?:full|loose|empty|whole|broken|new|old|small|large))?"
    r"(?:\s+of\s+\w+)?"
    r"\s*\.?$",
    flags=re.IGNORECASE,
)

# Embedded quantifier: "N <container> with M <unit> in each [<container>]".
# Optional second mention of the container after 'each' (the natural-
# language redundancy in the brief's Ella example).
_EMBEDDED_QUANTIFIER_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+(?P<anchor>has|have|had)\s+"
    rf"(?P<n>{_VALUE})\s+(?P<container>\w+)\s+with\s+"
    rf"(?P<m>{_VALUE})\s+(?P<unit>\w+)\s+in\s+each"
    r"(?:\s+(?P<container2>\w+))?"
    r"\s*\.?$",
    flags=re.IGNORECASE,
)

# Conjoined embedded quantifiers — both halves match the embedded shape.
# Emits a single SUM candidate (value = N1*M1 + N2*M2) — emitting two
# derived candidates with the same (entity, unit) is unsafe under the
# solver's overwrite-on-collision semantics (math_solver.py:206; would
# silently drop the first conjunct's value). Same-unit summation is the
# admissible interpretation; mismatched units refuse.
_CONJ_EMBEDDED_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+(?P<anchor>has|have|had)\s+"
    rf"(?P<n1>{_VALUE})\s+(?P<c1>\w+)\s+with\s+(?P<m1>{_VALUE})\s+(?P<u1>\w+)"
    r"\s+in\s+each(?:\s+\w+)?\s+and\s+"
    rf"(?P<n2>{_VALUE})\s+(?P<c2>\w+)\s+with\s+(?P<m2>{_VALUE})\s+(?P<u2>\w+)"
    r"\s+in\s+each(?:\s+\w+)?"
    r"\s*\.?$",
    flags=re.IGNORECASE,
)


def _canon_verb_to_anchor(verb: str) -> str:
    """Map surface verb to its canonical CandidateInitial anchor token.

    The constructor whitelist is keyed on lowercase singular-or-past
    tokens; we lowercase + strip particle ('saved up' was already
    stripped of 'up' by the regex's separate slot)."""
    return verb.lower()


def _conj_subject_each_candidates(sentence: str) -> list[CandidateInitial]:
    """Distributive `each` only. Collective readings refuse by not
    matching (no 'each' in the surface)."""
    s = sentence.strip().rstrip(".")
    m = _CONJ_SUBJECT_EACH_RE.match(s)
    if m is None:
        return []
    value_raw = m.group("value")
    if _is_indefinite_quantifier(value_raw):
        return []
    # Adversarial probe: 'each ... together' is a contradiction; refuse.
    # Captured in test_refuses_each_with_together.
    if re.search(r"\btogether\b|\bin total\b|\baltogether\b", s, re.IGNORECASE):
        return []
    entity_a = _normalize_entity(m.group("a"))
    entity_b = _normalize_entity(m.group("b"))
    if entity_a == entity_b:
        return []  # 'Aaron and Aaron each ...' is degenerate
    value = _resolve_value(value_raw)
    unit_raw = m.group("unit")
    unit = _canonicalize_unit(unit_raw)
    anchor = _canon_verb_to_anchor(m.group("verb"))
    out: list[CandidateInitial] = []
    for entity, entity_raw in ((entity_a, m.group("a")), (entity_b, m.group("b"))):
        try:
            out.append(
                CandidateInitial(
                    initial=InitialPossession(
                        entity=entity,
                        quantity=Quantity(value=value, unit=unit),
                    ),
                    source_span=sentence,
                    matched_anchor=anchor,
                    matched_value_token=value_raw,
                    matched_unit_token=unit_raw,
                    matched_entity_token=entity_raw,
                )
            )
        except Exception:
            return []  # all-or-nothing emission
    return out


def _conj_object_candidates(sentence: str) -> list[CandidateInitial]:
    """Conjoined object NPs sharing a verb. Same-unit conjuncts refused
    (cannot safely compose under solver's overwrite-on-collision)."""
    s = sentence.strip().rstrip(".")
    m = _CONJ_OBJECT_RE.match(s)
    if m is None:
        return []
    v1_raw, v2_raw = m.group("v1"), m.group("v2")
    if _is_indefinite_quantifier(v1_raw) or _is_indefinite_quantifier(v2_raw):
        return []
    u1_raw, u2_raw = m.group("u1"), m.group("u2")
    u1 = _canonicalize_unit(u1_raw)
    u2 = _canonicalize_unit(u2_raw)
    if u1 == u2:
        # Same-unit conjuncts would silently collide under the solver's
        # state[(entity,unit)] overwrite. Refuse rather than guess.
        return []
    entity = _normalize_entity(m.group("entity"))
    anchor = m.group("anchor").lower()
    out: list[CandidateInitial] = []
    for value_raw, unit_raw, unit in (
        (v1_raw, u1_raw, u1),
        (v2_raw, u2_raw, u2),
    ):
        try:
            out.append(
                CandidateInitial(
                    initial=InitialPossession(
                        entity=entity,
                        quantity=Quantity(value=_resolve_value(value_raw), unit=unit),
                    ),
                    source_span=sentence,
                    matched_anchor=anchor,
                    matched_value_token=value_raw,
                    matched_unit_token=unit_raw,
                    matched_entity_token=m.group("entity"),
                )
            )
        except Exception:
            return []
    return out


def _embedded_quantifier_candidates(sentence: str) -> list[CandidateInitial]:
    """Embedded quantifier 'N <container> with M <unit> in each' →
    derived InitialPossession(value=N*M, unit=<unit>). Also handles the
    conjoined-embedded shape via _CONJ_EMBEDDED_RE (single SUM
    candidate; same-unit only)."""
    s = sentence.strip().rstrip(".")

    # Try conjoined-embedded first (most specific).
    m = _CONJ_EMBEDDED_RE.match(s)
    if m is not None:
        return _build_conj_embedded_sum(m, sentence)

    m = _EMBEDDED_QUANTIFIER_RE.match(s)
    if m is None:
        return []
    n_raw, m_raw = m.group("n"), m.group("m")
    if _is_indefinite_quantifier(n_raw) or _is_indefinite_quantifier(m_raw):
        return []
    container = m.group("container").lower()
    container2_raw = m.group("container2")
    if container2_raw is not None:
        # 'with M unit in each <container2>' — container2 (if named)
        # must agree with the leading container; otherwise the scope of
        # 'each' is ambiguous and we refuse.
        c2 = container2_raw.lower()
        if c2 not in (container, container.rstrip("s"), container + "s"):
            return []
    n = _resolve_value(n_raw)
    per = _resolve_value(m_raw)
    total = n * per
    entity = _normalize_entity(m.group("entity"))
    unit_raw = m.group("unit")
    unit = _canonicalize_unit(unit_raw)
    try:
        return [
            CandidateInitial(
                initial=InitialPossession(
                    entity=entity,
                    quantity=Quantity(value=total, unit=unit),
                ),
                source_span=sentence,
                matched_anchor=m.group("anchor").lower(),
                # Provenance: anchor on the per-container value token (M).
                # The product N*M is a parser-committed derivation; the
                # source-token check passes on M's surface form.
                matched_value_token=m_raw,
                matched_unit_token=unit_raw,
                matched_entity_token=m.group("entity"),
            )
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Per-shape admitted-only wrappers (used by the G4 runner).
# Each filters its extractor's output through _initial_admissible from
# math_candidate_graph so the runner sees only round-trip-admissible
# candidates without re-implementing the check.
# ---------------------------------------------------------------------------

def _admit(cands: list[CandidateInitial]) -> list[CandidateInitial]:
    from generate.math_candidate_graph import _initial_admissible
    return [c for c in cands if _initial_admissible(c)]


def _conj_subject_each_admitted(sentence: str) -> list[CandidateInitial]:
    return _admit(_conj_subject_each_candidates(sentence))


def _conj_object_admitted(sentence: str) -> list[CandidateInitial]:
    return _admit(_conj_object_candidates(sentence))


def _embedded_quantifier_admitted(sentence: str) -> list[CandidateInitial]:
    # _embedded_quantifier_candidates dispatches to _CONJ_EMBEDDED_RE
    # *first*, so this wrapper returns the single-embedded candidate
    # only when the conjoined shape doesn't match. To distinguish,
    # callers that care about the conjoined branch use
    # _conj_embedded_admitted below.
    s = sentence.strip().rstrip(".")
    if _CONJ_EMBEDDED_RE.match(s) is not None:
        return []
    return _admit(_embedded_quantifier_candidates(sentence))


def _conj_embedded_admitted(sentence: str) -> list[CandidateInitial]:
    s = sentence.strip().rstrip(".")
    if _CONJ_EMBEDDED_RE.match(s) is None:
        return []
    return _admit(_embedded_quantifier_candidates(sentence))


def _build_conj_embedded_sum(
    m: re.Match[str], sentence: str
) -> list[CandidateInitial]:
    """Single SUM candidate for conjoined-embedded 'N1 C with M1 U in
    each and N2 C with M2 U in each'."""
    n1_raw, m1_raw = m.group("n1"), m.group("m1")
    n2_raw, m2_raw = m.group("n2"), m.group("m2")
    for raw in (n1_raw, m1_raw, n2_raw, m2_raw):
        if _is_indefinite_quantifier(raw):
            return []
    u1 = _canonicalize_unit(m.group("u1"))
    u2 = _canonicalize_unit(m.group("u2"))
    if u1 != u2:
        # Mixed-unit sum is meaningless; refuse.
        return []
    total = _resolve_value(n1_raw) * _resolve_value(m1_raw) + (
        _resolve_value(n2_raw) * _resolve_value(m2_raw)
    )
    entity = _normalize_entity(m.group("entity"))
    try:
        return [
            CandidateInitial(
                initial=InitialPossession(
                    entity=entity,
                    quantity=Quantity(value=total, unit=u1),
                ),
                source_span=sentence,
                matched_anchor=m.group("anchor").lower(),
                matched_value_token=m1_raw,  # provenance: first per-container M
                matched_unit_token=m.group("u1"),
                matched_entity_token=m.group("entity"),
            )
        ]
    except Exception:
        return []

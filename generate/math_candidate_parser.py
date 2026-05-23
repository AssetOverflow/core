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

# Numeric value alternation. Listed longest-form-first so the regex
# engine doesn't truncate on a shorter prefix:
#   - Money symbol literal: ``$N`` or ``$N.NN`` (1-2 decimal places).
#     ADR-0131.G.3. ``$N.NNN`` (3+ decimals) deliberately not matched
#     — refused as out-of-scope so wrong == 0 is preserved.
#   - Slash fraction literal: ``N/M``. Denominator-zero refused at
#     resolve time, not regex.
#   - Hyphenated multi-word cardinal: ``twenty-five``, ``ninety-nine``.
#     Resolved via :func:`language_packs.numerics_loader.parse_compound_cardinal`.
#   - Digit run.
#   - Single-word cardinal (legacy ``WORD_NUMBERS`` set).
_MONEY_SYMBOL: Final[str] = r"\$\d+(?:\.\d{1,2})?"
_SLASH_FRACTION: Final[str] = r"\d+/\d+"
_HYPHENATED_CARDINAL: Final[str] = r"[A-Za-z]+-[A-Za-z]+"
_WORD_NUM_OPTIONS: Final[str] = "|".join(
    re.escape(w) for w in sorted(WORD_NUMBERS.keys(), key=len, reverse=True)
)
_VALUE: Final[str] = (
    rf"(?:{_MONEY_SYMBOL}|{_SLASH_FRACTION}|"
    rf"{_HYPHENATED_CARDINAL}|"
    rf"\d+|{_WORD_NUM_OPTIONS})"
)

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
    rf"(?P<value>{_VALUE})"
    # ADR-0131.G.3: unit slot is optional. Money-symbol value literals
    # (``$40``) carry their unit implicitly (``cent``); a missing unit
    # slot is admissible IFF the value resolves with a unit override.
    # Non-money values without a unit slot are refused at resolve time.
    r"(?:\s+(?P<unit>\w+))?"
    # ADR-0127 substance qualifier: "Sam has 5 feet of rope" — the
    # 'of <NP>' tail is grammatically real but arithmetically inert.
    # ADR-0131.G.3: 'in <NP>' is also discardable
    # ("Bob has $40 in savings"; "Bob has $40 in his wallet").
    r"(?:\s+(?:of|in|for|with)\s+.+)?"
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


@dataclass(frozen=True, slots=True)
class _ResolvedValue:
    """Resolved value-slot reading.

    ADR-0131.G.3 widens the value slot beyond integer + single-word
    cardinal to include money literals (``$N`` / ``$N.NN``), slash
    fractions (``N/M``), and hyphenated multi-word cardinals
    (``twenty-five``). Money literals carry an implicit canonical unit
    (``cent``); when set, ``unit_override`` replaces the unit slot the
    regex captured (or fills it when the unit slot is absent).
    """

    value: int | float
    unit_override: str | None


# Money: canonical normalization to integer cents (en_units_v1
# ``canonical_unit`` for the ``money`` dimension is ``cent``).
_MONEY_UNIT: Final[str] = "cents"


def _resolve_value(value_token: str) -> _ResolvedValue | None:
    """Resolve a value-slot token into a numeric value + optional unit
    override. Returns ``None`` on refusal (indefinite quantifier,
    division-by-zero in slash fraction, unrecognized hyphenated form,
    unparseable money).

    Refusal at this layer is first-class: a ``None`` upstream means the
    candidate is not emitted, which preserves ``wrong == 0`` per
    ADR-0114a Obligation #4.
    """
    if not value_token:
        return None
    t = value_token.strip()
    # Money symbol literal: $N or $N.NN.
    if t.startswith("$"):
        body = t[1:]
        if re.fullmatch(r"\d+", body):
            return _ResolvedValue(int(body) * 100, _MONEY_UNIT)
        if re.fullmatch(r"\d+\.\d{1,2}", body):
            # round() avoids float drift: $2.50 → 250, not 249 or 251.
            return _ResolvedValue(int(round(float(body) * 100)), _MONEY_UNIT)
        return None  # $N.NNN (3+ decimals) refused — out-of-scope.
    # Slash fraction literal: N/M with M > 0.
    if "/" in t:
        m = re.fullmatch(r"(\d+)/(\d+)", t)
        if m is None:
            return None
        num, den = int(m.group(1)), int(m.group(2))
        if den == 0:
            return None  # division-by-zero refused.
        if num % den == 0:
            return _ResolvedValue(num // den, None)
        return _ResolvedValue(num / den, None)
    # Digit run.
    if t.isdigit():
        return _ResolvedValue(int(t), None)
    # Indefinite quantifier (ADR-0128.4) — refuse, never guess.
    if _is_indefinite_quantifier(t):
        return None
    # Hyphenated multi-word cardinal: twenty-five, ninety-nine, etc.
    if "-" in t:
        from language_packs.numerics_loader import parse_compound_cardinal

        parsed = parse_compound_cardinal(t)
        if parsed is None:
            return None  # Unrecognized hyphenated form refused.
        return _ResolvedValue(parsed, None)
    # Single-word cardinal (legacy WORD_NUMBERS table).
    lower = t.lower()
    if lower in WORD_NUMBERS:
        return _ResolvedValue(WORD_NUMBERS[lower], None)
    return None


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


def _money_unit_normalization(
    value: int | float, unit: str | None
) -> tuple[int | float, str | None]:
    """ADR-0131.G.3 — normalize ``dollar``/``dollars`` surface unit to the
    canonical money unit (``cent``).

    ``en_units_v1`` pins ``cent`` as ``canonical_unit`` for the ``money``
    dimension; ``dollar`` is convenience surface. A ``dollar`` value is
    100 ``cent``. Done at the candidate-build site so every money-bearing
    path normalizes uniformly (Quantity equality is exact — mixing
    ``cent`` and ``dollar`` units would silently break arithmetic).
    """
    if unit is None:
        return value, unit
    if unit.lower() in ("dollar", "dollars"):
        return value * 100, _MONEY_UNIT
    return value, unit


def extract_initial_candidates(sentence: str) -> list[CandidateInitial]:
    """Return all admissible initial-possession candidates for ``sentence``.

    Recognized shapes:
      1. "<Entity> has <N> <unit> [of <substance>]" — canonical.
      2. "There are <N> <unit> [in <place>]" — implicit-subject shape.

    Value-slot widenings (ADR-0131.G.3) apply to both shapes via
    :func:`_resolve_value`: money literals (``$N`` / ``$N.NN``), slash
    fractions (``N/M``), hyphenated multi-word cardinals (``twenty-five``).

    Refusal-first: indefinite quantifiers, division-by-zero fractions,
    unrecognized compound forms, and money literals with >2 decimals
    all return ``None`` from :func:`_resolve_value` and emit no
    candidate (preserves ``wrong == 0`` per ADR-0114a Obligation #4).
    """
    s = sentence.strip().rstrip(".")
    out: list[CandidateInitial] = []

    m = _INITIAL_HAS_RE.match(s)
    if m is not None:
        value_raw = m.group("value")
        rv = _resolve_value(value_raw)
        if rv is not None:
            entity = _normalize_entity(m.group("entity"))
            unit_raw = m.group("unit")  # may be None when value is money symbol
            # Unit precedence: explicit override from value (money symbol)
            # wins over the regex's unit slot. The unit slot is required
            # for non-money values; if both are absent the candidate
            # cannot be constructed.
            resolved_unit: str | None
            if rv.unit_override is not None:
                resolved_unit = rv.unit_override
            elif unit_raw is not None:
                resolved_unit = _canonicalize_unit(unit_raw)
            else:
                resolved_unit = None
            if resolved_unit is not None:
                value, final_unit = _money_unit_normalization(rv.value, resolved_unit)
                assert final_unit is not None
                out.append(
                    CandidateInitial(
                        initial=InitialPossession(
                            entity=entity,
                            quantity=Quantity(value=value, unit=final_unit),
                        ),
                        source_span=sentence,
                        matched_anchor=m.group("anchor"),
                        matched_value_token=value_raw,
                        matched_unit_token=unit_raw if unit_raw is not None else final_unit,
                        matched_entity_token=m.group("entity"),
                    )
                )

    m2 = _INITIAL_THERE_ARE_RE.match(s)
    if m2 is not None:
        value_raw = m2.group("value")
        rv = _resolve_value(value_raw)
        if rv is not None:
            unit_raw = m2.group("unit")
            assert unit_raw is not None  # there-are regex always captures unit slot
            if rv.unit_override is not None:
                unit_str: str = rv.unit_override
            else:
                unit_str = _canonicalize_unit(unit_raw)
            v_norm, u_norm = _money_unit_normalization(rv.value, unit_str)
            assert u_norm is not None
            value: int | float = v_norm
            unit: str = u_norm
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
    the value cannot be resolved or if no unit can be determined
    (unit slot absent AND value carries no implicit unit override).
    """
    value_raw = m.group("value")
    rv = _resolve_value(value_raw)
    if rv is None:
        return None
    unit_raw = m.group("unit")
    # ADR-0131.G.3: a money-symbol value carries its unit implicitly
    # (override 'cent'); for plain-numeric values, the unit slot must
    # be present.
    if rv.unit_override is not None:
        unit: str = rv.unit_override
    elif unit_raw is not None:
        unit = _canonicalize_unit(unit_raw)
    else:
        return None  # P2 does not emit unit-inherited candidates.
    subject = _normalize_entity(m.group("subject"))
    verb = m.group("verb").lower()
    value, unit_normalized = _money_unit_normalization(rv.value, unit)
    assert unit_normalized is not None
    unit = unit_normalized
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
        matched_unit_token=unit_raw if unit_raw is not None else unit,
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

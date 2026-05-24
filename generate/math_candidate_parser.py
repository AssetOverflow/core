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
        #
        # ADR-0131.G.1: _INITIAL_HAS_RE itself only emits has/have/had/started
        # — acquisition verbs (buys, bought, sells, collected, saved, makes)
        # live exclusively in ADD_VERBS / SUBTRACT_VERBS so a sentence like
        # "Sam buys 3 apples" parses as an add-operation only, avoiding
        # branch-disagreement when a canonical "has" initial precedes it.
        #
        # ADR-0131.G.4 introduces a separate conjoined-subject-each extractor
        # that legitimately emits CandidateInitial with a wider set of
        # state-introducing verbs (saved/earned/got/received/bought/made/paid +
        # inflections) for the closed shape "A and B each <verb> N <unit>".
        # That extractor is the only path into these wider anchors. The
        # whitelist below is the runtime safety net for both paths.
        if self.matched_anchor.lower() not in (
            "has", "have", "had", "started",
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

# Numeric value alternation. Listed longest-form-first so the regex
# engine doesn't truncate on a shorter prefix:
#   - Money symbol literal: ``$N`` / ``$N.NN`` (1-2 decimal places) plus
#     multi-currency symbols ``¢N`` ``€N`` ``£N`` ``¥N`` ``₱N``.
#     ADR-0131.G.3.1. ``$N.NNN`` (3+ decimals) deliberately not matched
#     — refused as out-of-scope so wrong == 0 is preserved.
#   - Slash fraction literal: ``N/M``. Denominator-zero refused at
#     resolve time, not regex.
#   - Hyphenated multi-word cardinal: ``twenty-five``, ``ninety-nine``.
#     Resolved via :func:`language_packs.numerics_loader.parse_compound_cardinal`.
#   - Digit run.
#   - Single-word cardinal (legacy ``WORD_NUMBERS`` set).

# ADR-0131.G.3.1: multi-currency symbol group. ¢ and $ are the only
# non-decimal currencies (sub-unit is the unit itself for ¢; $ converts
# to cents). €, £, ₱ admit 1-2 decimal places; ¥ is integer-only.
_MONEY_SYMBOL: Final[str] = (
    r"(?:\$\d+(?:\.\d{1,2})?|¢\d+|€\d+(?:\.\d{1,2})?|£\d+(?:\.\d{1,2})?|¥\d+|₱\d+(?:\.\d{1,2})?)"
)
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

# ADR-0131.G1 note: acquisition/action verbs (buys, bought, sells,
# collected, saved, makes) were removed from the anchor alternation here.
# They live exclusively in ADD_VERBS / SUBTRACT_VERBS so that sentences
# like "Sam buys 3 apples" are parsed as add-operations only, avoiding
# branch-disagreement when a canonical "has" initial precedes them.
# The solver defaults-from-zero for operations, so single-statement
# acquisition sentences ("Sam buys 5 apples. How many does Sam have?")
# still resolve correctly as 0 + 5 = 5.
_INITIAL_HAS_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+"
    # ADR-0131.G.1: pure-possession anchors only (with optional particle
    # for "had started with N", etc.). Acquisition verbs live in
    # ADD_VERBS / SUBTRACT_VERBS — see CandidateInitial.__post_init__.
    rf"(?P<anchor>has|have|had|started)(?:\s+(?:up|with))?\s+"
    rf"(?P<value>{_VALUE})"
    # ADR-0131.G.3: unit slot is optional. Money-symbol value literals
    # (``$40``) carry their unit implicitly (``cent``); a missing unit
    # slot is admissible IFF the value resolves with a unit override.
    # Non-money values without a unit slot are refused at resolve time.
    # ADR-0131.G.3.1 axis 4: optional adjective between value and unit
    # ("five full boxes" — adjective 'full' is consumed and discarded;
    # the unit head noun 'boxes' becomes the unit slot).
    r"(?:\s+(?:full|loose|empty|whole|broken|new|old|small|large|fresh|raw|flat))?"
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

# ADR-0131.G.3.1 — Axis 1: fraction-of-unit initial possession.
# "Bob has 3/4 of a cup." — the fraction is the value; "of a/an <unit>"
# carries the unit. The main _INITIAL_HAS_RE treats "of <NP>" as a
# discardable substance qualifier and emits no candidate (unit slot absent
# and no unit_override); this separate pattern extracts the unit from
# the "of" phrase explicitly.
_INITIAL_FRACTION_OF_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+"
    rf"(?P<anchor>has|have)\s+"
    rf"(?P<value>{_SLASH_FRACTION})\s+"
    r"of\s+(?:a\s+|an\s+)?(?P<unit>\w+)"
    r"(?:\s+of\s+.+)?"   # optional further substance qualifier
    r"\s*\.?$"
)

# ADR-0131.G.3.1 — Axis 3: multi-token space-separated cardinal.
# "Bob has one hundred apples." — parse_compound_cardinal already handles
# the value; this pattern captures it before the unit-slot boundary.
# Approach (a) chosen over (b) (_VALUE widening) because greedy cardinal-
# word matching inside _VALUE would span the unit slot and require
# look-ahead unwinding; a separate dedicated extractor is narrower and
# leaves _VALUE unchanged for all other paths.
# Build cardinal-word alternation from the WORD_NUMBERS table.
_CARDINAL_WORD_OPTIONS: Final[str] = "|".join(
    re.escape(w) for w in sorted(WORD_NUMBERS.keys(), key=len, reverse=True)
)
# At least two cardinal words (single-word is handled by _VALUE/_resolve_value).
_MULTI_WORD_CARDINAL_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+"
    rf"(?P<anchor>has|have)\s+"
    rf"(?P<value>(?:{_CARDINAL_WORD_OPTIONS})(?:\s+(?:{_CARDINAL_WORD_OPTIONS}))+)"
    # Optional adjective (axis 4 compound) between cardinal and unit.
    r"(?:\s+(?:full|loose|empty|whole|broken|new|old|small|large|fresh|raw|flat))?"
    r"\s+(?P<unit>\w+)"
    r"(?:\s+(?:of|in|for|with)\s+.+)?"
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

# ADR-0131.G.3.1: multi-currency symbol → (unit_surface, factor_to_unit).
# ``factor_to_unit`` is the multiplier applied to the face value to
# produce the canonical unit. For USD ($): face is dollars → *100 cents.
# For ¢: face is already cents → *1. For all others the pack has no
# sub-unit defined, so face == canonical (factor=1) and the unit is the
# pack's plural surface form.
_CURRENCY_SYMBOLS: Final[dict[str, tuple[str, float]]] = {
    "$":  ("cents",           100.0),   # dollar → 100 cents
    "¢":  ("cents",             1.0),   # cent already canonical
    "€":  ("euros",             1.0),
    "£":  ("pounds sterling",   1.0),
    "¥":  ("yen",               1.0),
    "₱":  ("pesos",             1.0),
}


def _resolve_currency(t: str) -> _ResolvedValue | None:
    """Resolve a currency-symbol value token (``$N``, ``¢N``, ``€N.NN``, …).

    Returns ``None`` when the format is out-of-scope (e.g. 3+ decimal places).
    Yen (``¥``) is integer-only (no sub-unit in en_units_v1).
    """
    for sym, (unit_surface, factor) in _CURRENCY_SYMBOLS.items():
        if not t.startswith(sym):
            continue
        body = t[len(sym):]
        if re.fullmatch(r"\d+", body):
            raw_val = int(body)
            final = int(raw_val * factor) if factor == int(factor) else raw_val * factor
            return _ResolvedValue(final, unit_surface)
        # ¥ is integer-only.
        if sym == "¥":
            return None
        if re.fullmatch(r"\d+\.\d{1,2}", body):
            raw_val = float(body)
            result = raw_val * factor
            return _ResolvedValue(int(round(result)) if factor != 1.0 else raw_val, unit_surface)
        return None  # 3+ decimals refused for all currency symbols
    return None


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
    # Multi-currency symbols (ADR-0131.G.3.1): $, ¢, €, £, ¥, ₱.
    if t and t[0] in _CURRENCY_SYMBOLS:
        return _resolve_currency(t)
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
    """ADR-0131.G.3 — normalize money word-form surface units to pack canonical.

    ``en_units_v1`` pins ``cent`` as ``canonical_unit`` for the ``money``
    dimension. ``dollar``/``dollars`` → 100 cents each. Other currencies
    (ADR-0131.G.3.1) are already in canonical form when they arrive via
    ``_resolve_currency``; this helper normalizes the word-form paths.
    """
    if unit is None:
        return value, unit
    lower = unit.lower()
    if lower in ("dollar", "dollars"):
        return value * 100, _MONEY_UNIT
    # Euro/pound-sterling/yen/peso word forms: already canonical (factor=1).
    # These enter via unit slot (word form) rather than symbol — pass through.
    if lower in ("euro", "euros"):
        return value, "euros"
    if lower in ("pound sterling", "pounds sterling"):
        return value, "pounds sterling"
    if lower == "yen":
        return value, "yen"
    if lower in ("peso", "pesos"):
        return value, "pesos"
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

    # ADR-0131.G.3.1 — Axis 1: fraction-of-unit shape.
    # "Bob has 3/4 of a cup." — separate regex extracts unit from "of" phrase.
    out.extend(_fraction_of_candidates(sentence))

    # ADR-0131.G.3.1 — Axis 3: multi-token space-separated cardinals.
    # "Bob has one hundred apples." — separate extractor; _VALUE is unchanged.
    out.extend(_multi_word_cardinal_candidates(sentence))

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
    # Optional verb particle: handles "saved up N", "picked up N",
    # "threw out N", etc.  The particle is grammatically real but
    # arithmetically inert — it does not affect the operation kind or
    # operand.  ADR-0131.G1: this clause replaces the former approach
    # of listing particle-bearing verbs as initial-possession anchors.
    verb_particle = r"(?:\s+(?:up|down|out|back|off|in|away))?"
    return re.compile(
        r"^"
        rf"(?P<subject>{_ENTITY})\s+"
        rf"(?P<verb>{verbs_pattern})"
        rf"{verb_particle}"
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

# Multiplicative: anchor-as-value form ("twice"/"thrice"/"half"/"quarter"/
# "third" carry the factor implicitly). "as many <unit>" required; unit
# ellipsis ("twice as many as Bob") is deferred to keep wrong==0 strict.
# "quarter" / "third" admit an optional article ("a quarter", "a third") —
# the article is not a named group; matched_verb is the anchor word itself,
# which is a substring of the source and registered in
# COMPARE_MULTIPLICATIVE_ANCHORS, so round-trip checks pass.
_COMPARE_MULT_ANCHOR_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>{_ENTITY})\s+{_comparison_anchor_verb()}\s+"
    r"(?:a\s+)?(?P<anchor>twice|thrice|half|quarter|third)\s+as\s+many\s+"
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
    # Registered in COMPARE_MULTIPLICATIVE_ANCHORS (math_roundtrip) and in the
    # round-trip factor-divisor table ("half":2, "third":3, "quarter":4).
    "twice": (2.0, "times"),
    "thrice": (3.0, "times"),
    "half": (0.5, "fraction"),
    "quarter": (0.25, "fraction"),
    "third": (1.0 / 3.0, "fraction"),
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
    rv = _resolve_value(delta_value_raw)
    if rv is None:
        return None
    delta_value = rv.value
    unit = rv.unit_override if rv.unit_override is not None else _canonicalize_unit(unit_raw)
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
        rv = _resolve_value(value_raw)
        if rv is None:
            return out
        factor = float(rv.value)
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
        rv = _resolve_value(factor_value_raw)
        factor = float(rv.value) if rv is not None else None
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


# ---------------------------------------------------------------------------
# ADR-0131.G.3.1 — Axis 1 + Axis 3 extractor functions
# ---------------------------------------------------------------------------

def _fraction_of_candidates(sentence: str) -> list[CandidateInitial]:
    """Axis 1 (fractions): 'Bob has 3/4 of a cup.' → value=0.75, unit='cups'.

    The main _INITIAL_HAS_RE treats 'of <NP>' as a discardable substance
    qualifier and cannot fill the unit slot from it. This extractor uses
    _INITIAL_FRACTION_OF_RE to explicitly capture the unit after 'of'.
    """
    s = sentence.strip().rstrip(".")
    m = _INITIAL_FRACTION_OF_RE.match(s)
    if m is None:
        return []
    value_raw = m.group("value")
    rv = _resolve_value(value_raw)
    if rv is None:
        return []
    unit_raw = m.group("unit")
    unit = _canonicalize_unit(unit_raw)
    entity = _normalize_entity(m.group("entity"))
    try:
        return [
            CandidateInitial(
                initial=InitialPossession(
                    entity=entity,
                    quantity=Quantity(value=rv.value, unit=unit),
                ),
                source_span=sentence,
                matched_anchor=m.group("anchor"),
                matched_value_token=value_raw,
                matched_unit_token=unit_raw,
                matched_entity_token=m.group("entity"),
            )
        ]
    except Exception:
        return []


def _multi_word_cardinal_candidates(sentence: str) -> list[CandidateInitial]:
    """Axis 3 (multi-word cardinals): 'Bob has one hundred apples.'

    Approach (a): dedicated extractor leaving _VALUE unchanged. The value
    group captures the full space-separated cardinal sequence; the unit
    slot is the next word token after the cardinal sequence (and optional
    adjective).
    """
    s = sentence.strip().rstrip(".")
    m = _MULTI_WORD_CARDINAL_RE.match(s)
    if m is None:
        return []
    value_raw = m.group("value")
    from language_packs.numerics_loader import parse_compound_cardinal
    parsed = parse_compound_cardinal(value_raw)
    if parsed is None:
        return []
    unit_raw = m.group("unit")
    value_n, unit_n = _money_unit_normalization(parsed, _canonicalize_unit(unit_raw))
    if unit_n is None:
        return []
    entity = _normalize_entity(m.group("entity"))
    try:
        return [
            CandidateInitial(
                initial=InitialPossession(
                    entity=entity,
                    quantity=Quantity(value=value_n, unit=unit_n),
                ),
                source_span=sentence,
                matched_anchor=m.group("anchor"),
                # Provenance: use the first cardinal word as the value token
                # for grounding (all cardinal words are in the source span).
                matched_value_token=value_raw.split()[0],
                matched_unit_token=unit_raw,
                matched_entity_token=m.group("entity"),
            )
        ]
    except Exception:
        return []


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
    rv = _resolve_value(value_raw)
    if rv is None:
        return []
    value = rv.value
    unit_raw = m.group("unit")
    unit = rv.unit_override if rv.unit_override is not None else _canonicalize_unit(unit_raw)
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
        rv = _resolve_value(value_raw)
        if rv is None:
            return []
        final_unit = rv.unit_override if rv.unit_override is not None else unit
        try:
            out.append(
                CandidateInitial(
                    initial=InitialPossession(
                        entity=entity,
                        quantity=Quantity(value=rv.value, unit=final_unit),
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
    rv_n = _resolve_value(n_raw)
    rv_per = _resolve_value(m_raw)
    if rv_n is None or rv_per is None:
        return []
    total = rv_n.value * rv_per.value
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
    rv_n1 = _resolve_value(n1_raw)
    rv_m1 = _resolve_value(m1_raw)
    rv_n2 = _resolve_value(n2_raw)
    rv_m2 = _resolve_value(m2_raw)
    if any(rv is None for rv in (rv_n1, rv_m1, rv_n2, rv_m2)):
        return []
    total = (rv_n1.value * rv_m1.value) + (rv_n2.value * rv_m2.value)  # type: ignore[union-attr]
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

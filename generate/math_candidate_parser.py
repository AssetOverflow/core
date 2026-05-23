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
        if self.matched_anchor.lower() not in ("has", "have"):
            raise ValueError(
                f"CandidateInitial.matched_anchor must be has/have; "
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
    r"(?P<unit>\w+)\s*\.?$"
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


def extract_initial_candidates(sentence: str) -> list[CandidateInitial]:
    """Return all admissible initial-possession candidates for ``sentence``.

    Currently emits at most one candidate (the single canonical shape
    "<Entity> has <N> <unit>"). Returns an empty list if no shape matches.
    """
    s = sentence.strip().rstrip(".")
    m = _INITIAL_HAS_RE.match(s)
    if not m:
        return []
    entity = _normalize_entity(m.group("entity"))
    value = _resolve_value(m.group("value"))
    unit_raw = m.group("unit")
    # Canonicalize: lowercase + ensure plural (matching math_parser._canonical_unit).
    unit = unit_raw.lower()
    if not unit.endswith("s"):
        unit = unit + "s"
    return [
        CandidateInitial(
            initial=InitialPossession(
                entity=entity,
                quantity=Quantity(value=value, unit=unit),
            ),
            source_span=sentence,
            matched_anchor=m.group("anchor"),
            matched_value_token=m.group("value"),
            matched_unit_token=unit_raw,
            matched_entity_token=m.group("entity"),
        )
    ]


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
            r"(?:\s+(?:on|from|at|in|onto|into|under|over)\s+.+)?"
        )
    else:
        target_part = ""
        # Note: 'to' is included in the discardable preposition set.
        trailing_prep = (
            r"(?:\s+(?:on|from|at|in|onto|into|under|over|to)\s+.+)?"
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


def _build_op_candidate(
    m: re.Match[str], kind: str, source: str
) -> CandidateOperation | None:
    """Build a CandidateOperation from a regex match. Returns None if
    the match lacks a required slot (e.g. unit token absent — P2 does
    not emit unit-inherited candidates)."""
    unit_raw = m.group("unit")
    if unit_raw is None:
        return None
    unit = unit_raw.lower()
    if not unit.endswith("s"):
        unit = unit + "s"
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

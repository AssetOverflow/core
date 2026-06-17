"""ADR-0126 — Round-trip admissibility filter.

The wrong-answer firewall for the candidate-graph parser topology.

A :class:`CandidateOperation` carries an :class:`Operation` plus the
source-span provenance for every content slot the parser claimed: the
verb token, the numeric value token, the unit token, the actor name as
it appeared, and (for transfers) the target name. Admissibility is a
deterministic byte-level check that each claimed slot's surface token
actually appears in the source span, AND that the verb the parser
consumed is registered for the operation kind it produced.

This is the load-bearing invariant of ADR-0126:

  admissible(c) iff every content slot in c.op grounds in c.source_span
                AND c.matched_verb is registered for c.op.kind

Two consequences:

1. A regex that mis-reads "loses" as add fails because "loses" is not
   in the add-verb registry — even if the resulting Operation looks
   numerically plausible.

2. A regex that hallucinates a number or unit not present in the
   source fails because the matched token won't ground.

Normalization is deliberately conservative: lowercase + word-boundary
containment. We do not strip morphology (plural "apples" must equal
the matched unit token "apples", not "apple"); we do not stem
("eats" != "ate"); we do not handle synonyms. The parser is expected
to canonicalize units before constructing the Quantity, so the
matched_unit_token carries the surface form.

Determinism: every check is pure byte / regex containment. No
randomness, no learning, no approximation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Mapping

from generate.math_problem_graph import Comparison, Operation, Quantity, Rate


# ---------------------------------------------------------------------------
# Verb registry — single source of truth for {operation kind -> valid verbs}.
#
# This is intentionally permissive (much wider than today's math_parser tables)
# because the candidate-graph topology relies on the round-trip filter to
# reject wrong candidates, not on the parser's regex narrowness.
#
# P2 will refactor math_parser.py to import these constants instead of
# maintaining its own _ADD_VERBS / _SUBTRACT_VERBS / etc. tables.
# ---------------------------------------------------------------------------

# Surface verbs that grammatically place the actor as the *gainer* of the
# operand quantity. Past tense and present tense both registered.
ADD_VERBS: Final[frozenset[str]] = frozenset({
    # acquisition
    "buy", "buys", "bought",
    "get", "gets", "got",
    "find", "finds", "found",
    "receive", "receives", "received",
    "earn", "earns", "earned",
    "add", "adds", "added",
    "pick", "picks", "picked",      # "picks up N"
    "collect", "collects", "collected",
    "gather", "gathers", "gathered",
    "catch", "catches", "caught",
    "save", "saves", "saved",
    # production (actor creates instances of the unit)
    "bake", "bakes", "baked",
    "make", "makes", "made",
    "cook", "cooks", "cooked",
    "slice", "slices", "sliced",
    "pack", "packs", "packed",
    "build", "builds", "built",
    "grow", "grows", "grew",
})

# Surface verbs that grammatically place the actor as the *loser* of the
# operand quantity.
SUBTRACT_VERBS: Final[frozenset[str]] = frozenset({
    "eat", "eats", "ate",
    "lose", "loses", "lost",
    "sell", "sells", "sold",
    "donate", "donates", "donated",
    "use", "uses", "used",
    "spend", "spends", "spent",
    "drop", "drops", "dropped",
    "remove", "removes", "removed",
    "break", "breaks", "broke",
    "destroy", "destroys", "destroyed",
    "throw", "throws", "threw",     # "throws out N"
    "discard", "discards", "discarded",
    "return", "returns", "returned",  # ambiguous — see TRANSFER_VERBS
    "consume", "consumes", "consumed",
    "give", "gives", "gave",        # ambiguous — see TRANSFER_VERBS
    "send", "sends", "sent",        # ambiguous — see TRANSFER_VERBS
})

# Surface verbs that grammatically place the actor as the *sender* and a
# named target as the *receiver*. These verbs ALSO appear in SUBTRACT_VERBS
# because the same surface token can take a transfer reading (with target)
# or a subtract reading (without target) — both candidates fire and the
# decision rule picks based on whether a target slot was grounded.
TRANSFER_VERBS: Final[frozenset[str]] = frozenset({
    "give", "gives", "gave",
    "send", "sends", "sent",
    "hand", "hands", "handed",
    "pass", "passes", "passed",
    "mail", "mails", "mailed",
    "deliver", "delivers", "delivered",
    "return", "returns", "returned",
})

MULTIPLY_VERBS: Final[frozenset[str]] = frozenset({
    "double", "doubles", "doubled",
    "triple", "triples", "tripled",
    "quadruple", "quadruples", "quadrupled",
    "multiply", "multiplies", "multiplied",
})

DIVIDE_VERBS: Final[frozenset[str]] = frozenset({
    "halve", "halves", "halved",
    "split", "splits", "split",
    "divide", "divides", "divided",
    "share", "shares", "shared",
})

# Comparison "verbs" — the surface anchor for compare_additive /
# compare_multiplicative is usually 'has'/'have' + comparator phrase
# ('N more than', 'twice as many as', etc.). The matched_verb slot for
# comparison candidates carries the comparator phrase head ('more',
# 'fewer', 'twice', 'times', 'half').
COMPARE_ADDITIVE_ANCHORS: Final[frozenset[str]] = frozenset({
    "more", "fewer", "less", "additional", "extra",
})
COMPARE_MULTIPLICATIVE_ANCHORS: Final[frozenset[str]] = frozenset({
    "twice", "thrice", "times", "half", "double", "triple",
    "quadruple", "third", "quarter",
})

# Rate anchors (ADR-0122): "per", "each", "every", "a"/"an" (when followed
# by a unit in a rate surface such as "$18 an hour" or "$2 a cup").
# The literal surface token from the sentence is used for matched_verb
# so that roundtrip_admissible / CandidateOperation post-init grounding
# succeeds.  "a"/"an" were documented in the comment but missing from the
# set; added here (Inc 2) with corresponding injector tests.
RATE_ANCHORS: Final[frozenset[str]] = frozenset({
    "per", "each", "every", "a", "an", "one",
})


KIND_TO_VERBS: Final[Mapping[str, frozenset[str]]] = {
    "add": ADD_VERBS,
    "subtract": SUBTRACT_VERBS,
    "transfer": TRANSFER_VERBS,
    "multiply": MULTIPLY_VERBS,
    "divide": DIVIDE_VERBS,
    "apply_rate": RATE_ANCHORS,
    "compare_additive": COMPARE_ADDITIVE_ANCHORS,
    "compare_multiplicative": COMPARE_MULTIPLICATIVE_ANCHORS,
}


# ---------------------------------------------------------------------------
# Number-word table — for grounding numeric value tokens that appear as
# words ("three apples") rather than digits ("3 apples").
# ---------------------------------------------------------------------------

WORD_NUMBERS: Final[Mapping[str, int]] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    # ordinals as factor-bearing forms ("a third", "a quarter")
    "half": 2, "third": 3, "quarter": 4,
}


# ---------------------------------------------------------------------------
# Public dataclass — what the candidate-graph parser will emit per match.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateOperation:
    """An Operation candidate plus the source-span provenance proving it.

    Every content slot the parser claims must trace back to a surface
    token in :attr:`source_span`. The round-trip filter
    (:func:`roundtrip_admissible`) verifies this; candidates that fail
    are rejected before they can produce a wrong answer.

    Slot conventions:

    - ``matched_verb``: the surface verb (or comparator phrase head) the
      parser consumed. MUST be a member of
      ``KIND_TO_VERBS[op.kind]``.
    - ``matched_value_token``: the surface form of the numeric value, as
      it appeared in the source ("3" or "three"). Required for all
      kinds except ``compare_multiplicative`` with factor anchors
      like "twice"/"half" where the anchor itself carries the factor —
      in that case set to the anchor word.
    - ``matched_unit_token``: the surface noun for the operand's unit.
      For Rate operands, this is the numerator_unit surface form. For
      Comparison operands, this can be empty when the comparison uses
      an implicit unit ("Sam has twice as many as Tom" — no unit token).
    - ``matched_actor_token``: the actor's name as it appeared. Case-
      preserving; the filter does case-insensitive matching.
    - ``matched_target_token``: required iff ``op.kind == 'transfer'``;
      otherwise must be None.
    - ``matched_reference_actor_token``: required iff ``op.operand`` is
      a Comparison; otherwise must be None.
    """

    op: Operation
    source_span: str
    matched_verb: str
    matched_value_token: str
    matched_unit_token: str
    matched_actor_token: str
    matched_target_token: str | None = None
    matched_reference_actor_token: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_span, str) or not self.source_span:
            raise ValueError("CandidateOperation.source_span must be non-empty")
        if not isinstance(self.matched_verb, str) or not self.matched_verb:
            raise ValueError("CandidateOperation.matched_verb must be non-empty")
        if not isinstance(self.matched_actor_token, str) or not self.matched_actor_token:
            raise ValueError(
                "CandidateOperation.matched_actor_token must be non-empty"
            )
        if self.op.kind == "transfer":
            if not self.matched_target_token:
                raise ValueError(
                    "matched_target_token required when op.kind='transfer'"
                )
        elif self.matched_target_token is not None:
            raise ValueError(
                "matched_target_token only valid when op.kind='transfer'"
            )
        if isinstance(self.op.operand, Comparison):
            if not self.matched_reference_actor_token:
                raise ValueError(
                    "matched_reference_actor_token required when operand is "
                    "Comparison"
                )
        elif self.matched_reference_actor_token is not None:
            raise ValueError(
                "matched_reference_actor_token only valid when operand is "
                "Comparison"
            )


# ---------------------------------------------------------------------------
# Normalization + containment primitives.
# ---------------------------------------------------------------------------

_WORD_RE: Final[re.Pattern[str]] = re.compile(r"\b\w+\b", flags=re.UNICODE)


def _tokens(text: str) -> frozenset[str]:
    """Lowercased word-token set for word-boundary containment checks."""
    return frozenset(m.group(0).lower() for m in _WORD_RE.finditer(text))


def _token_in(needle: str, haystack_tokens: frozenset[str]) -> bool:
    """Word-boundary containment: 'ate' must not match 'states'."""
    return needle.lower() in haystack_tokens


def _unit_grounds(
    unit_token: str,
    source_span: str,
    haystack_tokens: frozenset[str],
) -> bool:
    """A unit token grounds if it appears as a word token in source.

    ADR-0131.G.3 widening: when the canonical money unit ``cent`` is
    claimed, the source's ``$`` symbol counts as grounding evidence —
    the word-boundary tokenizer strips ``$`` so it must be inspected
    on the raw source span rather than the token set. Similarly for
    ``dollar``: an author may write either ``$N`` or ``N dollars``;
    both ground a money unit.

    ADR-0131.G.3.1 widening: multi-currency symbols (¢ € £ ¥ ₱) each
    ground their respective canonical unit when their symbol appears in
    the raw source span.
    """
    if _token_in(unit_token, haystack_tokens):
        return True
    lower = unit_token.lower()
    # Multi-word units (e.g. "Pokemon cards", "stop signs") ground when
    # every component appears as a word token in source. Conjunctive by
    # design — a missing component means the unit cannot be reconstructed
    # from the source, which preserves wrong=0.
    parts = lower.split()
    if len(parts) > 1 and all(p in haystack_tokens for p in parts):
        return True
    if lower in ("cent", "cents"):
        if "$" in source_span or "¢" in source_span:
            return True
        if "dollar" in haystack_tokens or "dollars" in haystack_tokens:
            return True
    if lower in ("dollar", "dollars"):
        if "$" in source_span:
            return True
    if lower in ("euro", "euros"):
        if "€" in source_span:
            return True
    # "pounds sterling" is a two-word unit; check both the multi-word
    # surface and the raw symbol.
    if lower in ("pound sterling", "pounds sterling"):
        if "£" in source_span:
            return True
        if "sterling" in haystack_tokens:
            return True
    if lower == "yen":
        if "¥" in source_span:
            return True
    if lower in ("peso", "pesos"):
        if "₱" in source_span:
            return True
    return False


def _value_grounds(value_token: str, haystack_tokens: frozenset[str]) -> bool:
    """A numeric value grounds if its surface token appears, OR if the token
    is a digit-string and any equivalent word-form appears, OR if it's a
    word-form and the digit appears.

    ADR-0128 integration: en_numerics_v1's cardinal table is consulted in
    addition to the legacy hard-coded WORD_NUMBERS, widening coverage from
    1-12 to the full pack cardinal range (0-1000+ plus compound rule). The
    hard-coded WORD_NUMBERS remains as a fast path and as a fallback if
    the pack is unavailable; the pack adds, never replaces.

    ADR-0131.G.3 widens the literal-class grounding:
      - Money symbol ``$N`` / ``$N.NN`` grounds when every digit run on
        either side of the optional decimal appears as a token in the
        source. The ``$`` itself is dropped by the word-boundary
        tokenizer; what survives is exactly the digit form an author
        would write.
      - Slash fraction ``N/M`` grounds when both numerator and
        denominator digit tokens appear.
      - Hyphenated multi-word cardinal (``twenty-five``) grounds when
        every component lemma is a token (the tokenizer splits on
        hyphens), OR the compound's integer value's digit form appears.
    """
    # ADR-0131.G.3 / G.3.1 widenings (handled first; the trailing existing
    # path would never recognize these surface shapes).
    # Currency symbol literals: extract digit parts, verify each in source.
    _CURRENCY_SYM_SET = frozenset({"$", "¢", "€", "£", "¥", "₱"})
    if value_token and value_token[0] in _CURRENCY_SYM_SET:
        body = value_token[1:]
        parts = [p for p in body.split(".") if p]
        return bool(parts) and all(p in haystack_tokens for p in parts)
    if "/" in value_token:
        m = re.fullmatch(r"(\d+)/(\d+)", value_token)
        if m is not None:
            return m.group(1) in haystack_tokens and m.group(2) in haystack_tokens
    # ADR-0179 EX-2 — bare decimal "N.M" (the currency branch above handles the
    # symbol form $N.NN; a decimal written without a symbol, e.g. "0.75", is never
    # a single token because the word-boundary tokenizer splits on ".", so it
    # grounds exactly when both digit-runs appear as tokens — symmetric with the
    # $N.NN and N/M widenings. Only returns True on a match; non-matching decimals
    # fall through to the existing paths (which ultimately refuse).
    if "." in value_token and re.fullmatch(r"\d+\.\d+", value_token) is not None:
        if all(part in haystack_tokens for part in value_token.split(".")):
            return True
    if "-" in value_token and not value_token[0].isdigit():
        try:
            from language_packs.numerics_loader import parse_compound_cardinal
            parsed = parse_compound_cardinal(value_token)
            if parsed is not None:
                components = [c for c in value_token.lower().split("-") if c]
                if all(c in haystack_tokens for c in components):
                    return True
                if str(parsed) in haystack_tokens:
                    return True
        except Exception:
            pass

    if _token_in(value_token, haystack_tokens):
        return True
    lowered = value_token.lower()

    # Pack-backed cardinal lookup (ADR-0128). Soft import — if the pack
    # isn't mounted (e.g., in legacy test environments) we silently fall
    # through to the hard-coded table.
    try:
        from language_packs.loader import lookup_cardinal
        entry = lookup_cardinal(lowered)
        if entry is not None:
            digit = str(entry.numeric_value)
            if digit in haystack_tokens:
                return True
    except Exception:
        pass  # fall through to hard-coded path

    # word -> digit equivalent (legacy)
    if lowered in WORD_NUMBERS:
        digit = str(WORD_NUMBERS[lowered])
        if digit in haystack_tokens:
            return True
    # digit -> any word with that integer value (legacy)
    try:
        n = int(value_token)
    except ValueError:
        return False
    for word, w_val in WORD_NUMBERS.items():
        if w_val == n and word in haystack_tokens:
            return True
    # Pack-backed reverse lookup: digit -> cardinal surface in haystack
    try:
        from language_packs.loader import lookup_cardinal
        for tok in haystack_tokens:
            entry = lookup_cardinal(tok)
            if entry is not None and entry.numeric_value == n:
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# The load-bearing primitive.
# ---------------------------------------------------------------------------

def roundtrip_admissible(c: CandidateOperation) -> bool:
    """True iff every content slot in ``c`` grounds in ``c.source_span``
    AND the matched verb is registered for the operation kind.

    This is the deterministic wrong-answer firewall. A candidate that
    fails is silently dropped from the candidate set — it never reaches
    the solver, never produces a number, and never appears in any
    ``SolutionTrace``.
    """
    # 1. Verb must be registered for the claimed kind.
    valid_verbs = KIND_TO_VERBS.get(c.op.kind)
    if valid_verbs is None or c.matched_verb.lower() not in valid_verbs:
        return False

    haystack = _tokens(c.source_span)

    # 2. Matched verb must appear in source.
    if not _token_in(c.matched_verb, haystack):
        return False

    # 3. Actor name must appear in source.
    if not _token_in(c.matched_actor_token, haystack):
        return False

    # 4. Numeric value must ground.
    #    Skipped only for multiplicative comparison anchors that carry
    #    the factor implicitly ("twice", "half", "thrice") — those use
    #    the anchor itself as the value token and pass via step (2).
    if c.op.kind == "compare_multiplicative" and c.matched_value_token == c.matched_verb:
        pass  # anchor already grounded by verb check
    elif not _value_grounds(c.matched_value_token, haystack):
        return False

    # 5. Unit must ground when non-empty. Empty unit token is only valid
    #    for comparison operands without explicit unit phrasing
    #    ("Sam has twice as many as Tom").
    if c.matched_unit_token:
        if not _unit_grounds(c.matched_unit_token, c.source_span, haystack):
            return False
    else:
        if not isinstance(c.op.operand, Comparison):
            return False  # only comparisons may have empty unit token

    # 6. Transfer target must appear.
    if c.matched_target_token is not None:
        if not _token_in(c.matched_target_token, haystack):
            return False

    # 7. Comparison reference_actor must appear.
    if c.matched_reference_actor_token is not None:
        if not _token_in(c.matched_reference_actor_token, haystack):
            return False

    # 8. Operand kind/shape sanity (defense-in-depth — Operation
    #    constructor already enforces shape, but we re-check kind ↔
    #    operand-type consistency here so an upstream bug can't slip a
    #    Quantity-as-Comparison candidate past the filter).
    if c.op.kind == "apply_rate":
        if not isinstance(c.op.operand, Rate):
            return False
        # Rate denominator unit must also ground.
        if not _token_in(c.op.operand.denominator_unit, haystack):
            return False
    elif c.op.kind in ("compare_additive", "compare_multiplicative"):
        if not isinstance(c.op.operand, Comparison):
            return False
    else:
        if not isinstance(c.op.operand, Quantity):
            return False

    return True

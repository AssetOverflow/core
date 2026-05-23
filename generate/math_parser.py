"""ADR-0115 Phase 1.3 — deterministic math word-problem parser.

Turns a grade-school math word problem into a :class:`MathProblemGraph`
via rule-based extraction. No LLM, no sampling, no statistical anything.
Same input string always produces the same graph; failures raise
:class:`ParseError` rather than guessing.

The parser handles the patterns documented in
``evals/gsm8k_parser_dev/README.md``'s pattern registry. Cases outside
that registry are rejected with a typed error pointing to the unsupported
construction.

Architecture:

1. Sentence-split on terminal ``.``/``?``/``!`` (with lookbehind to
   preserve the punctuation marker for question detection).
2. Partition into statement sentences (initial possessions + operations)
   and exactly one question sentence.
3. Per statement, try ``_try_initial`` first; on miss, split on
   compound markers (``,then`` / ``,and`` / ``;then``) and dispatch each
   clause to ``_try_operation``.
4. Per question, match ``_QUESTION_PATTERNS`` in order.
5. Assemble :class:`MathProblemGraph` with referential-integrity
   guaranteed by the dataclass constructors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from generate.math_problem_graph import (
    Comparison,
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
    Unknown,
)


class ParseError(ValueError):
    """Raised when the parser cannot classify a sentence or clause.

    The message names the sentence and the most-specific unsupported
    construction, so the caller can decide whether to author a new
    pattern (lift Phase 1.X scope) or fix the input.
    """


# Verb tables — each verb maps to exactly one operation kind.
# Drawn from the README's pattern registry; extending this dict requires
# updating the registry in the same PR.
_ADD_VERBS: frozenset[str] = frozenset(
    {"buys", "gets", "finds", "receives", "earns", "adds"}
)
_SUBTRACT_VERBS: frozenset[str] = frozenset(
    {
        "eats",
        "loses",
        "sells",
        "donates",
        "uses",
        "spends",
        "drops",
        "removes",
    }
)
_TRANSFER_VERBS: frozenset[str] = frozenset(
    {"gives", "sends", "hands", "passes", "mails"}
)
_MULTIPLY_FACTOR_VERBS: dict[str, int] = {
    "doubles": 2,
    "triples": 3,
}

_SINGULAR_PRONOUNS: frozenset[str] = frozenset({"he", "she", "it"})
_PLURAL_PRONOUNS: frozenset[str] = frozenset({"they"})

# Object pronouns referring to the actor's last-mentioned quantity.
# When the parser sees one of these in a unit slot, it falls back to
# state.last_unit rather than treating the pronoun as a literal unit.
_OBJECT_PRONOUNS_OF_QUANTITY: frozenset[str] = frozenset({"them", "it", "these", "those"})

# English plural irregulars the parser may encounter in grade-school
# problem text. Most nouns canonicalize via the simple "+s" rule below.
_PLURAL_IRREGULARS: dict[str, str] = {
    "candy": "candies",
    "berry": "berries",
    "cherry": "cherries",
    "fly": "flies",
    "story": "stories",
    "penny": "pennies",
    "box": "boxes",
    "bus": "buses",
    "dish": "dishes",
    "watch": "watches",
    "child": "children",
    "person": "people",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "tooth": "teeth",
    "mouse": "mice",
    "goose": "geese",
}


def _canonical_unit(raw: str) -> str:
    """Lowercase + pluralize per the README canonicalization rule.

    Grade-school problem text often uses singular for n=1 ("1 coin")
    even though ground-truth graphs canonicalize to plural ("coins").
    The parser bridges by normalizing every extracted unit to plural.
    """
    s = raw.lower()
    if s in _PLURAL_IRREGULARS:
        return _PLURAL_IRREGULARS[s]
    if s.endswith("s"):
        return s
    return s + "s"


@dataclass
class _ParserState:
    """Mutable state threaded through the parser.

    All fields are append-only or last-write-wins; the parser never
    revises an earlier decision. This keeps determinism trivial to
    prove.
    """

    entities: list[str] = field(default_factory=list)
    initial_state: list[InitialPossession] = field(default_factory=list)
    operations: list[Operation] = field(default_factory=list)
    unknown: Unknown | None = None
    last_unit: str | None = None
    last_singular_subject: str | None = None
    # ADR-0122: declared rates keyed by denominator_unit
    # (first-declaration-wins; redeclaration raises ParseError).
    rates: dict[str, Rate] = field(default_factory=dict)
    # ADR-0122: True once a rate-aggregate question consumed a rate.
    # Checked at end of parse to refuse orphan rates.
    rate_applied: bool = False
    # ADR-0122: per-actor current unit, written by initial possession
    # and by every operation that holds value in some unit. Used by
    # the rate-aggregate question to find the right denominator.
    actor_units: dict[str, str] = field(default_factory=dict)

    def add_entity(self, name: str) -> None:
        if name not in self.entities:
            self.entities.append(name)


def parse_problem(text: str) -> MathProblemGraph:
    """Parse ``text`` into a :class:`MathProblemGraph`.

    Raises :class:`ParseError` if any sentence cannot be classified, if
    no question sentence is present, if multiple question sentences are
    present, or if the resulting graph violates structural integrity
    (e.g. question references an entity never introduced).
    """
    if not isinstance(text, str) or not text.strip():
        raise ParseError(f"empty or non-string problem: {text!r}")

    state = _ParserState()
    sentences = _split_sentences(text)
    if not sentences:
        raise ParseError(f"no sentences found: {text!r}")

    question_sentences = [s for s in sentences if s.rstrip().endswith("?")]
    statement_sentences = [s for s in sentences if not s.rstrip().endswith("?")]

    if len(question_sentences) != 1:
        raise ParseError(
            f"expected exactly one question sentence ending in '?', got "
            f"{len(question_sentences)}: {text!r}"
        )

    for s in statement_sentences:
        _process_statement(s, state)

    _process_question(question_sentences[0], state)

    if state.unknown is None:
        raise ParseError(f"no question parsed: {text!r}")

    # ADR-0122: a rate that was declared but never consumed by a
    # rate-aggregate question is orphan structure — refuse rather
    # than emit a graph whose declared rate has no algebraic role.
    if state.rates and not state.rate_applied:
        unused = sorted(state.rates.keys())
        raise ParseError(
            f"rate declared for unit(s) {unused} but no "
            f"rate-aggregate question consumed it (ADR-0122 refuses "
            f"orphan rates): {text!r}"
        )

    return MathProblemGraph(
        entities=tuple(state.entities),
        initial_state=tuple(state.initial_state),
        operations=tuple(state.operations),
        unknown=state.unknown,
    )


# ---------------------------------------------------------------------------
# Sentence-level helpers
# ---------------------------------------------------------------------------

# Split on a sentence-terminal . ? or ! followed by whitespace.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!])\s+")

# Compound-clause split inside one statement sentence:
#   "She buys 5 more, then donates 3."
# Resulting clauses inherit the subject of the first clause.
_COMPOUND_SPLIT_RE = re.compile(r",\s*(?:then|and)\s+", flags=re.IGNORECASE)

# A statement sentence may open with "Then " as a sequence marker that
# inherits subject + unit from the prior sentence:
#   "Sam buys 3. Then he eats 1."
_SENTENCE_OPENER_THEN_RE = re.compile(r"^Then\s+", flags=re.IGNORECASE)


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    pieces = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in pieces if p.strip()]


# ---------------------------------------------------------------------------
# Initial-possession patterns
# ---------------------------------------------------------------------------

# "<Entity> has <N> <unit>." — entity is a Title-Cased word or a
# "the <noun>" collective ("The boys have 5 cards"). ADR-0123a widens
# the subject slot to match the comparison patterns; otherwise problems
# that introduce "the X" entities via initial possession can never
# reach the widened comparison patterns. Pronouns are NOT accepted
# here — initial possession must concretely introduce an entity.
_INITIAL_HAS_RE = re.compile(
    r"^(?P<entity>[A-Z]\w+|[Tt]he\s+\w+)\s+"
    r"(?:has|have)\s+"
    r"(?P<value>\d+|one|two|three|four|five|six|seven|eight|nine|ten"
    r"|eleven|twelve)\s+"
    r"(?P<unit>\w+)$"
)


def _process_statement(sentence: str, state: _ParserState) -> None:
    s = sentence.rstrip(".").strip()

    # Strip leading "Then " sequence marker — operation inherits subject
    # and unit from the prior sentence. Same semantics as the in-sentence
    # ", then" compound marker, just punctuated as a separate sentence.
    sentence_opens_with_then = bool(_SENTENCE_OPENER_THEN_RE.match(s))
    if sentence_opens_with_then:
        s = _SENTENCE_OPENER_THEN_RE.sub("", s).strip()

    # ADR-0122: rate declarations are statement-shaped but never carry
    # an actor or compound chain. Try them before everything else so the
    # regex specificity is preserved.
    if _try_rate_declaration(s, state):
        return

    # ADR-0123: comparison declarations ("X has 3 more apples than Y",
    # "X has twice as many apples as Y") share the leading "<Entity>
    # has <N>" shape with initial possessions; try them before
    # _try_initial so the comparison sentence is not greedily consumed
    # as an initial with unit='more'/'fewer'.
    if _try_comparison_declaration(s, state):
        return

    if _try_initial(s, state):
        return

    # Compound: split on ", then" / ", and" — first clause has explicit
    # subject unless the sentence opened with "Then" (in which case the
    # first clause also inherits).
    parts = _COMPOUND_SPLIT_RE.split(s)
    for index, clause in enumerate(parts):
        clause = clause.strip()
        if not clause:
            continue
        has_explicit_subject = (index == 0) and not sentence_opens_with_then
        if not _try_operation(clause, state, has_explicit_subject):
            raise ParseError(
                f"could not parse statement clause: {clause!r} "
                f"(in sentence: {sentence!r})"
            )


def _try_initial(s: str, state: _ParserState) -> bool:
    m = _INITIAL_HAS_RE.match(s)
    if not m:
        return False
    # ADR-0123a — canonicalize "the X" entity (collapse whitespace,
    # lowercase the article so "The boys" and "the boys" hash equal)
    # and resolve word-form value through the shared helper.
    entity_raw = m.group("entity")
    entity = re.sub(r"\s+", " ", entity_raw.strip())
    if entity.lower().startswith("the "):
        entity = "the " + entity[4:]
    value_raw = m.group("value")
    value = int(value_raw) if value_raw.isdigit() else _WORD_NUMBERS[value_raw.lower()]
    unit = _canonical_unit(m.group("unit"))
    state.add_entity(entity)
    state.initial_state.append(
        InitialPossession(entity=entity, quantity=Quantity(value=value, unit=unit))
    )
    state.last_unit = unit
    state.last_singular_subject = entity
    state.actor_units[entity] = unit
    return True


# ---------------------------------------------------------------------------
# Operation patterns
# ---------------------------------------------------------------------------

# Add / subtract / transfer share a structure:
#   [subject] verb value [more] [unit] [to target] [trailing prep phrase]
# Constraints expressed via lookaheads:
#   - unit cannot start with "to" or "more" (those are sentence chrome)
# A trailing prepositional phrase ("on the floor", "from the box") is
# semantically irrelevant for the graph and is harmlessly discarded.
_OP_RE = re.compile(
    r"^"
    r"(?:(?P<subject>[A-Z]\w+|he|she|He|She|It|it)\s+)?"
    r"(?P<verb>\w+)"
    r"\s+(?P<value>\d+)"
    r"(?:\s+more)?"
    r"(?:\s+(?!to\b)(?!more\b)(?!on\b)(?!from\b)(?!at\b)(?!in\b)"
    r"(?P<unit>\w+))?"
    r"(?:\s+to\s+(?P<target>[A-Z]\w+))?"
    r"(?:\s+(?:on|from|at|in|onto|into|under|over)\s+.+)?"
    r"$"
)

# Divide construction. Three syntactic frames the parser accepts:
#   "<S> splits them evenly into M groups [and keeps one group]"
#   "<S> splits his/her <unit> evenly into M groups [and keeps one group]"
#   "<S> splits <N> [<unit>] evenly into M groups [and keeps one group]"
# Semantics: actor's quantity becomes (original / M). Operand value = M;
# operand unit comes from the explicit unit if present, else from
# state.last_unit (via "them"/"his/her" reference).
_DIVIDE_SPLIT_RE = re.compile(
    r"^"
    r"(?:(?P<subject>[A-Z]\w+|he|she|He|She|It|it)\s+)?"
    r"splits\s+"
    r"(?:"
    r"(?P<object_pronoun>them|these|those)|"
    r"(?:his|her|their)\s+(?P<possessive_unit>\w+)|"
    r"(?P<value>\d+)(?:\s+(?P<explicit_unit>\w+))?"
    r")\s+"
    r"evenly\s+(?:into|among)\s+"
    r"(?P<groups>\d+)\s+(?:groups|piles|parts|people|stacks|bundles)"
    r"(?:\s+and\s+keeps\s+(?:one\s+(?:group|pile|part|stack|bundle)|"
    r"one|a\s+(?:group|pile|part|stack|bundle)))?"
    r"$"
)

# Multiply / divide:
#   "<subject> doubles his savings" / "<subject> triples them"
# The scalar comes from the verb; the unit comes from state.last_unit
# (which the prior initial-possession or operation set).
_MULTIPLY_FACTOR_RE = re.compile(
    r"^"
    r"(?:(?P<subject>[A-Z]\w+|he|she|He|She|It|it)\s+)?"
    r"(?P<verb>doubles|triples)"
    r"(?:\s+\w+(?:\s+\w+)*)?"  # any trailing object phrase (e.g. "his savings")
    r"$"
)


def _resolve_subject(
    raw_subject: str | None,
    has_explicit_subject: bool,
    state: _ParserState,
) -> str | None:
    """Resolve pronouns and inherited subjects to an entity name.

    Returns ``None`` if no valid subject can be determined.
    """
    if raw_subject is None:
        if has_explicit_subject:
            return None  # malformed: explicit subject expected, none found
        return state.last_singular_subject
    if raw_subject.lower() in _SINGULAR_PRONOUNS:
        return state.last_singular_subject
    return raw_subject


def _try_operation(
    clause: str, state: _ParserState, has_explicit_subject: bool
) -> bool:
    # First, try multiply/divide-style verbs which don't take a numeric
    # operand from the text.
    mm = _MULTIPLY_FACTOR_RE.match(clause)
    if mm:
        return _apply_multiply(mm, state, has_explicit_subject)

    md = _DIVIDE_SPLIT_RE.match(clause)
    if md:
        return _apply_divide_split(md, state, has_explicit_subject)

    m = _OP_RE.match(clause)
    if not m:
        return False

    subject = _resolve_subject(m.group("subject"), has_explicit_subject, state)
    if subject is None:
        return False

    verb = m.group("verb").lower()
    value = int(m.group("value"))
    unit_raw = m.group("unit")
    target = m.group("target")

    if unit_raw is None:
        unit = state.last_unit
    elif unit_raw.lower() in _OBJECT_PRONOUNS_OF_QUANTITY:
        # "Sam adds 3 of them" — pronoun reference to last unit.
        unit = state.last_unit
    else:
        unit = _canonical_unit(unit_raw)
    if unit is None:
        return False

    if verb in _ADD_VERBS:
        if target is not None:
            return False  # add never takes a target
        op = Operation(
            actor=subject, kind="add", operand=Quantity(value=value, unit=unit)
        )
    elif verb in _SUBTRACT_VERBS:
        if target is not None:
            return False
        op = Operation(
            actor=subject, kind="subtract", operand=Quantity(value=value, unit=unit)
        )
    elif verb in _TRANSFER_VERBS:
        if target is None:
            return False  # transfer requires explicit target
        op = Operation(
            actor=subject,
            kind="transfer",
            operand=Quantity(value=value, unit=unit),
            target=target,
        )
        state.add_entity(target)
    else:
        return False

    state.add_entity(subject)
    state.operations.append(op)
    state.last_unit = unit
    state.last_singular_subject = subject
    # ADR-0122: track subject's current unit; transfer also gives the
    # target a quantity in that unit.
    state.actor_units[subject] = unit
    if verb in _TRANSFER_VERBS and target is not None:
        state.actor_units[target] = unit
    return True


def _apply_divide_split(
    m: re.Match[str], state: _ParserState, has_explicit_subject: bool
) -> bool:
    subject = _resolve_subject(m.group("subject"), has_explicit_subject, state)
    if subject is None:
        return False
    groups = int(m.group("groups"))
    if groups <= 0:
        return False
    # Resolve unit from whichever of the three syntactic frames matched.
    if m.group("object_pronoun") is not None:
        unit = state.last_unit
    elif m.group("possessive_unit") is not None:
        unit = _canonical_unit(m.group("possessive_unit"))
    elif m.group("explicit_unit") is not None:
        unit = _canonical_unit(m.group("explicit_unit"))
    else:
        unit = state.last_unit
    if unit is None:
        return False
    state.add_entity(subject)
    state.operations.append(
        Operation(
            actor=subject,
            kind="divide",
            operand=Quantity(value=groups, unit=unit),
        )
    )
    state.last_singular_subject = subject
    state.last_unit = unit
    state.actor_units[subject] = unit
    return True


def _apply_multiply(
    m: re.Match[str], state: _ParserState, has_explicit_subject: bool
) -> bool:
    subject = _resolve_subject(m.group("subject"), has_explicit_subject, state)
    if subject is None:
        return False
    verb = m.group("verb").lower()
    factor = _MULTIPLY_FACTOR_VERBS[verb]
    unit = state.last_unit
    if unit is None:
        return False
    state.add_entity(subject)
    state.operations.append(
        Operation(
            actor=subject,
            kind="multiply",
            operand=Quantity(value=factor, unit=unit),
        )
    )
    state.last_singular_subject = subject
    state.actor_units[subject] = unit
    return True


# ---------------------------------------------------------------------------
# Rate declaration patterns (ADR-0122)
# ---------------------------------------------------------------------------

# "Each <unit> costs $<N>" / "An <unit> costs $<N>"
# <N> accepts decimal: "$2", "$0.50", "$2.5"
_RATE_COST_EACH_RE = re.compile(
    r"^(?:Each|An?)\s+(?P<unit>\w+)\s+costs?\s+\$(?P<value>\d+(?:\.\d+)?)$",
    flags=re.IGNORECASE,
)

# "<units> cost $<N> each" — note plural unit on left, "each" on right
_RATE_COST_EACH_TRAILING_RE = re.compile(
    r"^(?P<unit>\w+)\s+costs?\s+\$(?P<value>\d+(?:\.\d+)?)\s+each$",
    flags=re.IGNORECASE,
)


def _try_rate_declaration(s: str, state: _ParserState) -> bool:
    """Try to parse a money-rate declaration sentence (ADR-0122).

    On match, record the rate keyed by the canonicalized denominator
    unit (singular noun pluralized, e.g. ``apple`` → ``apples``). The
    numerator unit is fixed at ``"dollars"`` for this ADR. Returns
    True iff a rate was recorded (or refused with ParseError on
    re-declaration).
    """
    for pattern in (_RATE_COST_EACH_RE, _RATE_COST_EACH_TRAILING_RE):
        m = pattern.match(s)
        if not m:
            continue
        denom = _canonical_unit(m.group("unit"))
        raw_value = m.group("value")
        value: int | float = (
            float(raw_value) if "." in raw_value else int(raw_value)
        )
        if denom in state.rates:
            raise ParseError(
                f"rate redeclaration for unit {denom!r}: first "
                f"{state.rates[denom]!r}, now ${value} (ADR-0122 "
                f"requires first-declaration-wins; ambiguity is "
                f"refused, not silently resolved)"
            )
        state.rates[denom] = Rate(
            value=value,
            numerator_unit="dollars",
            denominator_unit=denom,
        )
        return True
    return False


# ---------------------------------------------------------------------------
# ADR-0123 — Comparison declaration patterns
# ADR-0123a — Shape-gap expansions (Groups 1/3/4/6/8 from Gemini Task 5)
# ---------------------------------------------------------------------------

# ADR-0123a Group 8 — supported verbs for comparison (present + past +
# acquire/spend lemmas). Includes plural-subject agreement ("have", "get",
# "take", "buy"). Excludes "lost" / "won" because they semantically invert
# direction ("Alice lost 3 more than Bob" ≠ "Alice has 3 more than Bob");
# silently mapping them would violate wrong==0.
_COMPARE_VERB = r"(?:has|have|had|gets|get|got|takes|take|took|buys|buy|bought)"

# ADR-0123a Group 3 — word-form integers accepted as comparison multipliers
# or additive values. Range 1..12 covers all sealed-set occurrences.
_WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_NUMBER = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
)

# ADR-0123a Group 1 — actor / reference slots accept:
#   - Proper noun ("Alice")
#   - Pronoun (resolved via state.last_singular_subject at emit time)
#   - Definite-article collective ("the boys", "the twins")
# Possessives ("Alice's collection") are deferred — they change the
# attribute model, not just the regex.
_ACTOR_SLOT = (
    r"(?:[A-Z]\w+|[Hh]e|[Ss]he|[Tt]hey|[Ii]t|[Tt]he\s+\w+)"
)
_REF_SLOT = (
    r"(?:[A-Z]\w+|him|her|them|it|[Tt]he\s+\w+|[Hh]is|[Hh]ers|[Tt]heirs)"
)


def _parse_compare_number(s: str) -> int:
    """Parse an integer that may be written as a digit string or a word.

    ADR-0123a Group 3. Returns the int value; raises ValueError on
    anything not in _WORD_NUMBERS and not int-parseable (defensive
    against regex drift).
    """
    if s.isdigit():
        return int(s)
    return _WORD_NUMBERS[s.lower()]


def _resolve_compare_entity(
    raw: str, state: _ParserState, *, sentence: str, role: str
) -> str:
    """Resolve a raw actor/reference token to a canonical entity name.

    ADR-0123a Group 1. Proper nouns and "the X" collectives are used
    verbatim (with whitespace collapsed). Pronouns resolve against
    ``state.last_singular_subject``; a pronoun with no prior subject is
    refused (ParseError) rather than silently dropped — otherwise the
    parser would emit a comparison with an empty actor.
    """
    rl = raw.lower().strip()
    pronouns_actor = {"he", "she", "they", "it"}
    pronouns_ref = {"him", "her", "them", "it", "his", "hers", "theirs"}
    if rl in pronouns_actor or rl in pronouns_ref:
        if state.last_singular_subject is None:
            raise ParseError(
                f"ADR-0123 refuses comparison sentence {sentence!r}: "
                f"{role} pronoun {raw!r} has no prior subject to resolve "
                f"against (would emit a comparison with no anchored entity)"
            )
        return state.last_singular_subject
    # Proper noun or "the X" — collapse whitespace; lowercase the
    # leading article so "The boys" and "the boys" canonicalize to the
    # same entity string (matches _try_initial's normalization).
    canon = re.sub(r"\s+", " ", raw.strip())
    if canon.lower().startswith("the "):
        canon = "the " + canon[4:]
    return canon


# Group A (additive): "Alice has 3 more apples than Bob"
# "less" treated as informal synonym of "fewer" — both map to direction='fewer'.
# ADR-0123a: subject/verb/value/reference slots widened (Groups 1/3/8).
_COMPARE_ADDITIVE_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+"
    rf"(?P<value>{_NUMBER})\s+"
    r"(?P<direction>more|fewer|less)\s+"
    r"(?P<unit>\w+)\s+than\s+"
    rf"(?P<reference>{_REF_SLOT})$"
)

# Group B (multiplicative — twice): "Alice has twice as many apples as Bob"
# ADR-0123a: subject/verb/reference slots widened (Groups 1/8); optional
# unit (Group 4 ellipsis: "Alice took twice as many as Bob").
_COMPARE_TWICE_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+twice\s+as\s+many"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)

# Group B (multiplicative — N times): "Alice has 3 times as many apples as Bob"
# ADR-0123a: subject/verb/value/reference slots widened (Groups 1/3/8);
# optional unit (Group 4 ellipsis).
_COMPARE_N_TIMES_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+"
    rf"(?P<value>{_NUMBER})\s+times\s+as\s+many"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)

# Group C (fractional — half): "Alice has half as many apples as Bob"
# ADR-0123a: subject/verb/reference slots widened (Groups 1/8); optional
# unit (Group 4 ellipsis).
_COMPARE_HALF_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+half\s+as\s+many"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)

# ADR-0123a Group 4 — "as much" and "the number/amount of" variants.
# These are multiplicative comparisons phrased over mass nouns or with
# the alternate "the (number|amount) of <unit>" construction. Unit is
# always optional (multiplicative semantics infer it from reference state).
_COMPARE_TWICE_AS_MUCH_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+twice\s+as\s+much"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)
_COMPARE_N_TIMES_AS_MUCH_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+"
    rf"(?P<value>{_NUMBER})\s+times\s+as\s+much"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)
_COMPARE_HALF_AS_MUCH_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+half\s+as\s+much"
    rf"(?:\s+(?P<unit>\w+))?\s+as\s+(?P<reference>{_REF_SLOT})$"
)
_COMPARE_TWICE_THE_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+twice\s+the\s+"
    r"(?:number|amount)\s+of\s+(?P<unit>\w+)\s+as\s+"
    rf"(?P<reference>{_REF_SLOT})$"
)
_COMPARE_N_TIMES_THE_RE = re.compile(
    rf"^(?P<actor>{_ACTOR_SLOT})\s+{_COMPARE_VERB}\s+"
    rf"(?P<value>{_NUMBER})\s+times\s+the\s+(?:number|amount)\s+of\s+"
    rf"(?P<unit>\w+)\s+as\s+(?P<reference>{_REF_SLOT})$"
)

# Forms the parser deliberately REFUSES (multi-construction / out of
# substrate scope). Better an honest typed ParseError than a misleading
# fallthrough.
_COMPARE_REFUSE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"^[A-Z]\w+\s+has\s+\d+\s+times\s+more\s+\w+\s+than\s+[A-Z]\w+$"
        ),
        "ambiguous 'N times more' (use 'N times as many' for unambiguous "
        "multiplicative comparison; ADR-0123 refuses the ambiguous form)",
    ),
    (
        re.compile(
            r"^[A-Z]\w+\s+is\s+(?:\d+\s+times\s+)?as\s+old\s+as\s+[A-Z]\w+$",
            flags=re.IGNORECASE,
        ),
        "age comparisons use a different actor-attribute model than "
        "holdings; out of ADR-0123 substrate scope",
    ),
    (
        re.compile(
            r"^[A-Z]\w+\s+is\s+\d+\s+years\s+(?:older|younger)\s+than\s+[A-Z]\w+$",
            flags=re.IGNORECASE,
        ),
        "age comparisons ('N years older/younger') are out of ADR-0123 "
        "substrate scope",
    ),
    (
        re.compile(
            r"^[A-Z]\w+\s+has\s+.*\b(?:combined|together)\b.*$",
            flags=re.IGNORECASE,
        ),
        "comparison combined with aggregation needs ADR-0126 to co-land; "
        "ADR-0123 alone refuses",
    ),
    (
        re.compile(
            r"^[A-Z]\w+\s+has\s+\d+\s+(?:more|fewer|less)\s+than\s+"
            r"(?:twice|\d+\s+times)\s+as\s+many\s+\w+\s+as\s+[A-Z]\w+$"
        ),
        "nested additive + multiplicative comparison needs both classes "
        "to co-resolve; ADR-0123 substrate refuses the nested form",
    ),
)


def _try_comparison_declaration(s: str, state: _ParserState) -> bool:
    """Try to parse a comparison-declaration sentence (ADR-0123).

    Order: happy-path patterns first (additive, then multiplicative by
    specificity), then explicit refusal patterns. Falling through
    returns False (the sentence is not a comparison; dispatcher
    proceeds to ``_try_initial``).
    """
    # ADR-0123a — additive (Group A): widened subject/verb/value slots.
    m = _COMPARE_ADDITIVE_RE.match(s)
    if m:
        actor = _resolve_compare_entity(
            m.group("actor"), state, sentence=s, role="actor"
        )
        value = _parse_compare_number(m.group("value"))
        direction_raw = m.group("direction").lower()
        direction = "more" if direction_raw == "more" else "fewer"
        unit = _canonical_unit(m.group("unit"))
        reference = _resolve_compare_entity(
            m.group("reference"), state, sentence=s, role="reference"
        )
        return _emit_comparison(
            state,
            actor=actor,
            reference=reference,
            kind="compare_additive",
            delta=Quantity(value=value, unit=unit),
            factor=None,
            direction=direction,
            sentence=s,
            tracking_unit=unit,
        )

    # ADR-0123a — multiplicative (Group B / Group 4 variants).
    # Each branch resolves entities, parses the (possibly word-form)
    # multiplier value, and emits with optional unit (None → solver
    # infers from reference's unique-unit state).
    for pattern, factor_kind in (
        (_COMPARE_TWICE_RE, ("times", 2.0)),
        (_COMPARE_TWICE_AS_MUCH_RE, ("times", 2.0)),
        (_COMPARE_TWICE_THE_RE, ("times", 2.0)),
        (_COMPARE_HALF_RE, ("fraction", 0.5)),
        (_COMPARE_HALF_AS_MUCH_RE, ("fraction", 0.5)),
    ):
        m = pattern.match(s)
        if m:
            direction, factor = factor_kind
            unit_raw = m.groupdict().get("unit")
            tracking_unit = _canonical_unit(unit_raw) if unit_raw else ""
            actor = _resolve_compare_entity(
                m.group("actor"), state, sentence=s, role="actor"
            )
            reference = _resolve_compare_entity(
                m.group("reference"), state, sentence=s, role="reference"
            )
            return _emit_comparison(
                state,
                actor=actor,
                reference=reference,
                kind="compare_multiplicative",
                delta=None,
                factor=factor,
                direction=direction,
                sentence=s,
                tracking_unit=tracking_unit,
            )

    for pattern in (_COMPARE_N_TIMES_RE, _COMPARE_N_TIMES_AS_MUCH_RE,
                    _COMPARE_N_TIMES_THE_RE):
        m = pattern.match(s)
        if m:
            unit_raw = m.groupdict().get("unit")
            tracking_unit = _canonical_unit(unit_raw) if unit_raw else ""
            value = _parse_compare_number(m.group("value"))
            actor = _resolve_compare_entity(
                m.group("actor"), state, sentence=s, role="actor"
            )
            reference = _resolve_compare_entity(
                m.group("reference"), state, sentence=s, role="reference"
            )
            return _emit_comparison(
                state,
                actor=actor,
                reference=reference,
                kind="compare_multiplicative",
                delta=None,
                factor=float(value),
                direction="times",
                sentence=s,
                tracking_unit=tracking_unit,
            )

    for refuse_pattern, reason in _COMPARE_REFUSE_PATTERNS:
        if refuse_pattern.match(s):
            raise ParseError(
                f"ADR-0123 refuses comparison sentence {s!r}: {reason}"
            )

    return False


def _emit_comparison(
    state: _ParserState,
    *,
    actor: str,
    reference: str,
    kind: str,
    delta: Quantity | None,
    factor: float | None,
    direction: str,
    sentence: str,
    tracking_unit: str,
) -> bool:
    """Append the Operation, register entities, update tracking state.

    Returns True unconditionally — caller's short-circuit treats True
    as "sentence consumed; stop dispatch". Refuses (ParseError) on
    self-reference; other semantic refusals live in the solver.
    """
    if actor == reference:
        raise ParseError(
            f"ADR-0123 refuses self-referential comparison: actor and "
            f"reference are both {actor!r} in sentence {sentence!r}"
        )
    state.add_entity(actor)
    state.add_entity(reference)
    state.operations.append(
        Operation(
            actor=actor,
            kind=kind,
            operand=Comparison(
                reference_actor=reference,
                delta=delta,
                factor=factor,
                direction=direction,  # type: ignore[arg-type]
            ),
        )
    )
    state.last_unit = tracking_unit
    state.last_singular_subject = actor
    return True


# ---------------------------------------------------------------------------
# Question patterns
# ---------------------------------------------------------------------------

# ADR-0123a widens entity slot to match initial-possession / comparison
# subjects: proper noun OR "the X" collective. Auxiliary widened to
# do/does for plural-collective subjects ("How many cards do the girls
# have?"). Pronoun subjects in questions are not accepted — the question
# must name the entity unambiguously.
_Q_ENTITY_RE = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+(?:does|do)\s+"
    r"(?P<entity>[A-Z]\w+|[Tt]he\s+\w+)"
    r"\s+have(?:\s+(?:left|now|in\s+total|altogether)){0,2}$",
    flags=re.IGNORECASE,
)

_Q_TOTAL_RE = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+do\s+they\s+have"
    r"(?:\s+(?:in\s+total|altogether|left|now)){0,2}$",
    flags=re.IGNORECASE,
)

# ADR-0122 rate-aggregate: "How much does X spend|pay|earn?"
# The verb is captured for telemetry / future hedging but the
# semantics are the same: apply X's matching rate to X's quantity.
_Q_RATE_AGGREGATE_RE = re.compile(
    r"^How\s+much\s+does\s+(?P<entity>[A-Z]\w+)"
    r"\s+(?P<verb>spend|pay|earn)"
    r"(?:\s+(?:in\s+total|altogether|now))?$",
    flags=re.IGNORECASE,
)


def _process_question(sentence: str, state: _ParserState) -> None:
    s = sentence.rstrip("?").strip()

    # ADR-0123a: try the total-across question FIRST. With the widened
    # entity regex accepting "do" as auxiliary, "do they have" would
    # otherwise greedily capture "they" as an entity name — but "they"
    # is reserved for total-across semantics. Order = specificity.
    m = _Q_TOTAL_RE.match(s)
    if m:
        unit = _canonical_unit(m.group("unit"))
        state.unknown = Unknown(entity=None, unit=unit)
        return

    m = _Q_ENTITY_RE.match(s)
    if m:
        unit = _canonical_unit(m.group("unit"))
        entity_raw = m.group("entity")
        # ADR-0123a — canonicalize "the X" the same way initial possession
        # does (lowercase article, collapse whitespace) so the question
        # resolves to the same entity name stored earlier.
        entity = re.sub(r"\s+", " ", entity_raw.strip())
        if entity.lower().startswith("the "):
            entity = "the " + entity[4:]
        if entity not in state.entities:
            raise ParseError(
                f"question references undefined entity {entity!r}: {sentence!r}"
            )
        state.unknown = Unknown(entity=entity, unit=unit)
        return

    m = _Q_RATE_AGGREGATE_RE.match(s)
    if m:
        _process_rate_aggregate_question(m, sentence, state)
        return

    raise ParseError(f"could not parse question: {sentence!r}")


def _process_rate_aggregate_question(
    m: re.Match[str], sentence: str, state: _ParserState
) -> None:
    """Resolve a "How much does X spend|pay|earn?" question (ADR-0122).

    Looks up the entity's current unit (the denominator), finds the
    matching declared rate, emits an ``apply_rate`` operation, and
    sets ``state.unknown`` to ``Unknown(entity, rate.numerator_unit)``.

    Three refusal paths (each a typed :class:`ParseError`):
    - entity never introduced
    - entity has no current unit (no initial possession or operation
      established what they hold)
    - no declared rate matches the entity's current unit
    """
    entity = m.group("entity")
    if entity not in state.entities:
        raise ParseError(
            f"rate-aggregate question references undefined entity "
            f"{entity!r}: {sentence!r}"
        )
    denom = state.actor_units.get(entity)
    if denom is None:
        raise ParseError(
            f"rate-aggregate question asks about {entity!r} but no "
            f"statement established what {entity!r} holds: {sentence!r}"
        )
    rate = state.rates.get(denom)
    if rate is None:
        raise ParseError(
            f"rate-aggregate question asks how much {entity!r} "
            f"spends/pays/earns on {denom!r}, but no rate was "
            f"declared for {denom!r}: {sentence!r}"
        )
    state.operations.append(
        Operation(actor=entity, kind="apply_rate", operand=rate)
    )
    state.rate_applied = True
    state.actor_units[entity] = rate.numerator_unit
    state.last_unit = rate.numerator_unit
    state.last_singular_subject = entity
    state.unknown = Unknown(entity=entity, unit=rate.numerator_unit)

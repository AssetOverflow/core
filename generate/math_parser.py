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
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
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

# "<Entity> has <N> <unit>." — entity must be a Title-Cased word.
_INITIAL_HAS_RE = re.compile(
    r"^(?P<entity>[A-Z]\w+)\s+has\s+(?P<value>\d+)\s+(?P<unit>\w+)$"
)


def _process_statement(sentence: str, state: _ParserState) -> None:
    s = sentence.rstrip(".").strip()

    # Strip leading "Then " sequence marker — operation inherits subject
    # and unit from the prior sentence. Same semantics as the in-sentence
    # ", then" compound marker, just punctuated as a separate sentence.
    sentence_opens_with_then = bool(_SENTENCE_OPENER_THEN_RE.match(s))
    if sentence_opens_with_then:
        s = _SENTENCE_OPENER_THEN_RE.sub("", s).strip()

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
    entity = m.group("entity")
    value = int(m.group("value"))
    unit = _canonical_unit(m.group("unit"))
    state.add_entity(entity)
    state.initial_state.append(
        InitialPossession(entity=entity, quantity=Quantity(value=value, unit=unit))
    )
    state.last_unit = unit
    state.last_singular_subject = entity
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
    return True


# ---------------------------------------------------------------------------
# Question patterns
# ---------------------------------------------------------------------------

_Q_ENTITY_RE = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+does\s+(?P<entity>[A-Z]\w+)"
    r"\s+have(?:\s+(?:left|now|in\s+total|altogether)){0,2}$",
    flags=re.IGNORECASE,
)

_Q_TOTAL_RE = re.compile(
    r"^How\s+many\s+(?P<unit>\w+)\s+do\s+they\s+have"
    r"(?:\s+(?:in\s+total|altogether|left|now)){0,2}$",
    flags=re.IGNORECASE,
)


def _process_question(sentence: str, state: _ParserState) -> None:
    s = sentence.rstrip("?").strip()

    m = _Q_ENTITY_RE.match(s)
    if m:
        unit = _canonical_unit(m.group("unit"))
        entity = m.group("entity")
        # Preserve case of the entity as written; entity must already be
        # introduced by the statements above.
        if entity not in state.entities:
            raise ParseError(
                f"question references undefined entity {entity!r}: {sentence!r}"
            )
        state.unknown = Unknown(entity=entity, unit=unit)
        return

    m = _Q_TOTAL_RE.match(s)
    if m:
        unit = _canonical_unit(m.group("unit"))
        state.unknown = Unknown(entity=None, unit=unit)
        return

    raise ParseError(f"could not parse question: {sentence!r}")

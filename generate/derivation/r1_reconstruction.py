"""R1 GSM8K reconstruction: explicit comparative-derived totals.

This is a narrow serving-safe reader for the first answer-changing GSM8K
reconstruction slice.  It emits a real :class:`MathProblemGraph` and admits only
after the normal solver and verifier replay the graph successfully.

Scope is deliberately small:

* one referenced source quantity;
* one comparative-derived quantity over the same canonical unit;
* a total-style question over the source + derived quantities.

Everything else returns a typed refusal reason so the caller can preserve the
existing refusal path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Final

from generate.math_candidate_parser import _resolve_value
from generate.math_problem_graph import (
    Comparison,
    InitialPossession,
    MathGraphError,
    MathProblemGraph,
    Operation,
    Quantity,
    Unknown,
)
from generate.math_solver import SolveError, solve
from generate.math_verifier import verify
from language_packs.numerics_loader import parse_compound_cardinal


@dataclass(frozen=True, slots=True)
class R1Reconstruction:
    graph: MathProblemGraph | None
    answer: float | None
    reader_trace: tuple[str, ...]
    refusal_reason: str | None

    @property
    def is_admitted(self) -> bool:
        return self.graph is not None and self.answer is not None


@dataclass(frozen=True, slots=True)
class _Fact:
    entity: str
    value: float
    unit: str
    source_token: str
    sentence_index: int


@dataclass(frozen=True, slots=True)
class _Comparative:
    actor: str
    factor: float
    factor_token: str
    unit: str | None
    reference: str | None
    sentence_index: int
    source_span: str
    implicit_kind: str | None = None


_SENTENCE_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")
_WORD_VALUE: Final[str] = (
    r"(?:a\s+|an\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"hundred|thousand)(?:[-\s]+(?:one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
    r"ninety|hundred|thousand))*"
)
_VALUE: Final[str] = rf"(?:\$\d+(?:\.\d+)?|\d+(?:\.\d+)?|{_WORD_VALUE})"
_FACTOR: Final[str] = rf"(?:twice|double|triple|quadruple|{_VALUE})"
_VERB: Final[str] = (
    r"(?:has|have|had|having|is|are|was|were|cost|costs|costed|scored|"
    r"taught|teaches|made|makes|owns|owned|caught|collected|received|earned)"
)
_MULTIPLIER_WORDS: Final[frozenset[str]] = frozenset(
    {"twice", "double", "triple", "quadruple"}
)

_THERE_FACT_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?:^|,\s*)there\s+(?:are|were|is|was)\s+(?P<value>{_VALUE})\s+"
    r"(?P<unit>(?:male|female|high school|new|old|large|small)?\s*[A-Za-z]+)",
    re.IGNORECASE,
)
_ENTITY_FACT_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<entity>[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){{0,3}}|"
    r"(?:the\s+)?[a-z]+(?:\s+[a-z]+){0,2})\s+"
    rf"(?P<verb>{_VERB})\s+"
    rf"(?P<value>{_VALUE})"
    r"(?:\s+(?P<unit>[A-Za-z]+(?:\s+[A-Za-z]+)?))?",
    re.IGNORECASE,
)
_RELATIVE_FACT_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?:as|than)\s+(?P<entity>[^,.?]+?),\s+who\s+{_VERB}\s+"
    rf"(?P<value>{_VALUE})\s+(?P<unit>[A-Za-z]+)",
    re.IGNORECASE,
)

_EXPLICIT_AS_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>{_FACTOR})\s+"
    r"(?:times\s+)?(?:as\s+many|as\s+much)\s+"
    r"(?P<unit>[A-Za-z]+(?:\s+[A-Za-z]+)?)?\s+as\s+(?P<ref>[^,.?]+)",
    re.IGNORECASE,
)
_THE_NUMBER_AS_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>{_FACTOR})\s+times\s+the\s+number\s+of\s+"
    r"(?P<unit>[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+as\s+(?P<ref>[^,.?]+)",
    re.IGNORECASE,
)
_GREATER_THAN_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>{_FACTOR})\s+times\s+"
    r"(?:greater|more)(?:\s+(?P<unit>[A-Za-z]+(?:\s+[A-Za-z]+)?))?\s+(?:than|as)\s+"
    r"(?:the\s+)?(?:cost\s+of\s+)?(?P<ref>[^,.?]+)",
    re.IGNORECASE,
)
_DOUBLE_WHAT_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>twice|double)\s+what\s+(?P<ref>[^,.?]+)",
    re.IGNORECASE,
)
_THAT_MANY_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>{_FACTOR})\s+times\s+that\s+many\s+"
    r"(?P<unit>[A-Za-z]+)",
    re.IGNORECASE,
)
_IMPLICIT_GENDER_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<prefix>.+?)\b(?P<factor>{_FACTOR})\s+"
    r"(?:times\s+)?as\s+many\s+(?P<unit>male\s+students|female\s+students)",
    re.IGNORECASE,
)


def reconstruct_r1_total(problem_text: str) -> R1Reconstruction | None:
    """Attempt R1 reconstruction, returning None when no R1 signal exists."""
    sentences = _sentences(problem_text)
    if not sentences:
        return None
    statements = [s for s in sentences if not s.rstrip().endswith("?")]
    question = next((s for s in reversed(sentences) if s.rstrip().endswith("?")), "")
    if not question:
        return None
    source_clauses = [*statements, *_question_given_clauses(question)]

    comparatives = _comparatives(statements, problem_text)
    if not comparatives:
        return None
    trace: list[str] = []
    if len(comparatives) != 1:
        return _refuse("multiple_comparatives", trace)
    comparative = comparatives[0]
    trace.append(_event("matched_comparative", actor=comparative.actor, sentence_index=comparative.sentence_index))

    if not _question_targets_total(question, comparative):
        return _refuse("question_not_total_target", trace)

    facts = _facts(source_clauses, problem_text)
    ref = _bind_reference(comparative, facts)
    if ref is None:
        return _refuse("reference_not_grounded", trace)
    derived_unit = _canonical_unit(comparative.unit or ref.unit)
    if derived_unit != ref.unit:
        return _refuse("unit_mismatch", trace, derived_unit=derived_unit, reference_unit=ref.unit)

    unused = _unused_source_quantity_tokens(source_clauses, ref, comparative)
    if unused:
        return _refuse("incomplete_source_quantities", trace, unused=unused)

    try:
        graph = _graph(ref, comparative, derived_unit)
        solved = solve(graph)
        verdict = verify(graph, solved)
    except (MathGraphError, SolveError, ValueError) as exc:
        return _refuse("graph_or_solver_refused", trace, error=str(exc))
    if not verdict.passed:
        return _refuse("verifier_refused", trace, reason=verdict.reason)

    trace.append(_event("admitted", answer=solved.answer_value))
    return R1Reconstruction(
        graph=graph,
        answer=solved.answer_value,
        reader_trace=tuple(trace),
        refusal_reason=None,
    )


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _question_given_clauses(question: str) -> tuple[str, ...]:
    """Conditional givens inside the question, e.g. ``If X has 22 sharks, ...``."""
    match = re.match(r"\s*if\s+(.+?),\s*(?:how|what|which|who|when|where)\b", question, re.IGNORECASE)
    return (match.group(1).strip(),) if match else ()


def _facts(statements: list[str], problem_text: str) -> list[_Fact]:
    out: list[_Fact] = []
    discourse_subject = _first_proper_noun(problem_text)
    for idx, sentence in enumerate(statements):
        for match in _THERE_FACT_RE.finditer(sentence):
            if _value_is_comparative_factor(sentence, match.end("value")):
                continue
            fact = _fact_from_parts(
                entity=match.group("unit"),
                value_token=match.group("value"),
                unit=match.group("unit"),
                sentence_index=idx,
            )
            if fact is not None:
                out.append(fact)
        for match in _RELATIVE_FACT_RE.finditer(sentence):
            fact = _fact_from_parts(
                entity=match.group("entity"),
                value_token=match.group("value"),
                unit=match.group("unit"),
                sentence_index=idx,
            )
            if fact is not None:
                out.append(fact)
        for match in _ENTITY_FACT_RE.finditer(sentence):
            if _value_is_comparative_factor(sentence, match.end("value")):
                continue
            entity = _clean_entity(match.group("entity"))
            if entity.lower() in {"he", "she"} and discourse_subject is not None:
                entity = discourse_subject
            if entity.lower() in {"there", "who", "what"}:
                continue
            unit = match.group("unit")
            fact = _fact_from_parts(
                entity=entity,
                value_token=match.group("value"),
                unit=unit,
                sentence_index=idx,
            )
            if fact is not None:
                out.append(fact)
    return _dedupe_facts(out)


def _value_is_comparative_factor(sentence: str, value_end: int) -> bool:
    tail = sentence[value_end:value_end + 16].lower()
    return bool(re.match(r"\s+times\b", tail))


def _fact_from_parts(
    *,
    entity: str,
    value_token: str,
    unit: str | None,
    sentence_index: int,
) -> _Fact | None:
    value = _parse_value(value_token)
    if value is None:
        return None
    value_number, value_unit = value
    final_unit = _canonical_unit(value_unit or unit or "")
    if not final_unit:
        return None
    return _Fact(
        entity=_clean_entity(entity),
        value=value_number,
        unit=final_unit,
        source_token=_quantity_surface_token(value_token),
        sentence_index=sentence_index,
    )


def _comparatives(statements: list[str], problem_text: str) -> list[_Comparative]:
    out: list[_Comparative] = []
    discourse_subject = _first_proper_noun(problem_text)
    for idx, sentence in enumerate(statements):
        for pattern in (
            _THE_NUMBER_AS_RE,
            _EXPLICIT_AS_RE,
            _GREATER_THAN_RE,
            _DOUBLE_WHAT_RE,
            _THAT_MANY_RE,
            _IMPLICIT_GENDER_RE,
        ):
            match = pattern.search(sentence)
            if match is None:
                continue
            factor = _parse_factor(match.group("factor"))
            if factor is None:
                continue
            ref = match.groupdict().get("ref")
            unit = match.groupdict().get("unit")
            implicit_kind = None
            if pattern is _THAT_MANY_RE:
                implicit_kind = "that_many"
            elif pattern is _IMPLICIT_GENDER_RE:
                implicit_kind = "gender_pair"
            actor = _actor_from_prefix(match.group("prefix"), discourse_subject)
            if actor is None and implicit_kind in {"that_many", "gender_pair"} and unit:
                actor = _clean_entity(unit)
            if actor is None:
                continue
            out.append(
                _Comparative(
                    actor=actor,
                    factor=factor,
                    factor_token=_quantity_surface_token(match.group("factor")),
                    unit=unit,
                    reference=_clean_reference(ref) if ref else None,
                    sentence_index=idx,
                    source_span=sentence,
                    implicit_kind=implicit_kind,
                )
            )
            break
    return out


def _bind_reference(comparative: _Comparative, facts: list[_Fact]) -> _Fact | None:
    if comparative.reference:
        for fact in reversed(facts):
            if _entity_matches(fact.entity, comparative.reference):
                return fact
        return None

    if comparative.implicit_kind == "gender_pair":
        target_unit = _canonical_unit(comparative.unit or "")
        candidates = [
            f for f in facts
            if f.sentence_index < comparative.sentence_index
            and f.unit == target_unit
            and _is_gender_counterpart(f.entity, comparative.actor)
        ]
        return candidates[0] if len(candidates) == 1 else None

    if comparative.implicit_kind == "that_many":
        target_unit = _canonical_unit(comparative.unit or "")
        candidates = [
            f for f in facts
            if f.sentence_index < comparative.sentence_index and f.unit == target_unit
        ]
        return candidates[0] if len(candidates) == 1 else None
    return None


def _graph(ref: _Fact, comparative: _Comparative, unit: str) -> MathProblemGraph:
    entities = (ref.entity, comparative.actor)
    return MathProblemGraph(
        entities=entities,
        initial_state=(
            InitialPossession(ref.entity, Quantity(ref.value, unit)),
        ),
        operations=(
            Operation(
                actor=comparative.actor,
                kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor=ref.entity,
                    delta=None,
                    factor=comparative.factor,
                    direction="times",
                ),
            ),
        ),
        unknown=Unknown(entity=None, unit=unit),
    )


def _parse_value(token: str) -> tuple[float, str | None] | None:
    raw = token.strip().rstrip(".,?")
    if raw.startswith("$"):
        try:
            return float(raw[1:]), "dollars"
        except ValueError:
            return None
    normalized = _strip_article(raw.lower())
    if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return float(normalized), None
    parsed = parse_compound_cardinal(normalized)
    if parsed is not None:
        return float(parsed), None
    resolved = _resolve_value(normalized)
    if resolved is None:
        return None
    return float(resolved.value), resolved.unit_override


def _parse_factor(token: str) -> float | None:
    raw = token.strip().lower().rstrip(".,?")
    if raw in {"twice", "double"}:
        return 2.0
    if raw == "triple":
        return 3.0
    if raw == "quadruple":
        return 4.0
    parsed = _parse_value(raw)
    return parsed[0] if parsed is not None else None


def _question_targets_total(question: str, comparative: _Comparative) -> bool:
    lowered = question.lower()
    total_cue = any(
        cue in lowered
        for cue in ("total", "altogether", "combined", "together", "both", "in all")
    )
    if total_cue:
        return True
    if comparative.unit is not None and "how many" in lowered:
        q_unit = _canonical_unit(_words_after_how_many(question))
        if q_unit and q_unit == _canonical_unit(comparative.unit):
            return True
    if "how much" in lowered and any(word in lowered for word in ("spent", "cost", "accessor")):
        return True
    return False


def _words_after_how_many(question: str) -> str:
    match = re.search(r"how\s+many\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", question, re.IGNORECASE)
    return match.group(1) if match else ""


def _unused_source_quantity_tokens(
    statements: list[str],
    ref: _Fact,
    comparative: _Comparative,
) -> tuple[str, ...]:
    required: list[str] = []
    for sentence in statements:
        required.extend(_quantity_surfaces(sentence))
    consumed = {ref.source_token.lower(), comparative.factor_token.lower()}
    return tuple(
        token for token in required
        if token.lower() not in consumed
    )


def _quantity_surfaces(text: str) -> tuple[str, ...]:
    surfaces: list[str] = []
    for match in re.finditer(r"\$\d+(?:\.\d+)?|\d+(?:\.\d+)?", text):
        surfaces.append(match.group(0))
    for match in re.finditer(r"\b(twice|double|triple|quadruple)\b", text, re.IGNORECASE):
        surfaces.append(match.group(1).lower())
    word = (
        r"(?:a\s+|an\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
        r"hundred|thousand)(?:[-\s]+(?:one|two|three|four|five|six|seven|"
        r"eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
        r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
        r"seventy|eighty|ninety|hundred|thousand))*"
    )
    for match in re.finditer(rf"\b{word}\b", text, re.IGNORECASE):
        token = _quantity_surface_token(match.group(0))
        if token.lower() not in _MULTIPLIER_WORDS:
            surfaces.append(token)
    return tuple(dict.fromkeys(surfaces))


def _quantity_surface_token(token: str) -> str:
    raw = token.strip().lower().rstrip(".,?")
    raw = _strip_article(raw)
    parts = [p for p in re.split(r"[\s-]+", raw) if p and p != "and"]
    return " ".join(parts) if parts else raw


def _canonical_unit(unit: str) -> str:
    raw = re.sub(r"[^A-Za-z\s]", "", unit).lower().strip()
    if not raw:
        return ""
    tokens = tuple(t for t in raw.split() if t not in {"of", "the", "a", "an", "as"})
    if not tokens:
        return ""
    if "student" in tokens or "students" in tokens:
        return "students"
    if any(t in {"lady", "ladies", "girl", "girls", "boy", "boys", "people", "person"} for t in tokens):
        return "people"
    if "credit" in tokens or "credits" in tokens:
        return "credits"
    head = tokens[-1]
    if head.endswith("ies"):
        return head[:-3] + "ies"
    if head.endswith("s") or head in {"dice"}:
        return head
    return head + "s"


def _actor_from_prefix(prefix: str, discourse_subject: str | None) -> str | None:
    text = re.sub(r"^[,.\s]+", "", prefix.strip())
    text = re.sub(r"^(?:if|and|but|while|meanwhile)\s+", "", text, flags=re.IGNORECASE)
    cost_match = re.search(r"cost\s+of\s+(?:the\s+)?(?P<actor>[A-Za-z][A-Za-z\s]+?)\s+(?:was|is|were|are)?$", text, re.IGNORECASE)
    if cost_match:
        return _clean_entity(cost_match.group("actor"))
    there_match = re.search(r"there\s+(?:are|were|is|was)\s*$", text, re.IGNORECASE)
    if there_match:
        return None
    verb_match = re.search(rf"(?P<actor>.+?)\s+{_VERB}\s*$", text, re.IGNORECASE)
    actor_raw = verb_match.group("actor") if verb_match else text
    actor_raw = re.sub(r"^.*\bcolleague\s+", "", actor_raw, flags=re.IGNORECASE)
    actor_raw = actor_raw.strip()
    if actor_raw.lower() in {"he", "she", "his", "her"}:
        return discourse_subject
    return _clean_entity(actor_raw)


def _clean_reference(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = re.split(r"\b(?:has|have|had|is|are|was|were|teaches|teach|scored)\b", raw, maxsplit=1, flags=re.IGNORECASE)[0]
    return _clean_entity(text)


def _clean_entity(raw: str) -> str:
    text = re.sub(r"[^A-Za-z0-9\s]", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:if|the|a|an|his|her|their|this|that)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:who|which|that)$", "", text, flags=re.IGNORECASE)
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"dad", "father"}:
        return "dad"
    if lowered in {"mom", "mother"}:
        return "mom"
    if "female student" in lowered:
        return "female students"
    if "male student" in lowered:
        return "male students"
    return " ".join(part.capitalize() if part.islower() else part for part in text.split())


def _first_proper_noun(text: str) -> str | None:
    match = re.search(r"\b([A-Z][a-z]+)\b", text)
    return match.group(1) if match else None


def _entity_matches(entity: str, reference: str) -> bool:
    e = _entity_key(entity)
    r = _entity_key(reference)
    return e == r or e.endswith(r) or r.endswith(e)


def _entity_key(entity: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", entity.lower())


def _is_gender_counterpart(source: str, actor: str) -> bool:
    s = set(source.lower().split())
    a = set(actor.lower().split())
    return (
        ("female" in s and "male" in a)
        or ("male" in s and "female" in a)
        or ("girls" in s and "boys" in a)
        or ("boys" in s and "girls" in a)
    )


def _dedupe_facts(facts: list[_Fact]) -> list[_Fact]:
    out: list[_Fact] = []
    seen: set[tuple[str, str, float, int]] = set()
    for fact in facts:
        key = (_entity_key(fact.entity), fact.unit, fact.value, fact.sentence_index)
        if key in seen:
            continue
        seen.add(key)
        out.append(fact)
    return out


def _strip_article(text: str) -> str:
    return re.sub(r"^(?:a|an)\s+", "", text.strip(), flags=re.IGNORECASE)


def _refuse(reason: str, trace: list[str], **detail: object) -> R1Reconstruction:
    trace.append(_event("refused", reason=reason, **detail))
    return R1Reconstruction(
        graph=None,
        answer=None,
        reader_trace=tuple(trace),
        refusal_reason=reason,
    )


def _event(outcome: str, **payload: object) -> str:
    data = {"layer": "r1_reconstruction", "outcome": outcome}
    data.update(payload)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))

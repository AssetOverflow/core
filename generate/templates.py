"""Deterministic surface templates for rhetorical moves.

Each template is a format string keyed by RhetoricalMove. Slots:
  {subject}   — primary subject from the articulation step
  {predicate} — semantic predicate (e.g. "is_defined_as", "contrasts_with")
  {obj}       — object slot from the graph node (may be "<pending>")

Templates are intentionally simple. The goal is structural correctness,
not fluency — fluency comes in a later phase when the generation stream
consumes these as constraints rather than final output.
"""

from __future__ import annotations

from generate.graph_planner import RhetoricalMove
from generate.morphology import base_form, past_participle, past_tense, present_participle


# Noun pluralisation — used under quantifiers (all/some/many/few/most).
# Closes english_fluency_ood gaps.md G2 (plural agreement).
_IRREGULAR_PLURALS: dict[str, str] = {
    "child": "children", "ox": "oxen", "foot": "feet", "tooth": "teeth",
    "man": "men", "woman": "women", "person": "people",
    "mouse": "mice", "louse": "lice", "goose": "geese",
    # invariant
    "sheep": "sheep", "fish": "fish", "deer": "deer", "moose": "moose",
    "series": "series", "species": "species",
    # latin/greek-origin domain vocabulary
    "datum": "data", "criterion": "criteria", "phenomenon": "phenomena",
    "analysis": "analyses", "axis": "axes", "basis": "bases",
    "thesis": "theses", "hypothesis": "hypotheses",
    "mitochondrion": "mitochondria",
}


def pluralize(noun: str) -> str:
    if not noun:
        return noun
    if noun in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[noun]
    n = noun
    if n.endswith(("s", "sh", "ch", "x", "z")):
        return n + "es"
    if n.endswith("y") and len(n) > 1 and n[-2] not in "aeiou":
        return n[:-1] + "ies"
    if n.endswith("fe"):
        return n[:-2] + "ves"
    if n.endswith("f"):
        return n[:-1] + "ves"
    return n + "s"


# Quantifiers that demand plural agreement on the subject + verb.
# "the" / "a" stay singular; "every" / "each" are singular by English
# rule even though semantically universal.
_PLURAL_QUANTIFIERS: frozenset[str] = frozenset({
    "all", "some", "many", "few", "most", "several", "various", "no",
})

# Mass nouns — uncountable in English, so "all evidence", "some wisdom"
# stay singular under quantifiers ("all evidences" is wrong).  The
# verb still agrees (singular: "all evidence supports truth").
# This list covers the abstract/epistemic vocabulary in
# en_core_cognition_v1 + common English mass nouns.
_MASS_NOUNS: frozenset[str] = frozenset({
    # epistemic / abstract (the seed-pack vocabulary)
    "evidence", "wisdom", "knowledge", "truth", "light", "darkness",
    "information", "data", "music", "art", "literature", "philosophy",
    "courage", "patience", "love", "hope", "fear", "grace",
    "meaning", "purpose", "beauty", "justice", "freedom",
    # physical mass
    "water", "air", "fire", "earth", "sand", "rain", "snow", "ice",
    "wood", "metal", "gold", "silver", "iron", "stone",
    "blood", "flesh", "bone",
    # collective / continuous
    "weather", "traffic", "furniture", "luggage", "advice",
    "equipment", "machinery", "scenery", "money", "news",
    "research", "progress", "feedback",
})


def is_mass_noun(noun: str) -> bool:
    return noun.lower() in _MASS_NOUNS


_PREDICATE_DISPLAY: dict[str, str] = {
    "is_defined_as": "is defined as",
    "is_caused_by": "is caused by",
    "has_steps": "has the following steps",
    "contrasts_with": "contrasts with",
    "corrects": "corrects",
    "recalls": "recalls",
    "is_verified_as": "is verified as",
    "addresses": "addresses",
    "defines": "defines",
    "means": "means",
    "grounds": "grounds",
    "supports": "supports",
    "causes": "causes",
    "reveals": "reveals",
    "precedes": "precedes",
    "follows": "follows",
    "belongs_to": "belongs to",
    "answers": "answers",
    "is_grounded_in": "is grounded in",
    "is_distinguished_from": "is distinguished from",
    "implies": "implies",
    "entails": "entails",
    "requires": "requires",
    "verifies": "verifies",
    "evidences": "evidences",
    "orders": "orders",
}


def _humanize_predicate(predicate: str) -> str:
    return _PREDICATE_DISPLAY.get(predicate, predicate.replace("_", " "))


_MOVE_TEMPLATES: dict[RhetoricalMove, str] = {
    RhetoricalMove.ASSERT: "{subject} {predicate_h} {obj}",
    RhetoricalMove.ELABORATE: "furthermore, {subject} {predicate_h} {obj}",
    RhetoricalMove.CONTRAST: "in contrast, {subject} {predicate_h} {obj}",
    RhetoricalMove.SEQUENCE: "next, {subject} {predicate_h} {obj}",
    RhetoricalMove.CORRECT: "correction: {subject} {predicate_h} {obj}",
}


def _inflect_predicate(
    predicate_h: str,
    *,
    negated: bool = False,
    tense: str | None = None,
    aspect: str | None = None,
    plural_subject: bool = False,
) -> str:
    """Apply tense/aspect/negation to a humanized predicate.

    When ``plural_subject`` is true, the conjugation uses plural
    agreement (do not / have / are / bare-base verb in present) so
    surfaces like "all molecules bind enzyme" come out correctly
    instead of "all molecule binds enzyme" (english_fluency_ood G2).
    """
    verb = predicate_h
    base = base_form(verb)

    match (aspect, tense, negated, plural_subject):
        case ("perfective", _, _, True):
            return f"have {past_participle(verb)}"
        case ("perfective", _, _, False):
            return f"has {past_participle(verb)}"
        case ("imperfective", _, _, True):
            return f"are {present_participle(verb)}"
        case ("imperfective", _, _, False):
            return f"is {present_participle(verb)}"
        case (_, "past", True, _):
            return f"did not {base}"
        case (_, "past", False, _):
            return past_tense(verb)
        case (_, "future", True, _):
            return f"will not {base}"
        case (_, "future", False, _):
            return f"will {base}"
        case (_, _, True, True):
            return f"do not {base}"
        case (_, _, True, False):
            return f"does not {base}"
        case (_, _, False, True):
            return base
        case _:
            return verb


def render_step(
    move: RhetoricalMove,
    subject: str,
    predicate: str,
    obj: str,
    *,
    negated: bool = False,
    quantifier: str | None = None,
    tense: str | None = None,
    aspect: str | None = None,
) -> str:
    """Render a single articulation step into a surface fragment."""
    template = _MOVE_TEMPLATES[move]
    # Mass nouns under a quantifier stay singular ("all evidence
    # supports", not "all evidences support").  Count nouns
    # pluralise and the verb de-conjugates ("all molecules bind").
    plural_q = quantifier is not None and quantifier.lower() in _PLURAL_QUANTIFIERS
    is_mass = is_mass_noun(subject)
    plural = plural_q and not is_mass
    predicate_h = _humanize_predicate(predicate)
    predicate_h = _inflect_predicate(
        predicate_h,
        negated=negated, tense=tense, aspect=aspect,
        plural_subject=plural,
    )
    obj_display = obj if obj != "<pending>" else "..."
    subject_form = pluralize(subject) if plural else subject
    subject_display = f"{quantifier} {subject_form}" if quantifier else subject_form
    return template.format(
        subject=subject_display,
        predicate_h=predicate_h,
        obj=obj_display,
    )

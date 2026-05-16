"""Deterministic English morphology for the realizer.

Handles inflection of predicates for tense, aspect, and negation.
This is intentionally rule-based and limited to the seed vocabulary.
Irregular forms are listed explicitly; regular forms follow English rules.
"""
from __future__ import annotations


_IRREGULAR_PAST: dict[str, str] = {
    "reveals": "revealed",
    "grounds": "grounded",
    "precedes": "preceded",
    "defines": "defined",
    "follows": "followed",
    "requires": "required",
    "supports": "supported",
    "implies": "implied",
    "entails": "entailed",
    "shows": "showed",
    "causes": "caused",
    "orders": "ordered",
}

_IRREGULAR_PARTICIPLE: dict[str, str] = {
    "reveals": "revealing",
    "grounds": "grounding",
    "precedes": "preceding",
    "defines": "defining",
    "follows": "following",
    "requires": "requiring",
    "supports": "supporting",
    "implies": "implying",
    "entails": "entailing",
    "shows": "showing",
    "causes": "causing",
    "orders": "ordering",
}

_IRREGULAR_PAST_PARTICIPLE: dict[str, str] = {
    "reveals": "revealed",
    "grounds": "grounded",
    "precedes": "preceded",
    "defines": "defined",
    "follows": "followed",
    "requires": "required",
    "supports": "supported",
    "implies": "implied",
    "entails": "entailed",
    "shows": "shown",
    "causes": "caused",
    "orders": "ordered",
}


def _base_form(verb_3sg: str) -> str:
    if verb_3sg.endswith("ies"):
        return verb_3sg[:-3] + "y"
    if verb_3sg.endswith("es"):
        return verb_3sg[:-2] if verb_3sg[:-2].endswith(("s", "sh", "ch", "x", "z", "o")) else verb_3sg[:-1]
    if verb_3sg.endswith("s"):
        return verb_3sg[:-1]
    return verb_3sg


def past_tense(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[verb_3sg]
    base = _base_form(verb_3sg)
    if base.endswith("e"):
        return base + "d"
    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ied"
    return base + "ed"


def present_participle(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PARTICIPLE:
        return _IRREGULAR_PARTICIPLE[verb_3sg]
    base = _base_form(verb_3sg)
    if base.endswith("e") and not base.endswith("ee"):
        return base[:-1] + "ing"
    return base + "ing"


def past_participle(verb_3sg: str) -> str:
    if verb_3sg in _IRREGULAR_PAST_PARTICIPLE:
        return _IRREGULAR_PAST_PARTICIPLE[verb_3sg]
    return past_tense(verb_3sg)


def base_form(verb_3sg: str) -> str:
    return _base_form(verb_3sg)

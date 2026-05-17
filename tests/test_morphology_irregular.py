"""Realizer morphology — irregular verb + doubling regression tests.

Closes english_fluency_ood gaps.md G1 (irregular past tense): the
realizer's `past_tense` no longer turns `bind` into `binded`.  Also
locks the CVC-doubling rule (`run` → `running`, `stop` → `stopped`)
and the short-`ies` exception (`die` keeps the `-ie-` stem).

These checks are tight enough that any regression in
`generate/morphology.py` is caught immediately.
"""

from __future__ import annotations

import pytest

from generate.morphology import (
    base_form,
    past_participle,
    past_tense,
    present_participle,
)


# (3sg, expected_past, expected_past_participle, expected_present_participle, expected_base)
_IRREGULAR_CASES: list[tuple[str, str, str, str, str]] = [
    ("binds",  "bound",   "bound",   "binding",  "bind"),
    ("runs",   "ran",     "run",     "running",  "run"),
    ("stands", "stood",   "stood",   "standing", "stand"),
    ("writes", "wrote",   "written", "writing",  "write"),
    ("brings", "brought", "brought", "bringing", "bring"),
    ("thinks", "thought", "thought", "thinking", "think"),
    ("eats",   "ate",     "eaten",   "eating",   "eat"),
    ("breaks", "broke",   "broken",  "breaking", "break"),
    ("flies",  "flew",    "flown",   "flying",   "fly"),
    ("swims",  "swam",    "swum",    "swimming", "swim"),
    ("knows",  "knew",    "known",   "knowing",  "know"),
    ("hides",  "hid",     "hidden",  "hiding",   "hide"),
]


@pytest.mark.parametrize("verb_3sg,past,pp,pres,base", _IRREGULAR_CASES)
def test_irregular_verb_forms(
    verb_3sg: str, past: str, pp: str, pres: str, base: str
) -> None:
    assert past_tense(verb_3sg) == past
    assert past_participle(verb_3sg) == pp
    assert present_participle(verb_3sg) == pres
    assert base_form(verb_3sg) == base


# Doubling rule: CVC bases double the final consonant before -ed / -ing.
_CVC_CASES: list[tuple[str, str, str]] = [
    ("stops", "stopped",  "stopping"),
    ("plans", "planned",  "planning"),
    ("begs",  "begged",   "begging"),
    # Non-CVC: should NOT double.
    ("cooks", "cooked",   "cooking"),    # CVCk pattern not doubled
    ("flows", "flowed",   "flowing"),    # ends in vowel+consonant but flow has 2 vowels
    ("plays", "played",   "playing"),    # CVC but ends in y (excluded)
]


@pytest.mark.parametrize("verb_3sg,past,pres", _CVC_CASES)
def test_cvc_doubling_rule(verb_3sg: str, past: str, pres: str) -> None:
    assert past_tense(verb_3sg) == past
    assert present_participle(verb_3sg) == pres


# Short-ies disambiguation: dies → die, cries → cry.
_IES_CASES: list[tuple[str, str, str]] = [
    ("dies",  "died",  "die"),
    ("lies",  "lay",   "lie"),   # lie is irregular; base must still be lie
    ("ties",  "tied",  "tie"),
    ("cries", "cried", "cry"),
    ("flies", "flew",  "fly"),
]


@pytest.mark.parametrize("verb_3sg,past,base", _IES_CASES)
def test_short_ies_disambiguation(verb_3sg: str, past: str, base: str) -> None:
    assert base_form(verb_3sg) == base
    assert past_tense(verb_3sg) == past


# Regular cases still pass — the suffix rules are unchanged for the
# Phase 5.1+ OOD lane vocabulary.
_REGULAR_CASES: list[tuple[str, str, str, str]] = [
    ("flows",   "flowed",   "flowed",   "flowing"),
    ("reveals", "revealed", "revealed", "revealing"),
    ("grounds", "grounded", "grounded", "grounding"),
    ("precedes","preceded", "preceded", "preceding"),
    ("yields",  "yielded",  "yielded",  "yielding"),
]


@pytest.mark.parametrize("verb_3sg,past,pp,pres", _REGULAR_CASES)
def test_regular_verbs_still_pass(
    verb_3sg: str, past: str, pp: str, pres: str
) -> None:
    assert past_tense(verb_3sg) == past
    assert past_participle(verb_3sg) == pp
    assert present_participle(verb_3sg) == pres

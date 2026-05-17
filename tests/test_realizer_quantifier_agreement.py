"""Realizer plural agreement under quantifiers — G2 regression.

Closes english_fluency_ood gaps.md G2: under universal/existential
quantifiers, count-noun subjects pluralise and the verb de-conjugates
to the bare base.  Mass nouns (evidence, wisdom, …) stay singular
under the same quantifiers ("all evidence supports truth" is correct;
"all evidences support truth" is wrong English).

Coverage also includes the quantifier-tense / quantifier-aspect /
quantifier-negation interactions so future regressions are caught.
"""

from __future__ import annotations

import pytest

from generate.graph_planner import RhetoricalMove
from generate.templates import is_mass_noun, pluralize, render_step


# Count-noun pluralisation under "all"/"some" quantifiers.
_PLURAL_CASES: list[tuple[str, str, str, str, str]] = [
    ("all",  "molecule", "binds", "enzyme",   "all molecules bind enzyme"),
    ("all",  "atom",     "forms", "bond",     "all atoms form bond"),
    ("some", "river",    "flows", "valley",   "some rivers flow valley"),
    ("all",  "child",    "fits",  "school",   "all children fit school"),     # irregular plural
    ("all",  "analysis", "yields","insight",  "all analyses yield insight"),  # latinate
    ("some", "ribosome", "assembles", "protein", "some ribosomes assemble protein"),
]


@pytest.mark.parametrize("quantifier,subj,pred,obj,expected", _PLURAL_CASES)
def test_count_noun_pluralises_under_quantifier(
    quantifier: str, subj: str, pred: str, obj: str, expected: str
) -> None:
    surface = render_step(RhetoricalMove.ASSERT, subj, pred, obj, quantifier=quantifier)
    assert surface == expected


# Mass-noun cases — must NOT pluralise; verb stays singular too.
_MASS_CASES: list[tuple[str, str, str, str, str]] = [
    ("all",  "evidence", "supports", "truth",     "all evidence supports truth"),
    ("all",  "wisdom",   "requires", "patience",  "all wisdom requires patience"),
    ("some", "truth",    "requires", "courage",   "some truth requires courage"),
    ("some", "knowledge","grounds",  "action",    "some knowledge grounds action"),
    ("all",  "water",    "flows",    "downhill",  "all water flows downhill"),
]


@pytest.mark.parametrize("quantifier,subj,pred,obj,expected", _MASS_CASES)
def test_mass_noun_stays_singular_under_quantifier(
    quantifier: str, subj: str, pred: str, obj: str, expected: str
) -> None:
    surface = render_step(RhetoricalMove.ASSERT, subj, pred, obj, quantifier=quantifier)
    assert surface == expected


# Quantifier + negation interaction: plural subject → "do not", mass/none → "does not".
def test_quantifier_negation_uses_do_not_for_plural_subject() -> None:
    s = render_step(
        RhetoricalMove.ASSERT, "molecule", "binds", "enzyme",
        quantifier="all", negated=True,
    )
    assert s == "all molecules do not bind enzyme"


def test_quantifier_negation_uses_does_not_for_mass_subject() -> None:
    s = render_step(
        RhetoricalMove.ASSERT, "evidence", "supports", "truth",
        quantifier="all", negated=True,
    )
    assert s == "all evidence does not support truth"


# Quantifier + aspect: plural subject → "have/are", mass/none → "has/is".
def test_quantifier_perfective_aspect_uses_have_for_plural() -> None:
    s = render_step(
        RhetoricalMove.ASSERT, "molecule", "binds", "enzyme",
        quantifier="all", aspect="perfective",
    )
    assert s == "all molecules have bound enzyme"


def test_quantifier_imperfective_aspect_uses_are_for_plural() -> None:
    s = render_step(
        RhetoricalMove.ASSERT, "atom", "forms", "bond",
        quantifier="some", aspect="imperfective",
    )
    assert s == "some atoms are forming bond"


# Helper-level checks (so future code changes that bypass render_step
# still hit the same rules).
def test_pluralize_handles_irregular_and_latinate() -> None:
    assert pluralize("child") == "children"
    assert pluralize("analysis") == "analyses"
    assert pluralize("bus") == "buses"
    assert pluralize("city") == "cities"
    assert pluralize("leaf") == "leaves"
    assert pluralize("fish") == "fish"  # invariant


def test_is_mass_noun_known_set() -> None:
    assert is_mass_noun("evidence")
    assert is_mass_noun("Wisdom")  # case-insensitive
    assert is_mass_noun("water")
    assert not is_mass_noun("molecule")
    assert not is_mass_noun("atom")

"""R1 GSM8K reconstruction: explicit comparative-derived totals.

Pins the first answer-changing reconstruction slice.  Admissions must flow
through a real MathProblemGraph and the independent verifier; no fast-path numeric
answer is allowed.
"""

from __future__ import annotations

import pytest

from core.reasoning import evidence_from_math_solution
from generate.derivation import reconstruct_r1_total
from generate.math_candidate_graph import parse_and_solve
from generate.math_solver import solve
from generate.math_verifier import verify


R1_POSITIVES = {
    "cv-0001": (
        "Fabian bought a brand new computer mouse and keyboard to be able to work "
        "from home. The cost of the keyboard was three times greater than the "
        "cost of the mouse. If the mouse cost $16, how much did Fabian spent on "
        "his new accessories?",
        64.0,
    ),
    "cv-0002": (
        "In a building, there are a hundred ladies on the first-floor studying. "
        "There are three times that many girls at a party being held on the "
        "second floor of the building. How many ladies are on the two floors in total?",
        400.0,
    ),
    "cv-0009": (
        "Ivan has 20 dice. Jerry has twice as many dice as Ivan. "
        "How many dice do they have altogether?",
        60.0,
    ),
    "heldout-0101": (
        "Eduardo is a teacher. He taught 3 classes last week while his colleague "
        "Frankie taught double what Eduardo teaches. How many classes did Eduardo "
        "and Frankie teach in total?",
        9.0,
    ),
    "heldout-0108": (
        "Dana Point beach has four times the number of sharks as Newport Beach. "
        "If Newport Beach has 22 sharks, how many sharks are there in total on "
        "the two beaches?",
        110.0,
    ),
    "heldout-0411": (
        "In a class, there were 13 female students. There were three times as "
        "many male students in this class. How many students were in the class?",
        52.0,
    ),
    "heldout-0453": (
        "Olaf is playing a game with his dad. He scored three times more points "
        "than his dad, who scored 7 points. How many points did they score in total?",
        28.0,
    ),
}


@pytest.mark.parametrize("case_id", sorted(R1_POSITIVES))
def test_r1_reconstruction_solves_with_verified_graph(case_id: str) -> None:
    text, expected = R1_POSITIVES[case_id]
    result = reconstruct_r1_total(text)

    assert result is not None
    assert result.is_admitted
    assert result.answer == expected
    assert result.graph is not None

    trace = solve(result.graph)
    verdict = verify(result.graph, trace)
    assert verdict.passed is True
    assert trace.answer_value == expected

    evidence = evidence_from_math_solution(
        graph=result.graph,
        trace=trace,
        reader_trace=result.reader_trace,
        operator="gsm8k_r1_reconstruction",
    )
    assert evidence.domain == "mathematics_logic"
    assert evidence.operator == "gsm8k_r1_reconstruction"
    assert evidence.outcome == "verified"
    assert evidence.commitment_key
    assert evidence.evidence_hash == evidence_from_math_solution(
        graph=result.graph,
        trace=trace,
        reader_trace=result.reader_trace,
        operator="gsm8k_r1_reconstruction",
    ).evidence_hash


@pytest.mark.parametrize("case_id", sorted(R1_POSITIVES))
def test_parse_and_solve_wires_r1_only_as_verified_graph(case_id: str) -> None:
    text, expected = R1_POSITIVES[case_id]
    result = parse_and_solve(text)

    assert result.is_admitted
    assert result.answer == expected
    assert result.selected_graph is not None
    assert any("r1_reconstruction" in event for event in result.reader_trace)


@pytest.mark.parametrize(
    "text",
    [
        (
            "Tom has 7 apples. Jerry has 3 times as many apples. "
            "How many apples do they have together?"
        ),
        (
            "Over several years, Daniel has adopted any stray animals he sees on "
            "the side of the road.  He now has 2 horses, 5 dogs, 7 cats, 3 turtles, "
            "and 1 goat.  All of the animals are perfectly healthy.  In total, "
            "how many legs do his animals have?"
        ),
        (
            "Mark does a gig every other day for 2 weeks.  For each gig, he plays "
            "3 songs.  2 of the songs are 5 minutes long and the last song is "
            "twice that long.  How many minutes did he play?"
        ),
        (
            "Sam has 7 apples. Tom has 4 oranges. Jerry has twice as many apples "
            "as Sam. How many apples and oranges do they have together?"
        ),
    ],
)
def test_r1_reconstruction_refuses_out_of_scope_shapes(text: str) -> None:
    result = parse_and_solve(text)
    assert not result.is_admitted

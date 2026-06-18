"""Review hardening for Sprint 10 A2o/A2p subject and chain binding."""

from __future__ import annotations

from generate.derivation.affine_comparative_inversion_total import (
    compose_affine_comparative_inversion_total,
)
from generate.derivation.sequential_comparative_scale import (
    compose_sequential_comparative_scale,
)


AFFINE_TOTAL_SUBJECT_MISMATCH = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "If Jen has 150 ducks, how many total birds does Sam have?"
)

AFFINE_TOTAL_UNRELATED_AGGREGATE = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "If Jen has 150 ducks, how many total dogs does she have?"
)

AFFINE_TOTAL_PRONOUN_TARGET = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "If Jen has 150 ducks, how many total birds does she have?"
)

AFFINE_TOTAL_FRUIT_SIBLING = (
    "Mia has 6 more apples than three times the number of oranges. "
    "If Mia has 42 apples, how many total fruits does she have?"
)

SEQUENTIAL_PAGE_READER_MISMATCH = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "By the time she was twice that age, she was reading books 5 times longer, "
    "and 8 years later, she was reading books 3 times longer than that. "
    "Presently, she reads books that are 4 times the previous length. "
    "How many pages do the books Bob reads now have?"
)

SEQUENTIAL_UNRELATED_LENGTH_CHAIN = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "Her jump rope was 5 times longer, and her scarf was 3 times longer than that. "
    "Presently, she reads books that are 4 times the previous length. "
    "How many pages do the books she reads now have?"
)

SEQUENTIAL_PAGE_READER_MATCH = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "By the time she was twice that age, she was reading books 5 times longer, "
    "and 8 years later, she was reading books 3 times longer than that. "
    "Presently, she reads books that are 4 times the previous length. "
    "How many pages do the books Mandy reads now have?"
)


def test_affine_total_question_subject_mismatch_refuses() -> None:
    assert compose_affine_comparative_inversion_total(AFFINE_TOTAL_SUBJECT_MISMATCH) is None


def test_affine_total_unrelated_aggregate_refuses() -> None:
    assert compose_affine_comparative_inversion_total(AFFINE_TOTAL_UNRELATED_AGGREGATE) is None


def test_affine_total_question_pronoun_target_still_admits() -> None:
    resolution = compose_affine_comparative_inversion_total(AFFINE_TOTAL_PRONOUN_TARGET)
    assert resolution is not None
    assert resolution.answer == 185.0


def test_affine_total_fruit_sibling_still_admits() -> None:
    resolution = compose_affine_comparative_inversion_total(AFFINE_TOTAL_FRUIT_SIBLING)
    assert resolution is not None
    assert resolution.answer == 54.0


def test_sequential_page_question_reader_mismatch_refuses() -> None:
    assert compose_sequential_comparative_scale(SEQUENTIAL_PAGE_READER_MISMATCH) is None


def test_sequential_unrelated_length_chain_refuses() -> None:
    assert compose_sequential_comparative_scale(SEQUENTIAL_UNRELATED_LENGTH_CHAIN) is None


def test_sequential_page_question_reader_match_still_admits() -> None:
    resolution = compose_sequential_comparative_scale(SEQUENTIAL_PAGE_READER_MATCH)
    assert resolution is not None
    assert resolution.answer == 480.0

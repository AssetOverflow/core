"""Domain-agnostic coverage for proper_noun_token primitive."""

from generate.comprehension.lexeme_primitives import scan


def test_math_surface_admits_name() -> None:
    assert scan("Tina") is not None


def test_non_math_surface_admits_geonames() -> None:
    boston = scan("Boston")
    massachusetts = scan("Massachusetts")
    assert boston is not None and boston.primitive_name == "proper_noun_token"
    assert massachusetts is not None and massachusetts.primitive_name == "proper_noun_token"

"""Tests for the central safe-display sanitiser (ADR-0051).

These tests are doctrine guards: they encode the trust boundary so any
future refactor that weakens the sanitiser fails closed in CI before it
can be merged.
"""
from __future__ import annotations

import pytest

from core._safe_display import safe_display, safe_pack_id


class TestSafeDisplay:
    def test_none_collapses_to_empty_mark(self) -> None:
        assert safe_display(None) == "<empty>"

    def test_empty_string_collapses_to_empty_mark(self) -> None:
        assert safe_display("") == "<empty>"

    def test_plain_ascii_is_passed_through(self) -> None:
        assert safe_display("memory") == "memory"

    def test_control_characters_are_replaced(self) -> None:
        # \x1b is ESC — the prefix of every ANSI escape sequence.
        assert safe_display("foo\x1b[31mbar") == "foo?[31mbar"

    def test_newline_and_carriage_return_are_replaced(self) -> None:
        # Newlines must never reach a log line uncleansed.
        assert "\n" not in safe_display("foo\nbar")
        assert "\r" not in safe_display("foo\r\nbar")

    def test_null_byte_is_replaced(self) -> None:
        assert "\x00" not in safe_display("foo\x00bar")

    def test_c1_control_range_is_replaced(self) -> None:
        # The C1 range (0x80..0x9F) is also control characters.
        for code in (0x80, 0x90, 0x9F):
            assert chr(code) not in safe_display(f"a{chr(code)}b")

    def test_truncation_to_default_max_len(self) -> None:
        out = safe_display("x" * 200)
        assert len(out) <= 64
        assert out.endswith("...")

    def test_truncation_marker_only_when_needed(self) -> None:
        assert safe_display("short") == "short"
        assert "..." not in safe_display("short")

    def test_custom_max_len_is_honoured(self) -> None:
        out = safe_display("abcdefghij", max_len=8)
        assert len(out) <= 8
        assert out.endswith("...")

    def test_zero_max_len_returns_empty_string(self) -> None:
        assert safe_display("anything", max_len=0) == ""

    def test_non_string_input_is_repr_coerced(self) -> None:
        # Callers cannot smuggle a custom __str__ into a log line.
        class Hostile:
            def __str__(self) -> str:  # pragma: no cover
                return "\x1b[31mPWNED"

        out = safe_display(Hostile(), max_len=128)
        assert "\x1b" not in out
        # repr() is what we coerce through, not str().
        assert "Hostile" in out

    def test_is_deterministic(self) -> None:
        # Identical input → byte-identical output, no clock / env.
        a = safe_display("test\x1btoken")
        b = safe_display("test\x1btoken")
        assert a == b


class TestSafePackId:
    def test_simple_pack_id_passes_through(self) -> None:
        assert safe_pack_id("en_core_cognition_v1") == "en_core_cognition_v1"

    def test_path_separators_are_masked(self) -> None:
        out = safe_pack_id("../etc/passwd")
        assert "/" not in out
        assert ".." in out  # dots are allowed; slashes are masked

    def test_whitespace_is_masked(self) -> None:
        assert " " not in safe_pack_id("foo bar")

    def test_unicode_is_masked(self) -> None:
        out = safe_pack_id("café")
        assert "é" not in out

    def test_none_collapses_to_empty_mark(self) -> None:
        assert safe_pack_id(None) == "<empty>"

    def test_empty_collapses_to_empty_mark(self) -> None:
        assert safe_pack_id("") == "<empty>"

    def test_truncation_for_long_input(self) -> None:
        out = safe_pack_id("a" * 200)
        assert len(out) <= 48
        assert out.endswith("...")


def test_module_exports_are_explicit() -> None:
    """``__all__`` lists exactly the public helpers (regression guard)."""
    from core import _safe_display as mod

    assert set(mod.__all__) == {"safe_display", "safe_pack_id"}

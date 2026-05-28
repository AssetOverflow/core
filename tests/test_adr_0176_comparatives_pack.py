"""ADR-0176 — en_core_comparatives_v1 pack + comparative-scalar extraction.

The curated, closed-set, refusal-preferring world-fact primitives that multi-step
composition needs (twice -> x2, half -> x0.5, '<N> times' -> xN). Tests cover the
extractor behaviour, determinism, refusal-preferring discipline, and pack
integrity (manifest checksum matches the bytes on disk — CLAUDE.md pack rule).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generate.derivation import ComparativeScalar, extract_comparative_scalars

_PACK = Path(__file__).resolve().parents[1] / "language_packs" / "data" / "en_core_comparatives_v1"


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------

class TestExtractComparativeScalars:
    def test_twice(self) -> None:
        cs = extract_comparative_scalars("She has twice as many apples.")
        assert cs == (ComparativeScalar("multiply", 2.0, "twice", "twice"),)

    def test_half(self) -> None:
        cs = extract_comparative_scalars("He keeps half of the cards.")
        assert cs == (ComparativeScalar("multiply", 0.5, "half", "half"),)

    def test_word_number_times(self) -> None:
        cs = extract_comparative_scalars("Brooke does three times as many jumping jacks.")
        assert cs == (ComparativeScalar("multiply", 3.0, "three times", "times", number_token="three"),)

    def test_digit_times(self) -> None:
        cs = extract_comparative_scalars("The price is 5 times the cost.")
        assert cs == (ComparativeScalar("multiply", 5.0, "5 times", "times", number_token="5"),)

    def test_triple_and_quarter(self) -> None:
        assert extract_comparative_scalars("output tripled")[0].scalar == 3.0
        assert extract_comparative_scalars("a quarter of the pie")[0].scalar == 0.25

    def test_multiple_in_text_order(self) -> None:
        cs = extract_comparative_scalars("First it doubled, then three times more.")
        # "doubled" matches the exact 'doubled' lexeme (word-boundary; not 'double')
        assert [(c.scalar, c.cue) for c in cs] == [(2.0, "doubled"), (3.0, "times")]

    def test_deterministic(self) -> None:
        t = "twice and three times and half"
        assert extract_comparative_scalars(t) == extract_comparative_scalars(t)


# ---------------------------------------------------------------------------
# refusal-preferring / closed-set discipline
# ---------------------------------------------------------------------------

class TestRefusalPreferring:
    def test_uncovered_comparative_yields_nothing(self) -> None:
        # "a third" (1/3, non-terminating) is deliberately NOT in the pack
        assert extract_comparative_scalars("he ate a third of it") == ()
        assert extract_comparative_scalars("several more apples") == ()

    def test_no_comparative_yields_nothing(self) -> None:
        assert extract_comparative_scalars("He has 5 apples and 3 oranges.") == ()

    def test_times_requires_a_positive_number(self) -> None:
        # bare "times" without a number -> no scalar (don't guess)
        assert extract_comparative_scalars("he goes to the gym sometimes") == ()

    def test_zero_times_not_emitted(self) -> None:
        assert extract_comparative_scalars("0 times the value") == ()


# ---------------------------------------------------------------------------
# pack integrity (CLAUDE.md: checksum hashes the bytes written to disk)
# ---------------------------------------------------------------------------

class TestPackIntegrity:
    def test_manifest_checksum_matches_bytes(self) -> None:
        manifest = json.loads((_PACK / "manifest.json").read_text())
        entry = manifest["files"][0]
        data_bytes = (_PACK / entry["path"]).read_bytes()
        assert hashlib.sha256(data_bytes).hexdigest() == entry["checksum"]

    def test_entry_count_matches(self) -> None:
        manifest = json.loads((_PACK / "manifest.json").read_text())
        entry = manifest["files"][0]
        lines = [ln for ln in (_PACK / entry["path"]).read_text().splitlines() if ln.strip()]
        assert len(lines) == entry["entry_count"]

    def test_all_entries_well_formed(self) -> None:
        for line in (_PACK / "comparatives.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            assert set(e) == {"lexeme", "op", "scalar"}
            assert e["op"] == "multiply"
            assert isinstance(e["scalar"], (int, float)) and e["scalar"] > 0

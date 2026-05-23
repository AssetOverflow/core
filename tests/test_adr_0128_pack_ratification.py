"""ADR-0128 sub-phase 0128.1 — pack ratification invariants.

Each invariant from the ADR §"Ratification invariants" is its own test.
The pack is canonical for English linguistic quantity forms; any drift
must be intentional and ratified, not accidental.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from language_packs.numerics_loader import (
    QUANTIFIER_SEMANTIC_TYPES,
    PACK_ROOT,
    _index,
    lookup_cardinal,
    lookup_fraction,
    lookup_ordinal,
    number_format_entries,
)

EXPECTED_CARDINALS_0_20 = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
]
EXPECTED_TENS = ["thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
EXPECTED_MAGNITUDES = ["hundred", "thousand", "million", "billion"]
EXPECTED_ORDINALS_1_31 = [
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
    "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth",
    "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth",
    "nineteenth", "twentieth", "twenty-first", "twenty-second",
    "twenty-third", "twenty-fourth", "twenty-fifth", "twenty-sixth",
    "twenty-seventh", "twenty-eighth", "twenty-ninth", "thirtieth",
    "thirty-first",
]
EXPECTED_NAMED_FRACTIONS = [
    ("half", 2), ("third", 3), ("quarter", 4), ("fifth", 5), ("sixth", 6),
    ("seventh", 7), ("eighth", 8), ("ninth", 9), ("tenth", 10),
]
EXPECTED_IRREGULAR_FRACTIONS = [("sixteenth", 16), ("thirty-second", 32)]


# ---------------------------------------------------------------------------
# Invariant 1: Cardinal exhaustiveness — 0..20 + tens + magnitudes
# ---------------------------------------------------------------------------
def test_cardinal_exhaustiveness_0_to_20():
    for i, word in enumerate(EXPECTED_CARDINALS_0_20):
        entry = lookup_cardinal(word)
        assert entry is not None, f"cardinal {word!r} missing"
        assert entry.numeric_value == i


def test_cardinal_tens_complete():
    expected = dict(zip(EXPECTED_TENS, range(30, 100, 10)))
    for word, val in expected.items():
        entry = lookup_cardinal(word)
        assert entry is not None, f"tens cardinal {word!r} missing"
        assert entry.numeric_value == val


def test_cardinal_magnitudes_complete():
    expected = dict(zip(EXPECTED_MAGNITUDES, [100, 1000, 1_000_000, 1_000_000_000]))
    for word, val in expected.items():
        entry = lookup_cardinal(word)
        assert entry is not None, f"magnitude cardinal {word!r} missing"
        assert entry.numeric_value == val


# ---------------------------------------------------------------------------
# Invariant 2: Ordinal exhaustiveness — 1st..31st present
# ---------------------------------------------------------------------------
def test_ordinal_exhaustiveness_1_to_31():
    for i, word in enumerate(EXPECTED_ORDINALS_1_31, start=1):
        entry = lookup_ordinal(word)
        assert entry is not None, f"ordinal {word!r} missing"
        assert entry.position == i


def test_ordinal_irregular_spellings_preserved():
    # The "th" rule is not literal; irregular morphology must be in the pack.
    irregular_pairs = {"fifth": 5, "eighth": 8, "ninth": 9, "twelfth": 12}
    for word, pos in irregular_pairs.items():
        entry = lookup_ordinal(word)
        assert entry is not None and entry.position == pos


# ---------------------------------------------------------------------------
# Invariant 3: Named fraction exhaustiveness 1/2..1/10
# ---------------------------------------------------------------------------
def test_fraction_named_1_2_through_1_10():
    for word, denom in EXPECTED_NAMED_FRACTIONS:
        entry = lookup_fraction(word)
        assert entry is not None, f"named fraction {word!r} missing"
        assert entry.numerator == 1 and entry.denominator == denom


def test_fraction_irregular_sixteenth_thirty_second():
    for word, denom in EXPECTED_IRREGULAR_FRACTIONS:
        entry = lookup_fraction(word)
        assert entry is not None, f"irregular fraction {word!r} missing"
        assert entry.numerator == 1 and entry.denominator == denom


def test_fraction_symbol_forms_present():
    symbols = ["½", "¼", "¾", "⅓", "⅔", "⅛", "⅜", "⅝", "⅞"]
    for sym in symbols:
        entry = lookup_fraction(sym)
        assert entry is not None, f"fraction symbol {sym!r} missing"
        assert 0 < entry.decimal_value < 1


# ---------------------------------------------------------------------------
# Invariant 5: Quantifier semantic-type completeness (closed set)
# ---------------------------------------------------------------------------
def test_quantifier_semantic_types_are_closed_set():
    idx = _index()
    assert idx.quantifiers, "no quantifiers loaded"
    for entry in idx.quantifiers.values():
        assert entry.semantic_type in QUANTIFIER_SEMANTIC_TYPES, (
            f"quantifier {entry.surface!r} carries "
            f"semantic_type={entry.semantic_type!r} outside closed set"
        )


def test_quantifier_indefinite_set_present():
    # "wrong == 0" preservation: at least these indefinites must refuse.
    for w in ("some", "many", "few", "several", "any"):
        idx_entries = _index().quantifiers
        assert w in idx_entries
        assert idx_entries[w].is_indefinite


def test_quantifier_determinate_paired_both_equals_two():
    both = _index().quantifiers["both"]
    assert both.semantic_type == "paired"
    assert both.determinate_value == 2


# ---------------------------------------------------------------------------
# Invariant 6: Format regex test corpus exists (cross-file gate)
# ---------------------------------------------------------------------------
def test_number_format_rules_present_and_well_formed():
    entries = number_format_entries()
    assert entries, "no number-format rules loaded"
    seen = set()
    for fmt in entries:
        assert fmt.format_id and fmt.regex and fmt.parser_function
        assert fmt.output_type in {"int", "float", "Fraction"}
        assert fmt.format_id not in seen, f"duplicate format_id {fmt.format_id}"
        seen.add(fmt.format_id)


# ---------------------------------------------------------------------------
# Manifest + mastery report self-seal — SHA-256 of bytes-on-disk
# ---------------------------------------------------------------------------
def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_manifest_checksum_matches_lexicon_bytes_on_disk():
    manifest = json.loads((PACK_ROOT / "manifest.json").read_text(encoding="utf-8"))
    lex_sha = _sha256(PACK_ROOT / "lexicon.jsonl")
    gloss_sha = _sha256(PACK_ROOT / "glosses.jsonl")
    assert manifest["checksum"] == lex_sha
    assert manifest["glosses_checksum"] == gloss_sha
    assert manifest["pack_id"] == "en_numerics_v1"
    assert manifest["gate_engaged"] is True


def test_mastery_report_self_seals():
    report_path = PACK_ROOT / "en_numerics_v1.mastery_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # The report's own checksums must match the bytes on disk.
    assert report["lexicon_sha256"] == _sha256(PACK_ROOT / "lexicon.jsonl")
    assert report["glosses_sha256"] == _sha256(PACK_ROOT / "glosses.jsonl")
    assert report["manifest_sha256"] == _sha256(PACK_ROOT / "manifest.json")
    assert report["pack_id"] == "en_numerics_v1"
    # Counts agree with what the loader can see.
    idx = _index()
    counts = report["entry_counts"]
    assert counts["cardinal"] == len(idx.cardinals)
    assert counts["ordinal"] == len(idx.ordinals)
    # fractions count includes both spelled and symbol-only entries
    assert counts["fraction"] >= len(EXPECTED_NAMED_FRACTIONS)
    assert counts["quantifier"] == len(idx.quantifiers)


def test_every_lexicon_entry_has_gloss():
    lex = {
        json.loads(l)["entry_id"]
        for l in (PACK_ROOT / "lexicon.jsonl").read_text("utf-8").splitlines() if l
    }
    glos = {
        json.loads(l)["entry_id"]
        for l in (PACK_ROOT / "glosses.jsonl").read_text("utf-8").splitlines() if l
    }
    missing = lex - glos
    assert not missing, f"entries without glosses: {sorted(missing)[:5]}"


def test_entry_ids_unique():
    ids = [
        json.loads(l)["entry_id"]
        for l in (PACK_ROOT / "lexicon.jsonl").read_text("utf-8").splitlines() if l
    ]
    assert len(ids) == len(set(ids)), "duplicate entry_id in lexicon"


@pytest.mark.parametrize("required", [
    "pack_id", "language", "role", "checksum", "glosses_checksum",
    "version", "gate_engaged", "provenance",
])
def test_manifest_required_fields(required):
    manifest = json.loads((PACK_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert required in manifest

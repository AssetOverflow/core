"""Deterministic generator for the en_numerics_v1 ratified semantic pack.

Writes lexicon.jsonl, glosses.jsonl, manifest.json, and a self-sealing
.mastery_report.json under language_packs/data/en_numerics_v1/.

Re-running yields byte-identical output. SHA-256 checksums hash the
bytes actually written to disk (CLAUDE.md rule).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PACK_ID = "en_numerics_v1"
PROVENANCE = "adr-0128:operator_seed:2026-05-23"
PACK_DIR = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID


def jline(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Cardinals: 0..20, tens (30..90), magnitudes (hundred/thousand/million/billion)
# ---------------------------------------------------------------------------
CARDINAL_UNITS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
]
CARDINAL_TENS = [
    ("thirty", 30), ("forty", 40), ("fifty", 50), ("sixty", 60),
    ("seventy", 70), ("eighty", 80), ("ninety", 90),
]
CARDINAL_MAGNITUDES = [
    ("hundred", 100), ("thousand", 1000),
    ("million", 1_000_000), ("billion", 1_000_000_000),
]

# Ordinals — exhaustive 1st..31st + decade/magnitude forms
ORDINALS = [
    ("first", 1), ("second", 2), ("third", 3), ("fourth", 4), ("fifth", 5),
    ("sixth", 6), ("seventh", 7), ("eighth", 8), ("ninth", 9), ("tenth", 10),
    ("eleventh", 11), ("twelfth", 12), ("thirteenth", 13), ("fourteenth", 14),
    ("fifteenth", 15), ("sixteenth", 16), ("seventeenth", 17),
    ("eighteenth", 18), ("nineteenth", 19), ("twentieth", 20),
    ("twenty-first", 21), ("twenty-second", 22), ("twenty-third", 23),
    ("twenty-fourth", 24), ("twenty-fifth", 25), ("twenty-sixth", 26),
    ("twenty-seventh", 27), ("twenty-eighth", 28), ("twenty-ninth", 29),
    ("thirtieth", 30), ("thirty-first", 31),
    ("fortieth", 40), ("fiftieth", 50), ("sixtieth", 60), ("seventieth", 70),
    ("eightieth", 80), ("ninetieth", 90),
    ("hundredth", 100), ("thousandth", 1000), ("millionth", 1_000_000),
]

# Fractions — named 1/2..1/10 + sixteenth + thirty-second + symbol forms
FRACTIONS_NAMED = [
    ("half", 1, 2, "½"),
    ("third", 1, 3, "⅓"),
    ("quarter", 1, 4, "¼"),
    ("fifth", 1, 5, "⅕"),
    ("sixth", 1, 6, "⅙"),
    ("seventh", 1, 7, "⅐"),
    ("eighth", 1, 8, "⅛"),
    ("ninth", 1, 9, "⅑"),
    ("tenth", 1, 10, "⅒"),
    ("sixteenth", 1, 16, None),
    ("thirty-second", 1, 32, None),
]
# Additional symbol-only fraction entries (no English-word form)
FRACTION_SYMBOL_ONLY = [
    ("⅔", 2, 3, "two-thirds"),
    ("¾", 3, 4, "three-quarters"),
    ("⅜", 3, 8, "three-eighths"),
    ("⅝", 5, 8, "five-eighths"),
    ("⅞", 7, 8, "seven-eighths"),
]

MULTIPLIERS = [
    ("double", 2.0), ("triple", 3.0), ("quadruple", 4.0),
    ("quintuple", 5.0), ("twice", 2.0), ("thrice", 3.0), ("half", 0.5),
]

QUANTIFIERS = [
    ("all",      "total",        None),
    ("none",     "empty",        0),
    ("some",     "indefinite",   None),
    ("both",     "paired",       2),
    ("each",     "distributive", None),
    ("every",    "distributive", None),
    ("many",     "indefinite",   None),
    ("few",      "indefinite",   None),
    ("several",  "indefinite",   None),
    ("most",     "partial",      None),
    ("any",      "indefinite",   None),
    ("no",       "empty",        0),
    ("single",   "total",        1),
]

COMPARE_ADDITIVE = [
    "more", "fewer", "less", "additional", "extra", "missing", "remaining",
]
COMPARE_MULTIPLICATIVE = [
    "twice", "thrice", "times", "half", "double", "triple",
    "quadruple", "third", "quarter",
]

NUMBER_FORMATS = [
    {
        "format_id": "thousand_separated",
        "regex": r"^\d{1,3}(?:,\d{3})+$",
        "parser_function": "parse_thousand_separated",
        "output_type": "int",
    },
    {
        "format_id": "decimal",
        "regex": r"^-?\d+\.\d+$",
        "parser_function": "parse_decimal",
        "output_type": "float",
    },
    {
        "format_id": "slash_fraction",
        "regex": r"^-?\d+/\d+$",
        "parser_function": "parse_slash_fraction",
        "output_type": "Fraction",
    },
    {
        "format_id": "mixed_number",
        "regex": r"^-?\d+ \d+/\d+$",
        "parser_function": "parse_mixed_number",
        "output_type": "Fraction",
    },
    {
        "format_id": "percentage",
        "regex": r"^-?\d+(?:\.\d+)?%$",
        "parser_function": "parse_percentage",
        "output_type": "float",
    },
    {
        "format_id": "signed_integer",
        "regex": r"^-?\d+$",
        "parser_function": "parse_signed_integer",
        "output_type": "int",
    },
]


def make_entry(entry_id: str, surface: str, *, pos: str, domains, tags, extra):
    e = {
        "entry_id": entry_id,
        "surface": surface,
        "lemma": surface,
        "language": "en",
        "pos": pos,
        "semantic_domains": list(domains),
        "morphology_tags": list(tags),
        "provenance_ids": [PROVENANCE],
    }
    e.update(extra)
    return e


def build_lexicon():
    rows = []
    glosses = []

    # Cardinals — units 0..20
    for i, w in enumerate(CARDINAL_UNITS):
        eid = f"en-num-card-{i:03d}"
        rows.append(make_entry(
            eid, w, pos="NUM",
            domains=["numerics.cardinal", "mathematics.value.integer"],
            tags=["cardinal", "unit" if i < 20 else "decade-anchor"],
            extra={"numeric_value": i, "morphology": "cardinal"},
        ))
        glosses.append({"entry_id": eid, "gloss": f"Cardinal number word for the integer {i}."})

    # Cardinals — tens 30..90
    for j, (w, val) in enumerate(CARDINAL_TENS, start=21):
        eid = f"en-num-card-{j:03d}"
        rows.append(make_entry(
            eid, w, pos="NUM",
            domains=["numerics.cardinal", "mathematics.value.integer"],
            tags=["cardinal", "decade-anchor"],
            extra={"numeric_value": val, "morphology": "cardinal"},
        ))
        glosses.append({"entry_id": eid, "gloss": f"Cardinal tens word for the integer {val}."})

    # Cardinals — magnitudes
    for k, (w, val) in enumerate(CARDINAL_MAGNITUDES, start=28):
        eid = f"en-num-card-{k:03d}"
        rows.append(make_entry(
            eid, w, pos="NUM",
            domains=["numerics.cardinal", "mathematics.value.magnitude"],
            tags=["cardinal", "magnitude"],
            extra={"numeric_value": val, "morphology": "cardinal-magnitude"},
        ))
        glosses.append({"entry_id": eid, "gloss": f"Cardinal magnitude word for the integer {val}."})

    # Ordinals
    for n, (w, pos_val) in enumerate(ORDINALS, start=1):
        eid = f"en-num-ord-{n:03d}"
        rows.append(make_entry(
            eid, w, pos="ADJ",
            domains=["numerics.ordinal", "mathematics.value.position"],
            tags=["ordinal"],
            extra={"position": pos_val, "morphology": "ordinal"},
        ))
        glosses.append({"entry_id": eid, "gloss": f"Ordinal number word for position {pos_val}."})

    # Fractions — named
    for m, (w, num, den, sym) in enumerate(FRACTIONS_NAMED, start=1):
        eid = f"en-num-frac-{m:03d}"
        extra = {
            "numerator": num,
            "denominator": den,
            "decimal_value": num / den,
            "morphology": "fraction",
        }
        if sym:
            extra["symbol"] = sym
        rows.append(make_entry(
            eid, w, pos="NOUN",
            domains=["numerics.fraction", "mathematics.value.rational"],
            tags=["fraction", "named"],
            extra=extra,
        ))
        glosses.append({"entry_id": eid, "gloss": f"Named fraction word for {num}/{den}."})

    # Fractions — symbol-only forms (canonical home; en_units_v1 cross-references)
    for m, (sym, num, den, name) in enumerate(FRACTION_SYMBOL_ONLY,
                                              start=len(FRACTIONS_NAMED) + 1):
        eid = f"en-num-frac-{m:03d}"
        rows.append(make_entry(
            eid, sym, pos="SYM",
            domains=["numerics.fraction", "mathematics.value.rational"],
            tags=["fraction", "symbol"],
            extra={
                "numerator": num,
                "denominator": den,
                "decimal_value": num / den,
                "morphology": "fraction-symbol",
                "spelled_form": name,
            },
        ))
        glosses.append({"entry_id": eid, "gloss": f"Unicode fraction symbol for {num}/{den}."})

    # Multipliers
    for i, (w, factor) in enumerate(MULTIPLIERS, start=1):
        eid = f"en-num-mult-{i:03d}"
        rows.append(make_entry(
            eid, w, pos="ADJ" if w not in {"twice", "thrice"} else "ADV",
            domains=["numerics.multiplier", "mathematics.value.scalar"],
            tags=["multiplier"],
            extra={"factor": factor, "morphology": "multiplier"},
        ))
        glosses.append({"entry_id": eid, "gloss": f"Multiplier word scaling a quantity by {factor}."})

    # Quantifiers
    for i, (w, sem_type, det_val) in enumerate(QUANTIFIERS, start=1):
        eid = f"en-num-quant-{i:03d}"
        extra = {"semantic_type": sem_type, "morphology": "quantifier"}
        if det_val is not None:
            extra["determinate_value"] = det_val
        rows.append(make_entry(
            eid, w, pos="DET",
            domains=["numerics.quantifier", "mathematics.value.quantifier"],
            tags=["quantifier", sem_type],
            extra=extra,
        ))
        glosses.append({"entry_id": eid,
                        "gloss": f"Quantifier ({sem_type}). "
                                 f"{'Determinate value ' + str(det_val) + '.' if det_val is not None else 'No determinate value; indefinite quantifiers trigger refusal.'}"})

    # Comparison anchors — additive
    for i, w in enumerate(COMPARE_ADDITIVE, start=1):
        eid = f"en-num-compare-add-{i:03d}"
        rows.append(make_entry(
            eid, w, pos="ADJ",
            domains=["numerics.compare.additive"],
            tags=["comparison-anchor", "additive"],
            extra={"anchor_class": "additive", "morphology": "comparison-anchor"},
        ))
        glosses.append({"entry_id": eid,
                        "gloss": f"Additive comparison anchor '{w}'."})

    # Comparison anchors — multiplicative
    for i, w in enumerate(COMPARE_MULTIPLICATIVE, start=1):
        eid = f"en-num-compare-mul-{i:03d}"
        rows.append(make_entry(
            eid, w, pos="ADJ",
            domains=["numerics.compare.multiplicative"],
            tags=["comparison-anchor", "multiplicative"],
            extra={"anchor_class": "multiplicative", "morphology": "comparison-anchor"},
        ))
        glosses.append({"entry_id": eid,
                        "gloss": f"Multiplicative comparison anchor '{w}'."})

    # Number formats (declarative rule entries)
    for i, fmt in enumerate(NUMBER_FORMATS, start=1):
        eid = f"en-num-format-{i:03d}"
        rows.append(make_entry(
            eid, fmt["format_id"], pos="X",
            domains=["numerics.format"],
            tags=["number-format"],
            extra={
                "format_id": fmt["format_id"],
                "regex": fmt["regex"],
                "parser_function": fmt["parser_function"],
                "output_type": fmt["output_type"],
                "morphology": "number-format",
            },
        ))
        glosses.append({"entry_id": eid,
                        "gloss": f"Number-format rule '{fmt['format_id']}' "
                                 f"(regex emits {fmt['output_type']})."})

    return rows, glosses


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    rows, glosses = build_lexicon()

    lex_text = "\n".join(jline(r) for r in rows) + "\n"
    gloss_text = "\n".join(jline(g) for g in glosses) + "\n"

    lex_path = PACK_DIR / "lexicon.jsonl"
    gloss_path = PACK_DIR / "glosses.jsonl"
    lex_path.write_text(lex_text, encoding="utf-8")
    gloss_path.write_text(gloss_text, encoding="utf-8")

    lex_checksum = sha256_bytes(lex_path.read_bytes())
    gloss_checksum = sha256_bytes(gloss_path.read_bytes())

    manifest = {
        "pack_id": PACK_ID,
        "language": "en",
        "role": "operational_base",
        "script": "Latin",
        "normalization_policy": "unitize_versor",
        "source_manifest": f"{PACK_ID}.lexicon.jsonl",
        "determinism_class": "D0",
        "checksum": lex_checksum,
        "version": "1.0.0",
        "gate_engaged": True,
        "oov_policy": "tagged_fallback",
        "glosses_checksum": gloss_checksum,
        "definitional_layer": False,
        "provenance": PROVENANCE,
    }
    manifest_path = PACK_DIR / "manifest.json"
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")

    # Self-sealing mastery report: hashes the bytes of the three pack files
    # (lexicon, glosses, manifest) actually written to disk. Recomputing
    # those checksums from disk and matching them seals the report.
    counts = {
        "cardinal": sum(1 for r in rows if r["entry_id"].startswith("en-num-card-")),
        "ordinal": sum(1 for r in rows if r["entry_id"].startswith("en-num-ord-")),
        "fraction": sum(1 for r in rows if r["entry_id"].startswith("en-num-frac-")),
        "multiplier": sum(1 for r in rows if r["entry_id"].startswith("en-num-mult-")),
        "quantifier": sum(1 for r in rows if r["entry_id"].startswith("en-num-quant-")),
        "comparison_anchor": sum(1 for r in rows if r["entry_id"].startswith("en-num-compare-")),
        "number_format": sum(1 for r in rows if r["entry_id"].startswith("en-num-format-")),
    }
    report = {
        "pack_id": PACK_ID,
        "version": "1.0.0",
        "provenance": PROVENANCE,
        "lexicon_sha256": lex_checksum,
        "glosses_sha256": gloss_checksum,
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "entry_counts": counts,
        "total_entries": len(rows),
        "ratified_at": "2026-05-23",
        "ratification_invariants": [
            "cardinal_exhaustive_0_to_20",
            "cardinal_tens_complete",
            "cardinal_magnitudes_complete",
            "ordinal_exhaustive_1_to_31",
            "fraction_named_1_2_through_1_10",
            "fraction_irregular_sixteenth_thirty_second",
            "quantifier_semantic_type_closed_set",
            "number_format_regex_corpus_gated",
        ],
    }
    report_path = PACK_DIR / f"{PACK_ID}.mastery_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    print(f"wrote {len(rows)} lexicon entries to {PACK_DIR}")
    print(f"lexicon sha256 = {lex_checksum}")
    print(f"glosses sha256 = {gloss_checksum}")
    print(f"entry counts: {counts}")


if __name__ == "__main__":
    main()

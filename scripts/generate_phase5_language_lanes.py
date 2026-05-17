"""Generate Phase 5.2 (Hebrew) and 5.3 (Koine Greek) fluency lanes.

These lanes are scoped honestly to v1 = C01 (simple declarative) only.
The realizer's tense/aspect/quantifier/negation logic in
``generate/templates.py`` is English-only; C02–C13 require new
HE/GRC morphology + templates before they can be measured here.
That work is named explicitly in each lane's ``gaps.md`` as the v2
unblock path.

What v1 *does* measure: that the deterministic articulation layer
(``generate/articulation.py``) produces grammatical surfaces in
script-appropriate word order when given a (subject, predicate,
object) triple drawn from the target pack's seed vocabulary.

Verb-second Hebrew: predicate-subject(-object), per
``generate.articulation._assemble``.
Greek (Koine): subject(-object)-predicate.

Run:
    .venv/bin/python scripts/generate_phase5_language_lanes.py
"""

from __future__ import annotations

import json
from pathlib import Path

# Triples drawn from the seed packs.  Surface forms taken from
# language_packs/data/<pack>/lexicon.jsonl.
# Triples use only verbs/nouns present in he_core_cognition_v1
# (12 NOUN, 3 VERB: גילה reveal, מצא find, קדם precede).
HEBREW_TRIPLES: list[tuple[str, str, str]] = [
    ("דבר", "גילה", "אמת"),     # word reveals truth
    ("אור", "קדם", "חושך"),     # light precedes darkness
    ("חכמה", "מצא", "דעת"),     # wisdom finds knowledge
]

# Triples use only verbs/nouns present in grc_logos_cognition_v1
# (12 NOUN, 3 main VERB: φαίνω reveal, εὑρίσκω find, προάγω precede).
GREEK_TRIPLES: list[tuple[str, str, str]] = [
    ("λόγος", "φαίνω", "ἀλήθεια"),     # logos reveals truth
    ("φῶς", "προάγω", "σκότος"),       # light precedes darkness
    ("σοφία", "εὑρίσκω", "γνῶσις"),    # wisdom finds knowledge
]


def _assemble(language: str, subj: str, pred: str, obj: str) -> str:
    """Mirror generate.articulation._assemble exactly."""
    if language == "he":
        return f"{pred} {subj} {obj}"
    if language == "grc":
        return f"{subj} {obj} {pred}"
    return f"{subj} {pred} {obj}"


def _build_case(
    cid: str,
    language: str,
    triple: tuple[str, str, str],
) -> dict:
    subj, pred, obj = triple
    expected = _assemble(language, subj, pred, obj)
    return {
        "id": cid,
        "construction": "C01",
        "construction_name": "simple_declarative",
        "language": language,
        "proposition_graph": {
            "nodes": [
                {
                    "node_id": "n1",
                    "subject": subj,
                    "predicate": pred,
                    "obj": obj,
                }
            ],
            "edges": [],
        },
        "accept_surfaces": [expected],
        "constraints": {
            "must_contain": [subj, pred, obj],
            "word_order": expected.split(),
            "max_words": 6,
        },
    }


def _emit(
    prefix: str,
    language: str,
    triples: list[tuple[str, str, str]],
    out_path: Path,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(_build_case(f"{prefix}_{i+1:02d}", language, t), ensure_ascii=False)
        for i, t in enumerate(triples)
    ]
    out_path.write_text("\n".join(lines) + "\n")
    return len(lines)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent

    # Hebrew (Phase 5.2)
    he_lane = root / "evals" / "hebrew_fluency"
    n_he_pub = _emit("HEB-PUB", "he", HEBREW_TRIPLES, he_lane / "public" / "v1" / "cases.jsonl")
    n_he_dev = _emit("HEB-DEV", "he", HEBREW_TRIPLES[:1], he_lane / "dev" / "cases.jsonl")
    # Holdouts intentionally reserved until v2 (more vocabulary).
    print(f"hebrew_fluency  public={n_he_pub}  dev={n_he_dev}")

    # Koine Greek (Phase 5.3)
    grc_lane = root / "evals" / "koine_greek_fluency"
    n_grc_pub = _emit("GRC-PUB", "grc", GREEK_TRIPLES, grc_lane / "public" / "v1" / "cases.jsonl")
    n_grc_dev = _emit("GRC-DEV", "grc", GREEK_TRIPLES[:1], grc_lane / "dev" / "cases.jsonl")
    print(f"koine_greek_fluency  public={n_grc_pub}  dev={n_grc_dev}")

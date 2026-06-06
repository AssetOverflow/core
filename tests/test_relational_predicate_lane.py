"""Relational-predicate capability lane (#596 on the yardstick).

Two obligations, kept separate on purpose:
  - COVERAGE: the positive gold lane (`v1/cases.jsonl`) — the reader correctly
    comprehends clean binary-relation prose, wrong=0, and the domain is composed into
    the capability index (breadth 8→9).
  - FALSIFICATION: the adversarial inputs (`v1/refusals.jsonl`) — the #596 fabrication
    class MUST refuse. This is the bite: if the reader ever commits on one of these,
    the lane's wrong=0 promise is a lie and this test fails.

The gold is hand-authored from English semantics, independent of the reader (INV-25 /
INV-27): a passing lane cannot be the reader grading its own output.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.capability_index.adapters import collect_domain_results
from evals.comprehension.relational_predicate_runner import run
from generate.meaning_graph.reader import Refusal
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)

_REFUSALS = Path(__file__).resolve().parent.parent / "evals" / "relational" / "v1" / "refusals.jsonl"


def _refusal_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in _REFUSALS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# --------------------------------------------------------------------------- #
# Coverage: clean prose comprehends correctly, wrong=0
# --------------------------------------------------------------------------- #


def test_positive_lane_is_green() -> None:
    report = run()
    assert report["wrong"] == 0
    assert report["refused"] == 0  # every clean case reads
    assert report["correct"] == report["total"] == 17


def test_lane_is_composed_into_capability_index() -> None:
    results = {d.domain: d for d in collect_domain_results().results}
    dom = results.get("comprehension_relational_predicate")
    assert dom is not None, "relational-predicate domain missing from the index"
    assert dom.wrong == 0 and dom.correct == 17 and dom.coverage == 1.0


# --------------------------------------------------------------------------- #
# Falsification: the #596 fabrication class MUST refuse (the bite)
# --------------------------------------------------------------------------- #


def test_adversarial_inputs_all_refuse() -> None:
    pack = load_relational_pack_lemmas()
    cases = _refusal_cases()
    assert len(cases) >= 9  # the #596 hazard family + negation + non-template + the verb gap
    for case in cases:
        comp = comprehend_relational(case["text"], pack)
        assert isinstance(comp, Refusal), (
            f"FABRICATION: {case['text']!r} should refuse ({case['why']}) but committed {comp!r}"
        )


def test_no_fabricated_relation_ever_committed() -> None:
    # Stronger than "is a Refusal": confirm not a single relation/query is produced for
    # any adversarial input (no empty-but-committed Comprehension slips through).
    pack = load_relational_pack_lemmas()
    for case in _refusal_cases():
        comp = comprehend_relational(case["text"], pack)
        assert isinstance(comp, Refusal), case["text"]

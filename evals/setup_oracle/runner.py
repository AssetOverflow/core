"""Setup-oracle runner — grade the reader's comprehended structure + UNITS vs gold.

For each relational_metric case: comprehend the prose into a binding-graph and compare,
against the INDEPENDENT gold, three axes:
  1. the relation STRUCTURE (facts + typed equations — from the IR, not a reparse),
  2. the per-symbol UNITS (read from the binding-graph, vs the expected_units fixture),
  3. the question TARGET (symbol, state-index, form, expected unit).
A mismatch on ANY axis is ``setup_wrong`` — the wrong=0-critical count — even if the
answer would be right. This is a STRICTER gate than the relational_metric (answer) lane,
and the gate every future GSM8K frame family must pass before serving.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.relational_metric.runner import _load_cases
from evals.setup_oracle.signature import (
    gold_unknown_signature,
    reader_symbol_units,
    reader_unknown_signature,
    relation_signature,
    symbol_unit_signature,
)
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import comprehend_quantitative, to_relational_metric

_EXPECTED_UNITS_PATH = Path(__file__).resolve().parent / "expected_units.json"


def _load_expected_units() -> dict[str, dict[str, str]]:
    raw = json.loads(_EXPECTED_UNITS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def run() -> dict[str, Any]:
    """Score the reader's setup (structure + units + target) against the independent gold."""
    cases = _load_cases()
    expected_units = _load_expected_units()
    setup_correct = setup_wrong = setup_refused = 0
    wrongs: list[dict[str, Any]] = []

    for case in cases:
        comp = comprehend_quantitative(case["text"])
        if isinstance(comp, Refusal):
            setup_refused += 1
            continue
        projected = to_relational_metric(comp)
        if projected is None:
            setup_refused += 1
            continue
        reader_relations, _reader_query = projected
        case_units = expected_units.get(case.get("id", ""), {})

        reader_rel = relation_signature(reader_relations)
        gold_rel = relation_signature(case["relations"])
        reader_units = reader_symbol_units(comp.binding_graph)
        gold_units = symbol_unit_signature(case_units)
        reader_unk = reader_unknown_signature(comp.binding_graph)
        gold_unk = gold_unknown_signature(case["relations"], case["query"], case_units)

        if reader_rel == gold_rel and reader_units == gold_units and reader_unk == gold_unk:
            setup_correct += 1
        else:
            setup_wrong += 1
            wrongs.append(
                {
                    "id": case.get("id"),
                    "relations_match": reader_rel == gold_rel,
                    "units_match": reader_units == gold_units,
                    "target_match": reader_unk == gold_unk,
                    "reader_units": reader_units,
                    "gold_units": gold_units,
                    "reader_target": reader_unk,
                    "gold_target": gold_unk,
                }
            )

    return {
        "lane": "setup_oracle",
        "grades": "structure + per-symbol units + question target (symbol/state/form/unit)",
        "total": len(cases),
        "setup_correct": setup_correct,
        "setup_wrong": setup_wrong,
        "setup_refused": setup_refused,
        "wrongs": wrongs,
        "counts": {
            "setup_correct": setup_correct,
            "setup_wrong": setup_wrong,
            "setup_refused": setup_refused,
        },
    }


__all__ = ["run"]

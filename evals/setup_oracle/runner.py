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

from evals.relational_metric.oracle import OracleError, oracle_answer
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
_R1_GOLD_PATH = Path(__file__).resolve().parent / "r1_gold.jsonl"


def _load_expected_units() -> dict[str, dict[str, str]]:
    raw = json.loads(_EXPECTED_UNITS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _load_r1_gold() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _R1_GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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


def _score_setup_fixture(fx: dict[str, Any]) -> tuple[str, str | None, dict[str, Any] | None]:
    """Score one independent setup fixture by structure, not answer.

    Returns ``(outcome, reason, detail)`` where outcome is ``correct`` / ``refused`` /
    ``WRONG``. Kept small so PR-6b can reuse the same setup gate before evaluating
    answers; answer scoring must never run on a structurally wrong reading.
    """
    comp = comprehend_quantitative(fx["text"])
    if isinstance(comp, Refusal):
        return "refused", comp.reason, None
    projected = to_relational_metric(comp)
    if projected is None:
        return "refused", "unprojectable", None
    reader_relations, _ = projected
    units = fx["expected_units"]

    reader_rel = relation_signature(reader_relations)
    gold_rel = relation_signature(fx["relations"])
    reader_units = reader_symbol_units(comp.binding_graph)
    gold_units = symbol_unit_signature(units)
    reader_unk = reader_unknown_signature(comp.binding_graph)
    gold_unk = gold_unknown_signature(fx["relations"], fx["query"], units)

    if reader_rel == gold_rel and reader_units == gold_units and reader_unk == gold_unk:
        return "correct", None, None
    return "WRONG", None, {
        "relations_match": reader_rel == gold_rel,
        "units_match": reader_units == gold_units,
        "target_match": reader_unk == gold_unk,
        "reader_relations": reader_rel,
        "gold_relations": gold_rel,
        "reader_target": reader_unk,
        "gold_target": gold_unk,
    }


def run_r1() -> dict[str, Any]:
    """Score the CURRENT reader against the independent, self-contained R1 gold.

    The reader cannot read most R1 shapes (multiplicative, multi-step, partition) yet.
    The SUCCESS CRITERION is **``setup_wrong == 0``**: it must REFUSE every unsupported
    shape, NEVER misread it as a simpler form. ``setup_refused`` is the unsupported count;
    ``setup_correct`` is any shape already faithfully supported. A ``setup_wrong`` is a
    pre-existing wrong-reading hazard to fix BEFORE building the R1 frame (PR-5c).
    """
    fixtures = _load_r1_gold()
    setup_correct = setup_wrong = setup_refused = 0
    details: list[dict[str, Any]] = []

    for fx in fixtures:
        outcome, reason, detail = _score_setup_fixture(fx)
        if outcome == "correct":
            setup_correct += 1
            details.append({"id": fx["id"], "outcome": "correct"})
        elif outcome == "refused":
            setup_refused += 1
            details.append({"id": fx["id"], "outcome": "refused", "reason": reason})
        else:
            setup_wrong += 1
            details.append({"id": fx["id"], "outcome": "WRONG", **(detail or {})})

    return {
        "lane": "setup_oracle_r1",
        "total": len(fixtures),
        "setup_correct": setup_correct,
        "setup_wrong": setup_wrong,
        "setup_refused": setup_refused,
        "details": details,
        "counts": {
            "setup_correct": setup_correct,
            "setup_wrong": setup_wrong,
            "setup_refused": setup_refused,
        },
    }


def run_r1_answers() -> dict[str, Any]:
    """Off-serving answer lane for setup-correct R1 fixtures (PR-6b).

    This does NOT expand the reader or serving path. It only asks the independent
    relational oracle to evaluate fixtures whose setup already matches the independent R1
    gold. Unsupported fixtures remain refused; setup-wrong fixtures are not answer-scored.
    """
    fixtures = _load_r1_gold()
    correct = wrong = refused = setup_wrong = gold_error = 0
    details: list[dict[str, Any]] = []

    for fx in fixtures:
        outcome, reason, detail = _score_setup_fixture(fx)
        if outcome == "WRONG":
            setup_wrong += 1
            details.append({"id": fx["id"], "outcome": "setup_WRONG", **(detail or {})})
            continue
        if outcome == "refused":
            refused += 1
            details.append({"id": fx["id"], "outcome": "refused", "reason": reason})
            continue

        try:
            got = oracle_answer(fx["relations"], fx["query"])
        except OracleError as exc:
            gold_error += 1
            details.append({"id": fx["id"], "outcome": "gold_error", "reason": str(exc)})
            continue

        expected = fx.get("gold")
        if got == expected:
            correct += 1
            details.append({"id": fx["id"], "outcome": "correct", "answer": got})
        else:
            wrong += 1
            details.append({"id": fx["id"], "outcome": "WRONG", "answer": got, "gold": expected})

    return {
        "lane": "setup_oracle_r1_answers",
        "total": len(fixtures),
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "setup_wrong": setup_wrong,
        "gold_error": gold_error,
        "details": details,
        "counts": {
            "correct": correct,
            "wrong": wrong,
            "refused": refused,
            "setup_wrong": setup_wrong,
            "gold_error": gold_error,
        },
    }


__all__ = ["run", "run_r1", "run_r1_answers"]

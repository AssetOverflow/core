"""Setup-oracle runner — grade the reader's comprehended structure vs gold structure.

For each relational_metric case: comprehend the prose into a binding-graph, project it
to relations + read its question target, and compare the (relations, target) SIGNATURE
to the case's INDEPENDENT gold (`relations` + `query`). A structural mismatch is
``setup_wrong`` — the wrong=0-critical count — even if the answer would be right.

This is a STRICTER gate than the relational_metric (answer) lane: it requires the
reader to have read the problem the way the gold says it reads, not merely to land on
the gold number. It is the gate every future frame family must pass before serving.
"""

from __future__ import annotations

from typing import Any

from evals.relational_metric.runner import _load_cases
from evals.setup_oracle.signature import (
    gold_unknown_signature,
    reader_unknown_signature,
    relation_signature,
)
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import comprehend_quantitative, to_relational_metric


def run() -> dict[str, Any]:
    """Score the reader's setup against the independent gold setup, structure-only."""
    cases = _load_cases()
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

        reader_sig = relation_signature(reader_relations)
        gold_sig = relation_signature(case["relations"])
        reader_unk = reader_unknown_signature(comp.binding_graph)
        gold_unk = gold_unknown_signature(case["relations"], case["query"])

        if reader_sig == gold_sig and reader_unk == gold_unk:
            setup_correct += 1
        else:
            setup_wrong += 1
            wrongs.append(
                {
                    "id": case.get("id"),
                    "relations_match": reader_sig == gold_sig,
                    "target_match": reader_unk == gold_unk,
                    "reader_relations": reader_sig,
                    "gold_relations": gold_sig,
                    "reader_target": reader_unk,
                    "gold_target": gold_unk,
                }
            )

    return {
        "lane": "setup_oracle",
        "grades": "structure-only (facts + equations + question target); units deferred",
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

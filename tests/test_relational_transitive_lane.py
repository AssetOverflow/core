"""Lane test — transitive strict-order relational inference (capability-index lane +
wrong=0 bite + independent-oracle cross-check).

The positive lane (``v1/cases.jsonl``) is the capability-index coverage (breadth 10→11);
the confuser lane (``v1/refusals.jsonl``) is the wrong=0 bite — every confuser MUST refuse,
or the transitive rule over-fired. The independent transitive-closure oracle
(``evals.relational_transitive.oracle``, disjoint from the engine per INV-25/27) confirms
every positive IS entailed and every confuser is NOT — so the gold is non-vacuous. Fixture
SHAs are pinned so the gold cannot drift silently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from evals.relational_transitive.oracle import transitively_entails
from evals.relational_transitive.runner import _load_cases, run
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import realize_comprehension
from session.context import SessionContext

_V1 = Path(__file__).resolve().parent.parent / "evals" / "relational_transitive" / "v1"
_CASES_SHA = "18f1c8fad6030b4d141f80a4e6547bec6ae384c5d1a098372d4d16cedda50150"
_REFUSALS_SHA = "984e0df23e286c857f72049a399d46d2a8e72660ded9cf59aa1f7a09d9b11673"
_HIGH = 10**9


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


@pytest.fixture(scope="module")
def pack():
    return load_relational_pack_lemmas()


def _determine_case(case, vocab_persona, pack):
    vocab, persona = vocab_persona
    ctx = SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH)
    for fact in case["facts"]:
        realize_comprehension(comprehend_relational(fact, pack), ctx)
    return determine(comprehend_relational(case["query"], pack), ctx)


def test_fixture_shas_pinned() -> None:
    assert _sha(_V1 / "cases.jsonl") == _CASES_SHA
    assert _sha(_V1 / "refusals.jsonl") == _REFUSALS_SHA


def test_positive_lane_wrong_zero_and_covers() -> None:
    r = run()
    assert r["wrong"] == 0, r["wrongs"]
    assert r["correct"] > 0  # coverage > 0 — else the index geomean zeroes the score
    assert r["correct"] + r["wrong"] + r["refused"] == r["total"]


def test_positives_determine_transitive(vocab_persona, pack) -> None:
    # non-vacuous coverage: every positive determines True via the TRANSITIVE rule.
    for case in _load_cases(_V1 / "cases.jsonl"):
        res = _determine_case(case, vocab_persona, pack)
        assert isinstance(res, Determined), case["id"]
        assert res.answer is True and res.rule == "transitive", case["id"]
        assert [res.predicate, res.subject, res.object] == case["query_edge"], case["id"]
        assert len(res.grounds) >= 2  # a real chain, not a single direct edge


def test_confusers_all_refuse(vocab_persona, pack) -> None:
    # wrong=0 BITE: a Determined on ANY confuser means the transitive rule over-fired
    # (a non-transitive predicate, a non-admitted spatial predicate, a mixed/disjoint
    # chain, a reflexive cycle, or inverse+transitive composition). All must refuse.
    asserted = []
    for case in _load_cases(_V1 / "refusals.jsonl"):
        res = _determine_case(case, vocab_persona, pack)
        if isinstance(res, Determined):
            asserted.append(
                {
                    "id": case["id"],
                    "why": case["why"],
                    "got": [res.answer, res.predicate, res.subject, res.object, res.rule],
                }
            )
        else:
            assert isinstance(res, Undetermined)
    assert not asserted, f"confuser(s) asserted (transitive rule over-fired): {asserted}"


def test_oracle_confirms_positives() -> None:
    # INV-25/27 independence + non-vacuity: the disjoint BFS oracle agrees every positive
    # IS in the same-predicate transitive closure (so the gold is real, not the engine's echo).
    for case in _load_cases(_V1 / "cases.jsonl"):
        p, s, o = case["query_edge"]
        assert transitively_entails(case["edges"], p, s, o) is True, case["id"]


def test_oracle_refutes_confusers() -> None:
    # the disjoint oracle agrees every confuser is NOT entailed — so each engine refusal is
    # the CORRECT verdict, not a coverage gap masking a real entailment.
    for case in _load_cases(_V1 / "refusals.jsonl"):
        p, s, o = case["query_edge"]
        assert transitively_entails(case["edges"], p, s, o) is False, case["id"]

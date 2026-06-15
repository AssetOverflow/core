"""Lane test — one-hop relational inference (capability-index lane + wrong=0 bite).

The positive lane (cases.jsonl) is the capability-index coverage; the confuser lane
(refusals.jsonl) is the wrong=0 bite — every confuser MUST refuse, or the inverse/
symmetric rule over-fired. Fixture SHAs are pinned so the gold cannot drift silently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from evals.comprehension.relational_inference_runner import _load_cases, run
from generate.determine import Determined, determine
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import realize_comprehension
from session.context import SessionContext

_V1 = Path(__file__).resolve().parent.parent / "evals" / "relational_inference" / "v1"
_CASES_SHA = "03310ecc3ab7b7bf26f0a1779709bf468e888bbca1e53a71cba1d269b5c1dd71"
_REFUSALS_SHA = "35cf8369ec0ba80a4e90ecc88de73dafac660ac5982288f49c3aeeb3e5123a16"
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


def test_fixture_shas_pinned() -> None:
    assert _sha(_V1 / "cases.jsonl") == _CASES_SHA
    assert _sha(_V1 / "refusals.jsonl") == _REFUSALS_SHA


def test_positive_lane_wrong_zero_and_covers() -> None:
    r = run()
    assert r["wrong"] == 0, r["wrongs"]
    assert r["correct"] > 0  # coverage > 0 — else the index geomean zeroes the score
    assert r["correct"] + r["wrong"] + r["refused"] == r["total"]


def test_confusers_all_refuse(vocab_persona, pack) -> None:
    # wrong=0 BITE: a Determined on ANY confuser means the one-hop rule over-fired
    # (an asymmetric self-converse, a cross-predicate, an object mismatch, transitive-
    # through-inverse, or an ungrounded guess). All must refuse. (The same-predicate
    # strict-order transitive chain that used to live here MIGRATED to a determination
    # under B2 — see evals/relational_transitive — so it is no longer a confuser.)
    vocab, persona = vocab_persona
    asserted = []
    for case in _load_cases(_V1 / "refusals.jsonl"):
        ctx = SessionContext(
            vocab=vocab, persona=persona, vault_reproject_interval=_HIGH
        )
        for fact in case["facts"]:
            realize_comprehension(comprehend_relational(fact, pack), ctx)
        res = determine(comprehend_relational(case["query"], pack), ctx)
        if isinstance(res, Determined):
            asserted.append(
                {
                    "id": case["id"],
                    "why": case["why"],
                    "got": [res.answer, res.predicate, res.subject, res.object],
                }
            )
    assert not asserted, f"confuser(s) asserted (rule over-fired): {asserted}"

"""Lane test — ProofWriter-OWA refusal floor (B1, measure-only).

The independent oracle computes the OWA gold; the production `determine()` path must never
assert True on a non-`True` gold (wrong=0 — the soundness floor). The oracle is itself
pinned to the fixture's hand-authored `expected`. This is NOT a capability-index domain.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from evals.proofwriter_owa.oracle import label as owa_label
from evals.proofwriter_owa.score import _comprehend_any, _load, run
from generate.determine import Determined, determine
from generate.meaning_graph.relational import load_relational_pack_lemmas
from generate.realize import realize_comprehension
from session.context import SessionContext

_FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "proofwriter_owa"
    / "fixtures.jsonl"
)
_FIXTURES_SHA = "7b340849a945d27306793a109fd65532803be40281b6da15809f9d33ea7f6580"
_HIGH = 10**9


def test_fixtures_sha_pinned() -> None:
    got = hashlib.sha256(_FIXTURES.read_bytes()).hexdigest()
    assert got == _FIXTURES_SHA, f"fixtures.jsonl drifted: {got}"


def test_oracle_matches_authored_expected() -> None:
    """Pin the independent oracle to the hand-authored intent — the oracle is verified,
    so its gold can be trusted as the disjoint reference for `determine()`."""
    for it in _load():
        assert owa_label(it["facts"], it["query"]) == it["expected"], it["id"]


@pytest.fixture(scope="module")
def report():
    return run()


def test_refusal_floor_wrong_zero(report) -> None:
    """THE floor: `determine()` never asserts True on a gold `Unknown`/`False`."""
    assert report["wrong"] == 0, report["wrongs"]


def test_serving_support_truths_are_determined(report) -> None:
    """Every gold-`True` item inside the engine's claimed support determines True —
    no silent coverage loss — and the lane actually exercises a positive path."""
    assert report["coverage_gaps"] == [], report["coverage_gaps"]
    assert report["correct"] > 0


def test_no_answer_false_constructed() -> None:
    """Behavioral echo of INV-30: across every item, `determine()` never yields
    `answer=False` (the open-world gear is True-or-refuse)."""
    pack = load_relational_pack_lemmas()
    rt = ChatRuntime(no_load_state=True)
    vocab, persona = rt._context.vocab, rt._context.persona
    for it in _load():
        ctx = SessionContext(
            vocab=vocab, persona=persona, vault_reproject_interval=_HIGH
        )
        for fact in it["facts"]:
            realize_comprehension(_comprehend_any(fact, pack), ctx)
        res = determine(_comprehend_any(it["query"], pack), ctx)
        if isinstance(res, Determined):
            assert res.answer is True, it["id"]

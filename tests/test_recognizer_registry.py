"""ADR-0163 Phase D — recognizer_registry tests.

Pins:
- load_ratified_registry returns empty tuple when log is empty
- filters by state=accepted + kind=exemplar_corpus
- order: sorted by (review_date, proposal_id)
- malformed spec -> RegistryLoadError with the offending proposal_id
- cache hit on identical log; cache invalidates on log mtime change
- pure: monkeypatch open() to count log reads
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from generate.recognizer_registry import (
    RegistryLoadError,
    clear_registry_cache,
    load_ratified_registry,
)
from teaching.proposals import ProposalLog


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    clear_registry_cache()
    yield
    clear_registry_cache()


def _make_proposal(
    *,
    proposal_id: str,
    shape_category: str,
    review_state: str,
    kind: str = "exemplar_corpus",
) -> dict[str, Any]:
    """Build a proposal dict the live log shape accepts.

    Mirrors the JSONL shape Phase C's CLI writes: source.kind +
    proposed_chain.recognizer_spec carry the load-bearing fields.
    """
    return {
        "claim_domain": "factual",
        "evidence": [
            {
                "epistemic_status": "coherent",
                "polarity": "affirms",
                "ref": "exemplar:test",
                "source": "corpus",
            }
        ],
        "operator_note": "",
        "polarity": "affirms",
        "proposal_id": proposal_id,
        "proposed_chain": {
            "subject": shape_category,
            "intent": "admissibility",
            "connective": "recognizes",
            "object": "abc123def456",
            "recognizer_spec": {
                "shape_category": shape_category,
                "canonical_pattern": {
                    "shape_category": shape_category,
                    "graph_intent": "setup"
                    if shape_category == "descriptive_setup_no_quantity"
                    else "aggregate",
                    "outcome": "inadmissible_by_design"
                    if shape_category == "descriptive_setup_no_quantity"
                    else "admissible",
                    "quantity_anchor_count": 0,
                    "unresolved_notes": [],
                },
                "exemplar_count": 1,
                "exemplar_digest": "deadbeef",
                "coverage": {},
            },
        },
        "provenance": None,
        "replay_evidence": None,
        "review_state": review_state,
        "source": {
            "emitted_at_revision": "abc",
            "kind": kind,
            "source_id": "digest" if kind != "operator" else "",
        },
        "source_candidate_id": f"cand-{proposal_id}",
    }


def _write_log(path: Path, events: list[dict[str, Any]]) -> None:
    """Write a synthetic proposal log JSONL at *path*."""
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, sort_keys=True, separators=(",", ":")) + "\n")


def test_empty_log_returns_empty_registry(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    log_path.write_text("", encoding="utf-8")
    log = ProposalLog(log_path)
    assert load_ratified_registry(log) == ()


def test_pending_proposals_not_in_registry(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {
            "event": "created",
            "proposal": _make_proposal(
                proposal_id="aaaa1111",
                shape_category="descriptive_setup_no_quantity",
                review_state="pending",
            ),
        },
    ])
    assert load_ratified_registry(ProposalLog(log_path)) == ()


def test_non_exemplar_corpus_kind_not_in_registry(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {
            "event": "created",
            "proposal": _make_proposal(
                proposal_id="bbbb2222",
                shape_category="descriptive_setup_no_quantity",
                review_state="pending",
                kind="contemplation",
            ),
        },
        {
            "event": "transition",
            "proposal_id": "bbbb2222",
            "to": "accepted",
            "note": "2026-05-27",
        },
    ])
    assert load_ratified_registry(ProposalLog(log_path)) == ()


def test_accepted_exemplar_proposal_enters_registry(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {
            "event": "created",
            "proposal": _make_proposal(
                proposal_id="cccc3333",
                shape_category="rate_with_currency",
                review_state="pending",
            ),
        },
        {
            "event": "transition",
            "proposal_id": "cccc3333",
            "to": "accepted",
            "note": "2026-05-27",
        },
    ])
    reg = load_ratified_registry(ProposalLog(log_path))
    assert len(reg) == 1
    assert reg[0].proposal_id == "cccc3333"
    assert reg[0].shape_category.value == "rate_with_currency"
    assert reg[0].review_date == "2026-05-27"


def test_registry_sort_order_is_review_date_then_id(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {"event": "created", "proposal": _make_proposal(
            proposal_id="zzzzzzzz",
            shape_category="rate_with_currency",
            review_state="pending",
        )},
        {"event": "transition", "proposal_id": "zzzzzzzz", "to": "accepted", "note": "2026-05-27"},
        {"event": "created", "proposal": _make_proposal(
            proposal_id="aaaaaaaa",
            shape_category="rate_with_currency",
            review_state="pending",
        )},
        {"event": "transition", "proposal_id": "aaaaaaaa", "to": "accepted", "note": "2026-05-26"},
    ])
    reg = load_ratified_registry(ProposalLog(log_path))
    # Earlier date first.
    assert [r.proposal_id for r in reg] == ["aaaaaaaa", "zzzzzzzz"]


def test_malformed_spec_raises_with_proposal_id(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    broken = _make_proposal(
        proposal_id="badbadbad",
        shape_category="rate_with_currency",
        review_state="pending",
    )
    # Corrupt: shape_category is not a member of ShapeCategory.
    broken["proposed_chain"]["recognizer_spec"]["shape_category"] = "not_a_category"
    _write_log(log_path, [
        {"event": "created", "proposal": broken},
        {"event": "transition", "proposal_id": "badbadbad", "to": "accepted", "note": "2026-05-27"},
    ])
    with pytest.raises(RegistryLoadError, match="badbadbad"):
        load_ratified_registry(ProposalLog(log_path))


def test_cache_hit_avoids_re_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {"event": "created", "proposal": _make_proposal(
            proposal_id="cccc3333", shape_category="rate_with_currency", review_state="pending",
        )},
        {"event": "transition", "proposal_id": "cccc3333", "to": "accepted", "note": "2026-05-27"},
    ])
    log = ProposalLog(log_path)

    read_counter = {"n": 0}
    real_read = Path.read_bytes

    def _tracking_read_bytes(self: Path) -> bytes:
        if str(self) == str(log_path):
            read_counter["n"] += 1
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", _tracking_read_bytes)
    load_ratified_registry(log)
    first = read_counter["n"]
    load_ratified_registry(log)
    # Second call uses cache: at most one extra read (the cache-key
    # mtime+sha lookup itself reads bytes), not a full re-projection.
    assert read_counter["n"] - first <= 1


def test_cache_invalidates_on_log_change(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    _write_log(log_path, [
        {"event": "created", "proposal": _make_proposal(
            proposal_id="cccc3333", shape_category="rate_with_currency", review_state="pending",
        )},
        {"event": "transition", "proposal_id": "cccc3333", "to": "accepted", "note": "2026-05-27"},
    ])
    log = ProposalLog(log_path)
    reg_a = load_ratified_registry(log)
    assert len(reg_a) == 1

    # Append another accepted proposal; cache must invalidate.
    import time
    time.sleep(0.01)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "created", "proposal": _make_proposal(
            proposal_id="dddd4444",
            shape_category="temporal_aggregation",
            review_state="pending",
        )}) + "\n")
        fh.write(json.dumps({
            "event": "transition", "proposal_id": "dddd4444",
            "to": "accepted", "note": "2026-05-28",
        }) + "\n")
    reg_b = load_ratified_registry(log)
    assert len(reg_b) == 2


def test_live_proposal_log_has_phase_c_proposals() -> None:
    """Audit-level check: the live log carries the three Phase C
    proposals.  Post-#304 (operator ratification round 1) they are
    all ``accepted`` and the registry returns three entries.  If a
    future ratification round withdraws any of them, this test will
    surface the change."""
    from tests._phase_d_fixture import PHASE_C_PROPOSAL_IDS

    log = ProposalLog()
    state = log.current_state()
    missing = [pid for pid in PHASE_C_PROPOSAL_IDS if pid not in state]
    assert not missing, (
        f"live proposal log is missing Phase C proposals {missing}; "
        "run `core teaching propose-from-exemplars --all` first"
    )
    # Post-#304 they are accepted.  ADR-0161 §5 — only the operator
    # ratifies; this test pins the operator's round-1 ratification.
    accepted_count = sum(
        1 for pid in PHASE_C_PROPOSAL_IDS
        if state[pid]["state"] == "accepted"
    )
    assert accepted_count == len(PHASE_C_PROPOSAL_IDS), (
        f"expected {len(PHASE_C_PROPOSAL_IDS)} accepted Phase C proposals, "
        f"got {accepted_count}: {[(pid[:12], state[pid]['state']) for pid in PHASE_C_PROPOSAL_IDS]}"
    )
    # Registry exposes the ratified set, which has grown past round 1 as later
    # ratification rounds (flywheel-demo, rat1-cli-seed, ME-waves) accepted more
    # recognizers. The contract here is that the Phase C three remain present
    # and ratified — not that they are the only entries.
    registry_proposal_ids = {r.proposal_id for r in load_ratified_registry(log)}
    assert set(PHASE_C_PROPOSAL_IDS) <= registry_proposal_ids



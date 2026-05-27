"""ADR-0172 W4 — Workbench math-proposals e2e tests.

Six core tests plus an ADR-0172 tightening decoupling test:

1. Loads from JSONL: GET /math-proposals returns items when proposals.jsonl exists.
2. Renders domain badge: items carry domain='math', distinct from cognition /proposals.
3. ratify-vocabulary_addition routes to LexicalClaim handler (200, routing_status=routed).
4. ratify-matcher_extension fails loudly (501, not_implemented).
5. All 4 trace steps visible: GET /math-proposals/{id} includes 4-step trace.
6. No cross-contamination: cognition /proposals and math /math-proposals are independent.
7. (Tightening follow-up #1) Workbench reads self-contained JSONL — no decompose_audit() coupling.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from workbench.api import WorkbenchApi
from workbench.readers import MATH_PROPOSALS_JSONL

# Resolve the real audit once (used only to build test JSONL via the
# decomposer); the workbench itself no longer needs the audit file.
REAL_AUDIT_PATH = (
    Path(__file__).resolve().parent.parent
    / "evals" / "gsm8k_math" / "train_sample" / "v1" / "audit_brief_11.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl_from_proposals(tmp_path: Path, proposals) -> Path:
    """Write proposals.jsonl using the self-contained to_jsonl_record() format."""
    from teaching.math_contemplation_proposal import to_jsonl_record

    lines: list[bytes] = []
    for p in proposals:
        record = to_jsonl_record(p)
        lines.append(
            json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            + b"\n"
        )
    path = tmp_path / "proposals.jsonl"
    path.write_bytes(b"".join(lines))
    return path


def _real_audit_proposals():
    from teaching.math_contemplation import decompose_audit
    return decompose_audit(REAL_AUDIT_PATH)


def _make_synthetic_proposals_jsonl(
    tmp_path: Path, change_kinds: list[str]
) -> tuple[Path, list[str]]:
    """Build a synthetic proposals.jsonl in to_jsonl_record() format."""
    from evals.refusal_taxonomy.shape_categories import ShapeCategory
    from teaching.math_contemplation_proposal import build_proposal
    from teaching.math_evidence import MathReaderRefusalEvidence, from_audit_row
    from teaching.math_reasoning_trace import ReasoningStep, build_trace
    from generate.comprehension.audit import AuditRow

    def _ev(case_id: str, missing_op: str) -> MathReaderRefusalEvidence:
        row = AuditRow(
            case_id=case_id,
            sentence_index=0,
            token_index=0,
            token_text="weight",
            recognized_terms=(),
            skipped_frame=None,
            missing_operator=missing_op,
            refusal_reason="lexicon_entry",
            refusal_detail="",
        )
        return from_audit_row(row, "lexical", claim_signature="")

    proposals = []
    proposal_ids: list[str] = []

    for i, ck in enumerate(change_kinds):
        ev1 = _ev(f"c{i:02d}a", "drain_token")
        ev2 = _ev(f"c{i:02d}b", "drain_token")

        obs = ReasoningStep(
            step_index=0, step_kind="observation",
            input_pointers=(ev1.case_id, ev2.case_id),
            claim=f"synthetic observation for {ck}", justification="test",
            output_payload={"evidence_count": 2},
        )
        grp = ReasoningStep(
            step_index=1, step_kind="grouping",
            input_pointers=(ev1.case_id, ev2.case_id),
            claim="group key", justification="test", output_payload={"k": "v"},
        )
        hyp = ReasoningStep(
            step_index=2, step_kind="hypothesis",
            input_pointers=(ev1.case_id, ev2.case_id),
            claim=f"change_kind={ck}", justification="test",
            output_payload={"ck": ck},
        )
        con = ReasoningStep(
            step_index=3, step_kind="conclusion",
            input_pointers=(ev1.case_id, ev2.case_id),
            claim="conclude", justification="test", output_payload={"done": 1},
        )
        trace = build_trace((obs, grp, hyp, con))

        p = build_proposal(
            shape_category=ShapeCategory.UNCATEGORIZED,
            structural_commonality=(
                f"synthetic {ck} test proposal — sufficient length for "
                "wrong_zero_assertion gating"
            ),
            evidence_pointers=(ev1, ev2),
            proposed_change_kind=ck,  # type: ignore[arg-type]
            proposed_change_payload={
                "evidence_count": 2,
                "group_key": {"k": "v"},
                "modal_sub_type": "lexical",
            },
            wrong_zero_assertion=(
                "synthetic proposal for test; ratification handler enforces wrong=0"
            ),
            replay_equivalence_hash=hashlib.sha256(
                f"replay-{ck}-{i}".encode()
            ).hexdigest(),
            reasoning_trace=trace,
        )
        proposals.append(p)
        proposal_ids.append(p.proposal_id)

    jsonl_path = _write_jsonl_from_proposals(tmp_path, proposals)
    return jsonl_path, proposal_ids


# ---------------------------------------------------------------------------
# Test 1: Loads from JSONL
# ---------------------------------------------------------------------------


def test_1_loads_from_jsonl(tmp_path: Path) -> None:
    """GET /math-proposals returns items from proposals.jsonl when it exists."""
    proposals = _real_audit_proposals()
    jsonl = _write_jsonl_from_proposals(tmp_path, proposals)

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", "/math-proposals")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 200
    items = resp.payload.get("data", {}).get("items", [])
    assert len(items) == len(proposals)


# ---------------------------------------------------------------------------
# Test 2: Renders domain:math badge, distinct from cognition domain
# ---------------------------------------------------------------------------


def test_2_renders_domain_math_badge(tmp_path: Path) -> None:
    """Items from /math-proposals have domain='math'; /proposals returns cognition (no domain field)."""
    proposals = _real_audit_proposals()
    jsonl = _write_jsonl_from_proposals(tmp_path, proposals)

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", "/math-proposals")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    items = resp.payload["data"]["items"]
    assert all(item["domain"] == "math" for item in items)

    cog_resp = WorkbenchApi().handle("GET", "/proposals")
    cog_items = cog_resp.payload.get("data", {}).get("items", [])
    for cog_item in cog_items:
        assert cog_item.get("domain") != "math"


# ---------------------------------------------------------------------------
# Test 3: ratify-vocabulary_addition routes to LexicalClaim handler
# ---------------------------------------------------------------------------


def test_3_ratify_vocabulary_addition_routes_to_lexical_claim(tmp_path: Path) -> None:
    """POST /math-proposals/{id}/ratify routes vocabulary_addition to LexicalClaim (200)."""
    jsonl_path, proposal_ids = _make_synthetic_proposals_jsonl(
        tmp_path, ["vocabulary_addition"]
    )
    vocab_pid = proposal_ids[0]

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl_path
    try:
        api = WorkbenchApi()
        resp = api.handle("POST", f"/math-proposals/{vocab_pid}/ratify")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 200, f"expected 200, got {resp.status}: {resp.payload}"
    data = resp.payload.get("data", {})
    assert data.get("handler_name") == "LexicalClaim"
    assert data.get("routing_status") == "routed"
    assert data.get("change_kind") == "vocabulary_addition"


# ---------------------------------------------------------------------------
# Test 4: ratify-matcher_extension fails loudly
# ---------------------------------------------------------------------------


def test_4_ratify_matcher_extension_fails_loudly(tmp_path: Path) -> None:
    """POST /math-proposals/{id}/ratify returns 501 for matcher_extension with clear message."""
    jsonl_path, proposal_ids = _make_synthetic_proposals_jsonl(
        tmp_path, ["matcher_extension"]
    )
    matcher_pid = proposal_ids[0]

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl_path
    try:
        api = WorkbenchApi()
        resp = api.handle("POST", f"/math-proposals/{matcher_pid}/ratify")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 501
    err = resp.payload.get("error", {})
    message = err.get("message", "")
    assert "handler not yet implemented" in message
    assert "matcher_extension" in message


# ---------------------------------------------------------------------------
# Test 5: All 4 trace steps visible
# ---------------------------------------------------------------------------


def test_5_all_4_trace_steps_visible(tmp_path: Path) -> None:
    """GET /math-proposals/{id} includes reasoning_trace_steps with all 4 steps.

    Post-tightening: the workbench reads steps directly from the
    self-contained JSONL record; no decompose_audit() re-run.
    """
    proposals = _real_audit_proposals()
    assert proposals
    jsonl = _write_jsonl_from_proposals(tmp_path, proposals)

    first_id = proposals[0].proposal_id

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", f"/math-proposals/{first_id}")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 200, f"expected 200, got {resp.status}: {resp.payload}"
    detail = resp.payload.get("data", {})
    steps = detail.get("reasoning_trace_steps", [])
    assert len(steps) == 4
    step_kinds = [s["step_kind"] for s in steps]
    assert "observation" in step_kinds
    assert "grouping" in step_kinds
    assert "hypothesis" in step_kinds
    assert "conclusion" in step_kinds


# ---------------------------------------------------------------------------
# Test 6: No cross-contamination between math and cognition queues
# ---------------------------------------------------------------------------


def test_6_no_cross_contamination(tmp_path: Path) -> None:
    """Math /math-proposals and cognition /proposals are independent queues."""
    proposals = _real_audit_proposals()
    jsonl = _write_jsonl_from_proposals(tmp_path, proposals)

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        math_resp = api.handle("GET", "/math-proposals")
        cog_resp = api.handle("GET", "/proposals")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    math_items = math_resp.payload.get("data", {}).get("items", [])
    cog_items = cog_resp.payload.get("data", {}).get("items", [])

    assert all(item.get("domain") == "math" for item in math_items)
    for cog_item in cog_items:
        assert cog_item.get("domain") != "math"

    math_ids = {item["proposal_id"] for item in math_items}
    cog_ids = {item["proposal_id"] for item in cog_items}
    assert math_ids.isdisjoint(cog_ids)


# ---------------------------------------------------------------------------
# Test 7: Tightening follow-up #1 — workbench decoupled from decomposer
# ---------------------------------------------------------------------------


def test_7_workbench_decoupled_from_decompose_audit(tmp_path: Path) -> None:
    """Workbench reads math proposals without decompose_audit() being importable.

    Mocks teaching.math_contemplation out of sys.modules to prove the
    workbench load path does not depend on the decomposer.  Prior to the
    tightening follow-up, read_math_proposal() re-ran decompose_audit() to
    recover full trace steps — that coupling is now removed.
    """
    proposals = _real_audit_proposals()
    jsonl = _write_jsonl_from_proposals(tmp_path, proposals)
    first_id = proposals[0].proposal_id

    import workbench.readers as _r
    orig_jsonl = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl

    # Drop teaching.math_contemplation from the module cache to surface any
    # residual import dependency.  Install a sentinel that raises on access.
    class _ExplodingModule:
        def __getattr__(self, name: str):
            raise ImportError(
                f"decoupling violated: workbench tried to access "
                f"teaching.math_contemplation.{name}"
            )

    saved_module = sys.modules.pop("teaching.math_contemplation", None)
    sys.modules["teaching.math_contemplation"] = _ExplodingModule()  # type: ignore[assignment]

    try:
        api = WorkbenchApi()
        list_resp = api.handle("GET", "/math-proposals")
        detail_resp = api.handle("GET", f"/math-proposals/{first_id}")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig_jsonl
        if saved_module is not None:
            sys.modules["teaching.math_contemplation"] = saved_module
        else:
            sys.modules.pop("teaching.math_contemplation", None)

    assert list_resp.status == 200
    assert detail_resp.status == 200
    detail = detail_resp.payload["data"]
    assert len(detail["reasoning_trace_steps"]) == 4

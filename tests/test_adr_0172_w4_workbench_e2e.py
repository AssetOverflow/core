"""ADR-0172 W4 — Workbench math-proposals e2e tests.

Six tests:

1. Loads from JSONL: GET /math-proposals returns items when proposals.jsonl exists.
2. Renders domain badge: items carry domain='math', distinct from cognition /proposals.
3. ratify-vocabulary_addition routes to LexicalClaim handler (200, routing_status=routed).
4. ratify-matcher_extension fails loudly (501, not_implemented).
5. All 4 trace steps visible: GET /math-proposals/{id} includes 4-step trace.
6. No cross-contamination: cognition /proposals and math /math-proposals are independent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from workbench.api import WorkbenchApi
from workbench.readers import (
    MATH_PROPOSALS_JSONL,
    _DEFAULT_MATH_AUDIT_PATH,
    _load_math_proposals_raw,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REAL_AUDIT_PATH = _DEFAULT_MATH_AUDIT_PATH


def _write_jsonl(tmp_path: Path, proposals_jsonl_bytes: bytes) -> Path:
    p = tmp_path / "proposals.jsonl"
    p.write_bytes(proposals_jsonl_bytes)
    return p


def _api(jsonl_path: Path | None = None, audit_path: Path | None = None) -> WorkbenchApi:
    """Return a WorkbenchApi with its readers patched to use tmp paths."""
    import workbench.readers as _r

    api = WorkbenchApi()
    _orig_list = _r.list_math_proposals
    _orig_read = _r.read_math_proposal
    _orig_ratify = _r.ratify_math_proposal

    if jsonl_path is not None:
        import functools

        api._list_math_proposals = functools.partial(_r.list_math_proposals, jsonl_path=jsonl_path)
        api._read_math_proposal = functools.partial(
            _r.read_math_proposal, jsonl_path=jsonl_path, audit_path=audit_path or REAL_AUDIT_PATH
        )
        api._ratify_math_proposal = functools.partial(
            _r.ratify_math_proposal, jsonl_path=jsonl_path
        )
        # Patch the module-level functions temporarily
        _r.list_math_proposals = api._list_math_proposals  # type: ignore[assignment]
        _r.read_math_proposal = api._read_math_proposal  # type: ignore[assignment]
        _r.ratify_math_proposal = api._ratify_math_proposal  # type: ignore[assignment]

    yield api

    # Restore
    _r.list_math_proposals = _orig_list
    _r.read_math_proposal = _orig_read
    _r.ratify_math_proposal = _orig_ratify


def _get(api: WorkbenchApi, path: str) -> dict:
    resp = api.handle("GET", path)
    return {"status": resp.status, "payload": resp.payload}


def _post(api: WorkbenchApi, path: str, body: bytes = b"{}") -> dict:
    resp = api.handle("POST", path, body)
    return {"status": resp.status, "payload": resp.payload}


def _make_synthetic_proposals_jsonl(tmp_path: Path, change_kinds: list[str]) -> tuple[Path, list[str]]:
    """Build a synthetic proposals.jsonl with one proposal per change_kind.

    Returns (jsonl_path, list_of_proposal_ids).
    """
    from evals.refusal_taxonomy.shape_categories import ShapeCategory
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import build_proposal, canonical_bytes
    from teaching.math_evidence import MathReaderRefusalEvidence, SUB_TYPE_FOR_OPERATOR
    from teaching.math_reasoning_trace import ReasoningStep, build_trace
    from generate.comprehension.audit import AuditRow

    def _ev(case_id: str, missing_op: str) -> MathReaderRefusalEvidence:
        from teaching.math_evidence import from_audit_row
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

    lines: list[bytes] = []
    proposal_ids: list[str] = []

    for i, ck in enumerate(change_kinds):
        ev1 = _ev(f"c{i:02d}a", "drain_token")
        ev2 = _ev(f"c{i:02d}b", "drain_token")

        obs = ReasoningStep(
            step_index=0, step_kind="observation", input_pointers=(ev1.case_id, ev2.case_id),
            claim=f"synthetic observation for {ck}", justification="test",
            output_payload={"evidence_count": 2},
        )
        grp = ReasoningStep(
            step_index=1, step_kind="grouping", input_pointers=(ev1.case_id, ev2.case_id),
            claim="group key", justification="test", output_payload={"k": "v"},
        )
        hyp = ReasoningStep(
            step_index=2, step_kind="hypothesis", input_pointers=(ev1.case_id, ev2.case_id),
            claim=f"change_kind={ck}", justification="test", output_payload={"ck": ck},
        )
        con = ReasoningStep(
            step_index=3, step_kind="conclusion", input_pointers=(ev1.case_id, ev2.case_id),
            claim="conclude", justification="test", output_payload={"done": 1},
        )
        trace = build_trace((obs, grp, hyp, con))

        p = build_proposal(
            shape_category=ShapeCategory.UNCATEGORIZED,
            structural_commonality=f"synthetic {ck} test proposal — sufficient length for wrong_zero_assertion",
            evidence_pointers=(ev1, ev2),
            proposed_change_kind=ck,  # type: ignore[arg-type]
            proposed_change_payload={"evidence_count": 2, "group_key": {"k": "v"}, "modal_sub_type": "lexical"},
            wrong_zero_assertion=(
                "synthetic proposal for test; ratification handler enforces wrong=0"
            ),
            replay_equivalence_hash=hashlib.sha256(f"replay-{ck}-{i}".encode()).hexdigest(),
            reasoning_trace=trace,
        )
        cb = canonical_bytes(p)
        lines.append(cb + b"\n")
        proposal_ids.append(p.proposal_id)

    jsonl_path = tmp_path / "proposals.jsonl"
    jsonl_path.write_bytes(b"".join(lines))
    return jsonl_path, proposal_ids


# ---------------------------------------------------------------------------
# Test 1: Loads from JSONL
# ---------------------------------------------------------------------------


def test_1_loads_from_jsonl(tmp_path: Path) -> None:
    """GET /math-proposals returns items from proposals.jsonl when it exists."""
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import canonical_bytes as cb

    proposals = decompose_audit(REAL_AUDIT_PATH)
    jsonl_bytes = b"".join(cb(p) + b"\n" for p in proposals)
    jsonl = _write_jsonl(tmp_path, jsonl_bytes)

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", "/math-proposals")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 200
    data = resp.payload.get("data", {})
    items = data.get("items", [])
    assert len(items) == len(proposals)


# ---------------------------------------------------------------------------
# Test 2: Renders domain:math badge, distinct from cognition domain
# ---------------------------------------------------------------------------


def test_2_renders_domain_math_badge(tmp_path: Path) -> None:
    """Items from /math-proposals have domain='math'; /proposals returns cognition (no domain field)."""
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import canonical_bytes as cb

    proposals = decompose_audit(REAL_AUDIT_PATH)
    jsonl_bytes = b"".join(cb(p) + b"\n" for p in proposals)
    jsonl = _write_jsonl(tmp_path, jsonl_bytes)

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", "/math-proposals")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    items = resp.payload["data"]["items"]
    assert all(item["domain"] == "math" for item in items), (
        "all math proposals must carry domain='math'"
    )

    # Cognition /proposals carries ProposalSummary — no domain field at all
    cog_resp = WorkbenchApi().handle("GET", "/proposals")
    cog_items = cog_resp.payload.get("data", {}).get("items", [])
    for cog_item in cog_items:
        assert cog_item.get("domain") != "math", (
            "cognition proposals must not carry domain='math'"
        )


# ---------------------------------------------------------------------------
# Test 3: ratify-vocabulary_addition routes to LexicalClaim handler
# ---------------------------------------------------------------------------


def test_3_ratify_vocabulary_addition_routes_to_lexical_claim(tmp_path: Path) -> None:
    """POST /math-proposals/{id}/ratify routes vocabulary_addition to LexicalClaim (200)."""
    jsonl_path, proposal_ids = _make_synthetic_proposals_jsonl(tmp_path, ["vocabulary_addition"])
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
    assert data.get("handler_name") == "LexicalClaim", (
        f"vocabulary_addition must route to LexicalClaim, got: {data.get('handler_name')!r}"
    )
    assert data.get("routing_status") == "routed"
    assert data.get("change_kind") == "vocabulary_addition"


# ---------------------------------------------------------------------------
# Test 4: ratify-matcher_extension fails loudly
# ---------------------------------------------------------------------------


def test_4_ratify_matcher_extension_fails_loudly(tmp_path: Path) -> None:
    """POST /math-proposals/{id}/ratify returns 501 for matcher_extension with clear message."""
    jsonl_path, proposal_ids = _make_synthetic_proposals_jsonl(tmp_path, ["matcher_extension"])
    matcher_pid = proposal_ids[0]

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    _r.MATH_PROPOSALS_JSONL = jsonl_path
    try:
        api = WorkbenchApi()
        resp = api.handle("POST", f"/math-proposals/{matcher_pid}/ratify")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig

    assert resp.status == 501, f"expected 501 for unimplemented handler, got {resp.status}"
    err = resp.payload.get("error", {})
    message = err.get("message", "")
    assert "handler not yet implemented" in message, (
        f"expected 'handler not yet implemented' in message, got: {message!r}"
    )
    assert "matcher_extension" in message, (
        f"expected change_kind in error message, got: {message!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: All 4 trace steps visible
# ---------------------------------------------------------------------------


def test_5_all_4_trace_steps_visible(tmp_path: Path) -> None:
    """GET /math-proposals/{id} includes reasoning_trace_steps with all 4 steps."""
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import canonical_bytes as cb

    proposals = decompose_audit(REAL_AUDIT_PATH)
    assert proposals, "real audit must produce at least one proposal"
    jsonl_bytes = b"".join(cb(p) + b"\n" for p in proposals)
    jsonl = _write_jsonl(tmp_path, jsonl_bytes)

    first_id = proposals[0].proposal_id

    import workbench.readers as _r
    orig = _r.MATH_PROPOSALS_JSONL
    orig_audit = _r._DEFAULT_MATH_AUDIT_PATH
    _r.MATH_PROPOSALS_JSONL = jsonl
    _r._DEFAULT_MATH_AUDIT_PATH = REAL_AUDIT_PATH
    try:
        api = WorkbenchApi()
        resp = api.handle("GET", f"/math-proposals/{first_id}")
    finally:
        _r.MATH_PROPOSALS_JSONL = orig
        _r._DEFAULT_MATH_AUDIT_PATH = orig_audit

    assert resp.status == 200, f"expected 200, got {resp.status}: {resp.payload}"
    detail = resp.payload.get("data", {})
    steps = detail.get("reasoning_trace_steps", [])
    assert len(steps) == 4, f"expected 4 trace steps, got {len(steps)}"
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
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import canonical_bytes as cb

    proposals = decompose_audit(REAL_AUDIT_PATH)
    jsonl_bytes = b"".join(cb(p) + b"\n" for p in proposals)
    jsonl = _write_jsonl(tmp_path, jsonl_bytes)

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

    # Math queue carries domain:math; cognition queue has no domain:math entries
    assert all(item.get("domain") == "math" for item in math_items)
    for cog_item in cog_items:
        assert cog_item.get("domain") != "math", (
            "cognition proposal leaked into math domain"
        )

    # proposal_ids from the two queues are disjoint
    math_ids = {item["proposal_id"] for item in math_items}
    cog_ids = {item["proposal_id"] for item in cog_items}
    assert math_ids.isdisjoint(cog_ids), (
        f"proposal IDs overlap between math and cognition queues: {math_ids & cog_ids}"
    )

"""ADR-0169 — CompositionClaim ratification handler tests.

Mirrors :mod:`tests.test_math_frame_ratification` (F1) and pins:

1.  SAFE_COMPOSITION_CATEGORIES is exactly the ADR-0169 allowlist (3 entries).
2.  apply_composition_claim writes an entry for a safe category.
3.  receipt records before/after sha + evidence_hash.
4.  idempotent same-evidence → AlreadyRatified.
5.  rejects non-composition sub_type.
6.  rejects categories outside SAFE_COMPOSITION_CATEGORIES → WrongCompositionCategory.
7.  rejects invalid polarity.
8.  rejects evidence tampering.
9.  rejects evidence laundering (source='corpus' is forbidden).
10. case 0050 hazard pin — after ratification, case 0050 still refuses.
11. polarity=falsifies branch records non-composing pattern without admitting.
12. duplicate evidence on second apply appends evidence_hash, not new row.
13. manifest.json checksum is unchanged by composition ratification.
14. alphabetical sort by surface_pattern preserved across writes.
15. claim signature canonicalization deterministic.
16. claim signature replay equivalence cross-process (subprocess).
17. queue-order independence (A→B == B→A ratify).
18. partition: cognition TeachingChainProposal records not seen by handler.
19. audit evidence not laundered as source="corpus" at proposal layer.
20. workbench dispatch routes composition_reclassification → CompositionClaim.
21. proposed_change_kind Literal accepts composition_reclassification.
22. JSONL round-trip preserves composition_reclassification change_kind.

ADR-0169 §"Decision" + ADR-0169.1 §"Evidence floor" + hazard pins.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension import lexicon as comprehension_lexicon
from generate.comprehension import lifecycle
from generate.comprehension.audit import AuditRow, audit_problem
from generate.comprehension.state import ReaderRefusal
from teaching.math_composition_proposal import (
    build_composition_claim_proposal,
    build_evidence_pointer,
    compute_claim_signature,
)
from teaching.math_composition_ratification import (
    AlreadyRatified,
    EvidenceLaundering,
    EvidenceTampering,
    InvalidPolarity,
    SAFE_COMPOSITION_CATEGORIES,
    WrongClaimSubType,
    WrongCompositionCategory,
    apply_composition_claim,
)
from teaching.math_contemplation_proposal import (
    _VALID_CHANGE_KINDS,
    ChangeKind,
    build_proposal,
    from_jsonl_record,
    to_jsonl_record,
)
from teaching.math_evidence import from_audit_row
from teaching.math_reasoning_trace import ReasoningStep, build_trace


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"
CASES_PATH = REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"
AUDIT_BRIEF_PATH = (
    REPO_ROOT
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "audit_brief_11.json"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pack_copy(tmp_path: Path) -> Path:
    target = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target)
    (target / "compositions").mkdir(exist_ok=True)
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    yield target
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()


def _row(
    surface: str,
    *,
    missing_operator: str = "quantity_extraction",
    refusal_reason: str = "incomplete_operation",
    case_id: str | None = None,
) -> AuditRow:
    return AuditRow(
        case_id=case_id or f"case-{surface}",
        sentence_index=0,
        token_index=2,
        token_text=surface,
        recognized_terms=("Mark", "buys"),
        skipped_frame=None,
        missing_operator=missing_operator,
        refusal_reason=refusal_reason,
        refusal_detail=f"composition gap for '{surface}'",
    )


def _claim(surface: str, *, sub_type: str = "composition", case_id: str | None = None):
    return from_audit_row(_row(surface, case_id=case_id), sub_type)  # type: ignore[arg-type]


def _entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _manifest_sha(pack_root: Path) -> str:
    return hashlib.sha256((pack_root / "manifest.json").read_bytes()).hexdigest()


def _use_pack_for_reader(monkeypatch: pytest.MonkeyPatch, pack_root: Path) -> None:
    comprehension_lexicon._CACHE.clear()

    @functools.cache
    def _tmp_lexicon():
        return comprehension_lexicon.load_lexicon(pack_root)

    monkeypatch.setattr(lifecycle, "_get_lexicon", _tmp_lexicon)


# ---------------------------------------------------------------------------
# 1 — SAFE_COMPOSITION_CATEGORIES allowlist pinned
# ---------------------------------------------------------------------------


def test_safe_composition_categories_is_adr_0169_allowlist() -> None:
    """The three ADR-0169 categories, no more, no less."""
    assert SAFE_COMPOSITION_CATEGORIES == frozenset(
        {
            "multiplicative_composition",
            "additive_composition",
            "subtractive_composition",
        }
    )


# ---------------------------------------------------------------------------
# 2 — apply writes an entry for a safe category
# ---------------------------------------------------------------------------


def test_apply_composition_claim_writes_entry(pack_copy: Path) -> None:
    receipt = apply_composition_claim(
        claim=_claim("each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        surface_pattern="bound(count) bound(unit_cost)",
        pack_root=pack_copy,
    )

    assert receipt.surface_pattern == "bound(count) bound(unit_cost)"
    assert receipt.composition_category == "multiplicative_composition"
    assert receipt.polarity == "affirms"
    assert receipt.is_duplicate_evidence is False
    entry = next(
        e
        for e in _entries(
            pack_copy / "compositions" / "multiplicative_composition.jsonl"
        )
        if e["surface_pattern"] == "bound(count) bound(unit_cost)"
    )
    assert entry["composition_category"] == "multiplicative_composition"
    assert entry["polarity"] == "affirms"
    assert receipt.evidence_hash in entry["evidence_hashes"]


# ---------------------------------------------------------------------------
# 3 — receipt records before/after sha
# ---------------------------------------------------------------------------


def test_receipt_records_before_after_sha(pack_copy: Path) -> None:
    receipt = apply_composition_claim(
        claim=_claim("each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert len(receipt.file_sha256_before) == 64
    assert len(receipt.file_sha256_after) == 64
    assert receipt.file_sha256_before != receipt.file_sha256_after
    assert receipt.evidence_hash == _claim("each").evidence_hash


# ---------------------------------------------------------------------------
# 4 — idempotent same-evidence raises AlreadyRatified
# ---------------------------------------------------------------------------


def test_idempotent_same_evidence_raises_already_ratified(pack_copy: Path) -> None:
    claim = _claim("each")
    apply_composition_claim(
        claim=claim,
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    with pytest.raises(AlreadyRatified, match="already ratified"):
        apply_composition_claim(
            claim=claim,
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 5 — rejects non-composition sub_type
# ---------------------------------------------------------------------------


def test_rejects_non_composition_sub_type(pack_copy: Path) -> None:
    with pytest.raises(WrongClaimSubType):
        apply_composition_claim(
            claim=_claim("each", sub_type="lexical"),
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 6 — rejects categories outside SAFE_COMPOSITION_CATEGORIES (wrong=0 hazard)
# ---------------------------------------------------------------------------


def test_rejects_unsafe_composition_category(pack_copy: Path) -> None:
    with pytest.raises(
        WrongCompositionCategory, match="SAFE_COMPOSITION_CATEGORIES"
    ):
        apply_composition_claim(
            claim=_claim("each"),
            composition_category="distributive_composition",  # not in allowlist
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 7 — rejects invalid polarity
# ---------------------------------------------------------------------------


def test_rejects_invalid_polarity(pack_copy: Path) -> None:
    with pytest.raises(InvalidPolarity, match="polarity must be one of"):
        apply_composition_claim(
            claim=_claim("each"),
            composition_category="multiplicative_composition",
            polarity="maybe",  # not affirms/falsifies
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 8 — rejects evidence tampering
# ---------------------------------------------------------------------------


def test_rejects_evidence_tampering(pack_copy: Path) -> None:
    claim = _claim("each")
    object.__setattr__(claim, "evidence_hash", "0" * 64)

    with pytest.raises(EvidenceTampering):
        apply_composition_claim(
            claim=claim,
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 9 — rejects evidence laundering as source='corpus'
# ---------------------------------------------------------------------------


def test_rejects_evidence_laundered_as_corpus(pack_copy: Path) -> None:
    """ADR-0169.1 §'Evidence floor': source='corpus' MUST be rejected."""
    with pytest.raises(EvidenceLaundering, match="MUST NOT be laundered"):
        apply_composition_claim(
            claim=_claim("each"),
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
            evidence_source="corpus",  # forbidden
        )


# ---------------------------------------------------------------------------
# 10 — case 0050 hazard pin: still refused after ratification
# ---------------------------------------------------------------------------


def test_case_0050_remains_refused_after_composition_ratification(
    pack_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After ratifying a safe composition pattern, case 0050 must still refuse.

    Case 0050 ("Mark does a gig every other day for 2 weeks. ..." — the
    period token at sentence_index=0 with missing_operator=
    pre_frame_filler_sentence) is the prototype wrong=0 hazard.  A
    speculative composition admission here would feed a wrong operand to
    the solver.  The new compositions/ entries must not open that
    admission path.
    """
    apply_composition_claim(
        claim=_claim("each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    _use_pack_for_reader(monkeypatch, pack_copy)
    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines()]
    case = next(c for c in cases if c["case_id"] == "gsm8k-train-sample-v1-0050")

    result, _rows = audit_problem(case["question"], case_id=case["case_id"])

    assert isinstance(result, ReaderRefusal), (
        "case 0050 must remain refused after CompositionClaim ratification"
    )
    assert result.sentence_index == 0


# ---------------------------------------------------------------------------
# 11 — polarity=falsifies branch records non-composing pattern
# ---------------------------------------------------------------------------


def test_polarity_falsifies_records_non_composing(pack_copy: Path) -> None:
    """A 'falsifies' ratification records the pattern as NOT composing.

    This is the negative-evidence path: an operator reviewed the audit row
    and decided the pattern does not in fact compose under the category.
    The entry is written to the same source file but with polarity=falsifies
    so downstream registry builds can mark the pattern as a known
    non-composer (refusal-stable).
    """
    receipt = apply_composition_claim(
        claim=_claim("along"),
        composition_category="multiplicative_composition",
        polarity="falsifies",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.polarity == "falsifies"
    entry = next(
        e
        for e in _entries(
            pack_copy / "compositions" / "multiplicative_composition.jsonl"
        )
        if e["surface_pattern"] == "along"
    )
    assert entry["polarity"] == "falsifies"

    # affirms + falsifies of the same pattern produce distinct entries
    receipt2 = apply_composition_claim(
        claim=_claim("each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    assert receipt2.polarity == "affirms"
    polarities = {
        e["polarity"]
        for e in _entries(
            pack_copy / "compositions" / "multiplicative_composition.jsonl"
        )
    }
    assert {"affirms", "falsifies"} <= polarities


# ---------------------------------------------------------------------------
# 12 — duplicate evidence appends to existing row
# ---------------------------------------------------------------------------


def test_duplicate_pattern_polarity_with_new_evidence_appends_hash(
    pack_copy: Path,
) -> None:
    """ADR-0169.1 §'Idempotency': same claim + new evidence appends hash, not row."""
    apply_composition_claim(
        claim=_claim("each", case_id="case-each-1"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    # Second evidence for the same claim — different case_id, so the
    # evidence_hash differs even though pattern+polarity+category match.
    second_row = AuditRow(
        case_id="case-each-2",
        sentence_index=1,
        token_index=4,
        token_text="each",
        recognized_terms=("Bob", "buys"),
        skipped_frame=None,
        missing_operator="quantity_extraction",
        refusal_reason="incomplete_operation",
        refusal_detail="duplicate composition evidence",
    )
    second_claim = from_audit_row(second_row, "composition")
    receipt = apply_composition_claim(
        claim=second_claim,
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.is_duplicate_evidence is True
    rows = [
        e
        for e in _entries(
            pack_copy / "compositions" / "multiplicative_composition.jsonl"
        )
        if e["surface_pattern"] == "each"
    ]
    assert len(rows) == 1, "duplicate evidence must not create a second row"
    assert len(rows[0]["evidence_hashes"]) == 2


# ---------------------------------------------------------------------------
# 13 — manifest.json checksum unchanged
# ---------------------------------------------------------------------------


def test_manifest_checksum_unchanged_by_composition_ratification(
    pack_copy: Path,
) -> None:
    manifest_bytes_before = (pack_copy / "manifest.json").read_bytes()
    manifest_sha_before = _manifest_sha(pack_copy)
    declared_before = json.loads(manifest_bytes_before)["checksum"]

    apply_composition_claim(
        claim=_claim("each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    manifest_bytes_after = (pack_copy / "manifest.json").read_bytes()
    assert manifest_bytes_after == manifest_bytes_before
    assert _manifest_sha(pack_copy) == manifest_sha_before
    assert json.loads(manifest_bytes_after)["checksum"] == declared_before


# ---------------------------------------------------------------------------
# 14 — alphabetical sort preserved across multiple writes
# ---------------------------------------------------------------------------


def test_alphabetical_sort_preserved(pack_copy: Path) -> None:
    for surface in ("times", "each", "apiece"):
        apply_composition_claim(
            claim=_claim(surface),
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )

    patterns = [
        e["surface_pattern"]
        for e in _entries(
            pack_copy / "compositions" / "multiplicative_composition.jsonl"
        )
    ]
    assert patterns == sorted(patterns)


# ---------------------------------------------------------------------------
# 15 — claim signature canonicalization deterministic
# ---------------------------------------------------------------------------


def test_claim_signature_canonicalization_deterministic() -> None:
    """ADR-0169 §'Replay obligations' #1: equivalent claims → identical signatures."""
    ev1 = _claim("each", case_id="case-1")
    ev2 = _claim("each", case_id="case-1")  # identical evidence
    p1 = build_evidence_pointer(ev1)
    p2 = build_evidence_pointer(ev2)

    sig_a = compute_claim_signature(
        surface_pattern="bound(count) bound(unit_cost)",
        composition_category="multiplicative_composition",
        polarity="affirms",
        evidence=(p1,),
    )
    sig_b = compute_claim_signature(
        surface_pattern="bound(count) bound(unit_cost)",
        composition_category="multiplicative_composition",
        polarity="affirms",
        evidence=(p2,),
    )
    assert sig_a == sig_b
    assert len(sig_a) == 64

    # Different polarity → different signature
    sig_c = compute_claim_signature(
        surface_pattern="bound(count) bound(unit_cost)",
        composition_category="multiplicative_composition",
        polarity="falsifies",
        evidence=(p1,),
    )
    assert sig_a != sig_c


# ---------------------------------------------------------------------------
# 16 — claim signature replay equivalence cross-process (subprocess)
# ---------------------------------------------------------------------------


def test_claim_signature_replay_equivalence_cross_process() -> None:
    """ADR-0169 §'Replay obligations' #2: equivalent across processes."""
    script = textwrap.dedent(
        """
        import json, sys
        from teaching.math_composition_proposal import (
            build_evidence_pointer, compute_claim_signature,
        )
        from teaching.math_evidence import from_audit_row
        from generate.comprehension.audit import AuditRow
        row = AuditRow(
            case_id="case-xprocess", sentence_index=0, token_index=2,
            token_text="each", recognized_terms=("Mark", "buys"),
            skipped_frame=None, missing_operator="quantity_extraction",
            refusal_reason="incomplete_operation",
            refusal_detail="composition gap for 'each'",
        )
        ev = from_audit_row(row, "composition")
        p = build_evidence_pointer(ev)
        sig = compute_claim_signature(
            surface_pattern="bound(count) bound(unit_cost)",
            composition_category="multiplicative_composition",
            polarity="affirms",
            evidence=(p,),
        )
        sys.stdout.write(sig)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    subprocess_sig = proc.stdout.strip()

    # In-process compute
    row = AuditRow(
        case_id="case-xprocess",
        sentence_index=0,
        token_index=2,
        token_text="each",
        recognized_terms=("Mark", "buys"),
        skipped_frame=None,
        missing_operator="quantity_extraction",
        refusal_reason="incomplete_operation",
        refusal_detail="composition gap for 'each'",
    )
    ev = from_audit_row(row, "composition")
    p = build_evidence_pointer(ev)
    inproc_sig = compute_claim_signature(
        surface_pattern="bound(count) bound(unit_cost)",
        composition_category="multiplicative_composition",
        polarity="affirms",
        evidence=(p,),
    )

    assert subprocess_sig == inproc_sig
    assert len(subprocess_sig) == 64


# ---------------------------------------------------------------------------
# 17 — queue-order independence (A→B == B→A)
# ---------------------------------------------------------------------------


def test_queue_order_independence(pack_copy: Path, tmp_path: Path) -> None:
    """ADR-0169 §'Replay obligations' #2: queue-order independence.

    Ratifying claim A then claim B produces the same target file as
    ratifying B then A.  Sort-by-surface_pattern write discipline carries
    most of the load; this test pins it.
    """
    # Order A → B
    target_a = tmp_path / "en_core_math_v1_a"
    shutil.copytree(PACK_ROOT, target_a)
    (target_a / "compositions").mkdir(exist_ok=True)
    apply_composition_claim(
        claim=_claim("each", case_id="case-each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=target_a,
    )
    apply_composition_claim(
        claim=_claim("apiece", case_id="case-apiece"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=target_a,
    )
    out_a = (
        target_a / "compositions" / "multiplicative_composition.jsonl"
    ).read_bytes()

    # Order B → A
    target_b = tmp_path / "en_core_math_v1_b"
    shutil.copytree(PACK_ROOT, target_b)
    (target_b / "compositions").mkdir(exist_ok=True)
    apply_composition_claim(
        claim=_claim("apiece", case_id="case-apiece"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=target_b,
    )
    apply_composition_claim(
        claim=_claim("each", case_id="case-each"),
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="Ada",
        pack_root=target_b,
    )
    out_b = (
        target_b / "compositions" / "multiplicative_composition.jsonl"
    ).read_bytes()

    # Provenance carries the date but not the order, so byte-equality holds.
    assert out_a == out_b


# ---------------------------------------------------------------------------
# 18 — partition: cognition TeachingChainProposal records not seen
# ---------------------------------------------------------------------------


def test_partition_cognition_proposals_not_seen(pack_copy: Path) -> None:
    """ADR-0169 §'Partition guarantees': handler is math-only.

    A cognition-style proposal (a TeachingChainProposal-like dict, or any
    object that is not a MathReaderRefusalEvidence with
    sub_type='composition') must be rejected by the handler — not silently
    accepted as if it were math evidence.
    """
    # A non-composition sub_type is the cognition-flow analog: rejected.
    with pytest.raises(WrongClaimSubType):
        apply_composition_claim(
            claim=_claim("each", sub_type="lexical"),
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )

    # A non-evidence object (the cognition TeachingChainProposal would not
    # carry sub_type at all) must also fail loudly — AttributeError or
    # TypeError, not a silent admit.
    class _NotEvidence:
        pass

    with pytest.raises((AttributeError, TypeError)):
        apply_composition_claim(
            claim=_NotEvidence(),  # type: ignore[arg-type]
            composition_category="multiplicative_composition",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# 19 — audit evidence not laundered as source="corpus" at proposal layer
# ---------------------------------------------------------------------------


def test_audit_evidence_not_laundered_as_corpus_at_proposal_layer() -> None:  # noqa: D401
    """ADR-0169.1 §'Trip-wires' #1: proposal layer rejects corpus pointers.

    Defense-in-depth: the handler rejects source='corpus' on apply, and the
    proposal-build layer (build_composition_claim_proposal) also rejects
    pointers whose source drifted from 'math_audit'.
    """
    ev = _claim("each")
    pointer = build_evidence_pointer(ev)

    # Forge a pointer with corpus source — direct dataclass construction
    # since the factory pins source='math_audit'.
    from teaching.math_composition_proposal import MathReaderRefusalEvidencePointer

    laundered = MathReaderRefusalEvidencePointer(
        source="corpus",  # type: ignore[arg-type]
        case_id=pointer.case_id,
        sentence_index=pointer.sentence_index,
        token_index=pointer.token_index,
        missing_operator=pointer.missing_operator,
        refusal_reason=pointer.refusal_reason,
        evidence_hash=pointer.evidence_hash,
        audit_row_digest=pointer.audit_row_digest,
    )
    with pytest.raises(ValueError, match="math_audit"):
        build_composition_claim_proposal(
            surface_pattern="bound(count) bound(unit_cost)",
            composition_category="multiplicative_composition",
            polarity="affirms",
            evidence=(laundered,),
        )


# ---------------------------------------------------------------------------
# 20 — workbench dispatch routes composition_reclassification
# ---------------------------------------------------------------------------


def test_workbench_dispatch_composition_reclassification() -> None:
    """Workbench routes composition_reclassification → CompositionClaim, not 501."""
    from workbench.readers import _HANDLER_DISPATCH

    assert _HANDLER_DISPATCH["composition_reclassification"] == "CompositionClaim"
    # Sibling routes still exist
    assert _HANDLER_DISPATCH["vocabulary_addition"] == "LexicalClaim"
    assert _HANDLER_DISPATCH["frame_reclassification"] == "FrameClaim"


# ---------------------------------------------------------------------------
# 21 — proposed_change_kind Literal accepts composition_reclassification
# ---------------------------------------------------------------------------


def test_proposal_change_kind_literal_accepts_composition_reclassification() -> None:
    """Literal extension permits composition_reclassification as a valid ChangeKind."""
    from typing import get_args

    assert "composition_reclassification" in _VALID_CHANGE_KINDS
    assert "composition_reclassification" in get_args(ChangeKind)


# ---------------------------------------------------------------------------
# 22 — JSONL round-trip preserves composition_reclassification change_kind
# ---------------------------------------------------------------------------


def test_jsonl_round_trip_with_composition_reclassification() -> None:
    """W1 round-trip test extended for the new change_kind (ADR-0169 §'Acceptance gates')."""
    ev1 = _claim("each", case_id="case-1")
    ev2 = _claim("each", case_id="case-2")
    steps = (
        ReasoningStep(
            step_index=0,
            step_kind="observation",
            input_pointers=("case-1", "case-2"),
            claim="2 refusal rows share composition gap",
            justification="grouped by (refusal_reason, missing_operator)",
            output_payload={"evidence_count": 2},
        ),
        ReasoningStep(
            step_index=1,
            step_kind="grouping",
            input_pointers=("case-1", "case-2"),
            claim="group key",
            justification="exact pair equality",
            output_payload={"k": "v"},
        ),
        ReasoningStep(
            step_index=2,
            step_kind="hypothesis",
            input_pointers=("case-1", "case-2"),
            claim="composition_reclassification fits",
            justification="dispatched via pair table to composition_reclassification",
            output_payload={"proposed_change_kind": "composition_reclassification"},
        ),
        ReasoningStep(
            step_index=3,
            step_kind="conclusion",
            input_pointers=("case-1", "case-2"),
            claim="propose composition_reclassification",
            justification="evidence-only proposal",
            output_payload={"proposed_change_kind": "composition_reclassification"},
        ),
    )
    trace = build_trace(steps)
    proposal = build_proposal(
        shape_category=ShapeCategory.UNCATEGORIZED,
        structural_commonality="2 refusals share composition gap",
        evidence_pointers=(ev1, ev2),
        proposed_change_kind="composition_reclassification",
        proposed_change_payload={"k": "v"},
        wrong_zero_assertion=(
            "Proposal is evidence-only; ratification handler is the wrong=0 surface."
        ),
        replay_equivalence_hash="0" * 64,
        reasoning_trace=trace,
    )

    record = to_jsonl_record(proposal)
    assert record["proposed_change_kind"] == "composition_reclassification"
    round_tripped = from_jsonl_record(record)
    assert round_tripped.proposed_change_kind == "composition_reclassification"
    assert round_tripped.proposal_id == proposal.proposal_id

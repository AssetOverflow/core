"""ADR-0168 — FrameClaim ratification handler tests.

Mirrors :mod:`tests.test_math_lexical_ratification` (W2-D) and pins:

1. SAFE_FRAME_CATEGORIES is exactly the ADR-0168 allowlist (4 entries).
2. apply_frame_claim writes a frame entry for a safe category.
3. receipt records before/after sha + evidence_hash.
4. idempotent same-evidence → AlreadyRatified.
5. rejects non-frame sub_type.
6. rejects categories outside SAFE_FRAME_CATEGORIES (wrong=0 hazard).
7. rejects invalid polarity (must be affirms|falsifies).
8. rejects evidence tampering.
9. rejects evidence laundering (source='corpus' is forbidden).
10. case 0050 hazard pin — after ratification, case 0050 still refuses.
11. polarity=falsifies branch records non-opener without admitting.
12. duplicate evidence on second apply appends evidence_hash, not new row.
13. manifest.json checksum is unchanged by frame ratification.
14. alphabetical sort by surface_form preserved across writes.

ADR-0168 §"Decision" + ADR-0168.1 §"Evidence floor" + hazard pins.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from generate.comprehension import lexicon as comprehension_lexicon
from generate.comprehension import lifecycle
from generate.comprehension.audit import AuditRow, audit_problem
from generate.comprehension.state import ReaderRefusal
from teaching.math_evidence import from_audit_row
from teaching.math_frame_ratification import (
    AlreadyRatified,
    EvidenceLaundering,
    EvidenceTampering,
    InvalidPolarity,
    SAFE_FRAME_CATEGORIES,
    WrongClaimSubType,
    WrongZeroViolationCandidate,
    apply_frame_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"
CASES_PATH = REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pack_copy(tmp_path: Path) -> Path:
    target = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target)
    # Ensure the frames/ scaffold exists in the copy.
    (target / "frames").mkdir(exist_ok=True)
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    yield target
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()


def _row(
    surface: str,
    *,
    missing_operator: str = "pre_frame_filler_sentence",
    refusal_reason: str = "unexpected_category",
) -> AuditRow:
    return AuditRow(
        case_id=f"case-{surface}",
        sentence_index=0,
        token_index=2,
        token_text=surface,
        recognized_terms=("Mark", "does"),
        skipped_frame=None,
        missing_operator=missing_operator,
        refusal_reason=refusal_reason,
        refusal_detail=f"unexpected category for '{surface}'",
    )


def _claim(surface: str, *, sub_type: str = "frame"):
    return from_audit_row(_row(surface), sub_type)  # type: ignore[arg-type]


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
# Test 1 — SAFE_FRAME_CATEGORIES is the ADR-0168 allowlist
# ---------------------------------------------------------------------------


def test_safe_frame_categories_is_adr_0168_allowlist() -> None:
    """The four ADR-0168 categories, no more, no less."""
    assert SAFE_FRAME_CATEGORIES == frozenset(
        {"increment_frame", "decrement_frame", "transfer_frame", "remainder_frame"}
    )


# ---------------------------------------------------------------------------
# Test 2 — apply writes a frame entry for a safe category
# ---------------------------------------------------------------------------


def test_apply_frame_claim_writes_entry(pack_copy: Path) -> None:
    receipt = apply_frame_claim(
        claim=_claim("gives"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.surface_form == "gives"
    assert receipt.frame_category == "transfer_frame"
    assert receipt.polarity == "affirms"
    assert receipt.is_duplicate_evidence is False
    entry = next(
        e
        for e in _entries(pack_copy / "frames" / "transfer_frame.jsonl")
        if e["surface_form"] == "gives"
    )
    assert entry["frame_category"] == "transfer_frame"
    assert entry["polarity"] == "affirms"
    assert receipt.evidence_hash in entry["evidence_hashes"]


# ---------------------------------------------------------------------------
# Test 3 — receipt records before/after sha
# ---------------------------------------------------------------------------


def test_receipt_records_before_after_sha(pack_copy: Path) -> None:
    receipt = apply_frame_claim(
        claim=_claim("gives"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert len(receipt.file_sha256_before) == 64
    assert len(receipt.file_sha256_after) == 64
    assert receipt.file_sha256_before != receipt.file_sha256_after
    assert receipt.evidence_hash == _claim("gives").evidence_hash


# ---------------------------------------------------------------------------
# Test 4 — idempotent same-evidence raises AlreadyRatified
# ---------------------------------------------------------------------------


def test_idempotent_same_evidence_raises_already_ratified(pack_copy: Path) -> None:
    claim = _claim("gives")
    apply_frame_claim(
        claim=claim,
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    with pytest.raises(AlreadyRatified, match="already ratified"):
        apply_frame_claim(
            claim=claim,
            frame_category="transfer_frame",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# Test 5 — rejects non-frame sub_type
# ---------------------------------------------------------------------------


def test_rejects_non_frame_sub_type(pack_copy: Path) -> None:
    with pytest.raises(WrongClaimSubType):
        apply_frame_claim(
            claim=_claim("gives", sub_type="lexical"),
            frame_category="transfer_frame",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# Test 6 — rejects categories outside SAFE_FRAME_CATEGORIES (wrong=0 hazard)
# ---------------------------------------------------------------------------


def test_rejects_unsafe_frame_category(pack_copy: Path) -> None:
    with pytest.raises(
        WrongZeroViolationCandidate, match="SAFE_FRAME_CATEGORIES"
    ):
        apply_frame_claim(
            claim=_claim("gives"),
            frame_category="comparison_frame",  # not in allowlist
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# Test 7 — rejects invalid polarity
# ---------------------------------------------------------------------------


def test_rejects_invalid_polarity(pack_copy: Path) -> None:
    with pytest.raises(InvalidPolarity, match="polarity must be one of"):
        apply_frame_claim(
            claim=_claim("gives"),
            frame_category="transfer_frame",
            polarity="maybe",  # not affirms/falsifies
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# Test 8 — rejects evidence tampering
# ---------------------------------------------------------------------------


def test_rejects_evidence_tampering(pack_copy: Path) -> None:
    claim = _claim("gives")
    object.__setattr__(claim, "evidence_hash", "0" * 64)

    with pytest.raises(EvidenceTampering):
        apply_frame_claim(
            claim=claim,
            frame_category="transfer_frame",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )


# ---------------------------------------------------------------------------
# Test 9 — rejects evidence laundering as source='corpus'
# ---------------------------------------------------------------------------


def test_rejects_evidence_laundered_as_corpus(pack_copy: Path) -> None:
    """ADR-0168.1 §'Evidence floor': source='corpus' MUST be rejected."""
    with pytest.raises(EvidenceLaundering, match="MUST NOT be laundered"):
        apply_frame_claim(
            claim=_claim("gives"),
            frame_category="transfer_frame",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
            evidence_source="corpus",  # forbidden
        )


# ---------------------------------------------------------------------------
# Test 10 — case 0050 hazard pin: still refused after ratification
# ---------------------------------------------------------------------------


def test_case_0050_remains_refused_after_frame_ratification(
    pack_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After ratifying a safe transfer-frame verb, case 0050 must still refuse.

    Case 0050 ("Mark does a gig every other day for 2 weeks. ..." — the
    period token at sentence_index=0 with missing_operator=
    pre_frame_filler_sentence) is the prototype wrong=0 hazard: a
    speculative frame opener here would admit a partial graph.  The new
    frames/ entries must not open that admission path.
    """
    apply_frame_claim(
        claim=_claim("gives"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    _use_pack_for_reader(monkeypatch, pack_copy)
    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines()]
    case = next(c for c in cases if c["case_id"] == "gsm8k-train-sample-v1-0050")

    result, _rows = audit_problem(case["question"], case_id=case["case_id"])

    assert isinstance(result, ReaderRefusal), (
        "case 0050 must remain refused after FrameClaim ratification"
    )
    assert result.sentence_index == 0


# ---------------------------------------------------------------------------
# Test 11 — polarity=falsifies branch records non-opener
# ---------------------------------------------------------------------------


def test_polarity_falsifies_records_non_opener(pack_copy: Path) -> None:
    """A 'falsifies' ratification records the surface as NOT opening the frame.

    This is the negative-evidence path: an operator reviewed the audit row
    and decided the surface does not in fact open the frame category.  The
    entry is written to the same source file but with polarity=falsifies
    so downstream registry builds can mark the surface as a known non-opener.
    """
    receipt = apply_frame_claim(
        claim=_claim("along"),  # not actually a transfer verb
        frame_category="transfer_frame",
        polarity="falsifies",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.polarity == "falsifies"
    entry = next(
        e
        for e in _entries(pack_copy / "frames" / "transfer_frame.jsonl")
        if e["surface_form"] == "along"
    )
    assert entry["polarity"] == "falsifies"

    # affirms + falsifies of the same surface produce distinct entries
    receipt2 = apply_frame_claim(
        claim=_claim("gave"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    assert receipt2.polarity == "affirms"
    polarities = {
        e["polarity"]
        for e in _entries(pack_copy / "frames" / "transfer_frame.jsonl")
    }
    assert {"affirms", "falsifies"} <= polarities


# ---------------------------------------------------------------------------
# Test 12 — duplicate evidence appends to existing row
# ---------------------------------------------------------------------------


def test_duplicate_surface_polarity_with_new_evidence_appends_hash(
    pack_copy: Path,
) -> None:
    """ADR-0168.1 §'Idempotency': same claim + new evidence appends hash, not row."""
    # First ratification
    apply_frame_claim(
        claim=_claim("gives"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    # Second piece of evidence for the same claim — different case_id, so
    # the evidence_hash differs even though surface+polarity+category match.
    second_row = AuditRow(
        case_id="case-gives-2",
        sentence_index=1,
        token_index=4,
        token_text="gives",
        recognized_terms=("Bob", "buys"),
        skipped_frame=None,
        missing_operator="pre_frame_filler_sentence",
        refusal_reason="unexpected_category",
        refusal_detail="duplicate surface evidence",
    )
    second_claim = from_audit_row(second_row, "frame")
    receipt = apply_frame_claim(
        claim=second_claim,
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.is_duplicate_evidence is True
    rows = [
        e
        for e in _entries(pack_copy / "frames" / "transfer_frame.jsonl")
        if e["surface_form"] == "gives"
    ]
    assert len(rows) == 1, "duplicate evidence must not create a second row"
    assert len(rows[0]["evidence_hashes"]) == 2


# ---------------------------------------------------------------------------
# Test 13 — manifest.json checksum unchanged
# ---------------------------------------------------------------------------


def test_lexicon_checksum_preserved_by_frame_ratification(pack_copy: Path) -> None:
    """RAT-1 — the lexicon ``checksum`` field is preserved across frame
    ratification. The manifest may gain a ``frame_checksum`` field
    (auto-compile per RAT-1), but the pre-existing lexicon checksum
    bytes are untouched.
    """
    manifest_before = json.loads((pack_copy / "manifest.json").read_bytes())
    declared_before = manifest_before["checksum"]

    apply_frame_claim(
        claim=_claim("gives"),
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    manifest_after = json.loads((pack_copy / "manifest.json").read_bytes())
    assert manifest_after["checksum"] == declared_before, (
        "lexicon checksum must not change during frame ratification"
    )
    # RAT-1: frame_checksum may now be present (auto-compile).
    if "frame_checksum" in manifest_after:
        assert isinstance(manifest_after["frame_checksum"], str)


# ---------------------------------------------------------------------------
# Test 14 — alphabetical sort preserved across multiple writes
# ---------------------------------------------------------------------------


def test_alphabetical_sort_preserved(pack_copy: Path) -> None:
    for surface in ("transfers", "gives", "ceded"):
        apply_frame_claim(
            claim=_claim(surface),
            frame_category="transfer_frame",
            polarity="affirms",
            reviewer="Ada",
            pack_root=pack_copy,
        )

    surfaces = [
        e["surface_form"]
        for e in _entries(pack_copy / "frames" / "transfer_frame.jsonl")
    ]
    assert surfaces == sorted(surfaces)

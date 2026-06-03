"""ADR-0167 W3-A — End-to-end determinism + cognition regression.

Closes the LexicalClaim-first slice: refusal → adapter → signature →
ratification → re-audit → row movement.

Pure tests.  Every ratification uses a tmpdir pack copy; the real
``language_packs/data/en_core_math_v1/`` is byte-identical before and
after the suite runs.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from core.protocol import canonical_bytes
from generate.comprehension import lexicon as comprehension_lexicon
from generate.comprehension import lifecycle
from generate.comprehension.audit import AuditRow, audit_problem
from generate.comprehension.state import ReaderRefusal
from teaching.discovery import DiscoveryCandidate
from teaching.math_claim_signature import lexical_claim_signature
from teaching.math_contemplation import audit_to_evidence
from teaching.math_evidence import (
    SUB_TYPE_FOR_OPERATOR,
    MathReaderRefusalEvidence,
    from_audit_row,
)
from teaching.math_lexical_ratification import apply_lexical_claim

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ARTIFACT_PATH = (
    REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "audit_brief_11.json"
)
CASES_PATH = (
    REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"
)
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"
PACK_HAZARD_CASE_ID = "gsm8k-train-sample-v1-0050"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_from_artifact_case(case: dict[str, object]) -> AuditRow:
    return AuditRow(
        case_id=str(case["case_id"]),
        sentence_index=int(case["sentence_index"]),
        token_index=int(case["token_index"]),
        token_text=str(case["token_text"]),
        recognized_terms=tuple(str(t) for t in case["recognized_terms"]),  # type: ignore[arg-type]
        skipped_frame=(
            None if case["skipped_frame"] is None else str(case["skipped_frame"])
        ),
        missing_operator=(
            None
            if case["missing_operator"] is None
            else str(case["missing_operator"])
        ),
        refusal_reason=str(case["refusal_reason"]),
        refusal_detail=str(case["refusal_detail"]),
    )


def _load_artifact_rows() -> list[AuditRow]:
    artifact = json.loads(AUDIT_ARTIFACT_PATH.read_text(encoding="utf-8"))
    return [_row_from_artifact_case(case) for case in artifact["per_case"]]


def _load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _real_pack_digest() -> str:
    """Recursive sha256 of all bytes in the real math pack (sorted paths)."""
    digest = hashlib.sha256()
    for path in sorted(PACK_ROOT.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(PACK_ROOT).as_posix().encode("utf-8"))
            digest.update(b"\x00")
            digest.update(path.read_bytes())
            digest.update(b"\x00")
    return digest.hexdigest()


@pytest.fixture()
def pack_copy(tmp_path: Path):
    """Copy the real math pack to tmpdir; clear lexicon caches around use."""
    target = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target)
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    yield target
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()


@pytest.fixture(autouse=True)
def _real_pack_untouched():
    """Hard assertion: the real math pack must be byte-identical after each test."""
    before = _real_pack_digest()
    yield
    after = _real_pack_digest()
    assert after == before, "real en_core_math_v1 pack was mutated by a test"


def _use_pack_for_reader(monkeypatch: pytest.MonkeyPatch, pack_root: Path) -> None:
    comprehension_lexicon._CACHE.clear()

    @functools.cache
    def _tmp_lexicon():
        return comprehension_lexicon.load_lexicon(pack_root)

    monkeypatch.setattr(lifecycle, "_get_lexicon", _tmp_lexicon)


# ---------------------------------------------------------------------------
# Test 1 — full pipeline from audit to evidence
# ---------------------------------------------------------------------------


def test_full_pipeline_from_audit_to_evidence() -> None:
    rows = _load_artifact_rows()
    evidence = audit_to_evidence(rows)
    expected = sum(
        1
        for row in rows
        if row.missing_operator is not None
        and row.missing_operator in SUB_TYPE_FOR_OPERATOR
    )
    assert len(evidence) == expected
    for record in evidence:
        assert isinstance(record, MathReaderRefusalEvidence)
        assert len(record.evidence_hash) == 64
        assert all(c in "0123456789abcdef" for c in record.evidence_hash)
        if record.sub_type == "lexical":
            assert len(record.claim_signature) == 64
            assert all(c in "0123456789abcdef" for c in record.claim_signature)
        else:
            assert record.claim_signature == ""
        # audit_row round-trips intact
        rebuilt = from_audit_row(
            record.audit_row,
            record.sub_type,
            claim_signature=record.claim_signature,
        )
        assert rebuilt.evidence_hash == record.evidence_hash


# ---------------------------------------------------------------------------
# Test 2 — replay equivalence (in-process)
# ---------------------------------------------------------------------------


def test_e2e_replay_equivalence() -> None:
    rows = _load_artifact_rows()
    first = audit_to_evidence(rows)
    second = audit_to_evidence(rows)
    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a == b
        assert a.evidence_hash == b.evidence_hash
        assert a.to_canonical_bytes() == b.to_canonical_bytes()


# ---------------------------------------------------------------------------
# Test 3 — load-bearing integration test: lexical ratification advances a row
# ---------------------------------------------------------------------------


def test_lexical_ratification_advances_unknown_word_row(
    pack_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ADR-0167 thesis-claim test: engine teaches itself in math domain.

    Steps (per W3-A brief):
      1. Run audit on case 0040 with tmpdir pack → refusal at 'sees'
      2. Wrap refusal in MathReaderRefusalEvidence via audit_to_evidence
      3. apply_lexical_claim with category='drain_token', tmpdir pack
      4. Re-audit case 0040 with tmpdir pack → refusal still happens
      5. Assert previously-blocking token resolves (no unknown_word at 'sees')
      6. Assert refusal moved away from 'lexicon_entry'
      7. Assert wrong == 0 holds (no admission)
      8. Assert case 0050 hazard still pinned at sentence_index 0
    """
    cases = _load_cases()
    case_0050 = next(c for c in cases if c["case_id"] == PACK_HAZARD_CASE_ID)

    # Reader-stable synthetic target. The train_sample cases that once
    # first-refused at an unknown WORD (case 0040 / 'sees') have been outgrown
    # by the reader, so this e2e pins the self-teaching loop against a crafted
    # statement instead: an unknown verb ('zorps') with a clear quantity, plus a
    # second unknown verb ('quibbles') that keeps the statement refused after the
    # first is ratified. The lexical-ratification primitives are unit-tested in
    # test_math_lexical_ratification.py and others; this asserts the integration
    # loop (audit -> evidence -> ratify -> re-audit -> the token resolves).
    target_statement = (
        "Sam zorps 5 apples and quibbles 3 oranges. How many apples does Sam have?"
    )
    target_surface = "zorps"
    target_case_id = "synthetic-lexratify-zorps"

    # Step 1: initial audit produces a lexicon_entry refusal at the unknown verb.
    _use_pack_for_reader(monkeypatch, pack_copy)
    result_before, rows_before = audit_problem(
        target_statement, case_id=target_case_id
    )
    assert isinstance(result_before, ReaderRefusal)
    assert rows_before, "expected at least one audit row"
    first_refusal = rows_before[0]
    assert first_refusal.missing_operator == "lexicon_entry"
    assert first_refusal.token_text == target_surface

    # Step 2: wrap as evidence.
    evidence = audit_to_evidence([first_refusal])
    assert len(evidence) == 1
    claim = evidence[0]
    assert claim.sub_type == "lexical"
    assert claim.claim_signature  # non-empty for lexical sub_type

    # Step 3: ratify into tmpdir drain_token.jsonl.
    receipt = apply_lexical_claim(
        claim=claim,
        category="drain_token",
        reviewer="w3a_test",
        pack_root=pack_copy,
    )
    assert receipt.lemma == target_surface
    assert receipt.category == "drain_token"
    assert receipt.file_sha256_before != receipt.file_sha256_after

    # Step 4 + 5 + 6: re-audit; previously-blocking token resolves; refusal moved.
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    _use_pack_for_reader(monkeypatch, pack_copy)
    result_after, rows_after = audit_problem(
        target_statement, case_id=target_case_id
    )

    # Lexicon now resolves the ratified verb as drain_token in the tmpdir pack.
    lex = comprehension_lexicon.load_lexicon(pack_copy)
    resolved = comprehension_lexicon.lookup(lex, target_surface)
    assert resolved is not None
    assert resolved.category == "drain_token"

    # Refusal still happens (the second unknown verb 'quibbles' remains a
    # barrier) but no longer as a lexicon_entry miss on the ratified token.
    assert isinstance(result_after, ReaderRefusal)
    if rows_after:
        new_refusal = rows_after[0]
        # Either we advanced past the ratified token, OR hit a different token,
        # OR a different missing_operator class entirely.
        progressed = (
            new_refusal.token_text != target_surface
            or new_refusal.missing_operator != "lexicon_entry"
            or new_refusal.sentence_index != first_refusal.sentence_index
        )
        assert progressed, (
            f"ratification of {target_surface!r} did not move the refusal class: "
            f"before={first_refusal.missing_operator!r}@s{first_refusal.sentence_index}"
            f"/{first_refusal.token_text!r}, "
            f"after={new_refusal.missing_operator!r}@s{new_refusal.sentence_index}"
            f"/{new_refusal.token_text!r}"
        )

    # Step 7: wrong == 0 — the statement still refuses (not admitted): the
    # ratified drain_token resolved one barrier but 'quibbles' remains.
    assert not _is_admission(result_after)

    # Step 8: case 0050 hazard still pinned.
    result_hazard, _hazard_rows = audit_problem(
        case_0050["question"], case_id=case_0050["case_id"]
    )
    assert isinstance(result_hazard, ReaderRefusal)
    assert result_hazard.sentence_index == 0


def _is_admission(result: object) -> bool:
    """Return True iff the reader admitted (produced a MathProblemGraph)."""
    from generate.math_problem_graph import MathProblemGraph

    return isinstance(result, MathProblemGraph)


# ---------------------------------------------------------------------------
# Test 4 — cross-process determinism
# ---------------------------------------------------------------------------


def test_e2e_determinism_across_processes() -> None:
    rows = _load_artifact_rows()
    in_process = audit_to_evidence(rows)
    assert in_process, "expected at least one evidence record"

    expected_hash = in_process[0].evidence_hash
    expected_case_id = in_process[0].case_id

    script = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "from generate.comprehension.audit import AuditRow\n"
        "from teaching.math_contemplation import audit_to_evidence\n"
        f"artifact = json.loads(Path({str(AUDIT_ARTIFACT_PATH)!r}).read_text())\n"
        "def to_row(c):\n"
        "    return AuditRow(\n"
        "        case_id=str(c['case_id']),\n"
        "        sentence_index=int(c['sentence_index']),\n"
        "        token_index=int(c['token_index']),\n"
        "        token_text=str(c['token_text']),\n"
        "        recognized_terms=tuple(str(t) for t in c['recognized_terms']),\n"
        "        skipped_frame=None if c['skipped_frame'] is None else str(c['skipped_frame']),\n"
        "        missing_operator=None if c['missing_operator'] is None else str(c['missing_operator']),\n"
        "        refusal_reason=str(c['refusal_reason']),\n"
        "        refusal_detail=str(c['refusal_detail']),\n"
        "    )\n"
        "rows = [to_row(c) for c in artifact['per_case']]\n"
        "ev = audit_to_evidence(rows)\n"
        "print(ev[0].case_id)\n"
        "print(ev[0].evidence_hash)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, f"subprocess failed: {proc.stderr}"
    out_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert out_lines[0] == expected_case_id
    assert out_lines[1] == expected_hash


# ---------------------------------------------------------------------------
# Test 5 — cognition teaching corridor unaffected
# ---------------------------------------------------------------------------


def _cognition_candidate() -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id="w3a_cognition_probe",
        proposed_chain={
            "subject": "wisdom",
            "intent": "cause",
            "connective": None,
            "object": None,
        },
        trigger="would_have_grounded",
        source_turn_trace="t_w3a",
        pack_consistent=True,
        boundary_clean=True,
    )


def test_cognition_teaching_corridor_unaffected() -> None:
    cand = _cognition_candidate()
    assert cand.domain == "cognition"

    # Canonical-bytes invariant (per W2-C contract: domain is serialised in
    # the canonical bytes; only as_dict() omits the key for cognition).
    cb = canonical_bytes(cand)
    assert b'"domain":"cognition"' in cb
    assert b'"domain":"math"' not in cb

    # Replay-equivalent across reruns.
    assert canonical_bytes(_cognition_candidate()) == cb

    # Round-trip through as_dict/from_dict without raising.
    payload = cand.as_dict()
    assert "domain" not in payload  # cognition omits per W2-C
    restored = DiscoveryCandidate.from_dict(payload)
    assert restored.domain == "cognition"
    assert canonical_bytes(restored) == cb

    # Defensive: math candidate canonical bytes differ.
    math_cand = DiscoveryCandidate(
        candidate_id="w3a_math_probe",
        proposed_chain={
            "subject": "crayons",
            "intent": "lexical_claim",
            "connective": None,
            "object": None,
        },
        trigger="would_have_grounded",
        source_turn_trace="t_w3a_math",
        pack_consistent=True,
        boundary_clean=True,
        domain="math",
    )
    assert canonical_bytes(math_cand) != cb
    assert b'"domain":"math"' in canonical_bytes(math_cand)


# ---------------------------------------------------------------------------
# Test 6 — evidence dedup via claim_signature
# ---------------------------------------------------------------------------


def test_evidence_dedup_via_claim_signature() -> None:
    """Two cases refusing on the same surface collapse under signature dedup."""
    shared_surface = "crayons"
    refusal_detail = f"no primitive or lexicon match for '{shared_surface}'"

    row_a = AuditRow(
        case_id="case-A",
        sentence_index=0,
        token_index=4,
        token_text=shared_surface,
        recognized_terms=("Ava", "has", "5"),
        skipped_frame=None,
        missing_operator="lexicon_entry",
        refusal_reason="unknown_word",
        refusal_detail=refusal_detail,
    )
    row_b = AuditRow(
        case_id="case-B",
        sentence_index=0,
        token_index=4,
        token_text=shared_surface,
        recognized_terms=("Ava", "has", "5"),
        skipped_frame=None,
        missing_operator="lexicon_entry",
        refusal_reason="unknown_word",
        refusal_detail=refusal_detail,
    )

    evidence = audit_to_evidence([row_a, row_b])
    assert len(evidence) == 2
    e_a, e_b = evidence

    # Signatures match (dedup key)
    assert e_a.claim_signature == e_b.claim_signature
    assert (
        e_a.claim_signature
        == lexical_claim_signature(surface=shared_surface, refusal_detail=refusal_detail)
    )

    # Per-record hashes differ (case_id is part of canonical bytes)
    assert e_a.evidence_hash != e_b.evidence_hash

    # Future Workbench dedup logic — pin the contract via a minimal snippet.
    deduped: dict[str, MathReaderRefusalEvidence] = {}
    for record in evidence:
        deduped.setdefault(record.claim_signature, record)
    assert len(deduped) == 1


# ---------------------------------------------------------------------------
# Test 7 — audit-artifact round-trip with signatures
# ---------------------------------------------------------------------------


def test_audit_artifact_round_trip_with_signatures(tmp_path: Path) -> None:
    rows = _load_artifact_rows()
    evidence = audit_to_evidence(rows)

    out_path = tmp_path / "evidence.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for record in evidence:
            payload = {
                "case_id": record.case_id,
                "sentence_index": record.sentence_index,
                "token_index": record.token_index,
                "refusal_reason": record.refusal_reason,
                "missing_operator": record.missing_operator,
                "claim_signature": record.claim_signature,
                "evidence_hash": record.evidence_hash,
                "sub_type": record.sub_type,
                "audit_row": asdict(record.audit_row),
            }
            fh.write(
                json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n"
            )

    # Reload, rebuild evidence from the audit_row, and check byte-equality.
    rebuilt: list[MathReaderRefusalEvidence] = []
    with out_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            payload = json.loads(line)
            audit_row = AuditRow(
                case_id=payload["audit_row"]["case_id"],
                sentence_index=payload["audit_row"]["sentence_index"],
                token_index=payload["audit_row"]["token_index"],
                token_text=payload["audit_row"]["token_text"],
                recognized_terms=tuple(payload["audit_row"]["recognized_terms"]),
                skipped_frame=payload["audit_row"]["skipped_frame"],
                missing_operator=payload["audit_row"]["missing_operator"],
                refusal_reason=payload["audit_row"]["refusal_reason"],
                refusal_detail=payload["audit_row"]["refusal_detail"],
            )
            rebuilt.append(
                from_audit_row(
                    audit_row,
                    payload["sub_type"],
                    claim_signature=payload["claim_signature"],
                )
            )

    assert len(rebuilt) == len(evidence)
    for original, restored in zip(evidence, rebuilt):
        assert original.evidence_hash == restored.evidence_hash
        assert original.to_canonical_bytes() == restored.to_canonical_bytes()

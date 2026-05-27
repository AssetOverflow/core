"""ADR-0167 W2-D — LexicalClaim ratification handler tests."""

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
from teaching.math_lexical_ratification import (
    AlreadyRatified,
    EvidenceTampering,
    SAFE_CATEGORIES,
    UnknownCategory,
    WrongClaimSubType,
    WrongZeroViolationCandidate,
    apply_lexical_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"
CASES_PATH = REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"


@pytest.fixture()
def pack_copy(tmp_path: Path) -> Path:
    target = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target)
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    yield target
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()


def _row(surface: str, *, missing_operator: str = "lexicon_entry") -> AuditRow:
    return AuditRow(
        case_id=f"case-{surface}",
        sentence_index=0,
        token_index=2,
        token_text=surface,
        recognized_terms=("Ava", "counts"),
        skipped_frame=None,
        missing_operator=missing_operator,
        refusal_reason="unknown_word",
        refusal_detail=f"no primitive or lexicon match for '{surface}'",
    )


def _claim(surface: str, *, sub_type: str = "lexical"):
    return from_audit_row(_row(surface), sub_type)  # type: ignore[arg-type]


def _entries(path: Path) -> list[dict]:
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


def test_apply_lexical_claim_writes_lemma(pack_copy: Path) -> None:
    receipt = apply_lexical_claim(
        claim=_claim("widgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.lemma == "widgets"
    assert receipt.category == "drain_token"
    assert receipt.is_alias is False
    assert receipt.aliased_to is None
    entry = next(e for e in _entries(pack_copy / "lexicon" / "drain_token.jsonl") if e["lemma"] == "widgets")
    assert entry == {
        "lemma": "widgets",
        "category": "drain_token",
        "aliases": [],
        "provenance": receipt.provenance,
    }
    lex = comprehension_lexicon.load_lexicon(pack_copy)
    resolved = comprehension_lexicon.lookup(lex, "widgets")
    assert resolved is not None
    assert resolved.category == "drain_token"


def test_receipt_records_before_after_sha(pack_copy: Path) -> None:
    receipt = apply_lexical_claim(
        claim=_claim("widgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert len(receipt.file_sha256_before) == 64
    assert len(receipt.file_sha256_after) == 64
    assert receipt.file_sha256_before != receipt.file_sha256_after
    assert receipt.evidence_hash == _claim("widgets").evidence_hash


def test_idempotent_raises_already_ratified(pack_copy: Path) -> None:
    claim = _claim("widgets")
    apply_lexical_claim(
        claim=claim,
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    with pytest.raises(AlreadyRatified, match="already ratified"):
        apply_lexical_claim(
            claim=claim,
            category="drain_token",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_rejects_non_lexical_sub_type(pack_copy: Path) -> None:
    with pytest.raises(WrongClaimSubType):
        apply_lexical_claim(
            claim=_claim("widgets", sub_type="frame"),
            category="drain_token",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_rejects_unsafe_category(pack_copy: Path) -> None:
    with pytest.raises(WrongZeroViolationCandidate, match="open reader frames"):
        apply_lexical_claim(
            claim=_claim("widgets"),
            category="accumulation_verb",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_rejects_unknown_category(pack_copy: Path) -> None:
    with pytest.raises(UnknownCategory):
        apply_lexical_claim(
            claim=_claim("widgets"),
            category="not_a_category",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_rejects_evidence_tampering(pack_copy: Path) -> None:
    claim = _claim("widgets")
    object.__setattr__(claim, "evidence_hash", "0" * 64)

    with pytest.raises(EvidenceTampering):
        apply_lexical_claim(
            claim=claim,
            category="drain_token",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_alphabetical_sort_preserved(pack_copy: Path) -> None:
    apply_lexical_claim(
        claim=_claim("aardwidgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    lemmas = [entry["lemma"] for entry in _entries(pack_copy / "lexicon" / "drain_token.jsonl")]
    assert lemmas == sorted(lemmas)


def test_manifest_checksum_unchanged(pack_copy: Path) -> None:
    manifest_bytes_before = (pack_copy / "manifest.json").read_bytes()
    manifest_sha_before = _manifest_sha(pack_copy)
    declared_before = json.loads(manifest_bytes_before)["checksum"]

    apply_lexical_claim(
        claim=_claim("widgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    manifest_bytes_after = (pack_copy / "manifest.json").read_bytes()
    assert manifest_bytes_after == manifest_bytes_before
    assert _manifest_sha(pack_copy) == manifest_sha_before
    assert json.loads(manifest_bytes_after)["checksum"] == declared_before


def test_hazard_case_0050_remains_refused(pack_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AlreadyRatified):
        apply_lexical_claim(
            claim=_claim("along"),
            category="drain_token",
            reviewer="Ada",
            pack_root=pack_copy,
        )
    _use_pack_for_reader(monkeypatch, pack_copy)
    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines()]
    case = next(c for c in cases if c["case_id"] == "gsm8k-train-sample-v1-0050")

    result, _rows = audit_problem(case["question"], case_id=case["case_id"])

    assert isinstance(result, ReaderRefusal)
    assert result.sentence_index == 0


def test_audit_artifact_still_has_zero_admissions_after_tmp_ratification(
    pack_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    apply_lexical_claim(
        claim=_claim("widgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    _use_pack_for_reader(monkeypatch, pack_copy)
    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines()]

    for case in cases:
        result, _rows = audit_problem(case["question"], case_id=case["case_id"])
        assert isinstance(result, ReaderRefusal) or result is None, case["case_id"]


def test_load_lexicon_resolves_newly_ratified_lemma(pack_copy: Path) -> None:
    apply_lexical_claim(
        claim=_claim("ratifiables"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )
    comprehension_lexicon._CACHE.clear()

    lex = comprehension_lexicon.load_lexicon(pack_copy)
    resolved = comprehension_lexicon.lookup(lex, "ratifiables")

    assert resolved is not None
    assert resolved.lemma == "ratifiables"
    assert resolved.category == "drain_token"


def test_alias_path_when_existing_lemma_is_stem(pack_copy: Path) -> None:
    apply_lexical_claim(
        claim=_claim("widget"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    receipt = apply_lexical_claim(
        claim=_claim("widgets"),
        category="drain_token",
        reviewer="Ada",
        pack_root=pack_copy,
    )

    assert receipt.is_alias is True
    assert receipt.aliased_to == "widget"
    entry = next(e for e in _entries(pack_copy / "lexicon" / "drain_token.jsonl") if e["lemma"] == "widget")
    assert "widgets" in entry["aliases"]
    lex = comprehension_lexicon.load_lexicon(pack_copy)
    resolved = comprehension_lexicon.lookup(lex, "widgets")
    assert resolved is not None
    assert resolved.lemma == "widget"


def test_rejects_existing_frame_opener_surface(pack_copy: Path) -> None:
    with pytest.raises(WrongZeroViolationCandidate, match="frame-opener"):
        apply_lexical_claim(
            claim=_claim("earn"),
            category="drain_token",
            reviewer="Ada",
            pack_root=pack_copy,
        )


def test_safe_categories_w2d_scope_is_drain_token_only() -> None:
    assert SAFE_CATEGORIES == frozenset({"drain_token"})

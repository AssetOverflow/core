"""ADR-0131.2 — Math teaching corpus lane ratification tests.

Validates:
- Dataset integrity (no duplicates, well-formed fields, 30 cases)
- Bounded domain (lemmas belong strictly to en_mathematics_logic_v1)
- Replay equivalence (runs exit criterion successfully)
- Determinism (report.json byte-equal across runs)
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.pack_resolver import _pack_lexicon_for
from evals.math_teaching_corpus.v1.runner import (
    _load_cases,
    build_report,
)

_ROOT = Path(__file__).resolve().parent.parent
_CASES_PATH = _ROOT / "evals" / "math_teaching_corpus" / "v1" / "cases.jsonl"
_CORPUS_PATH = _ROOT / "teaching" / "math_corpora" / "math_teaching_v1.jsonl"


class TestDatasetIntegrity:
    def test_files_exist(self) -> None:
        assert _CASES_PATH.exists(), f"missing cases file: {_CASES_PATH}"
        assert _CORPUS_PATH.exists(), f"missing corpus file: {_CORPUS_PATH}"

    def test_cases_are_well_formed(self) -> None:
        cases = _load_cases(_CASES_PATH)
        assert len(cases) >= 20, "v1 must ship at least 20 cases"
        for c in cases:
            for k in ("case_id", "proposed_chain", "expected", "category", "provenance"):
                assert k in c, f"case {c.get('case_id')} missing field {k!r}"
            assert c["expected"] == "replay_equivalent"
            chain = c["proposed_chain"]
            for field in ("subject", "intent", "connective", "object"):
                assert field in chain, f"proposed_chain missing field {field!r}"
                assert isinstance(chain[field], str) and chain[field], f"empty or invalid field {field!r}"

    def test_no_duplicate_case_ids(self) -> None:
        cases = _load_cases(_CASES_PATH)
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids)), "duplicate case_ids in dataset"

    def test_corpus_integrity(self) -> None:
        candidates = []
        with _CORPUS_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
        
        assert len(candidates) >= 20, "v1 corpus must have at least 20 candidates"
        cids = [c["candidate_id"] for c in candidates]
        assert len(cids) == len(set(cids)), "duplicate candidate_ids in corpus"
        
        for c in candidates:
            assert "candidate_id" in c
            assert "proposed_chain" in c
            assert "evidence" in c
            assert len(c["evidence"]) >= 1
            assert any(ev.get("source") == "corpus" for ev in c["evidence"])


class TestBoundedDomain:
    def test_no_out_of_domain_lemmas(self) -> None:
        # Load the mathematics logic pack
        pack_lexicon = _pack_lexicon_for("en_mathematics_logic_v1")
        assert pack_lexicon, "en_mathematics_logic_v1 pack not found or empty"

        cases = _load_cases(_CASES_PATH)
        for c in cases:
            chain = c["proposed_chain"]
            sub = chain["subject"]
            obj = chain["object"]
            assert sub in pack_lexicon, f"subject {sub!r} is not in en_mathematics_logic_v1"
            assert obj in pack_lexicon, f"object {obj!r} is not in en_mathematics_logic_v1"


class TestLaneGate:
    def test_lane_passes_exit_criterion(self) -> None:
        cases = _load_cases(_CASES_PATH)
        report = build_report(cases)
        assert report["exit_criterion"]["passed"], (
            f"lane gate failed: counts={report['counts']!r} "
            f"correct_rate={report['correct_rate']!r}"
        )
        assert report["counts"]["wrong"] == 0, "wrong count must be zero"
        assert report["counts"]["correct"] == len(cases), "all cases must be correct"

    def test_report_is_byte_equal_across_runs(self) -> None:
        cases = _load_cases(_CASES_PATH)
        r1 = build_report(cases)
        r2 = build_report(cases)
        s1 = json.dumps(r1, sort_keys=True).encode("utf-8")
        s2 = json.dumps(r2, sort_keys=True).encode("utf-8")
        assert s1 == s2

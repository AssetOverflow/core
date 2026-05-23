"""ADR-0131.2.B — Math teaching corpus lane ratification tests.

Validates:
- Dataset integrity (no duplicates, well-formed fields, positive + negative + refused cases)
- Bounded domain (lemmas belong strictly to en_mathematics_logic_v1 for all valid chains)
- Replay equivalence (runs exit criterion successfully)
- Determinism (report.json byte-equal across runs)
- Verdict class diversity (at least one case of each expected class)
- Honest evidence (no dangling evidence references in math teaching corpus)
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
        assert len(cases) >= 30, "v1.B must ship at least 30 cases"
        for c in cases:
            for k in ("case_id", "proposed_chain", "expected", "category", "provenance"):
                assert k in c, f"case {c.get('case_id')} missing field {k!r}"
            assert c["expected"] in ("replay_equivalent", "not_equivalent", "refused")
            
            # Non-refused cases should have fully populated strings in proposed_chain
            if c["expected"] != "refused":
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

    def test_expected_verdict_class_diversity(self) -> None:
        """Asserts that cases.jsonl contains at least one of each expected class."""
        cases = _load_cases(_CASES_PATH)
        expected_classes = {c["expected"] for c in cases}
        for cls in ("replay_equivalent", "not_equivalent", "refused"):
            assert cls in expected_classes, f"missing expected class {cls!r} in cases.jsonl"


class TestBoundedDomain:
    def test_no_out_of_domain_lemmas_in_corpus(self) -> None:
        """Asserts that all valid corpus chains contain subject and object strictly in en_mathematics_logic_v1."""
        pack_lexicon = _pack_lexicon_for("en_mathematics_logic_v1")
        assert pack_lexicon, "en_mathematics_logic_v1 pack not found or empty"

        candidates = []
        with _CORPUS_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))

        for c in candidates:
            chain = c["proposed_chain"]
            sub = chain["subject"]
            obj = chain["object"]
            assert sub in pack_lexicon, f"subject {sub!r} is not in en_mathematics_logic_v1"
            assert obj in pack_lexicon, f"object {obj!r} is not in en_mathematics_logic_v1"

    def test_no_out_of_domain_lemmas_in_positive_cases(self) -> None:
        """Asserts that positive cases only query math logic pack lemmas."""
        pack_lexicon = _pack_lexicon_for("en_mathematics_logic_v1")
        cases = _load_cases(_CASES_PATH)
        for c in cases:
            if c["expected"] == "replay_equivalent":
                chain = c["proposed_chain"]
                sub = chain["subject"]
                obj = chain["object"]
                assert sub in pack_lexicon, f"positive case subject {sub!r} is not in en_mathematics_logic_v1"
                assert obj in pack_lexicon, f"positive case object {obj!r} is not in en_mathematics_logic_v1"


class TestHonestEvidence:
    def test_no_dangling_evidence_refs(self) -> None:
        """Ensures that every evidence pointer cites a valid lemma ID or preceding corpus chain ID."""
        valid_refs: set[str] = set()

        # 1. Load lemma IDs from permitted packs
        for pack_id in ("en_mathematics_logic_v1", "en_arithmetic_v1", "en_units_v1"):
            pack_path = _ROOT / "language_packs" / "data" / pack_id / "lexicon.jsonl"
            if pack_path.exists():
                with pack_path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            eid = entry.get("entry_id")
                            if eid:
                                valid_refs.add(eid)

        # 2. Parse candidates from the math teaching corpus and collect their future accepted chain IDs as valid references
        candidates = []
        with _CORPUS_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))

        for c in candidates:
            chain = c["proposed_chain"]
            intent = chain["intent"]
            sub = chain["subject"]
            conn = chain["connective"]
            obj = chain["object"]
            chain_id = f"{intent}_{sub}_{conn}_{obj}"
            valid_refs.add(chain_id)

        # 3. Assert all evidence refs in the corpus resolve to one of these valid references
        for c in candidates:
            for ev in c["evidence"]:
                ref = ev["ref"]
                assert ref in valid_refs, f"dangling reference: {ref!r} cited in candidate {c['candidate_id']}"


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

"""ADR-0174 Phase 4 — in-loop contemplate.

Acceptance tests for ``generate.comprehension.contemplate.contemplate``
and the gendered-pronoun resolution use case wired against the new
``en_core_names_v1`` pack.

All tests are skipped until the implementer:
  1. Creates ``generate/comprehension/contemplate.py`` per the scope brief
  2. Moves the ``en_core_names_v1`` pack into ``language_packs/data/``
  3. Wires ``contemplate`` at the ``len(survivors) >= 2`` site in
     ``generate/math_candidate_graph.py``
  4. Removes the ``@pytest.mark.skip`` decorators
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# 1. contemplate() primitive contract
# ---------------------------------------------------------------------------


class TestContemplatePrimitive:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_empty_residual_returns_none(self) -> None:
        """No survivors to disambiguate → no-op."""
        from generate.comprehension.contemplate import contemplate
        from generate.comprehension.state import ProblemReadingState
        ps = ProblemReadingState(
            entity_registry=(), accumulated_initial_state=(),
            accumulated_operations=(), unknown_target_slot=None,
            pronoun_resolution_history=(), sentence_index=0,
            source_text_offset=0,
        )
        assert contemplate(ps, residual=()) is None

    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_single_survivor_returns_none(self) -> None:
        """Single survivor is unambiguous — caller doesn't need contemplate."""
        # contemplate should return None when residual has length 1;
        # the caller (math_candidate_graph) only invokes contemplate
        # when len(survivors) >= 2 anyway, but defensive.
        from generate.comprehension.contemplate import contemplate
        from generate.comprehension.state import (
            Hypothesis, ProblemReadingState,
        )
        ps = ProblemReadingState(
            entity_registry=(), accumulated_initial_state=(),
            accumulated_operations=(), unknown_target_slot=None,
            pronoun_resolution_history=(), sentence_index=0,
            source_text_offset=0,
        )
        h = Hypothesis(
            candidate=("sentinel",), category_assignments=(),
            constraint_state=(), confidence_rank=0, unresolved=(),
        )
        assert contemplate(ps, residual=(h,)) is None


# ---------------------------------------------------------------------------
# 2. Resolution dataclass invariants
# ---------------------------------------------------------------------------


class TestResolutionDataclass:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_valid_resolution_constructs(self) -> None:
        from generate.comprehension.contemplate import Resolution
        r = Resolution(
            kind="eliminate",
            target_hypothesis_id=1,
            sub_question="which antecedent is female-gendered?",
            source="pack",
            evidence=(("en_core_names_v1", "Alice→female"),),
        )
        assert r.kind == "eliminate"
        assert r.source == "pack"

    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_invalid_kind_refused(self) -> None:
        from generate.comprehension.contemplate import Resolution
        from generate.comprehension.state import ComprehensionStateError
        with pytest.raises(ComprehensionStateError, match="kind"):
            Resolution(
                kind="guess",  # not in {eliminate, admit_unknown}
                target_hypothesis_id=0, sub_question="x",
                source="pack", evidence=(),
            )

    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_invalid_source_refused(self) -> None:
        from generate.comprehension.contemplate import Resolution
        from generate.comprehension.state import ComprehensionStateError
        with pytest.raises(ComprehensionStateError, match="source"):
            Resolution(
                kind="eliminate", target_hypothesis_id=0,
                sub_question="x",
                source="llm",  # not in {vault, pack, audit_history}
                evidence=(),
            )


# ---------------------------------------------------------------------------
# 3. Gendered-pronoun pack resolution — the killer use case
# ---------------------------------------------------------------------------


class TestGenderedPronounResolution:
    @pytest.mark.skip(reason="Phase 4 + en_core_names_v1 pack not yet wired")
    def test_she_resolves_to_alice_via_gender_pack(self) -> None:
        """Multi-actor case where one antecedent is female-gendered
        and one is male-gendered. 'She' resolves to the female one
        via deterministic pack consult."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 marbles. "
            "Bob has 3 marbles. "
            "She collected 2 marbles. "
            "How many marbles does Alice have?"
        )
        r = parse_and_solve(text)
        # Phase 4 contemplate fires when the Phase 3a defense would
        # have refused (multi-actor). Pack consults gender of Alice
        # (female) and Bob (male); "She" requires female → Alice.
        assert r.answer == 7  # 5 + 2 collected
        contemplate_events = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "contemplate"
        ]
        resolved = [e for e in contemplate_events
                    if e.get("outcome") == "resolved"]
        assert resolved, f"expected contemplate resolved event; got {contemplate_events}"
        assert resolved[0]["source"] == "pack"

    @pytest.mark.skip(reason="Phase 4 + en_core_names_v1 pack not yet wired")
    def test_he_resolves_to_bob_via_gender_pack(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 marbles. "
            "Bob has 3 marbles. "
            "He collected 2 marbles. "
            "How many marbles does Bob have?"
        )
        r = parse_and_solve(text)
        assert r.answer == 5  # Bob's 3 + 2 collected

    @pytest.mark.skip(reason="Phase 4 + en_core_names_v1 pack not yet wired")
    def test_same_gender_antecedents_refuse(self) -> None:
        """If both prior subjects are the same gender, pronoun is
        still ambiguous after pack consult. Refuse cleanly."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 marbles. "
            "Mary has 3 marbles. "
            "She collected 2 marbles. "
            "How many marbles does Alice have?"
        )
        r = parse_and_solve(text)
        # Both Alice and Mary are female → contemplate returns None
        # → refuse with ambiguous_unresolvable trace event.
        assert r.answer is None
        contemplate_events = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "contemplate"
        ]
        assert any(e.get("outcome") == "ambiguous_unresolvable"
                   for e in contemplate_events)

    @pytest.mark.skip(reason="Phase 4 + en_core_names_v1 pack not yet wired")
    def test_unknown_name_refuses(self) -> None:
        """If an antecedent name is not in the pack, refuse cleanly
        (refusal-preferring on uncovered evidence)."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Xqzqzy has 5 marbles. "
            "Bob has 3 marbles. "
            "She collected 2 marbles. "
            "How many marbles does Bob have?"
        )
        r = parse_and_solve(text)
        # 'Xqzqzy' not in pack → can't determine gender → refuse.
        assert r.answer is None


# ---------------------------------------------------------------------------
# 4. Evidence-source precedence (vault > packs > audit_history)
# ---------------------------------------------------------------------------


class TestEvidenceSourcePrecedence:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_vault_resolution_preferred_over_pack(self) -> None:
        """If both vault and pack would resolve the ambiguity, vault wins.
        This codifies the precedence from ADR-0174 §Open Q#3."""
        # Mock or instrument vault to claim prior resolution that
        # disagrees with pack; assert vault's wins and the trace
        # records source="vault".
        # (Implementation detail: depends on vault-mocking pattern)
        from generate.comprehension.contemplate import contemplate
        # Skeleton — implementer fills in vault mock per existing
        # test_vault_recall patterns.
        pass


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_two_runs_produce_identical_resolution(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 marbles. Bob has 3 marbles. "
            "She collected 2 marbles. How many marbles does Alice have?"
        )
        r1 = parse_and_solve(text)
        r2 = parse_and_solve(text)
        assert r1.answer == r2.answer
        assert r1.reader_trace == r2.reader_trace


# ---------------------------------------------------------------------------
# 6. Trace event shape contract
# ---------------------------------------------------------------------------


class TestTraceEventShape:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_resolved_event_carries_evidence(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 marbles. Bob has 3 marbles. "
            "She collected 2 marbles. How many marbles does Alice have?"
        )
        r = parse_and_solve(text)
        contemplate_events = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "contemplate"
        ]
        resolved = next(
            (e for e in contemplate_events if e.get("outcome") == "resolved"),
            None,
        )
        assert resolved is not None
        # Required fields per the scope brief
        assert resolved["phase"] == 4
        assert resolved["source"] in {"vault", "pack", "audit_history"}
        assert "evidence" in resolved
        assert resolved["target_hypothesis_id"] in (0, 1)  # one of the two survivors


# ---------------------------------------------------------------------------
# 7. wrong=0 invariant + case 0050 canary
# ---------------------------------------------------------------------------


class TestWrongZeroPreservation:
    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_train_sample_wrong_is_zero(self) -> None:
        from pathlib import Path
        from evals.gsm8k_math.train_sample.v1.runner import (
            build_report, _CASES_PATH,
        )
        cases = [
            json.loads(l) for l in Path(_CASES_PATH).open() if l.strip()
        ]
        report = build_report(cases, use_reader=True)
        assert report["counts"]["wrong"] == 0

    @pytest.mark.skip(reason="Phase 4 not yet implemented")
    def test_case_0050_remains_refused(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Mark does a gig every other day for 2 weeks. "
            "He gets paid $50 per gig. He then gets a 50% raise. "
            "How much money does he make per week?"
        )
        r = parse_and_solve(text)
        assert r.answer is None

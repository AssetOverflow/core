"""ADR-0174 Phase 4 — in-loop contemplate acceptance tests.

Covers:
  1. contemplate() primitive — direct unit tests
  2. Resolution dataclass invariants
  3. Names pack + pronoun gender lookups
  4. Gendered-pronoun resolution (the load-bearing Phase 4a use case)
  5. End-to-end wiring through parse_and_solve — verifies the
     contemplate trace event fires when the recognizer-injection
     path encounters a multi-actor pronoun with disambiguating gender
     evidence
  6. Determinism — pure function contract
  7. Closed-set contract assertions
  8. wrong=0 invariant + case 0050 canary

Note on end-to-end answer correctness:
  Phase 4 wires contemplate into the recognizer-injection branch's
  multi-actor defense site. When the regex parser ALSO produces
  candidates for the same sentence (simpler shapes without intervening
  prepositional phrases), the regex-path candidates compete in the
  Cartesian product and the contemplate-resolved candidates may be
  shadowed. Phase 4 trace events fire correctly; full answer lift
  requires regex-path defense (Phase 5 regex retirement work).
  Tracked in project-adr-0174-multi-actor-pronoun-hazard memory.
"""

from __future__ import annotations

import json

import pytest

from generate.comprehension.contemplate import (
    Resolution,
    VALID_RESOLUTION_KINDS,
    VALID_RESOLUTION_SOURCES,
    _load_names_pack,
    _pronoun_required_gender,
    contemplate,
)
from generate.comprehension.state import (
    ComprehensionStateError,
    Hypothesis,
    ProblemReadingState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_state() -> ProblemReadingState:
    return ProblemReadingState(
        entity_registry=(), accumulated_initial_state=(),
        accumulated_operations=(), unknown_target_slot=None,
        pronoun_resolution_history=(), sentence_index=0,
        source_text_offset=0,
    )


def _residual_two(antecedents: tuple[str, str]) -> tuple[Hypothesis, ...]:
    return tuple(
        Hypothesis(
            candidate=(ant,),
            category_assignments=(),
            constraint_state=(),
            confidence_rank=i,
            unresolved=("actor_pronoun",),
        )
        for i, ant in enumerate(antecedents)
    )


# ---------------------------------------------------------------------------
# 1. contemplate() primitive contract
# ---------------------------------------------------------------------------


class TestContemplatePrimitive:
    def test_empty_residual_returns_none(self) -> None:
        assert contemplate(_stub_state(), residual=()) is None

    def test_single_survivor_returns_none(self) -> None:
        h = Hypothesis(
            candidate=("sentinel",), category_assignments=(),
            constraint_state=(), confidence_rank=0, unresolved=(),
        )
        assert contemplate(_stub_state(), residual=(h,)) is None

    def test_no_pronoun_hint_returns_none(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
        )
        assert r is None


# ---------------------------------------------------------------------------
# 2. Resolution dataclass invariants
# ---------------------------------------------------------------------------


class TestResolutionDataclass:
    def test_valid_resolution_constructs(self) -> None:
        r = Resolution(
            kind="eliminate", target_hypothesis_id=1,
            sub_question="which antecedent is female-gendered?",
            source="pack",
            evidence=(("en_core_names_v1", "Alice=female"),),
        )
        assert r.kind == "eliminate"
        assert r.source == "pack"

    def test_invalid_kind_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="kind"):
            Resolution(
                kind="guess",  # type: ignore[arg-type]
                target_hypothesis_id=0, sub_question="x",
                source="pack", evidence=(),
            )

    def test_invalid_source_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="source"):
            Resolution(
                kind="eliminate", target_hypothesis_id=0,
                sub_question="x",
                source="llm",  # type: ignore[arg-type]
                evidence=(),
            )

    def test_negative_target_id_refused(self) -> None:
        with pytest.raises(
            ComprehensionStateError, match="target_hypothesis_id"
        ):
            Resolution(
                kind="eliminate", target_hypothesis_id=-1,
                sub_question="x", source="pack", evidence=(),
            )

    def test_empty_sub_question_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="sub_question"):
            Resolution(
                kind="eliminate", target_hypothesis_id=0,
                sub_question="", source="pack", evidence=(),
            )

    def test_invalid_evidence_shape_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="evidence"):
            Resolution(
                kind="eliminate", target_hypothesis_id=0,
                sub_question="x", source="pack",
                evidence=(("only_one",),),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# 3. Names pack + pronoun gender lookups
# ---------------------------------------------------------------------------


class TestNamesPackLoad:
    def test_pack_loads_non_empty(self) -> None:
        pack = _load_names_pack()
        assert len(pack) >= 30
        assert pack.get("alice") == "female"
        assert pack.get("bob") == "male"
        assert pack.get("daniel") == "male"
        assert pack.get("malcolm") == "male"

    def test_unknown_name_returns_none(self) -> None:
        pack = _load_names_pack()
        assert pack.get("xqzqzy") is None


class TestPronounGenderLookup:
    def test_female_pronouns(self) -> None:
        assert _pronoun_required_gender("She") == "female"
        assert _pronoun_required_gender("her") == "female"
        assert _pronoun_required_gender("HERS") == "female"

    def test_male_pronouns(self) -> None:
        assert _pronoun_required_gender("He") == "male"
        assert _pronoun_required_gender("him") == "male"
        assert _pronoun_required_gender("HIS") == "male"

    def test_epicene_pronouns_return_none(self) -> None:
        """They/them/it are deliberately epicene — refusal-preferring."""
        assert _pronoun_required_gender("They") is None
        assert _pronoun_required_gender("them") is None
        assert _pronoun_required_gender("it") is None


# ---------------------------------------------------------------------------
# 4. Gendered-pronoun resolution — the load-bearing Phase 4a use case
# ---------------------------------------------------------------------------


class TestGenderedPronounResolution:
    def test_she_resolves_to_female_antecedent(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("Alice", "Bob"),
        )
        assert r is not None
        assert r.source == "pack"
        assert r.kind == "admit_unknown"
        chosen_facts = [
            f for _src, f in r.evidence if f.startswith("chosen=")
        ]
        assert len(chosen_facts) == 1
        assert chosen_facts[0] == "chosen=Alice"

    def test_he_resolves_to_male_antecedent(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="He",
            candidate_antecedents=("Alice", "Bob"),
        )
        assert r is not None
        chosen_facts = [
            f for _src, f in r.evidence if f.startswith("chosen=")
        ]
        assert chosen_facts[0] == "chosen=Bob"

    def test_same_gender_returns_none(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Mary")),
            pronoun_hint="She",
            candidate_antecedents=("Alice", "Mary"),
        )
        assert r is None

    def test_unknown_name_returns_none(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Xqzqzy", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("Xqzqzy", "Bob"),
        )
        assert r is None

    def test_epicene_pronoun_returns_none(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="They",
            candidate_antecedents=("Alice", "Bob"),
        )
        assert r is None

    def test_no_matching_gender_returns_none(self) -> None:
        r = contemplate(
            _stub_state(),
            residual=_residual_two(("John", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("John", "Bob"),
        )
        assert r is None


# ---------------------------------------------------------------------------
# 5. End-to-end wiring — trace event fires through parse_and_solve
# ---------------------------------------------------------------------------


class TestPhase4EndToEnd:
    def test_contemplate_trace_event_fires(self) -> None:
        """Verifies the contemplate resolved event appears in
        reader_trace when a multi-actor pronoun + gendered-name
        evidence is present AND the regex parser refuses the held
        sentence (multi-PP shape defeats regex)."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 100 followers. "
            "Bob has 50 followers. "
            "She has 5 followers on Instagram and 3 followers on Facebook. "
            "How many followers does Alice have?"
        )
        r = parse_and_solve(text)
        contemplate_events = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "contemplate"
        ]
        resolved = [
            e for e in contemplate_events if e.get("outcome") == "resolved"
        ]
        assert resolved, (
            f"expected contemplate resolved event; got events={contemplate_events}"
        )
        ev = resolved[0]
        assert ev["pronoun"] == "She"
        assert ev["resolved_to"] == "Alice"
        assert ev["source"] == "pack"
        assert ev["phase"] == 4


# ---------------------------------------------------------------------------
# 6. Determinism — pure function contract
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_calls_produce_identical_resolution(self) -> None:
        a = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("Alice", "Bob"),
        )
        b = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("Alice", "Bob"),
        )
        assert a == b

    def test_resolution_evidence_sorted_for_determinism(self) -> None:
        """Evidence is sorted (Alice before Bob) regardless of input
        order — canonical bytes / trace hash stay stable."""
        a = contemplate(
            _stub_state(),
            residual=_residual_two(("Alice", "Bob")),
            pronoun_hint="She",
            candidate_antecedents=("Alice", "Bob"),
        )
        b = contemplate(
            _stub_state(),
            residual=_residual_two(("Bob", "Alice")),
            pronoun_hint="She",
            candidate_antecedents=("Bob", "Alice"),
        )
        assert a is not None and b is not None
        # First two evidence entries (sorted antecedent name=gender pairs)
        # should be identical regardless of input order.
        assert a.evidence[0] == b.evidence[0]
        assert a.evidence[1] == b.evidence[1]


# ---------------------------------------------------------------------------
# 7. Closed-set contract assertions
# ---------------------------------------------------------------------------


class TestClosedSetContracts:
    def test_valid_resolution_kinds_membership(self) -> None:
        assert VALID_RESOLUTION_KINDS == frozenset(
            {"eliminate", "admit_unknown"}
        )

    def test_valid_resolution_sources_membership(self) -> None:
        assert VALID_RESOLUTION_SOURCES == frozenset(
            {"vault", "pack", "audit_history"}
        )


# ---------------------------------------------------------------------------
# 8. wrong=0 invariant + case 0050 canary
# ---------------------------------------------------------------------------


class TestWrongZeroPreservation:
    def test_train_sample_wrong_is_zero(self) -> None:
        from pathlib import Path
        from evals.gsm8k_math.train_sample.v1.runner import (
            build_report, _CASES_PATH,
        )
        cases = [
            json.loads(line) for line in Path(_CASES_PATH).open() if line.strip()
        ]
        report = build_report(cases)
        assert report["counts"]["wrong"] == 0

    def test_case_0050_remains_refused(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Mark does a gig every other day for 2 weeks. "
            "He gets paid $50 per gig. He then gets a 50% raise. "
            "How much money does he make per week?"
        )
        r = parse_and_solve(text)
        assert r.answer is None

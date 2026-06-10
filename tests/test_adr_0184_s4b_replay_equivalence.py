"""ADR-0184 S4b — the replay/provenance equivalence harness tests.

Three layers, each non-vacuous (CLAUDE.md "Schema-Defined Proof Obligations"):

1. **Corpus equivalence** — live canonical traces for the full GSM8K/derivation
   corpus must match the committed reference artifact byte-for-byte.  The
   reference pins behavior proven byte-equal to the pre-semantic-ledger legacy
   path by the #684/#685 cross-tree differentials, so this is NOT a
   self-comparison: the artifact is frozen evidence, the live run is the code
   under test.  Updating the artifact requires the explicit, reviewable
   ``scripts/verify_semantic_equivalence.py --update``.
2. **Authority preservation** — every live trace obeys the verifier/pool commit
   law re-derived from trace content, and every boundary candidate is the
   faithful in-order replay of its semantic world (provenance).
3. **Harness non-vacuity** — single-dimension perturbations (reorder, dropped
   duplicate, classification flip, authority bypass, unfaithful replay) must
   each be caught.  A harness that cannot fail proves nothing.
"""

from __future__ import annotations

import copy
from typing import Any

from evals.gsm8k_math.equivalence import trace as eq
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.model import (
    SemanticLedger,
    StateKey,
    StateTransition,
)
from generate.derivation.state.provenance import (
    faithfulness_violations,
    replay_is_faithful,
)
from generate.derivation.state.replay import replay_accumulation_ledger

_CLEAN_GAIN = "Sam has 14 apples. He buys 9 more apples. How many apples does Sam have?"
_DISTRACTOR_0014 = (
    "Kate has 20 pencils. She studies for 3 hours and then buys 5 more pencils. "
    "How many pencils does Kate have?"
)


class TestCorpusEquivalence:
    def test_live_traces_match_committed_reference(self) -> None:
        live = eq.corpus_traces()
        expected = eq.load_expected_traces()
        differences = eq.compare_traces(expected, live)
        assert not differences, (
            f"{len(differences)} drift(s) from the pinned reference — first five:\n  "
            + "\n  ".join(differences[:5])
            + "\nIf the change is intentional and reviewed, re-pin with "
            "`python scripts/verify_semantic_equivalence.py --update`."
        )
        assert eq.traces_sha(live) == eq.traces_sha(expected)

    def test_manifest_pins_the_committed_artifact(self) -> None:
        # A hand-edited artifact (without --update) must fail here even if the
        # live comparison happens to pass.
        expected = eq.load_expected_traces()
        manifest = eq.load_manifest()
        assert manifest["corpus_sha"] == eq.traces_sha(expected)
        assert manifest["problem_count"] == len(expected)

    def test_corpus_is_the_differential_corpus(self) -> None:
        # The #684/#685 cross-tree differentials covered exactly 937 unique
        # problems; a corpus change is a conscious re-pin, never silent.
        assert len(eq.corpus_problems()) == 937

    def test_wrapper_still_delegates_everywhere(self) -> None:
        assert all(trace["wrapper_equal"] for trace in eq.corpus_traces())


class TestAuthorityPreservation:
    """The verifier/pool commit law, re-derived from trace content, corpus-wide."""

    def test_no_live_trace_violates_the_commit_law(self) -> None:
        violations = [
            f"{trace['problem_sha'][:16]}: {violation}"
            for trace in eq.corpus_traces()
            for violation in eq.authority_violations(trace)
        ]
        assert not violations, "\n".join(violations[:5])

    def test_every_candidate_is_a_faithful_replay_of_its_world(self) -> None:
        reports = [
            f"{eq.problem_sha(text)[:16]}: {violation}"
            for text in eq.corpus_problems()
            for violation in eq.replay_faithfulness_report(text)
        ]
        assert not reports, "\n".join(reports[:5])


class TestHarnessNonVacuity:
    """Perturb exactly one dimension; the harness must catch it."""

    def _clean_trace(self) -> dict[str, Any]:
        trace = eq.problem_trace(_CLEAN_GAIN)
        # preconditions for the perturbations below
        assert len(trace["semantic"]) == 3 and trace["resolution"] is not None
        assert "complete" in trace["classifications"]
        return trace

    def test_reordered_candidates_fail(self) -> None:
        # Needs a pool with >= 2 DISTINCT readings, or reversal is a no-op —
        # the distractor problem pools the additive and product rivals.
        original = eq.problem_trace(_DISTRACTOR_0014)
        assert len({eq.trace_line(c) for c in original["pooled"]}) >= 2
        perturbed = copy.deepcopy(original)
        perturbed["pooled"] = list(reversed(perturbed["pooled"]))
        differences = eq.compare_traces([original], [perturbed])
        assert differences and "pooled" in differences[0]
        assert eq.traces_sha([perturbed]) != eq.traces_sha([original])

    def test_dropped_duplicate_fails(self) -> None:
        # The clean problem's three semantic readings coincide; dropping ONE
        # duplicate leaves values identical but multiplicity wrong — caught.
        original = self._clean_trace()
        perturbed = copy.deepcopy(original)
        del perturbed["semantic"][1]
        differences = eq.compare_traces([original], [perturbed])
        assert differences and "semantic" in differences[0]

    def test_flipped_classification_fails_both_nets(self) -> None:
        original = self._clean_trace()
        perturbed = copy.deepcopy(original)
        perturbed["classifications"] = [
            "exempt" if kind == "complete" else kind
            for kind in perturbed["classifications"]
        ]
        # snapshot net: the trace differs from the reference
        differences = eq.compare_traces([original], [perturbed])
        assert differences and "classifications" in differences[0]
        # authority net: a commit now stands with no complete reading -> bypass
        assert any(
            "authority bypassed" in violation
            for violation in eq.authority_violations(perturbed)
        )

    def test_injected_commit_on_refused_problem_is_detected(self) -> None:
        # Simulate a semantic-ledger path committing directly on a problem the
        # pool refuses (the distractor disagreement). The authority checker must
        # flag it without any reference artifact at all.
        trace = eq.problem_trace(_DISTRACTOR_0014)
        assert trace["resolution"] is None  # pool law: disagreement refuses
        tampered = copy.deepcopy(trace)
        tampered["resolution"] = {
            "answer": 25.0,
            "answer_unit": "pencils",
            "derivation": tampered["pooled"][0],
        }
        assert eq.authority_violations(tampered)

    def test_commit_from_empty_pool_is_detected(self) -> None:
        trace = {
            "problem_sha": "0" * 64,
            "pooled": [],
            "classifications": [],
            "resolution": {"answer": 1.0, "answer_unit": "", "derivation": {}},
        }
        violations = eq.authority_violations(trace)
        assert any("fail-closed" in violation for violation in violations)

    def test_refusal_is_always_lawful(self) -> None:
        # The checker is one-directional by design: it can never punish refusal.
        trace = eq.problem_trace(_DISTRACTOR_0014)
        assert trace["resolution"] is None
        assert eq.authority_violations(trace) == ()


def _clean_world_and_replay() -> tuple[SemanticLedger, GroundedDerivation]:
    ledger = build_accumulation_ledger(
        ["Sam has 14 apples.", "He buys 9 more apples.", "He eats 2 apples."],
        drop_isolated_foreign=False,
    )
    assert ledger is not None
    derivation = replay_accumulation_ledger(ledger)
    assert derivation is not None
    return ledger, derivation


class TestProvenanceCheckerNonVacuity:
    """`replay_is_faithful` must reject every single-mutation class."""

    def test_true_replay_is_faithful(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        assert replay_is_faithful(ledger, derivation)

    def test_mutated_step_op_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        steps = list(derivation.steps)
        steps[0] = Step(op="subtract", operand=steps[0].operand, cue=steps[0].cue)
        mutated = GroundedDerivation(start=derivation.start, steps=tuple(steps))
        assert not replay_is_faithful(ledger, mutated)

    def test_mutated_operand_value_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        steps = list(derivation.steps)
        steps[0] = Step(
            op=steps[0].op,
            operand=Quantity(99.0, steps[0].operand.unit, steps[0].operand.source_token),
            cue=steps[0].cue,
        )
        mutated = GroundedDerivation(start=derivation.start, steps=tuple(steps))
        assert not replay_is_faithful(ledger, mutated)

    def test_mutated_cue_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        steps = list(derivation.steps)
        steps[0] = Step(op=steps[0].op, operand=steps[0].operand, cue="invented")
        mutated = GroundedDerivation(start=derivation.start, steps=tuple(steps))
        assert not replay_is_faithful(ledger, mutated)

    def test_reordered_steps_fail(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        assert len(derivation.steps) == 2  # gain then loss
        mutated = GroundedDerivation(
            start=derivation.start, steps=tuple(reversed(derivation.steps))
        )
        assert not replay_is_faithful(ledger, mutated)

    def test_dropped_step_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        mutated = GroundedDerivation(start=derivation.start, steps=derivation.steps[:1])
        violations = faithfulness_violations(ledger, mutated)
        assert any("steps" in violation for violation in violations)

    def test_invented_step_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        extra = Step(op="add", operand=Quantity(1.0, "apples", "1"), cue="more")
        mutated = GroundedDerivation(
            start=derivation.start, steps=(*derivation.steps, extra)
        )
        assert not replay_is_faithful(ledger, mutated)

    def test_mutated_start_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        mutated = GroundedDerivation(
            start=Quantity(15.0, derivation.start.unit, derivation.start.source_token),
            steps=derivation.steps,
        )
        assert not replay_is_faithful(ledger, mutated)

    def test_comparative_step_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        steps = list(derivation.steps)
        steps[0] = Step(
            op=steps[0].op, operand=steps[0].operand, cue=steps[0].cue, comparative=True
        )
        mutated = GroundedDerivation(start=derivation.start, steps=tuple(steps))
        assert not replay_is_faithful(ledger, mutated)

    def test_broken_unit_inheritance_fails(self) -> None:
        # "9 more" inherits the anchor unit during replay; an operand that kept
        # its bare extracted unit would break classification downstream.
        ledger = build_accumulation_ledger(
            ["Sam has 14 apples.", "He buys 9 more."], drop_isolated_foreign=False
        )
        assert ledger is not None
        derivation = replay_accumulation_ledger(ledger)
        assert derivation is not None
        steps = list(derivation.steps)
        steps[0] = Step(
            op=steps[0].op,
            operand=Quantity(steps[0].operand.value, "", steps[0].operand.source_token),
            cue=steps[0].cue,
        )
        mutated = GroundedDerivation(start=derivation.start, steps=tuple(steps))
        violations = faithfulness_violations(ledger, mutated)
        assert any("anchor-inheritance" in violation for violation in violations)

    def test_cross_key_transition_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        key = ledger.transitions[0].key
        foreign = StateTransition(
            key=StateKey(entity="Tom", unit=key.unit),
            op="gain",
            quantity=ledger.transitions[1].quantity,
            cue=ledger.transitions[1].cue,
            clause_index=1,
        )
        mutated_ledger = SemanticLedger(
            transitions=(ledger.transitions[0], foreign, ledger.transitions[2])
        )
        assert not replay_is_faithful(mutated_ledger, derivation)

    def test_non_set_start_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        gain_only = SemanticLedger(transitions=ledger.transitions[1:])
        assert not replay_is_faithful(gain_only, derivation)

    def test_unknown_transition_op_fails(self) -> None:
        ledger, derivation = _clean_world_and_replay()
        # Closed-set bypass: an op outside gain/loss must be rejected by the
        # checker even if a future model widening admits it structurally.
        sample = ledger.transitions[1]
        widened = StateTransition(
            key=sample.key,
            op="set",  # a second SET mid-ledger is not a replayable change
            quantity=sample.quantity,
            cue=sample.cue,
            clause_index=sample.clause_index,
        )
        mutated_ledger = SemanticLedger(
            transitions=(ledger.transitions[0], widened, ledger.transitions[2])
        )
        violations = faithfulness_violations(mutated_ledger, derivation)
        assert any("not gain/loss" in violation for violation in violations)

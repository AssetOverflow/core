"""Doctrine tests for :class:`teaching.store.PackMutationProposal` (ADR-0051).

Pack mutations are proposal-only.  ADR-0027 and ADR-0033 state this as
policy; this test file pins it as a *type-level* invariant so any future
refactor that tries to make the proposal mutable, add a "permanent" flag,
or rename ``applied`` away from a default-False boolean breaks CI.
"""
from __future__ import annotations

import dataclasses

import pytest

from teaching.store import PackMutationProposal
from teaching.epistemic import EpistemicStatus
from teaching.source import ProposalSource


def _sample_proposal(**overrides: object) -> PackMutationProposal:
    defaults: dict[str, object] = {
        "proposal_id": "p_test_1",
        "candidate_id": "c_test_1",
        "subject": "memory",
        "correction_text": "memory is the storage of recalled experience",
        "prior_surface": "i do not know what memory means",
        "source": ProposalSource(
            kind="operator", source_id="", emitted_at_revision="test"
        ),
    }
    defaults.update(overrides)
    return PackMutationProposal(**defaults)  # type: ignore[arg-type]


def test_proposal_is_a_dataclass() -> None:
    assert dataclasses.is_dataclass(PackMutationProposal)


def test_proposal_is_frozen() -> None:
    """A frozen dataclass cannot be mutated in place — this is the
    type-level enforcement of proposal-only discipline."""
    proposal = _sample_proposal()
    with pytest.raises(dataclasses.FrozenInstanceError):
        proposal.applied = True  # type: ignore[misc]


def test_proposal_uses_slots() -> None:
    """``slots=True`` prevents callers from monkey-patching arbitrary
    attributes onto a proposal (e.g. ``proposal.bypass = True``)."""
    proposal = _sample_proposal()
    with pytest.raises((AttributeError, TypeError)):
        proposal.bypass = True  # type: ignore[attr-defined]


def test_applied_defaults_to_false() -> None:
    """Proposals start un-applied.  ADR-0027 § Teaching Safety: pack
    mutation is proposal-only until reviewed."""
    assert _sample_proposal().applied is False


def test_default_epistemic_status_is_speculative() -> None:
    """ADR-0021 § Schema impact pins SPECULATIVE as the only legal
    starting status."""
    assert _sample_proposal().epistemic_status == EpistemicStatus.SPECULATIVE


def test_with_status_returns_a_new_instance() -> None:
    """``with_status`` must be immutable-update, never in-place."""
    proposal = _sample_proposal()
    updated = proposal.with_status(EpistemicStatus.COHERENT)
    assert updated is not proposal
    assert proposal.epistemic_status == EpistemicStatus.SPECULATIVE
    assert updated.epistemic_status == EpistemicStatus.COHERENT


def test_no_forbidden_finality_flags_on_proposal() -> None:
    """ADR-0021 § non-hardening invariant: no ``final``, ``frozen``,
    ``axiom``, or ``permanent`` flag may exist on a proposal."""
    field_names = {f.name for f in dataclasses.fields(PackMutationProposal)}
    forbidden = {"final", "frozen", "axiom", "permanent", "immutable"}
    leaked = field_names & forbidden
    assert leaked == set(), f"forbidden finality flags on proposal: {leaked}"


def test_as_dict_round_trips_applied_and_status() -> None:
    proposal = _sample_proposal()
    d = proposal.as_dict()
    assert d["applied"] is False
    assert d["epistemic_status"] == EpistemicStatus.SPECULATIVE.value


def test_proposal_id_field_is_present() -> None:
    """The proposal must carry an opaque identifier so downstream review
    paths can refer to it without re-deriving the hash."""
    field_names = {f.name for f in dataclasses.fields(PackMutationProposal)}
    assert "proposal_id" in field_names

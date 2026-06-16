"""Default-dark FrameVerdict -> response-governance mapping (B4 PR-4).

The closed-world adapter is the ONLY lawful surface path for a FrameVerdict. It is
default-dark: the open-world ``govern_response`` / ``shape_surface`` STRICT path is
byte-identical (no existing file changed), a forged/untagged object cannot widen serving,
and the open-world renderer cannot render a FrameVerdict.
"""

from __future__ import annotations

import pytest

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.disposition import ServedDisposition
from core.epistemic_state import EpistemicState
from core.response_governance import ReachLevel, STRICT_POLICY, govern_response, shape_surface
from core.response_governance.frame_verdict import disposition_for_frame_verdict
from generate.frame_verdict import (
    ClosedFrame,
    FrameKind,
    FrameVerdictKind,
    WorldAssumption,
    evaluate_frame_verdict,
)


def _verdict(propositions, query, *, closure=True, kind=FrameKind.TEXT, wa=WorldAssumption.CLOSED):
    frame = ClosedFrame("f1", kind, wa, tuple(propositions), closure, "test", ())
    return evaluate_frame_verdict(frame, query)


# --------------------------------------------------------------------------- #
# Default-dark: the open-world strict path is untouched
# --------------------------------------------------------------------------- #


def test_strict_default_path_is_byte_identical() -> None:
    # govern_response still returns STRICT and shape_surface is the identity transform there —
    # the PR adds a NEW module and changes no existing governance file.
    assert govern_response().level is ReachLevel.STRICT
    assert (
        shape_surface(STRICT_POLICY, committed_surface="hello", decode_state=EpistemicState.DECODED)
        == "hello"
    )


# --------------------------------------------------------------------------- #
# Verdict -> disposition mapping (ADR §7)
# --------------------------------------------------------------------------- #


def test_entailed_true_commits_inferred_none() -> None:
    d = disposition_for_frame_verdict(_verdict(["a", "a -> b"], "b"))
    assert d.verdict is FrameVerdictKind.ENTAILED_TRUE
    assert d.served_disposition is ServedDisposition.COMMIT
    assert d.epistemic_state is EpistemicState.INFERRED
    assert d.disclosure_claim is DisclosureClaim.NONE
    assert d.surface == "Yes."


def test_entailed_false_commits_grounded_negative() -> None:
    d = disposition_for_frame_verdict(_verdict(["a", "a -> ~b"], "b"))
    assert d.verdict is FrameVerdictKind.ENTAILED_FALSE
    assert d.served_disposition is ServedDisposition.COMMIT  # a committed "No", not a block
    assert d.epistemic_state is EpistemicState.INFERRED
    assert d.disclosure_claim is DisclosureClaim.NONE
    assert d.surface == "No."


def test_contradiction_reports_not_no() -> None:
    d = disposition_for_frame_verdict(_verdict(["a", "~a"], "b"))
    assert d.verdict is FrameVerdictKind.CONTRADICTION
    assert d.served_disposition is ServedDisposition.REPORT
    assert d.surface != "No."  # the frame is inconsistent — not a grounded negative answer


def test_undetermined_does_not_commit() -> None:
    d = disposition_for_frame_verdict(_verdict(["a"], "b"))
    assert d.verdict is FrameVerdictKind.UNDETERMINED
    assert d.served_disposition is ServedDisposition.REFUSE
    assert d.served_disposition is not ServedDisposition.COMMIT


def test_scope_boundary_explains() -> None:
    d = disposition_for_frame_verdict(_verdict(["a", "a -> ~b"], "b", wa=WorldAssumption.OPEN))
    assert d.verdict is FrameVerdictKind.SCOPE_BOUNDARY
    assert d.served_disposition is ServedDisposition.EXPLAIN
    assert d.served_disposition is not ServedDisposition.COMMIT


def test_never_disclose_verified_by_default() -> None:
    # closed-world committed answers default to DisclosureClaim.NONE — never VERIFIED.
    for v in (_verdict(["a", "a -> b"], "b"), _verdict(["a", "a -> ~b"], "b")):
        d = disposition_for_frame_verdict(v)
        assert d.disclosure_claim is DisclosureClaim.NONE
        assert d.disclosure_claim is not DisclosureClaim.VERIFIED


# --------------------------------------------------------------------------- #
# Forged / untagged objects cannot widen serving; open-world renderer rejects FV
# --------------------------------------------------------------------------- #


def test_forged_dict_is_rejected() -> None:
    with pytest.raises(TypeError):
        disposition_for_frame_verdict({"verdict": "entailed_false"})  # type: ignore[arg-type]


def test_untagged_object_is_rejected() -> None:
    class _FakeVerdict:
        verdict = FrameVerdictKind.ENTAILED_FALSE

    with pytest.raises(TypeError):
        disposition_for_frame_verdict(_FakeVerdict())  # type: ignore[arg-type]


def test_open_world_renderer_cannot_render_a_frame_verdict() -> None:
    # the open-world render_determination expects a Determined; a FrameVerdict has no `answer`
    # / open-world fields, so it cannot be rendered as an open-world answer.
    from generate.determine.render import render_determination

    fv = _verdict(["a", "a -> ~b"], "b")
    with pytest.raises((AttributeError, TypeError)):
        render_determination(fv)  # type: ignore[arg-type]


def test_determine_still_has_no_answer_false() -> None:
    # belt-and-suspenders: the open-world gear still constructs only answer=True (INV-30
    # proves this exhaustively; here a quick smoke that a refusal stays a refusal).
    from generate.determine import Determined, Undetermined, determine
    from generate.frame_verdict import ClosedFrame as _CF

    frame = _CF("f", FrameKind.TEXT, WorldAssumption.CLOSED, ("a",), True, "t", ())
    res = determine(frame, None)  # type: ignore[arg-type]
    assert isinstance(res, Undetermined) and not isinstance(res, Determined)

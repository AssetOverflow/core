"""Wiring CMB (R4 combined-rate) into the multi-organ router + bounded contemplation (CMB-d).

Pins the integration matrix and the CMB-over-R3 domain-precedence rule:
  - supported CMB setup            -> SOLVED_VERIFIED (organ r4)
  - CMB solver boundary            -> REFUSED_KNOWN_BOUNDARY (no proposal)
  - CMB substantive reader refusal -> REFUSED_KNOWN_BOUNDARY (cmb_* family)
  - CMB deferred-capability refusal -> PROPOSAL_EMITTED (cmb_unsupported_*, owner r4, proposal-only)
  - cmb-11 (missing_second_rate)   -> R3's single-rate over-read is VETOED; REFUSED, never a wrong 12
  - cmb-15 (genuine single-rate)   -> CMB cedes (input_shape); R3 SOLVES 180
  - R1/R2/R3 gold unaffected; no gold routes ambiguous.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.comprehension_attempt import classify_cmb, cmb_reason, route_setup
from evals.combined_rate_oracle.runner import _load_combined_rate_gold
from evals.constraint_oracle.runner import _load_r2_gold
from evals.rate_oracle.runner import _load_rate_gold
from evals.setup_oracle.runner import _load_r1_gold
from generate.contemplation import Terminal, contemplate

_REFUSE_FAMILY = {  # CMB substantive reader refusals -> REFUSED_KNOWN_BOUNDARY via these families
    "rate_unit_mismatch": "cmb_unit_mismatch",
    "combine_mode_ambiguous": "cmb_combine_ambiguous",
    "missing_second_rate": "cmb_underdetermined",
}
_PROPOSAL_FAMILY = {  # CMB deferred-capability refusals -> PROPOSAL_EMITTED via these families
    "three_or_more_rates": "cmb_unsupported_rate_count",
    "reciprocal_work_rate_deferred": "cmb_unsupported_reciprocal",
    "clock_interval_deferred": "cmb_unsupported_clock_interval",
}


def _by_id(fid: str) -> dict:
    return next(f for f in _load_combined_rate_gold() if f["id"] == fid)


# --- classification + routing -------------------------------------------------------------- #


def test_classify_cmb_matches_gold_with_namespaced_reasons() -> None:
    for fx in _load_combined_rate_gold():
        att = classify_cmb(fx["text"], case_id=fx["id"])
        assert att.organ == "r4_combined_rate"
        if fx["expect"] in ("solved", "solver_refuses"):
            assert att.outcome == "setup_correct" and att.setup_signature is not None
        else:
            assert att.outcome == "setup_refused"
            assert att.refusal_reason == cmb_reason(fx["reader_reason"])


def test_router_routes_combined_to_cmb_vetoes_r3_overread_and_cedes_single_rate() -> None:
    routed_cmb = 0
    for fx in _load_combined_rate_gold():
        r = route_setup(fx["text"])
        assert len(r.attempts) == 4 and r.status != "ambiguous"
        if fx["expect"] in ("solved", "solver_refuses"):
            assert r.selected is not None and r.selected.organ == "r4_combined_rate", fx["id"]
            routed_cmb += 1
    assert routed_cmb == 11  # 6 solved + 5 solver_refuses
    # the veto: a missing-second-rate combined problem must NOT route to R3 (which would solve it wrong)
    assert route_setup(_by_id("cmb-11-missing-second-rate")["text"]).selected is None
    # the cede: a genuine single-rate problem CMB stepped aside on routes to R3
    assert route_setup(_by_id("cmb-15-not-combined-shaped")["text"]).selected.organ == "r3_rate"


def test_r1_r2_r3_gold_not_stolen_by_cmb_and_never_ambiguous() -> None:
    for fx in _load_r1_gold() + _load_r2_gold() + _load_rate_gold():
        r = route_setup(fx["text"])
        assert r.status != "ambiguous", fx.get("id")
        if r.selected is not None:
            assert r.selected.organ != "r4_combined_rate", fx.get("id")


# --- contemplation terminals --------------------------------------------------------------- #


def test_cmb_contemplation_terminal_matrix(tmp_path: Path) -> None:
    for fx in _load_combined_rate_gold():
        kw = {"options": fx["options"], "answer_key": fx["answer"]} if fx["expect"] == "solved" else {}
        r = contemplate(fx["text"], proposal_root=tmp_path, case_id=fx["id"], **kw)
        if fx["expect"] == "solved":
            assert r.terminal == Terminal.SOLVED_VERIFIED and r.selected_organ == "r4_combined_rate"
            assert r.answer == fx["gold"], fx["id"]
        elif fx["expect"] == "solver_refuses":
            assert r.terminal == Terminal.REFUSED_KNOWN_BOUNDARY and r.answer is None, fx["id"]
            expected = "cmb_non_positive_net" if fx["solver_reason"] == "non_positive_net_rate" else "cmb_non_integer"
            assert r.family == expected, fx["id"]
        else:
            reason = fx["reader_reason"]
            if reason in _REFUSE_FAMILY:
                assert r.terminal == Terminal.REFUSED_KNOWN_BOUNDARY and r.family == _REFUSE_FAMILY[reason], fx["id"]
                assert r.answer is None
            elif reason in _PROPOSAL_FAMILY:
                assert r.terminal == Terminal.PROPOSAL_EMITTED and r.family == _PROPOSAL_FAMILY[reason], fx["id"]


def test_cmb11_veto_yields_refusal_not_a_wrong_answer(tmp_path: Path) -> None:
    r = contemplate(_by_id("cmb-11-missing-second-rate")["text"], proposal_root=tmp_path)
    assert r.terminal == Terminal.REFUSED_KNOWN_BOUNDARY
    assert r.family == "cmb_underdetermined" and r.answer is None
    assert not list(tmp_path.glob("*.json"))  # an under-specified input is not a growth proposal


def test_cmb15_cedes_to_r3_which_solves_the_single_rate(tmp_path: Path) -> None:
    r = contemplate(_by_id("cmb-15-not-combined-shaped")["text"], proposal_root=tmp_path)
    assert r.terminal == Terminal.SOLVED_VERIFIED and r.selected_organ == "r3_rate" and r.answer == 180


def test_cmb_solver_boundaries_never_propose(tmp_path: Path) -> None:
    # non_positive_net_rate / non_integer_solution: prose understood, math outside v1 -> terminal
    # refusal, NEVER a growth proposal (protects against a future registry change).
    for fid in ("cmb-07-tank-non-positive-net", "cmb-08-paint-non-integer-time"):
        r = contemplate(_by_id(fid)["text"], proposal_root=tmp_path)
        assert r.terminal == Terminal.REFUSED_KNOWN_BOUNDARY and r.selected_organ == "r4_combined_rate"
    assert not list(tmp_path.glob("*.json"))


def test_cmb_deferred_capabilities_emit_cmb_owned_proposal_only_artifacts(tmp_path: Path) -> None:
    from core.comprehension_attempt import family_by_name

    for fid, family in (
        ("cmb-12-three-rates", "cmb_unsupported_rate_count"),
        ("cmb-13-reciprocal-work-rate", "cmb_unsupported_reciprocal"),
        ("cmb-14-clock-interval", "cmb_unsupported_clock_interval"),
    ):
        r = contemplate(_by_id(fid)["text"], proposal_root=tmp_path, case_id=fid)
        assert r.terminal == Terminal.PROPOSAL_EMITTED and r.family == family, fid
        fam = family_by_name(family)
        assert fam.owner == "r4" and fam.proposal_target == "cmb_gold_fixture" and not fam.must_remain_refused
        assert r.proposal_path is not None
        artifact = json.loads(Path(r.proposal_path).read_text())
        # proposal-only: never mounted, requires review (the N5 emitter contract).
        assert artifact.get("mounted") is False and artifact.get("requires_review") is True


def test_cmb_wiring_modules_are_off_serving() -> None:
    # classify_cmb + the contemplation pass that runs it must import no serving path — substring
    # scans false-negative on docstring mentions, so check actual imports via AST.
    import ast

    import core.comprehension_attempt.classify as classify_mod
    import generate.contemplation.pass_manager as pass_mod

    forbidden = ("generate.derivation", "core.reliability_gate")
    for mod in (classify_mod, pass_mod):
        for node in ast.walk(ast.parse(Path(str(mod.__file__)).read_text(encoding="utf-8"))):
            names = (
                [a.name for a in node.names] if isinstance(node, ast.Import)
                else [node.module or ""] if isinstance(node, ast.ImportFrom)
                else []
            )
            for name in names:
                assert not any(name.startswith(t) for t in forbidden), f"{mod.__name__} imports {name}"


def test_no_combined_rate_gold_routes_ambiguous() -> None:
    # AMBIGUOUS_ORGAN is a router invariant for two organs admitting with conflicting signatures. The
    # readers are mutually exclusive on shape (R3 refuses >=2 rates; CMB refuses <2), and signatures
    # are organ-tagged, so this never occurs naturally — proven here across the whole CMB corpus.
    for fx in _load_combined_rate_gold():
        assert route_setup(fx["text"]).status != "ambiguous", fx["id"]

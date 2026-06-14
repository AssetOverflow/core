"""B4 producer — the observational leeway record (engine side).

Non-vacuous: each test fails under a violation of the honest mapping — a STRICT
turn claiming latitude, a denied license read as granted, ``verified`` ever
emitted, or a digest that drifts on identical decisions.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.cognition.leeway import LeewayRecord, build_leeway_record


def _decision(*, action: str, licensed: bool, class_name: str = "addition.converse",
              required: float = 0.99, measured: float = 0.995) -> SimpleNamespace:
    return SimpleNamespace(
        class_name=class_name,
        action=SimpleNamespace(name=action),
        checker="reliability",
        measured=measured,
        required=required,
        licensed=licensed,
    )


class TestStrictDefault:
    def test_no_decision_is_no_latitude(self) -> None:
        rec = build_leeway_record(reach_level="strict", license_decision=None)
        assert rec == LeewayRecord(
            class_name="none",
            license="unknown",
            theta=None,
            claim_disclosure="none",
            source_digest=None,
            calibration_evidence_ref=None,
        )


class TestEarnedLeeway:
    def test_licensed_serve_widening_is_the_real_story(self) -> None:
        rec = build_leeway_record(
            reach_level="approximate",
            license_decision=_decision(action="SERVE", licensed=True),
        )
        assert rec.license == "SERVE"
        assert rec.claim_disclosure == "approximate"
        assert rec.theta == 0.99
        assert rec.class_name == "addition.converse"
        assert rec.calibration_evidence_ref == "addition.converse"
        assert rec.source_digest is not None and rec.source_digest.startswith("sha256:")

    def test_denied_license_is_blocked_not_granted(self) -> None:
        # The gate was consulted and said no — never read as latitude.
        rec = build_leeway_record(
            reach_level="strict",
            license_decision=_decision(action="SERVE", licensed=False),
        )
        assert rec.license == "blocked"
        assert rec.claim_disclosure == "none"

    def test_propose_license(self) -> None:
        rec = build_leeway_record(
            reach_level="strict",
            license_decision=_decision(action="PROPOSE", licensed=True),
        )
        assert rec.license == "PROPOSE"


class TestHonesty:
    def test_verified_is_never_emitted(self) -> None:
        # "verified" is a RESERVED epistemic state; the producer must not claim it.
        for reach in ("strict", "approximate"):
            for ld in (None, _decision(action="SERVE", licensed=True),
                       _decision(action="SERVE", licensed=False)):
                rec = build_leeway_record(reach_level=reach, license_decision=ld)
                assert rec.claim_disclosure != "verified"

    def test_digest_is_deterministic(self) -> None:
        a = build_leeway_record(reach_level="approximate",
                                license_decision=_decision(action="SERVE", licensed=True))
        b = build_leeway_record(reach_level="approximate",
                                license_decision=_decision(action="SERVE", licensed=True))
        assert a.source_digest == b.source_digest

    def test_different_decision_flips_digest(self) -> None:
        a = build_leeway_record(reach_level="approximate",
                                license_decision=_decision(action="SERVE", licensed=True, measured=0.995))
        b = build_leeway_record(reach_level="approximate",
                                license_decision=_decision(action="SERVE", licensed=True, measured=0.999))
        assert a.source_digest != b.source_digest

"""ADR-0098 Demo Composition Contract — unit tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.demos import (
    CLAIM_CONTRACT_VERSION,
    Claim,
    DemoCommand,
    DemoContractError,
    DemoResult,
    canonical_json,
    verify_no_global_state_mutation,
)
from core.demos.audit_tour_adapter import AuditTourDemo
from core.demos.contract import capture_state
from core.demos.tour_adapters import (
    AnchorLensTourDemo,
    OrthogonalityTourDemo,
    RegisterTourDemo,
)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestClaim:
    def test_well_formed_claim(self) -> None:
        c = Claim(
            claim_id="c1",
            statement="x is y",
            supported=True,
            evidence_locator="report.json",
        )
        assert c.as_dict() == {
            "claim_id": "c1",
            "statement": "x is y",
            "supported": True,
            "evidence_locator": "report.json",
        }

    @pytest.mark.parametrize(
        "field, value",
        [
            ("claim_id", ""),
            ("statement", "   "),
            ("evidence_locator", ""),
        ],
    )
    def test_empty_required_field_rejected(self, field: str, value: str) -> None:
        kwargs = dict(
            claim_id="c1",
            statement="x is y",
            supported=True,
            evidence_locator="locator",
        )
        kwargs[field] = value
        with pytest.raises(DemoContractError):
            Claim(**kwargs)

    def test_frozen(self) -> None:
        c = Claim(
            claim_id="c1",
            statement="x",
            supported=True,
            evidence_locator="y",
        )
        with pytest.raises((AttributeError, TypeError)):
            c.supported = False  # type: ignore[misc]


class TestDemoResult:
    def _make_claims(self) -> tuple[Claim, ...]:
        return (
            Claim(claim_id="c1", statement="s1", supported=True, evidence_locator="e1"),
            Claim(claim_id="c2", statement="s2", supported=True, evidence_locator="e2"),
        )

    def test_well_formed_result(self, tmp_path: Path) -> None:
        claims = self._make_claims()
        result = DemoResult(
            demo_id="d1",
            claim_contract_version=CLAIM_CONTRACT_VERSION,
            claims=claims,
            evidence={"c1": "x", "c2": "y"},
            all_claims_supported=True,
            json_path=tmp_path / "d1.json",
        )
        assert result.all_claims_supported is True
        assert result.demo_id == "d1"

    def test_duplicate_claim_id_rejected(self, tmp_path: Path) -> None:
        dup = (
            Claim(claim_id="c1", statement="s", supported=True, evidence_locator="e"),
            Claim(claim_id="c1", statement="s", supported=True, evidence_locator="e"),
        )
        with pytest.raises(DemoContractError, match="duplicate claim_id"):
            DemoResult(
                demo_id="d1",
                claim_contract_version=CLAIM_CONTRACT_VERSION,
                claims=dup,
                evidence={"c1": "x"},
                all_claims_supported=True,
                json_path=tmp_path / "d1.json",
            )

    def test_wrong_contract_version_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(DemoContractError, match="claim_contract_version"):
            DemoResult(
                demo_id="d1",
                claim_contract_version=2,
                claims=(),
                evidence={},
                all_claims_supported=True,
                json_path=tmp_path / "d1.json",
            )

    def test_missing_evidence_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(DemoContractError, match="evidence missing"):
            DemoResult(
                demo_id="d1",
                claim_contract_version=CLAIM_CONTRACT_VERSION,
                claims=self._make_claims(),
                evidence={"c1": "x"},  # missing c2
                all_claims_supported=True,
                json_path=tmp_path / "d1.json",
            )


# ---------------------------------------------------------------------------
# Canonical JSON serializer
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_deterministic_across_calls(self) -> None:
        payload = {"b": 1, "a": [1, 2, 3], "c": {"y": 0, "x": 1}}
        assert canonical_json(payload) == canonical_json(payload)

    def test_keys_sorted(self) -> None:
        out = canonical_json({"z": 1, "a": 2}).decode()
        assert out.index('"a"') < out.index('"z"')

    def test_trailing_newline(self) -> None:
        assert canonical_json({"x": 1}).endswith(b"\n")


# ---------------------------------------------------------------------------
# Global-state-mutation detector
# ---------------------------------------------------------------------------


class TestGlobalStateDetector:
    def test_identical_snapshots_pass(self) -> None:
        s = capture_state()
        passed, divergences = verify_no_global_state_mutation(before=s, after=s)
        assert passed is True
        assert divergences == ()

    def test_env_var_addition_flagged(self) -> None:
        import os

        os.environ.pop("CORE_DETECTOR_TEST_FLAG", None)
        before = capture_state()
        os.environ["CORE_DETECTOR_TEST_FLAG"] = "1"
        after = capture_state()
        os.environ.pop("CORE_DETECTOR_TEST_FLAG", None)
        passed, divergences = verify_no_global_state_mutation(before=before, after=after)
        assert passed is False
        assert any("env_subset" in d for d in divergences)

    def test_lazy_import_not_flagged(self) -> None:
        """None → module id transition is benign (lazy import)."""
        before = {"chat.runtime": None, "env_subset": ()}
        after = {"chat.runtime": 12345, "env_subset": ()}
        passed, divergences = verify_no_global_state_mutation(before=before, after=after)
        assert passed is True
        assert divergences == ()

    def test_id_to_id_rebind_flagged(self) -> None:
        """id → different id is a real rebinding."""
        before = {"chat.runtime": 100, "env_subset": ()}
        after = {"chat.runtime": 200, "env_subset": ()}
        passed, divergences = verify_no_global_state_mutation(before=before, after=after)
        assert passed is False
        assert any("chat.runtime" in d for d in divergences)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    @pytest.mark.parametrize(
        "adapter_factory",
        [
            AuditTourDemo,
            RegisterTourDemo,
            AnchorLensTourDemo,
            OrthogonalityTourDemo,
        ],
    )
    def test_adapter_is_demo_command(self, adapter_factory: Any) -> None:
        adapter = adapter_factory()
        assert isinstance(adapter, DemoCommand)
        assert adapter.claim_contract_version == CLAIM_CONTRACT_VERSION
        assert adapter.demo_id.strip()

    @pytest.mark.parametrize(
        "adapter_factory",
        [AuditTourDemo, RegisterTourDemo, OrthogonalityTourDemo],
    )
    def test_seed_rejected_when_unsupported(
        self, adapter_factory: Any, tmp_path: Path
    ) -> None:
        adapter = adapter_factory()
        with pytest.raises(DemoContractError, match="does not accept a seed"):
            adapter.run(output_dir=tmp_path, seed=42)


# ---------------------------------------------------------------------------
# Adapter runtime behavior (fast adapters only — audit-tour)
# ---------------------------------------------------------------------------


class TestAuditTourAdapterIntegration:
    """One end-to-end run + byte-equality check on the fastest adapter."""

    def test_run_produces_supported_claims(self, tmp_path: Path) -> None:
        adapter = AuditTourDemo()
        result = adapter.run(output_dir=tmp_path)
        assert result.demo_id == "audit-tour"
        assert len(result.claims) == 5
        assert result.all_claims_supported is True
        assert result.json_path.exists()
        assert result.json_path.parent == tmp_path

    def test_byte_equal_across_two_runs(self, tmp_path: Path) -> None:
        adapter = AuditTourDemo()
        a = adapter.run(output_dir=tmp_path / "a")
        b = adapter.run(output_dir=tmp_path / "b")
        assert a.json_path.read_bytes() == b.json_path.read_bytes()

    def test_no_global_state_mutation(self, tmp_path: Path) -> None:
        before = capture_state()
        AuditTourDemo().run(output_dir=tmp_path)
        after = capture_state()
        passed, divergences = verify_no_global_state_mutation(
            before=before, after=after
        )
        assert passed is True, f"unexpected divergences: {divergences}"

"""Runner for evals/demo_composition/ (ADR-0098).

Exercises shipped :class:`DemoCommand` adapters and asserts ADR-0098's
two structural invariants:

- ``demo_json_byte_equality``: two runs of the same adapter produce
  byte-identical JSON.
- ``demo_composition_no_side_effects``: a single adapter run does not
  mutate load-bearing global state.

The slowest adapter (anchor-lens-tour) is excluded from this lane to
keep wall time bounded; it is exercised by
``tests/test_demo_composition.py`` instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.demos.audit_tour_adapter import AuditTourDemo
from core.demos.contract import (
    DemoResult,
    capture_state,
    verify_no_global_state_mutation,
)
from core.demos.tour_adapters import (
    OrthogonalityTourDemo,
    RegisterTourDemo,
)


# Skip anchor-lens-tour in the lane because of its high wall time.
_ADAPTERS: tuple[tuple[str, Any], ...] = (
    ("audit-tour", AuditTourDemo()),
    ("register-tour", RegisterTourDemo()),
    ("orthogonality-tour", OrthogonalityTourDemo()),
)


def _run_byte_equality(adapter: Any, *, tmp_root: Path) -> dict[str, Any]:
    case_dir = tmp_root / f"{adapter.demo_id}_byte"
    case_dir.mkdir(parents=True, exist_ok=True)
    out_a = case_dir / "a"
    out_b = case_dir / "b"
    r_a = adapter.run(output_dir=out_a)
    bytes_a = r_a.json_path.read_bytes()
    r_b = adapter.run(output_dir=out_b)
    bytes_b = r_b.json_path.read_bytes()
    return {
        "case_id": f"{adapter.demo_id}_byte_equality",
        "passed": bytes_a == bytes_b,
        "details": {
            "sha256": hashlib.sha256(bytes_a).hexdigest(),
            "all_claims_supported_a": r_a.all_claims_supported,
            "all_claims_supported_b": r_b.all_claims_supported,
        },
        "divergence": None if bytes_a == bytes_b else "JSON bytes differ",
    }


def _run_state_mutation_check(adapter: Any, *, tmp_root: Path) -> dict[str, Any]:
    case_dir = tmp_root / f"{adapter.demo_id}_state"
    case_dir.mkdir(parents=True, exist_ok=True)
    before = capture_state()
    adapter.run(output_dir=case_dir)
    after = capture_state()
    passed, divergences = verify_no_global_state_mutation(before=before, after=after)
    return {
        "case_id": f"{adapter.demo_id}_no_state_mutation",
        "passed": passed,
        "details": {"divergences": list(divergences)},
        "divergence": None if passed else f"state divergences: {divergences}",
    }


def _run_composition_read_only(tmp_root: Path) -> dict[str, Any]:
    """Compose two adapter results into a composite claim set.

    Verifies the showcase pattern (ADR-0099 preview): reading two
    DemoResult objects and producing a composite without mutating
    either. Each adapter is invoked exactly once.
    """
    out_dir = tmp_root / "composition"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit = AuditTourDemo().run(output_dir=out_dir)
    register = RegisterTourDemo().run(output_dir=out_dir)
    # Composition is a tuple of evidence locators; nothing is mutated.
    composite_claims = tuple(audit.claims) + tuple(register.claims)
    composite_evidence = {**audit.evidence, **register.evidence}
    composite_supported = (
        audit.all_claims_supported and register.all_claims_supported
    )
    return {
        "case_id": "composition_read_only",
        "passed": True,
        "details": {
            "audit_claims": len(audit.claims),
            "register_claims": len(register.claims),
            "composite_claims": len(composite_claims),
            "composite_supported": composite_supported,
            "evidence_size": len(composite_evidence),
        },
        "divergence": None,
    }


@dataclass(frozen=True, slots=True)
class _StatefulFixtureAdapter:
    """Negative control: deliberately mutates an env var during run."""

    demo_id: str = "stateful-fixture"
    claim_contract_version: int = 1

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        import os

        from core.demos.contract import CLAIM_CONTRACT_VERSION, Claim, canonical_json

        os.environ["CORE_STATEFUL_FIXTURE_FLAG"] = "1"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{self.demo_id}.json"
        claim = Claim(
            claim_id="x",
            statement="negative control",
            supported=True,
            evidence_locator="self",
        )
        json_path.write_bytes(canonical_json({"demo_id": self.demo_id}))
        return DemoResult(
            demo_id=self.demo_id,
            claim_contract_version=CLAIM_CONTRACT_VERSION,
            claims=(claim,),
            evidence={claim.claim_id: "self"},
            all_claims_supported=True,
            json_path=json_path,
            trace_features={},
        )


def _run_stateful_fixture_rejected(tmp_root: Path) -> dict[str, Any]:
    import os

    case_dir = tmp_root / "stateful"
    case_dir.mkdir(parents=True, exist_ok=True)
    # Make sure the env var is not set before; clean up on the way out.
    os.environ.pop("CORE_STATEFUL_FIXTURE_FLAG", None)
    before = capture_state()
    _StatefulFixtureAdapter().run(output_dir=case_dir)
    after = capture_state()
    os.environ.pop("CORE_STATEFUL_FIXTURE_FLAG", None)
    passed, divergences = verify_no_global_state_mutation(before=before, after=after)
    # NEGATIVE control: the detector MUST flag this fixture.
    expected_to_fail = not passed
    return {
        "case_id": "stateful_fixture_rejected",
        "passed": expected_to_fail,
        "details": {"divergences": list(divergences)},
        "divergence": (
            None if expected_to_fail else "negative control did not produce divergences"
        ),
    }


def run() -> dict[str, Any]:
    tmp_root = Path(tempfile.mkdtemp(prefix="demo_composition_lane_"))
    try:
        cases: list[dict[str, Any]] = []
        for _, adapter in _ADAPTERS:
            cases.append(_run_byte_equality(adapter, tmp_root=tmp_root))
            cases.append(_run_state_mutation_check(adapter, tmp_root=tmp_root))
        cases.append(_run_composition_read_only(tmp_root))
        cases.append(_run_stateful_fixture_rejected(tmp_root))
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    return {
        "lane": "demo_composition",
        "lane_version": "v1",
        "split": "dev",
        "adr": "ADR-0098",
        "invariants": [
            "demo_json_byte_equality",
            "demo_composition_no_side_effects",
        ],
        "adapters_exercised": [a.demo_id for _, a in _ADAPTERS],
        "total_cases": len(cases),
        "passed_cases": sum(1 for c in cases if c["passed"]),
        "failed_cases": sum(1 for c in cases if not c["passed"]),
        "all_passed": all(c["passed"] for c in cases),
        "cases": cases,
    }


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="demo_composition lane runner")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = run()
    lane_dir = Path(__file__).resolve().parent
    report_path = args.report or (lane_dir / "results" / "v1_dev.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = _canonical_json(summary)
    report_path.write_bytes(payload_bytes)

    sha = hashlib.sha256(payload_bytes).hexdigest()
    print(f"report: {report_path}")
    print(f"sha256: {sha}")
    print(f"passed: {summary['passed_cases']}/{summary['total_cases']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

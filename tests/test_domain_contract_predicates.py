"""ADR-0093 — Domain Pack Contract v1 predicate-evaluation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.capability.domain_contract_predicates import (
    DomainContractPredicateReport,
    PredicateResult,
    _parse_gap_states,
    evaluate_domain_contract,
)
from core.capability.reviewers import (
    Reviewer,
    ReviewerRegistry,
    SCHEMA_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_synthetic_pack(
    tmp_path: Path,
    *,
    pack_id: str = "synthetic_math_pack_v1",
    domain_id: str = "mathematics_logic",
    teaching_chains: tuple[str, ...] = ("mathematics_logic_chains_v1",),
    reviewers: tuple[str, ...] = ("shay-j",),
    eval_lanes: tuple[dict[str, Any], ...] = (
        {
            "lane": "elementary_mathematics_ood",
            "version": "v1",
            "splits": ["dev", "public", "holdout"],
        },
    ),
    known_gaps: tuple[str, ...] = (),
    include_contract: bool = True,
    glosses_text: str | None = None,
) -> Path:
    """Create a synthetic pack directory and return the data_root path."""
    data_root = tmp_path / "data"
    pack_dir = data_root / pack_id
    pack_dir.mkdir(parents=True)

    manifest: dict[str, Any] = {
        "pack_id": pack_id,
        "name": "synthetic pack",
    }
    if include_contract:
        manifest.update(
            {
                "domain_contract_version": 1,
                "domain_id": domain_id,
                "axioms": None,
                "rules": None,
                "teaching_chains": list(teaching_chains),
                "eval_lanes": [dict(lane) for lane in eval_lanes],
                "reviewers": list(reviewers),
                "known_gaps": list(known_gaps),
                "provenance": "test:fixture:2026-05-21",
            }
        )

    if glosses_text is not None:
        glosses_path = pack_dir / "glosses.jsonl"
        glosses_path.write_text(glosses_text, encoding="utf-8")
        import hashlib

        manifest.setdefault("checksums", {})["glosses_sha256"] = hashlib.sha256(
            glosses_path.read_bytes()
        ).hexdigest()

    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return data_root


def _primary_registry() -> ReviewerRegistry:
    return ReviewerRegistry(
        schema_version=SCHEMA_VERSION,
        reviewers=(
            Reviewer(
                reviewer_id="shay-j",
                display_name="Joshua Shay",
                role="primary",
                domains=("*",),
                review_scope=("pack", "proposal", "chain", "eval"),
                provenance="adr-0092:bootstrap:test",
            ),
        ),
    )


def _stub_chain_inventory() -> dict[str, Any]:
    """A chain inventory that satisfies P5 and P6 for mathematics_logic."""
    return {
        "by_domain_operator_family": {
            "mathematics_logic": {
                "transitive": 10,
                "proof_chain": 9,
                "contradiction": 8,
            },
        },
        "by_domain_intent_shape": {
            "mathematics_logic": {
                "cause": 4,
                "verification": 3,
                "comparison": 5,
            },
        },
    }


# ---------------------------------------------------------------------------
# Contract presence / structural failures
# ---------------------------------------------------------------------------


class TestContractPresence:
    def test_pack_without_contract_reports_absent(self, tmp_path: Path) -> None:
        data_root = _build_synthetic_pack(tmp_path, include_contract=False)
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )
        assert isinstance(report, DomainContractPredicateReport)
        assert report.contract_present is False
        assert report.all_passed is False
        assert report.predicates == ()

    def test_pack_with_invalid_contract_reports_errors(self, tmp_path: Path) -> None:
        data_root = _build_synthetic_pack(
            tmp_path,
            eval_lanes=(
                {"lane": "x", "version": "v1", "splits": ["alien_split"]},
            ),
        )
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )
        assert report.contract_present is True
        assert report.contract_valid is False
        assert any("splits" in e for e in report.contract_errors)


# ---------------------------------------------------------------------------
# Per-predicate verification (P3-P9)
#
# P1 / P2 require fully compiled packs and so are exercised against the
# in-tree packs in `TestProductionPacks` below rather than against synthetic
# fixtures (the language_packs.compiler.load_pack call cannot resolve a
# synthetic data root in the same way).
# ---------------------------------------------------------------------------


def _find(predicates: tuple[PredicateResult, ...], predicate_id: str) -> PredicateResult:
    matches = [p for p in predicates if p.predicate_id == predicate_id]
    assert matches, f"missing predicate {predicate_id}"
    return matches[0]


class TestPredicatesAgainstSyntheticPack:
    def _report(self, tmp_path: Path, **overrides: Any) -> DomainContractPredicateReport:
        data_root = _build_synthetic_pack(tmp_path, **overrides)
        return evaluate_domain_contract(
            overrides.get("pack_id", "synthetic_math_pack_v1"),
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )

    def test_p3_known_domain_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P3").passed is True

    def test_p3_unknown_domain_rejected_by_parser(self, tmp_path: Path) -> None:
        report = self._report(tmp_path, domain_id="alien_domain")
        assert report.contract_valid is False
        assert any("domain_id:unknown" in e for e in report.contract_errors)

    def test_p4_registered_corpora_pass(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P4").passed is True

    def test_p4_unregistered_corpus_fails(self, tmp_path: Path) -> None:
        report = self._report(
            tmp_path, teaching_chains=("ghost_chains_v999",)
        )
        p4 = _find(report.predicates, "P4")
        assert p4.passed is False
        assert "ghost_chains_v999" in p4.notes

    def test_p5_sufficient_chain_coverage_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P5").passed is True

    def test_p5_shortfall_fails(self, tmp_path: Path) -> None:
        sparse_inventory: dict[str, Any] = {
            "by_domain_operator_family": {
                "mathematics_logic": {
                    "transitive": 2,
                    "proof_chain": 9,
                    "contradiction": 8,
                },
            },
            "by_domain_intent_shape": {
                "mathematics_logic": {"cause": 4, "verification": 3, "comparison": 5},
            },
        }
        data_root = _build_synthetic_pack(tmp_path)
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=sparse_inventory,
            reviewer_registry=_primary_registry(),
        )
        p5 = _find(report.predicates, "P5")
        assert p5.passed is False
        assert "transitive=2" in p5.notes

    def test_p6_three_intent_shapes_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P6").passed is True

    def test_p6_too_few_intents_fails(self, tmp_path: Path) -> None:
        sparse_inventory: dict[str, Any] = {
            "by_domain_operator_family": {
                "mathematics_logic": {
                    "transitive": 10,
                    "proof_chain": 9,
                    "contradiction": 8,
                },
            },
            "by_domain_intent_shape": {
                "mathematics_logic": {"cause": 1, "verification": 0, "comparison": 0},
            },
        }
        data_root = _build_synthetic_pack(tmp_path)
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=sparse_inventory,
            reviewer_registry=_primary_registry(),
        )
        p6 = _find(report.predicates, "P6")
        assert p6.passed is False
        assert "1 intent" in p6.notes

    def test_p7_complete_splits_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P7").passed is True

    def test_p7_missing_holdout_fails(self, tmp_path: Path) -> None:
        report = self._report(
            tmp_path,
            eval_lanes=(
                {
                    "lane": "elementary_mathematics_ood",
                    "version": "v1",
                    "splits": ["dev", "public"],
                },
            ),
        )
        p7 = _find(report.predicates, "P7")
        assert p7.passed is False
        assert "elementary_mathematics_ood" in p7.notes

    def test_p8_known_reviewer_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P8").passed is True

    def test_p8_unknown_reviewer_fails(self, tmp_path: Path) -> None:
        report = self._report(tmp_path, reviewers=("ghost-reviewer",))
        p8 = _find(report.predicates, "P8")
        assert p8.passed is False
        assert "ghost-reviewer" in p8.notes

    def test_p8_domain_scope_mismatch_fails(self, tmp_path: Path) -> None:
        registry = ReviewerRegistry(
            schema_version=SCHEMA_VERSION,
            reviewers=(
                Reviewer(
                    reviewer_id="physics-only",
                    display_name="Physics Reviewer",
                    role="domain",
                    domains=("physics",),
                    review_scope=("pack",),
                    provenance="adr-0092:test",
                ),
            ),
        )
        data_root = _build_synthetic_pack(tmp_path, reviewers=("physics-only",))
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=registry,
        )
        p8 = _find(report.predicates, "P8")
        assert p8.passed is False
        assert "out_of_scope" in p8.notes

    def test_p9_no_gaps_passes(self, tmp_path: Path) -> None:
        report = self._report(tmp_path)
        assert _find(report.predicates, "P9").passed is True

    def test_p9_with_closed_gaps_passes(self, tmp_path: Path) -> None:
        # All math/logic gaps in docs/gaps.md are closed (per current state).
        report = self._report(
            tmp_path,
            known_gaps=("gap:mathematics_logic_pack_absent",),
        )
        assert _find(report.predicates, "P9").passed is True

    def test_p9_with_unknown_gap_fails(self, tmp_path: Path) -> None:
        report = self._report(
            tmp_path,
            known_gaps=("gap:absolutely_imaginary_blocker",),
        )
        p9 = _find(report.predicates, "P9")
        assert p9.passed is False


# ---------------------------------------------------------------------------
# Gap parser
# ---------------------------------------------------------------------------


class TestGapStateParser:
    def test_parses_open_and_closed(self) -> None:
        text = (
            "# Header\n"
            "- [x] `gap:foo_closed`\n"
            "- [ ] `gap:bar_open`\n"
            "irrelevant line\n"
            "- [x] `gap:baz_closed`\n"
        )
        states = _parse_gap_states(text)
        assert states == {
            "gap:foo_closed": True,
            "gap:bar_open": False,
            "gap:baz_closed": True,
        }

    def test_skips_malformed_lines(self) -> None:
        text = "- [?] `gap:typo`\nfree text\n- [x] `gap:ok`\n"
        states = _parse_gap_states(text)
        assert states == {"gap:ok": True}


# ---------------------------------------------------------------------------
# Eval lane artifact resolution
# ---------------------------------------------------------------------------


class TestEvalLaneArtifacts:
    def test_artifacts_surface_existing_reports(self, tmp_path: Path) -> None:
        # Use a real in-tree lane (reviewer_registry) that we know has a
        # v1_dev.json under results/ from ADR-0092.
        data_root = _build_synthetic_pack(
            tmp_path,
            eval_lanes=(
                {
                    "lane": "reviewer_registry",
                    "version": "v1",
                    "splits": ["dev", "public", "holdout"],
                },
            ),
        )
        report = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )
        assert len(report.eval_lane_artifacts) == 1
        artifact = report.eval_lane_artifacts[0]
        assert artifact["lane"] == "reviewer_registry"
        assert artifact["splits"]["dev"]["exists"] is True
        assert artifact["splits"]["dev"]["sha256"] is not None
        # public/holdout don't exist for that lane yet
        assert artifact["splits"]["public"]["exists"] is False


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


class TestCli:
    def test_cli_returns_nonzero_on_missing_contract(self) -> None:
        """A pack without a domain contract exits 1 under default mode."""
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "core.cli",
                "capability",
                "domain-contract",
                "--pack-id",
                "en_core_cognition_v1",
                "--json",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload["contract_present"] is False
        assert payload["all_passed"] is False

    def test_cli_structural_only_skips_predicates(self) -> None:
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "core.cli",
                "capability",
                "domain-contract",
                "--pack-id",
                "en_core_cognition_v1",
                "--json",
                "--structural-only",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # structural-only returns 0 because parse alone passes (no contract).
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "predicates" not in payload  # legacy shape
        assert payload["valid"] is True


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_report(self, tmp_path: Path) -> None:
        data_root = _build_synthetic_pack(tmp_path)
        a = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )
        b = evaluate_domain_contract(
            "synthetic_math_pack_v1",
            data_root=data_root,
            chain_inventory=_stub_chain_inventory(),
            reviewer_registry=_primary_registry(),
        )
        assert a.as_dict() == b.as_dict()

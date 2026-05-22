"""ADR-0112 — Runnable Expert-Demo Showcase invariants.

Pins six load-bearing invariants:

1. Building an expert-demo for a promoted domain (`mathematics_logic`,
   `physics`) succeeds and reports ``all_claims_supported=True``.

2. The recomputed digest matches the signed ``claim_digest`` byte-for-byte.

3. The composer refuses an unpromoted domain (no signed claim).

4. Output JSON is byte-identical across two consecutive runs (same
   on-disk lane result files → same showcase bytes).

5. Per-lane shape-check verdicts are present for every attached lane on
   both public and holdout splits.

6. The showcase does not mutate any source artifact (lane result files,
   reviewers.yaml).
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from core.demos.expert_demo import (
    SAMPLE_CASES_PER_SPLIT,
    build_expert_demo,
    run_expert_demo,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


_PROMOTED_DOMAINS = ("mathematics_logic", "physics")


@pytest.mark.parametrize("domain_id", _PROMOTED_DOMAINS)
class TestPromotedDomainsBuildSuccessfully:
    def test_build_returns_all_claims_supported(self, domain_id: str) -> None:
        payload = build_expert_demo(domain_id)
        assert payload["all_claims_supported"] is True
        assert payload["all_lanes_pass"] is True
        assert payload["all_digests_match"] is True

    def test_derived_digest_matches_signed(self, domain_id: str) -> None:
        payload = build_expert_demo(domain_id)
        dv = payload["digest_verification"]
        assert dv["matches"] is True
        assert dv["derived"] == dv["signed"]
        # 64-char lowercase hex (SHA-256)
        assert len(dv["signed"]) == 64
        assert all(c in "0123456789abcdef" for c in dv["signed"])

    def test_every_lane_split_has_shape_check(self, domain_id: str) -> None:
        payload = build_expert_demo(domain_id)
        assert len(payload["lanes"]) == 3, (
            "every promoted domain in this slate attaches exactly three lanes"
        )
        for lane in payload["lanes"]:
            assert set(lane["splits"].keys()) == {"public", "holdout"}
            for split_name, split in lane["splits"].items():
                assert split["shape_check"]["passed"] is True, (
                    f"{lane['lane_id']}/{split_name} failed shape check: "
                    f"{split['shape_check']}"
                )
                assert split["shape_check"]["shape"] is not None

    def test_sample_cases_are_capped(self, domain_id: str) -> None:
        payload = build_expert_demo(domain_id)
        for lane in payload["lanes"]:
            for split_name, split in lane["splits"].items():
                assert len(split["sample_cases"]) <= SAMPLE_CASES_PER_SPLIT
                assert len(split["sample_cases"]) >= 1, (
                    f"{lane['lane_id']}/{split_name} has zero sample cases"
                )


class TestUnpromotedDomainRefused:
    def test_unpromoted_domain_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="No expert_demo_claims entry"):
            build_expert_demo("systems_software")

    def test_unknown_domain_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="No expert_demo_claims entry"):
            build_expert_demo("not_a_real_domain")


class TestByteDeterminism:
    @pytest.mark.parametrize("domain_id", _PROMOTED_DOMAINS)
    def test_two_runs_produce_byte_identical_json(self, domain_id: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_a = Path(tmp) / "a"
            out_b = Path(tmp) / "b"
            run_expert_demo(domain_id=domain_id, output_dir=out_a)
            run_expert_demo(domain_id=domain_id, output_dir=out_b)
            bytes_a = (out_a / "expert_demo.json").read_bytes()
            bytes_b = (out_b / "expert_demo.json").read_bytes()
            assert bytes_a == bytes_b
            sha_a = hashlib.sha256(bytes_a).hexdigest()
            sha_b = hashlib.sha256(bytes_b).hexdigest()
            assert sha_a == sha_b


class TestComposerIsReadOnly:
    def test_run_does_not_mutate_reviewers_yaml(self) -> None:
        path = _REPO_ROOT / "docs" / "reviewers.yaml"
        before = path.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            run_expert_demo(domain_id="physics", output_dir=Path(tmp))
        after = path.read_bytes()
        assert before == after

    def test_run_does_not_mutate_lane_result_files(self) -> None:
        results_dir = _REPO_ROOT / "evals" / "foundational_physics_ood" / "results"
        before = {p.name: p.read_bytes() for p in results_dir.glob("v1_*.json")}
        with tempfile.TemporaryDirectory() as tmp:
            run_expert_demo(domain_id="physics", output_dir=Path(tmp))
        after = {p.name: p.read_bytes() for p in results_dir.glob("v1_*.json")}
        assert before == after


class TestOutputArtifacts:
    def test_json_and_html_both_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_expert_demo(domain_id="physics", output_dir=out)
            assert (out / "expert_demo.json").is_file()
            assert (out / "expert_demo.html").is_file()
            html = (out / "expert_demo.html").read_text(encoding="utf-8")
            assert "<title>CORE Expert-Demo: physics</title>" in html
            assert "a104cad136f3219df05dc7ce6a78437c02f7b5827cd3cdce568db3acda6a43ed" in html

    def test_html_contains_per_lane_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_expert_demo(domain_id="physics", output_dir=out)
            html = (out / "expert_demo.html").read_text(encoding="utf-8")
            for lane_id in (
                "foundational_physics_ood",
                "inference_closure",
                "fabrication_control",
            ):
                assert lane_id in html
            assert "public split" in html
            assert "holdout split" in html

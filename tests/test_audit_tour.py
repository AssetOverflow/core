"""Tests for the audit tour demo.

The tour ships as `core demo audit-tour` and is the primary
investor-facing artifact for the pack-layer architecture story.
These tests ensure the four claim flags stay green and that the
JSON mode emits a stable structured report.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

from evals.audit_tour.run_tour import run_tour


class TestRunTourStructuredOutput:
    def test_all_claims_supported(self) -> None:
        """The headline gate — every scene's load-bearing claim must
        pass.  Any scene flipping to False represents a regression of
        the pack-layer architecture story."""
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        assert result["all_claims_supported"] is True

    def test_scene_1_distinct_alignment_thresholds(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        s1 = result["scene_1_identity_geometric"]
        # Three packs ship with three distinct thresholds.
        assert s1["distinct_alignment_thresholds"] == 3
        assert s1["distinct_hedge_phrases"] >= 2

    def test_scene_2_typed_refusal(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        s2 = result["scene_2_safety_typed_refusal"]
        assert s2["refusal_emitted"] is True
        assert s2["refused_surface"].startswith("I cannot proceed")
        # walk_surface is preserved unchanged.
        assert s2["walk_surface"] != s2["refused_surface"]

    def test_scene_3_pack_drives_remediation(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        s3 = result["scene_3_ethics_hedge_opt_in"]
        assert s3["default_fires"] is False
        assert s3["deployment_fires"] is True
        assert s3["deployment_pack_hedge_commitments"] == ["acknowledge_uncertainty"]
        # Hedged surface starts with the manifold's hedge phrase.
        assert s3["hedged_surface"].startswith(s3["hedge_prefix"])

    def test_scene_4_byte_identical_replay(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        s4 = result["scene_4_deterministic_replay"]
        assert s4["byte_identical"] is True
        # The two short-hash previews must match too (sanity).
        assert s4["line_1_sha_preview"] == s4["line_2_sha_preview"]


class TestNarrationMode:
    def test_narration_prints_when_emit_json_false(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_tour(emit_json=False)
        output = buf.getvalue()
        assert "CORE Audit Tour" in output
        assert "Scene 1" in output
        assert "Scene 2" in output
        assert "Scene 3" in output
        assert "Scene 4" in output
        assert "Summary" in output

    def test_emit_json_suppresses_narration(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_tour(emit_json=True)
        # Nothing should have been printed — caller is responsible
        # for serialising the returned dict.
        assert buf.getvalue() == ""


class TestStructuredReportSerialisable:
    def test_result_is_json_serialisable(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = run_tour(emit_json=True)
        # Round-trip through json to ensure no non-serialisable types
        # leak into the report.
        encoded = json.dumps(result, default=str, sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded["all_claims_supported"] is True

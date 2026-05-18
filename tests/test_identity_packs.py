"""Identity-pack loader + runtime wiring tests.

Covers ADR-0027 Phase 1–4 surface area:

* Loader bounds checks (missing fields, malformed direction, weight,
  threshold, duplicate axis id, missing pack).
* Round-trip parity: ``default_general_v1`` constructs an
  ``IdentityManifold`` equal to the pre-ADR hardcoded one.
* Runtime wiring: ``ChatRuntime`` loads the pack indicated by
  ``RuntimeConfig.identity_pack`` (and falls back to the default).
* Pack swap: ``precision_first_v1`` and ``generosity_first_v1`` produce
  manifolds that differ from the default in axis weights / thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.config import DEFAULT_IDENTITY_PACK, RuntimeConfig
from packs.identity.loader import (
    IdentityPackError,
    available_packs,
    load_identity_manifold,
)


# ---------- loader bounds ----------


class TestLoaderHappyPath:
    def test_loads_default_general(self) -> None:
        m = load_identity_manifold(
            "default_general_v1", require_ratified=False,
        )
        assert len(m.value_axes) == 3
        axis_ids = {a.axis_id for a in m.value_axes}
        assert axis_ids == {"truthfulness", "coherence", "reverence"}
        assert m.alignment_threshold == 0.45
        assert m.boundary_ids == frozenset(
            {"no_fabricated_source", "no_hot_path_repair"}
        )

    def test_loads_precision_first(self) -> None:
        m = load_identity_manifold(
            "precision_first_v1", require_ratified=False,
        )
        weights = {a.axis_id: a.weight for a in m.value_axes}
        # Precision pack boosts truthfulness weight to 2.0; defaults are 1.0.
        assert weights["truthfulness"] == 2.0
        assert weights["coherence"] == 0.7
        assert m.alignment_threshold == 0.55

    def test_loads_generosity_first(self) -> None:
        m = load_identity_manifold(
            "generosity_first_v1", require_ratified=False,
        )
        weights = {a.axis_id: a.weight for a in m.value_axes}
        assert weights["coherence"] == 2.0
        assert weights["truthfulness"] == 0.8

    def test_available_packs(self) -> None:
        packs = available_packs()
        ids = {p["pack_id"] for p in packs}
        assert {"default_general_v1", "precision_first_v1", "generosity_first_v1"} <= ids
        # Phase 5 complete — v1 packs are ratified.
        ratified_ids = {p["pack_id"] for p in packs if p["ratified"]}
        assert {"default_general_v1", "precision_first_v1", "generosity_first_v1"} <= ratified_ids

    def test_available_packs_excludes_mastery_reports(self) -> None:
        """Companion ``<pack_id>.mastery_report.json`` files must not surface as packs."""
        packs = available_packs()
        ids = {p["pack_id"] for p in packs}
        for pid in ids:
            assert not pid.endswith(".mastery_report"), (
                f"mastery report companion leaked into available_packs(): {pid!r}"
            )

    def test_v1_packs_load_in_production_mode(self) -> None:
        # require_ratified default (None) -> production unless env override.
        for pid in (
            "default_general_v1", "precision_first_v1", "generosity_first_v1",
        ):
            m = load_identity_manifold(pid)
            assert len(m.value_axes) == 3


# ---------- error paths ----------


class TestLoaderRejects:
    def test_missing_pack(self) -> None:
        with pytest.raises(IdentityPackError, match="not found"):
            load_identity_manifold(
                "does_not_exist", require_ratified=False,
            )

    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(IdentityPackError, match="invalid pack_id"):
            load_identity_manifold(
                "../../etc/passwd", require_ratified=False,
            )

    def test_unratified_pack_refused_in_production(self, tmp_path: Path) -> None:
        # An unratified test pack (empty mastery_report_sha256) must be
        # refused in production mode.
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0, 0.0], "weight": 1.0,
            }],
        )
        with pytest.raises(IdentityPackError, match="not ratified"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=True,
            )

    def test_missing_companion_report_refused(
        self, tmp_path: Path,
    ) -> None:
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0, 0.0], "weight": 1.0,
            }],
            mastery_report_sha256="0" * 64,
        )
        with pytest.raises(IdentityPackError, match="companion report file"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=True,
            )

    def test_companion_report_sha_mismatch_refused(
        self, tmp_path: Path,
    ) -> None:
        # Pack claims one SHA; companion report carries a different one.
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0, 0.0], "weight": 1.0,
            }],
            mastery_report_sha256="a" * 64,
        )
        report_path = tmp_path / f"{bad['pack_id']}.mastery_report.json"
        report_path.write_text(
            json.dumps({"report_sha256": "b" * 64, "ratified": True}),
            encoding="utf-8",
        )
        with pytest.raises(IdentityPackError, match="does not match"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=True,
            )

    def test_companion_report_seal_failure_refused(
        self, tmp_path: Path,
    ) -> None:
        # Companion report's claimed SHA does not actually self-seal.
        bogus_sha = "c" * 64
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0, 0.0], "weight": 1.0,
            }],
            mastery_report_sha256=bogus_sha,
        )
        report_path = tmp_path / f"{bad['pack_id']}.mastery_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "report_sha256": bogus_sha,
                    "ratified": True,
                    "other_field": "anything",
                },
            ),
            encoding="utf-8",
        )
        with pytest.raises(IdentityPackError, match="self-seal"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=True,
            )

    def test_malformed_direction(self, tmp_path: Path) -> None:
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0],  # length 2, not 3
                "weight": 1.0,
            }],
        )
        with pytest.raises(IdentityPackError, match="direction"):
            load_identity_manifold(
                bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=False,
            )

    def test_direction_out_of_bounds(self, tmp_path: Path) -> None:
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [5.0, 0.0, 0.0],
                "weight": 1.0,
            }],
        )
        with pytest.raises(IdentityPackError, match="out of bounds"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=False,
            )

    def test_weight_out_of_bounds(self, tmp_path: Path) -> None:
        bad = _write_pack(
            tmp_path,
            value_axes=[{
                "axis_id": "x", "name": "x",
                "direction": [1.0, 0.0, 0.0],
                "weight": 999.0,
            }],
        )
        with pytest.raises(IdentityPackError, match="weight"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=False,
            )

    def test_duplicate_axis_id(self, tmp_path: Path) -> None:
        bad = _write_pack(
            tmp_path,
            value_axes=[
                {"axis_id": "x", "name": "x", "direction": [1.0, 0.0, 0.0], "weight": 1.0},
                {"axis_id": "x", "name": "y", "direction": [0.0, 1.0, 0.0], "weight": 1.0},
            ],
        )
        with pytest.raises(IdentityPackError, match="duplicate axis_id"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=False,
            )

    def test_empty_axes(self, tmp_path: Path) -> None:
        bad = _write_pack(tmp_path, value_axes=[])
        with pytest.raises(IdentityPackError, match="at least"):
            load_identity_manifold(
                bad["pack_id"], search_paths=[tmp_path], require_ratified=False,
            )


# ---------- runtime wiring ----------


class TestRuntimeWiring:
    def test_runtime_loads_default_pack(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert rt.identity_pack_id == DEFAULT_IDENTITY_PACK
        axis_ids = {a.axis_id for a in rt.identity_manifold.value_axes}
        assert axis_ids == {"truthfulness", "coherence", "reverence"}

    def test_runtime_loads_precision_pack_via_config(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack="precision_first_v1"))
        assert rt.identity_pack_id == "precision_first_v1"
        weights = {a.axis_id: a.weight for a in rt.identity_manifold.value_axes}
        assert weights["truthfulness"] == 2.0

    def test_runtime_loads_generosity_pack_via_config(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack="generosity_first_v1"))
        weights = {a.axis_id: a.weight for a in rt.identity_manifold.value_axes}
        assert weights["coherence"] == 2.0

    def test_empty_identity_pack_falls_back_to_default(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack=""))
        assert rt.identity_pack_id == DEFAULT_IDENTITY_PACK


# ---------- pack swap proof ----------


class TestPackSwap:
    def test_precision_vs_default_manifolds_differ(self) -> None:
        default_m = load_identity_manifold("default_general_v1", require_ratified=False)
        precision_m = load_identity_manifold("precision_first_v1", require_ratified=False)
        assert default_m.alignment_threshold != precision_m.alignment_threshold
        default_weights = {a.axis_id: a.weight for a in default_m.value_axes}
        precision_weights = {a.axis_id: a.weight for a in precision_m.value_axes}
        assert default_weights != precision_weights

    def test_generosity_adds_no_extra_boundaries(self) -> None:
        # Identity packs may add boundaries (precision_first does) but
        # must not silently drop the core ones.
        for pack_id in (
            "default_general_v1", "precision_first_v1", "generosity_first_v1",
        ):
            m = load_identity_manifold(pack_id, require_ratified=False)
            assert "no_fabricated_source" in m.boundary_ids
            assert "no_hot_path_repair" in m.boundary_ids


# ---------- CLI: --list-identity-packs ----------


class TestListIdentityPacksCLI:
    def test_table_output_lists_all_three_packs(self) -> None:
        import subprocess
        import sys

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "chat", "--list-identity-packs"],
            cwd=str(repo_root),
            env={"PYTHONPATH": str(repo_root), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, check=True,
        )
        # Header + three pack rows; no mastery_report companion rows.
        assert "default_general_v1" in result.stdout
        assert "precision_first_v1" in result.stdout
        assert "generosity_first_v1" in result.stdout
        assert "mastery_report" not in result.stdout
        # All three ratified -> three "yes" flags.
        assert result.stdout.count(" yes ") >= 3

    def test_json_output_is_valid_json(self) -> None:
        import subprocess
        import sys

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable, "-m", "core.cli", "chat",
                "--list-identity-packs", "--json",
            ],
            cwd=str(repo_root),
            env={"PYTHONPATH": str(repo_root), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, check=True,
        )
        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        pack_ids = {p["pack_id"] for p in payload}
        assert {"default_general_v1", "precision_first_v1", "generosity_first_v1"} <= pack_ids
        for p in payload:
            assert p["ratified"] is True


# ---------- ratification script idempotency ----------


class TestRatificationScript:
    def test_script_idempotent(self) -> None:
        """Re-running scripts/ratify_identity_packs.py must not change anything."""
        import subprocess
        import sys

        repo_root = Path(__file__).resolve().parents[1]
        before = {
            pid: (repo_root / "packs" / "identity" / f"{pid}.json").read_text(
                encoding="utf-8"
            )
            for pid in (
                "default_general_v1", "precision_first_v1", "generosity_first_v1",
            )
        }
        result = subprocess.run(
            [sys.executable, "scripts/ratify_identity_packs.py"],
            cwd=str(repo_root),
            env={"PYTHONPATH": str(repo_root), "PATH": "/usr/bin:/bin"},
            check=True,
            capture_output=True,
            text=True,
        )
        assert "ratified 0 pack(s); 3 already current" in result.stdout
        after = {
            pid: (repo_root / "packs" / "identity" / f"{pid}.json").read_text(
                encoding="utf-8"
            )
            for pid in before
        }
        for pid, txt in before.items():
            assert after[pid] == txt, f"pack {pid} changed during idempotent re-run"


# ---------- helpers ----------


def _write_pack(
    tmp_path: Path,
    *,
    value_axes: list,
    pack_id: str = "test_pack",
    mastery_report_sha256: str = "",
) -> dict:
    body = {
        "pack_id": pack_id,
        "version": "1.0.0",
        "description": "test",
        "schema_version": "1.0.0",
        "mastery_report_sha256": mastery_report_sha256,
        "alignment_threshold": 0.45,
        "boundary_ids": ["test_boundary"],
        "value_axes": value_axes,
    }
    path = tmp_path / f"{pack_id}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return body

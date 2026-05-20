"""ADR-0087 substrate tests — rhetorical-style pack loader.

Pins the substrate contract end-to-end:

  1. ``default_unstyled_v1`` ratifies and loads with the same
     mastery-report self-seal discipline as anchor-lens packs.
  2. Schema gate rejects unknown keys, malformed lists, invalid
     ``default_unstyled`` interactions.
  3. Frame and move vocabularies are allow-listed; unknown values
     refused.
  4. ``RuntimeConfig.rhetorical_style_id`` field exists and defaults
     to ``None``.

No consumer code is invoked — this PR ships substrate only.  The
null-lift behavior (loading ``default_unstyled_v1`` changes nothing
about runtime surfaces) is trivially true today because no composer
reads the pack; that becomes a real test when the consumer ADR lands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packs.rhetorical_style import (
    DEFAULT_RHETORICAL_STYLE_PACK,
    RhetoricalStylePack,
    RhetoricalStylePackError,
    load_rhetorical_style_pack,
)
from packs.rhetorical_style.loader import (
    available_rhetorical_style_packs,
)


# --------------------------------------------------------------------------- #
# Default null-lift pack
# --------------------------------------------------------------------------- #


class TestDefaultUnstyledPack:
    def test_loads(self) -> None:
        pack = load_rhetorical_style_pack()
        assert isinstance(pack, RhetoricalStylePack)
        assert pack.pack_id == DEFAULT_RHETORICAL_STYLE_PACK

    def test_is_null_lift(self) -> None:
        pack = load_rhetorical_style_pack()
        assert pack.is_null_lift() is True
        assert pack.default_unstyled is True
        assert pack.permitted_frames == ()
        assert pack.required_moves_per_claim == ()
        assert pack.forbidden_moves == ()

    def test_mastery_report_self_seal_verified(self) -> None:
        # Loading with require_ratified=True (the default) implicitly
        # verifies the companion mastery-report self-seal.  If the seal
        # is broken the load raises RhetoricalStylePackError — so the
        # mere fact load_rhetorical_style_pack() returns at all is the
        # assertion.  Re-load explicitly for clarity:
        pack = load_rhetorical_style_pack(require_ratified=True)
        assert pack.mastery_report_sha256, "ratified pack must declare mastery_report_sha256"
        # SHA hex string length sanity.
        assert len(pack.mastery_report_sha256) == 64

    def test_discovery_lists_default_pack(self) -> None:
        summaries = available_rhetorical_style_packs()
        ids = {s["pack_id"] for s in summaries}
        assert "default_unstyled_v1" in ids
        # The default pack must show as ratified in the discovery list.
        default_summary = next(s for s in summaries if s["pack_id"] == "default_unstyled_v1")
        assert default_summary["ratified"] is True
        assert default_summary["default_unstyled"] is True


# --------------------------------------------------------------------------- #
# Schema gate via fixture packs in a tmp_path
# --------------------------------------------------------------------------- #


def _write_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, pack_id: str = "fixture_v1",
    overrides: dict | None = None, write_report: bool = False,
) -> str:
    from packs.rhetorical_style import loader as _loader

    valid = {
        "pack_id": pack_id,
        "schema_version": "1.0.0",
        "version": 1,
        "issued_at": "2026-05-21T00:00:00Z",
        "default_unstyled": True,
        "permitted_frames": [],
        "required_moves_per_claim": [],
        "forbidden_moves": [],
        "provenance": "test:fixture",
        "mastery_report_sha256": "",
    }
    if overrides:
        valid.update(overrides)
    (tmp_path / f"{pack_id}.json").write_text(json.dumps(valid), encoding="utf-8")

    if write_report:
        # Build a minimal self-sealed report that agrees with the pack's
        # mastery_report_sha256.  Easiest path: use the existing ratify
        # script's seal helper directly.
        from formation.hashing import self_seal, sha256_of
        probe = dict(valid)
        probe["mastery_report_sha256"] = ""
        pack_source = sha256_of(probe)
        report = {
            "pack_id": pack_id,
            "schema_version": "1.0.0",
            "ratification_method": "rhetorical_style_substrate",
            "ratified": True,
            "issued_at": valid["issued_at"],
            "pack_source_sha256": pack_source,
            "failure_reasons": [],
            "evidence": {},
            "report_sha256": "",
        }
        sealed = self_seal(report, sha_field="report_sha256")
        (tmp_path / f"{pack_id}.mastery_report.json").write_text(
            json.dumps(sealed), encoding="utf-8"
        )
        # Update pack to declare matching sha
        valid["mastery_report_sha256"] = sealed["report_sha256"]
        (tmp_path / f"{pack_id}.json").write_text(json.dumps(valid), encoding="utf-8")

    monkeypatch.setattr(_loader, "_DEFAULT_SEARCH_PATHS", (tmp_path,))
    return pack_id


class TestSchemaGate:
    def test_missing_required_key_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={"version": None},  # we'll delete a key below
        )
        # Write a pack missing 'version'
        bad = {
            "pack_id": pack_id,
            "schema_version": "1.0.0",
            "issued_at": "2026-05-21T00:00:00Z",
            "default_unstyled": True,
            "permitted_frames": [],
            "required_moves_per_claim": [],
            "forbidden_moves": [],
            "provenance": "test:fixture",
            "mastery_report_sha256": "",
        }
        (tmp_path / f"{pack_id}.json").write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(RhetoricalStylePackError, match=r"missing required key"):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_unknown_key_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch, overrides={"rogue_field": True},
        )
        with pytest.raises(RhetoricalStylePackError, match=r"unrecognised key"):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_unknown_frame_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={
                "default_unstyled": False,
                "permitted_frames": ["rogue_frame"],
            },
        )
        with pytest.raises(RhetoricalStylePackError, match=r"unknown value 'rogue_frame'"):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_unknown_move_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={
                "default_unstyled": False,
                "required_moves_per_claim": ["rogue_move"],
            },
        )
        with pytest.raises(RhetoricalStylePackError, match=r"unknown value 'rogue_move'"):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_duplicate_frame_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={
                "default_unstyled": False,
                "permitted_frames": ["warrant", "warrant"],
            },
        )
        with pytest.raises(RhetoricalStylePackError, match=r"duplicate value 'warrant'"):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_default_unstyled_with_constraints_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # ADR-0087 invariant: default_unstyled=true ⟺ all three lists empty.
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={
                "default_unstyled": True,
                "permitted_frames": ["warrant"],
            },
        )
        with pytest.raises(
            RhetoricalStylePackError,
            match=r"default_unstyled=true requires empty",
        ):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_non_default_with_no_constraints_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A non-default pack with zero constraints would silently look
        # like null-lift but bypass the default_unstyled invariant test
        # — rejected to keep the two states distinguishable.
        pack_id = _write_pack(
            tmp_path, monkeypatch, overrides={"default_unstyled": False},
        )
        with pytest.raises(
            RhetoricalStylePackError,
            match=r"non-default pack must declare at least one",
        ):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_pack_id_mismatch_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={"pack_id": "different_id_v1"},
        )
        with pytest.raises(
            RhetoricalStylePackError,
            match=r"declares pack_id=",
        ):
            load_rhetorical_style_pack(pack_id, require_ratified=False)

    def test_path_traversal_pack_id_rejected(self) -> None:
        with pytest.raises(RhetoricalStylePackError, match=r"invalid rhetorical-style pack_id"):
            load_rhetorical_style_pack("../escape", require_ratified=False)


# --------------------------------------------------------------------------- #
# Ratification gate
# --------------------------------------------------------------------------- #


class TestRatificationGate:
    def test_unratified_pack_rejected_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # require_ratified defaults to True; an empty mastery_report_sha256
        # is refused absent the env-var bypass.
        pack_id = _write_pack(tmp_path, monkeypatch)
        monkeypatch.delenv("CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE", raising=False)
        with pytest.raises(RhetoricalStylePackError, match=r"not ratified"):
            load_rhetorical_style_pack(pack_id)

    def test_env_var_bypass_permits_unratified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_pack(tmp_path, monkeypatch)
        monkeypatch.setenv("CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE", "1")
        pack = load_rhetorical_style_pack(pack_id)
        assert pack.mastery_report_sha256 == ""

    def test_companion_report_missing_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Pack declares a mastery_report_sha256 but no companion file
        # on disk — refused.
        pack_id = _write_pack(
            tmp_path, monkeypatch,
            overrides={"mastery_report_sha256": "deadbeef" * 8},
        )
        with pytest.raises(RhetoricalStylePackError, match=r"companion mastery report missing"):
            load_rhetorical_style_pack(pack_id, require_ratified=True)

    def test_companion_sha_mismatch_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Pack declares one SHA; companion report has a different one.
        pack_id = _write_pack(tmp_path, monkeypatch, write_report=True)
        # Tamper with the declared SHA on the pack to break agreement.
        pack_path = tmp_path / f"{pack_id}.json"
        raw = json.loads(pack_path.read_text())
        raw["mastery_report_sha256"] = "f" * 64
        pack_path.write_text(json.dumps(raw))
        with pytest.raises(RhetoricalStylePackError, match=r"does not match companion"):
            load_rhetorical_style_pack(pack_id, require_ratified=True)


# --------------------------------------------------------------------------- #
# RuntimeConfig field
# --------------------------------------------------------------------------- #


class TestRuntimeConfigField:
    def test_default_is_none(self) -> None:
        from core.config import RuntimeConfig
        cfg = RuntimeConfig()
        assert cfg.rhetorical_style_id is None

    def test_field_accepts_string(self) -> None:
        from core.config import RuntimeConfig
        cfg = RuntimeConfig(rhetorical_style_id="default_unstyled_v1")
        assert cfg.rhetorical_style_id == "default_unstyled_v1"

    def test_field_independent_of_other_axes(self) -> None:
        # Sanity: setting rhetorical_style_id does not perturb other
        # axes' defaults (register, anchor lens, ADR-0085 flag, etc.).
        from core.config import RuntimeConfig
        cfg = RuntimeConfig(rhetorical_style_id="default_unstyled_v1")
        assert cfg.gloss_aware_cause is False
        assert cfg.transitive_surface is False
        assert cfg.composed_surface is False

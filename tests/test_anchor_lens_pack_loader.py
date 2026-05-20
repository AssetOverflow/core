"""Anchor-lens pack loader tests (ADR-0073b/c — v2 schema).

Covers:
- Load / list / verify-seal happy paths
- Unanchored sentinel vs on-disk ``default_unanchored_v1`` distinction
- Invalid lens_id rejection (traversal, empty, non-string)
- Missing mastery report rejection in production mode
- Companion-report SHA mismatch rejection
- Bounds violations (substrate, atom shape, label length)
- v1→v2 normalisation back-compat
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from packs.anchor_lens.loader import (
    AnchorLens,
    AnchorLensError,
    UNANCHORED,
    available_anchor_lens_packs,
    load_anchor_lens,
    verify_anchor_lens_seal,
)


# ---------- happy paths ----------


def test_loads_default_unanchored_v1():
    lens = load_anchor_lens("default_unanchored_v1")
    assert lens.lens_id == "default_unanchored_v1"
    assert lens.primary_substrate == "none"
    assert lens.semantic_domain_preferences == ()
    assert lens.cognitive_mode_label == ""
    assert lens.is_null_lens() is True
    assert lens.is_unanchored() is False  # only the in-memory sentinel is "unanchored"
    assert lens.mastery_report_sha256  # ratified


def test_seal_verifies_for_ratified_pack():
    assert verify_anchor_lens_seal("default_unanchored_v1") is True


def test_available_lists_default_pack():
    packs = available_anchor_lens_packs()
    ids = [p["lens_id"] for p in packs]
    assert "default_unanchored_v1" in ids
    entry = next(p for p in packs if p["lens_id"] == "default_unanchored_v1")
    assert entry["ratified"] is True
    assert entry["primary_substrate"] == "none"


# ---------- unanchored sentinel ----------


def test_unanchored_sentinel_is_null_lens():
    sentinel = AnchorLens.unanchored()
    assert sentinel.is_unanchored() is True
    assert sentinel.is_null_lens() is True
    assert sentinel.primary_substrate == "none"
    assert sentinel.semantic_domain_preferences == ()
    assert sentinel.cognitive_mode_label == ""


def test_module_level_unanchored_constant_matches_classmethod():
    assert UNANCHORED == AnchorLens.unanchored()
    assert UNANCHORED.is_unanchored() is True


def test_sentinel_structurally_matches_default_unanchored():
    """Structural-identity gate: in-memory sentinel matches the disk pack
    on every payload field; differs only on lens_id (identity metadata)."""
    sentinel = AnchorLens.unanchored()
    on_disk = load_anchor_lens("default_unanchored_v1")
    assert sentinel.primary_substrate == on_disk.primary_substrate
    assert sentinel.semantic_domain_preferences == on_disk.semantic_domain_preferences
    assert sentinel.cognitive_mode_label == on_disk.cognitive_mode_label
    assert sentinel.substrate == on_disk.substrate
    assert sentinel.atom == on_disk.atom
    assert sentinel.cognitive_mode == on_disk.cognitive_mode
    # The two differ only on lens_id + mastery_report_sha256.
    assert sentinel.lens_id != on_disk.lens_id  # "__unanchored__" vs "default_unanchored_v1"


# ---------- invalid lens_id ----------


def test_rejects_empty_lens_id():
    with pytest.raises(AnchorLensError, match="invalid lens_id"):
        load_anchor_lens("")


def test_rejects_path_traversal_lens_id():
    with pytest.raises(AnchorLensError, match="invalid lens_id"):
        load_anchor_lens("../../../etc/passwd")


def test_rejects_slash_in_lens_id():
    with pytest.raises(AnchorLensError, match="invalid lens_id"):
        load_anchor_lens("subdir/lens")


def test_rejects_missing_pack():
    with pytest.raises(AnchorLensError, match="not found"):
        load_anchor_lens("bogus_v999")


# ---------- ratification gate ----------


def _v2_pack(**overrides) -> dict:
    base = {
        "lens_id": "test_v1",
        "version": "0.1.0",
        "description": "test",
        "schema_version": "1.0.0",
        "substrate": "none",
        "atom": "",
        "cognitive_mode": "",
        "source_entry_id": "",
        "pair_lens_id": None,
        "ratification_method": "anchor_lens_lifts_proposition",
        "mastery_report_sha256": "",
    }
    base.update(overrides)
    return base


def test_unratified_pack_rejected_in_production_mode(tmp_path: Path):
    """A pack with empty mastery_report_sha256 is refused unless bypassed."""
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps(_v2_pack(lens_id="transient_v1")))
    with pytest.raises(AnchorLensError, match="not ratified"):
        load_anchor_lens(
            "transient_v1", search_paths=(tmp_path,), require_ratified=True,
        )


def test_unratified_pack_accepted_with_explicit_bypass(tmp_path: Path):
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps(_v2_pack(lens_id="transient_v1")))
    lens = load_anchor_lens(
        "transient_v1", search_paths=(tmp_path,), require_ratified=False,
    )
    assert lens.lens_id == "transient_v1"


def test_env_var_bypasses_ratification(monkeypatch, tmp_path: Path):
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps(_v2_pack(lens_id="transient_v1")))
    monkeypatch.setenv("CORE_ALLOW_UNRATIFIED_ANCHOR_LENS", "1")
    lens = load_anchor_lens("transient_v1", search_paths=(tmp_path,))
    assert lens.lens_id == "transient_v1"


def test_companion_sha_mismatch_rejected(tmp_path: Path):
    """Pack declares a SHA that doesn't match the on-disk report."""
    src = Path("packs/anchor_lens")
    shutil.copy(src / "default_unanchored_v1.json", tmp_path / "default_unanchored_v1.json")
    shutil.copy(
        src / "default_unanchored_v1.mastery_report.json",
        tmp_path / "default_unanchored_v1.mastery_report.json",
    )
    pack_path = tmp_path / "default_unanchored_v1.json"
    raw = json.loads(pack_path.read_text())
    raw["mastery_report_sha256"] = "0" * 64
    pack_path.write_text(json.dumps(raw))
    with pytest.raises(AnchorLensError, match="does not match"):
        load_anchor_lens(
            "default_unanchored_v1", search_paths=(tmp_path,),
            require_ratified=True,
        )


# ---------- bounds violations (v2 schema) ----------


def _write(tmp_path: Path, pack: dict) -> None:
    (tmp_path / f"{pack['lens_id']}.json").write_text(json.dumps(pack))


def _load_unratified(tmp_path: Path, lens_id: str) -> AnchorLens:
    return load_anchor_lens(
        lens_id, search_paths=(tmp_path,), require_ratified=False,
    )


def test_unknown_substrate_rejected(tmp_path: Path):
    _write(tmp_path, _v2_pack(substrate="latin"))
    with pytest.raises(AnchorLensError, match="substrate"):
        _load_unratified(tmp_path, "test_v1")


def test_atom_must_be_nonempty_string_when_substrate_set(tmp_path: Path):
    _write(tmp_path, _v2_pack(substrate="grc", atom="", cognitive_mode="x"))
    with pytest.raises(AnchorLensError, match="non-empty"):
        _load_unratified(tmp_path, "test_v1")


def test_atom_length_capped(tmp_path: Path):
    _write(tmp_path, _v2_pack(
        substrate="grc", atom="x" * 200, cognitive_mode="x",
    ))
    with pytest.raises(AnchorLensError, match="atom"):
        _load_unratified(tmp_path, "test_v1")


def test_label_length_capped(tmp_path: Path):
    _write(tmp_path, _v2_pack(cognitive_mode="x" * 200))
    with pytest.raises(AnchorLensError, match="cognitive_mode"):
        _load_unratified(tmp_path, "test_v1")


def test_missing_field_rejected(tmp_path: Path):
    pack = _v2_pack()
    del pack["substrate"]
    _write(tmp_path, pack)
    with pytest.raises(AnchorLensError, match="missing required fields"):
        _load_unratified(tmp_path, "test_v1")


def test_lens_id_mismatch_rejected(tmp_path: Path):
    """Filename and declared lens_id must agree."""
    pack = _v2_pack(lens_id="declared_different")
    (tmp_path / "test_v1.json").write_text(json.dumps(pack))
    with pytest.raises(AnchorLensError, match="declares lens_id"):
        _load_unratified(tmp_path, "test_v1")


def test_unsupported_schema_version_rejected(tmp_path: Path):
    _write(tmp_path, _v2_pack(schema_version="2.0.0"))
    with pytest.raises(AnchorLensError, match="schema_version"):
        _load_unratified(tmp_path, "test_v1")


# ---------- v1→v2 back-compat normalisation ----------


def test_v1_legacy_pack_normalises(tmp_path: Path):
    """A pack written in v1 schema (primary_substrate + semantic_domain_preferences
    + cognitive_mode_label) loads successfully under v2 via _normalise_raw."""
    v1_pack = {
        "lens_id": "v1_legacy_v1",
        "version": "0.1.0",
        "description": "v1 legacy pack for migration test",
        "schema_version": "1.0.0",
        "display_name": "Legacy",
        "primary_substrate": "grc",
        "semantic_domain_preferences": ["logos.episteme.systematic_knowledge"],
        "cognitive_mode_label": "systematic",
        "mastery_report_sha256": "",
    }
    (tmp_path / "v1_legacy_v1.json").write_text(json.dumps(v1_pack))
    lens = load_anchor_lens(
        "v1_legacy_v1", search_paths=(tmp_path,), require_ratified=False,
    )
    assert lens.substrate == "grc"
    assert lens.atom == "logos.episteme.systematic_knowledge"
    assert lens.cognitive_mode == "systematic"
    # v1 attribute views work too
    assert lens.primary_substrate == "grc"
    assert lens.semantic_domain_preferences == ("logos.episteme.systematic_knowledge",)
    assert lens.cognitive_mode_label == "systematic"

"""Anchor-lens pack loader tests (ADR-0073b, Plan Phase L1.2).

Covers:
- Load / list / verify-seal happy paths
- Unanchored sentinel structural identity vs default_unanchored_v1
- Invalid lens_id rejection (traversal, empty, non-string)
- Missing mastery report rejection in production mode
- Companion-report SHA mismatch rejection
- Bounds violations (substrate, preferences shape, label length)
- Duplicate-atom rejection in semantic_domain_preferences
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
    assert lens.is_unanchored() is False  # only the sentinel is "unanchored"
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
    """L1.2 byte-identity gate: the in-memory sentinel is
    structurally indistinguishable from the disk-ratified default."""
    sentinel = AnchorLens.unanchored()
    on_disk = load_anchor_lens("default_unanchored_v1")
    assert sentinel.primary_substrate == on_disk.primary_substrate
    assert sentinel.semantic_domain_preferences == on_disk.semantic_domain_preferences
    assert sentinel.cognitive_mode_label == on_disk.cognitive_mode_label
    # The two differ only on lens_id + version + mastery_report_sha256,
    # which are identity metadata, not structural payload.
    assert sentinel.lens_id != on_disk.lens_id  # "__unanchored__" vs "default_..."


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


def test_unratified_pack_rejected_in_production_mode(tmp_path: Path):
    """A pack with empty mastery_report_sha256 is refused unless
    explicitly bypassed."""
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps({
        "lens_id": "transient_v1",
        "version": "0.1.0",
        "description": "transient test pack",
        "schema_version": "1.0.0",
        "display_name": "Transient",
        "primary_substrate": "none",
        "semantic_domain_preferences": [],
        "cognitive_mode_label": "",
        "mastery_report_sha256": "",
    }))
    with pytest.raises(AnchorLensError, match="not ratified"):
        load_anchor_lens(
            "transient_v1", search_paths=(tmp_path,), require_ratified=True,
        )


def test_unratified_pack_accepted_with_explicit_bypass(tmp_path: Path):
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps({
        "lens_id": "transient_v1",
        "version": "0.1.0",
        "description": "transient test pack",
        "schema_version": "1.0.0",
        "display_name": "Transient",
        "primary_substrate": "none",
        "semantic_domain_preferences": [],
        "cognitive_mode_label": "",
        "mastery_report_sha256": "",
    }))
    lens = load_anchor_lens(
        "transient_v1", search_paths=(tmp_path,), require_ratified=False,
    )
    assert lens.lens_id == "transient_v1"


def test_env_var_bypasses_ratification(monkeypatch, tmp_path: Path):
    pack_path = tmp_path / "transient_v1.json"
    pack_path.write_text(json.dumps({
        "lens_id": "transient_v1",
        "version": "0.1.0",
        "description": "transient test pack",
        "schema_version": "1.0.0",
        "display_name": "Transient",
        "primary_substrate": "none",
        "semantic_domain_preferences": [],
        "cognitive_mode_label": "",
        "mastery_report_sha256": "",
    }))
    monkeypatch.setenv("CORE_ALLOW_UNRATIFIED_ANCHOR_LENS", "1")
    lens = load_anchor_lens("transient_v1", search_paths=(tmp_path,))
    assert lens.lens_id == "transient_v1"


def test_companion_sha_mismatch_rejected(tmp_path: Path):
    """Pack declares a SHA that doesn't match the on-disk report."""
    # Copy ratified pack + report
    src = Path("packs/anchor_lens")
    shutil.copy(src / "default_unanchored_v1.json", tmp_path / "default_unanchored_v1.json")
    shutil.copy(
        src / "default_unanchored_v1.mastery_report.json",
        tmp_path / "default_unanchored_v1.mastery_report.json",
    )
    # Tamper with pack's declared SHA
    pack_path = tmp_path / "default_unanchored_v1.json"
    raw = json.loads(pack_path.read_text())
    raw["mastery_report_sha256"] = "0" * 64
    pack_path.write_text(json.dumps(raw))
    with pytest.raises(AnchorLensError, match="does not match"):
        load_anchor_lens(
            "default_unanchored_v1", search_paths=(tmp_path,),
            require_ratified=True,
        )


# ---------- bounds violations ----------


def _base_pack(**overrides) -> dict:
    base = {
        "lens_id": "test_v1",
        "version": "0.1.0",
        "description": "test",
        "schema_version": "1.0.0",
        "display_name": "Test",
        "primary_substrate": "none",
        "semantic_domain_preferences": [],
        "cognitive_mode_label": "",
        "mastery_report_sha256": "",
    }
    base.update(overrides)
    return base


def _write(tmp_path: Path, pack: dict) -> None:
    (tmp_path / f"{pack['lens_id']}.json").write_text(json.dumps(pack))


def _load_unratified(tmp_path: Path, lens_id: str) -> AnchorLens:
    return load_anchor_lens(
        lens_id, search_paths=(tmp_path,), require_ratified=False,
    )


def test_unknown_substrate_rejected(tmp_path: Path):
    _write(tmp_path, _base_pack(primary_substrate="latin"))
    with pytest.raises(AnchorLensError, match="primary_substrate"):
        _load_unratified(tmp_path, "test_v1")


def test_preferences_must_be_list(tmp_path: Path):
    _write(tmp_path, _base_pack(semantic_domain_preferences="not_a_list"))
    with pytest.raises(AnchorLensError, match="must be a list"):
        _load_unratified(tmp_path, "test_v1")


def test_atom_must_be_nonempty_string(tmp_path: Path):
    _write(tmp_path, _base_pack(
        primary_substrate="grc",
        semantic_domain_preferences=[""],
        cognitive_mode_label="experiential",
    ))
    with pytest.raises(AnchorLensError, match="non-empty"):
        _load_unratified(tmp_path, "test_v1")


def test_atom_length_capped(tmp_path: Path):
    _write(tmp_path, _base_pack(
        primary_substrate="grc",
        semantic_domain_preferences=["x" * 65],
        cognitive_mode_label="experiential",
    ))
    with pytest.raises(AnchorLensError, match="≤"):
        _load_unratified(tmp_path, "test_v1")


def test_duplicate_atoms_rejected(tmp_path: Path):
    _write(tmp_path, _base_pack(
        primary_substrate="grc",
        semantic_domain_preferences=["logos.foo", "logos.bar", "logos.foo"],
        cognitive_mode_label="x",
    ))
    with pytest.raises(AnchorLensError, match="duplicate"):
        _load_unratified(tmp_path, "test_v1")


def test_too_many_preferences(tmp_path: Path):
    _write(tmp_path, _base_pack(
        primary_substrate="grc",
        semantic_domain_preferences=[f"logos.a{i}" for i in range(65)],
        cognitive_mode_label="x",
    ))
    with pytest.raises(AnchorLensError, match="max is 64"):
        _load_unratified(tmp_path, "test_v1")


def test_label_length_capped(tmp_path: Path):
    _write(tmp_path, _base_pack(cognitive_mode_label="x" * 65))
    with pytest.raises(AnchorLensError, match="cognitive_mode_label"):
        _load_unratified(tmp_path, "test_v1")


def test_missing_field_rejected(tmp_path: Path):
    pack = _base_pack()
    del pack["primary_substrate"]
    _write(tmp_path, pack)
    with pytest.raises(AnchorLensError, match="missing required fields"):
        _load_unratified(tmp_path, "test_v1")


def test_lens_id_mismatch_rejected(tmp_path: Path):
    """Filename and declared lens_id must agree."""
    pack = _base_pack(lens_id="declared_different")
    (tmp_path / "test_v1.json").write_text(json.dumps(pack))
    with pytest.raises(AnchorLensError, match="declares lens_id"):
        _load_unratified(tmp_path, "test_v1")


def test_unsupported_schema_version_rejected(tmp_path: Path):
    _write(tmp_path, _base_pack(schema_version="2.0.0"))
    with pytest.raises(AnchorLensError, match="schema_version"):
        _load_unratified(tmp_path, "test_v1")

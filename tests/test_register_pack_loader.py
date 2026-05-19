"""Register pack loader tests (ADR-0068, Plan Phase R1).

Covers:
- Load / list / verify-seal happy paths
- Unregistered sentinel structural identity vs default_neutral_v1
- Ratification idempotence
- Invalid register_id rejection (traversal, empty, non-string)
- Missing mastery report rejection in production mode
- Checksum mismatch rejection
- Bounds violations (depth_preference, overrides shape, marker buckets)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from packs.register.loader import (
    DiscourseMarkers,
    RegisterPack,
    RegisterPackError,
    available_register_packs,
    load_register_pack,
    verify_register_pack_seal,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKS_DIR = REPO_ROOT / "packs" / "register"
RATIFY_SCRIPT = REPO_ROOT / "scripts" / "ratify_register_packs.py"


# ---------- happy path ----------


def test_loads_default_neutral_v1():
    pack = load_register_pack("default_neutral_v1")
    assert isinstance(pack, RegisterPack)
    assert pack.register_id == "default_neutral_v1"
    assert pack.depth_preference == "standard"
    assert pack.is_null_register()
    assert not pack.is_unregistered()
    assert pack.mastery_report_sha256 != ""


def test_unregistered_sentinel_matches_null_register_shape():
    sentinel = RegisterPack.unregistered()
    pack = load_register_pack("default_neutral_v1")
    assert sentinel.is_unregistered()
    assert sentinel.is_null_register()
    assert sentinel.depth_preference == pack.depth_preference
    assert dict(sentinel.realizer_overrides) == dict(pack.realizer_overrides)
    assert sentinel.discourse_markers == pack.discourse_markers


def test_available_register_packs_lists_default_neutral():
    listed = available_register_packs()
    ids = [entry["register_id"] for entry in listed]
    assert "default_neutral_v1" in ids
    entry = next(e for e in listed if e["register_id"] == "default_neutral_v1")
    assert entry["ratified"] is True


def test_verify_seal_default_neutral():
    assert verify_register_pack_seal("default_neutral_v1") is True


def test_pack_is_frozen():
    pack = load_register_pack("default_neutral_v1")
    with pytest.raises(Exception):
        pack.register_id = "mutated"  # type: ignore[misc]


def test_discourse_markers_is_frozen():
    markers = DiscourseMarkers(openings=("Hi",))
    with pytest.raises(Exception):
        markers.openings = ()  # type: ignore[misc]


# ---------- invalid register_id ----------


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "../etc/passwd",
        "foo/bar",
        "foo\\bar",
        "..",
    ],
)
def test_invalid_register_id_rejected(bad):
    with pytest.raises(RegisterPackError):
        load_register_pack(bad)


def test_missing_pack_rejected():
    with pytest.raises(RegisterPackError, match="not found"):
        load_register_pack("no_such_pack_v99")


# ---------- bounds checks ----------


def _write_pack(tmp_path: Path, register_id: str, body: dict) -> None:
    (tmp_path / f"{register_id}.json").write_text(
        json.dumps(body, indent=2) + "\n", encoding="utf-8",
    )


def _baseline_body(register_id: str) -> dict:
    return {
        "register_id": register_id,
        "version": "1.0.0",
        "description": "test pack",
        "schema_version": "1.0.0",
        "mastery_report_sha256": "",
        "display_name": "Test",
        "depth_preference": "standard",
        "realizer_overrides": {},
        "discourse_markers": {
            "openings": [],
            "transitions": [],
            "closings": [],
        },
    }


def test_unknown_schema_version_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    body["schema_version"] = "2.0.0"
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="schema_version"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


def test_missing_field_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    del body["display_name"]
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="missing required fields"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


def test_register_id_field_must_match_filename(tmp_path):
    body = _baseline_body("custom_v1")
    body["register_id"] = "different_id"
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="declares register_id"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


@pytest.mark.parametrize("bad_depth", ["", "fast", "verbose", 1])
def test_invalid_depth_preference_rejected(tmp_path, bad_depth):
    body = _baseline_body("custom_v1")
    body["depth_preference"] = bad_depth
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="depth_preference"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


def test_overrides_must_be_dict(tmp_path):
    body = _baseline_body("custom_v1")
    body["realizer_overrides"] = ["not", "a", "dict"]
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="realizer_overrides"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


def test_missing_marker_bucket_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    body["discourse_markers"] = {"openings": [], "transitions": []}
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="missing buckets"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


def test_marker_empty_string_is_allowed(tmp_path):
    """ADR-0071 (R4): empty-string entries are legitimate — they let
    the seeded selector pick "no marker this turn"."""
    body = _baseline_body("custom_v1")
    body["discourse_markers"]["openings"] = ["", "Hello"]
    _write_pack(tmp_path, "custom_v1", body)
    pack = load_register_pack(
        "custom_v1",
        search_paths=(tmp_path,),
        require_ratified=False,
    )
    assert pack.discourse_markers.openings == ("", "Hello")


def test_marker_must_be_string(tmp_path):
    """Non-string entries are still refused."""
    body = _baseline_body("custom_v1")
    body["discourse_markers"]["openings"] = [42]
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="openings"):
        load_register_pack(
            "custom_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )


# ---------- ratification gating ----------


def test_unratified_pack_refused_by_default(tmp_path):
    body = _baseline_body("custom_v1")
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="not ratified"):
        load_register_pack("custom_v1", search_paths=(tmp_path,))


def test_unratified_pack_loads_when_require_ratified_false(tmp_path):
    body = _baseline_body("custom_v1")
    _write_pack(tmp_path, "custom_v1", body)
    pack = load_register_pack(
        "custom_v1",
        search_paths=(tmp_path,),
        require_ratified=False,
    )
    assert pack.register_id == "custom_v1"


def test_env_escape_allows_unratified(tmp_path, monkeypatch):
    body = _baseline_body("custom_v1")
    _write_pack(tmp_path, "custom_v1", body)
    monkeypatch.setenv("CORE_ALLOW_UNRATIFIED_REGISTER", "1")
    pack = load_register_pack("custom_v1", search_paths=(tmp_path,))
    assert pack.register_id == "custom_v1"


def test_declared_sha_without_companion_report_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    body["mastery_report_sha256"] = "a" * 64
    _write_pack(tmp_path, "custom_v1", body)
    with pytest.raises(RegisterPackError, match="companion report"):
        load_register_pack("custom_v1", search_paths=(tmp_path,))


def test_companion_report_sha_mismatch_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    body["mastery_report_sha256"] = "a" * 64
    _write_pack(tmp_path, "custom_v1", body)
    report = {
        "register_id": "custom_v1",
        "ratified": True,
        "report_sha256": "b" * 64,
    }
    (tmp_path / "custom_v1.mastery_report.json").write_text(
        json.dumps(report), encoding="utf-8",
    )
    with pytest.raises(RegisterPackError, match="does not match"):
        load_register_pack("custom_v1", search_paths=(tmp_path,))


def test_companion_report_failing_seal_rejected(tmp_path):
    body = _baseline_body("custom_v1")
    bogus_sha = "c" * 64
    body["mastery_report_sha256"] = bogus_sha
    _write_pack(tmp_path, "custom_v1", body)
    report = {
        "register_id": "custom_v1",
        "ratified": True,
        "report_sha256": bogus_sha,
    }
    (tmp_path / "custom_v1.mastery_report.json").write_text(
        json.dumps(report), encoding="utf-8",
    )
    with pytest.raises(RegisterPackError, match="self-seal"):
        load_register_pack("custom_v1", search_paths=(tmp_path,))


# ---------- ratification idempotence ----------


def test_ratify_script_is_idempotent(tmp_path):
    """Running the ratify script twice produces byte-identical files."""
    work = tmp_path / "packs" / "register"
    work.mkdir(parents=True)
    shutil.copy(
        DEFAULT_PACKS_DIR / "default_neutral_v1.json",
        work / "default_neutral_v1.json",
    )
    shutil.copy(
        DEFAULT_PACKS_DIR / "default_neutral_v1.mastery_report.json",
        work / "default_neutral_v1.mastery_report.json",
    )

    pack_before = (work / "default_neutral_v1.json").read_bytes()
    report_before = (
        work / "default_neutral_v1.mastery_report.json"
    ).read_bytes()

    env = {
        "PYTHONPATH": str(REPO_ROOT),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    result = subprocess.run(
        [sys.executable, str(RATIFY_SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "idempotent" in result.stdout

    pack_after = (DEFAULT_PACKS_DIR / "default_neutral_v1.json").read_bytes()
    report_after = (
        DEFAULT_PACKS_DIR / "default_neutral_v1.mastery_report.json"
    ).read_bytes()

    assert pack_before == pack_after
    assert report_before == report_after

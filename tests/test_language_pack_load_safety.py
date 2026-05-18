"""Trust-boundary tests for ``language_packs.compiler`` pack loading (ADR-0051).

These tests guard the path-traversal boundary at every public entrypoint
that takes a ``pack_id`` string and resolves it into a filesystem path
under ``language_packs/data/``.  The guard runs *before* any
:class:`pathlib.Path` join so a malicious id cannot escape the data
directory even briefly.
"""
from __future__ import annotations

import pytest

from language_packs.compiler import (
    _validate_pack_id,
    load_mounted_packs,
    load_pack,
    load_pack_entries,
)


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "..",
        "../etc",
        "../../etc/passwd",
        "/etc/passwd",
        "/tmp/foo",
        "foo/bar",
        r"foo\bar",
        ".hidden",
        "..foo",
        "foo bar",  # whitespace
        "foo\nbar",  # newline
        "foo\x00bar",  # null byte
        "café",  # non-ascii
    ],
)
def test_validate_pack_id_rejects_unsafe_inputs(bad: str) -> None:
    with pytest.raises(ValueError):
        _validate_pack_id(bad)


@pytest.mark.parametrize(
    "bad_type",
    [None, 123, b"en_core_cognition_v1", ["en"], {"id": "en"}],
)
def test_validate_pack_id_rejects_non_strings(bad_type: object) -> None:
    with pytest.raises(ValueError):
        _validate_pack_id(bad_type)


@pytest.mark.parametrize(
    "good",
    ["en", "en_core_cognition_v1", "grc_logos_micro_v1", "he-test", "abc123"],
)
def test_validate_pack_id_accepts_safe_inputs(good: str) -> None:
    assert _validate_pack_id(good) == good


def test_load_pack_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        load_pack("../etc")


def test_load_pack_rejects_absolute_path() -> None:
    with pytest.raises(ValueError):
        load_pack("/etc/passwd")


def test_load_pack_rejects_empty() -> None:
    with pytest.raises(ValueError):
        load_pack("")


def test_load_pack_entries_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        load_pack_entries("../etc")


def test_load_pack_entries_rejects_path_separator() -> None:
    with pytest.raises(ValueError):
        load_pack_entries("foo/bar")


def test_load_mounted_packs_rejects_traversal_in_any_id() -> None:
    # Even a single bad id in the tuple must fail closed before any
    # filesystem access.
    with pytest.raises(ValueError):
        load_mounted_packs(("en_core_cognition_v1", "../etc"))


def test_load_mounted_packs_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        load_mounted_packs(("",))


def test_load_pack_does_not_touch_filesystem_for_bad_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard must fire *before* any Path operation.

    We monkeypatch ``Path.read_text`` to explode loudly; if the guard is
    missing or weakened, the test fails with the wrong exception type and
    we know the boundary moved.
    """
    from pathlib import Path

    def boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("filesystem touched before pack_id validation")

    monkeypatch.setattr(Path, "read_text", boom)
    monkeypatch.setattr(Path, "read_bytes", boom)

    with pytest.raises(ValueError):
        load_pack("../escape")


def test_load_pack_still_works_on_real_pack() -> None:
    """Smoke test: the guard does not break the happy path."""
    manifest, manifold = load_pack("en_core_cognition_v1")
    assert manifest.pack_id == "en_core_cognition_v1"
    assert len(manifold) > 0

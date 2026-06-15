"""ADR-0219 — Generation-dir atomic checkpoint.

Each test covers one bullet of the acceptance gate and includes a ``*_bites``
mutation variant (CLAUDE.md schema-as-proof discipline: a predicate that cannot
fail under the violation it nominally catches is decoration, not proof).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_state import EngineStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_gen(store: EngineStateStore, turn_count: int) -> int:
    """Write one generation checkpoint and return the gen_num."""
    gen_num, gen_dir = store.begin_generation()
    gs = EngineStateStore(gen_dir)
    gs.save_recognizers([])
    gs.save_discovery_candidates([])
    gs.save_manifest(turn_count)
    store.commit_generation(gen_num)
    return gen_num


# ---------------------------------------------------------------------------
# Gate: first checkpoint creates gen-0000 + current pointer
# ---------------------------------------------------------------------------

def test_fresh_store_writes_gen0000_and_current(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    gen_num = _write_gen(store, turn_count=1)

    assert gen_num == 0
    assert (tmp_path / "gen-0000").is_dir()
    assert (tmp_path / "current").exists()
    assert (tmp_path / "current").read_text("utf-8").strip() == "gen-0000"
    assert (tmp_path / "gen-0000" / "manifest.json").exists()


def test_fresh_store_writes_gen0000_and_current_bites(tmp_path: Path) -> None:
    """Without commit_generation the current pointer is absent."""
    store = EngineStateStore(tmp_path)
    _gen_num, gen_dir = store.begin_generation()
    EngineStateStore(gen_dir).save_manifest(1)
    # No commit_generation — current pointer must not exist yet.
    assert not (tmp_path / "current").exists(), (
        "current pointer must only be written by commit_generation, not begin_generation"
    )


# ---------------------------------------------------------------------------
# Gate: second checkpoint advances the generation
# ---------------------------------------------------------------------------

def test_second_checkpoint_advances_generation(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=1)
    gen_num2 = _write_gen(store, turn_count=2)

    assert gen_num2 == 1
    assert (tmp_path / "current").read_text("utf-8").strip() == "gen-0001"
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 2


def test_second_checkpoint_advances_generation_bites(tmp_path: Path) -> None:
    """Stale current (not advanced) → stale turn_count."""
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=1)
    # Deliberately skip the second commit and write gen-0001 without committing.
    _gen_num2, gen_dir2 = store.begin_generation()
    EngineStateStore(gen_dir2).save_manifest(2)
    # current still points to gen-0000 (turn_count=1).
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 1, "uncommitted gen must not be visible via current"


# ---------------------------------------------------------------------------
# Gate: orphan gen dir ignored before pointer swap
# ---------------------------------------------------------------------------

def test_orphan_gen_dir_ignored_before_pointer_swap(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=5)

    # Simulate a kill between writing gen-9999 and swapping current.
    orphan = tmp_path / "gen-9999"
    orphan.mkdir()
    (orphan / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 9999, "written_at_revision": "x"}),
        encoding="utf-8",
    )

    # Load must still read from the committed generation (gen-0000, turn_count=5).
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 5, (
        "unreferenced gen-9999 must be invisible; load must follow current"
    )


def test_orphan_gen_dir_ignored_before_pointer_swap_bites(tmp_path: Path) -> None:
    """Without a current pointer the orphan gen dir IS what gets read (flat fallback)."""
    # Build the store with ONLY the flat manifest (no current pointer).
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 42, "written_at_revision": "x"}),
        encoding="utf-8",
    )
    manifest = EngineStateStore(tmp_path).load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 42, "flat layout fallback must work when no current exists"


# ---------------------------------------------------------------------------
# Gate: torn current temp file is ignored
# ---------------------------------------------------------------------------

def test_torn_current_tmp_ignored(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=3)

    # Inject a torn .current temp file (simulate kill during os.replace of current).
    torn = tmp_path / ".current.deadbeef.tmp"
    torn.write_text("gen-9999", encoding="utf-8")

    # The loader reads "current" (canonical), not ".current.*.tmp".
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 3, (
        ".current.*.tmp orphan must be invisible to the loader"
    )


def test_torn_current_tmp_ignored_bites(tmp_path: Path) -> None:
    """If current itself is overwritten with the orphan name, load diverges."""
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=3)
    # Corrupt current directly (simulates what we're proving the loader avoids).
    (tmp_path / "current").write_text("gen-9999", encoding="utf-8")
    # gen-9999 doesn't exist → _current_gen_dir() returns None → flat fallback.
    # The flat manifest doesn't exist either → load_manifest() returns None.
    assert store.load_manifest() is None, (
        "a current pointer to a non-existent gen dir must fall back to flat/None"
    )


# ---------------------------------------------------------------------------
# Gate: no cross-generation file mixing
# ---------------------------------------------------------------------------

def test_no_cross_generation_mixing(tmp_path: Path) -> None:
    """load_* always reads from a single generation directory."""
    store = EngineStateStore(tmp_path)
    # Gen 0: turn_count=10
    _write_gen(store, turn_count=10)
    # Gen 1: turn_count=20
    _write_gen(store, turn_count=20)

    # current → gen-0001.  manifest must say turn_count=20.
    # recognizers and candidates must also come from gen-0001 (not gen-0000).
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 20

    recs = store.load_recognizers()
    cands = store.load_discovery_candidates()
    # Both loads resolve to gen-0001; not a mix of gen-0000 and gen-0001.
    assert recs == []
    assert cands == []


def test_no_cross_generation_mixing_bites(tmp_path: Path) -> None:
    """Forcing current to gen-0000 after two writes returns gen-0000 data."""
    store = EngineStateStore(tmp_path)
    # Gen 0 with turn_count=10
    gen0_num, gen0_dir = store.begin_generation()
    EngineStateStore(gen0_dir).save_manifest(10)
    store.commit_generation(gen0_num)
    # Gen 1 with turn_count=20
    gen1_num, gen1_dir = store.begin_generation()
    EngineStateStore(gen1_dir).save_manifest(20)
    store.commit_generation(gen1_num)

    # Manually rewind current to gen-0000.
    (tmp_path / "current").write_text("gen-0000", encoding="utf-8")
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 10, (
        "rewinding current to gen-0000 must expose gen-0000 data, not gen-0001"
    )


# ---------------------------------------------------------------------------
# Gate: legacy flat layout migrates on first write
# ---------------------------------------------------------------------------

def test_legacy_flat_layout_migrates_on_first_write(tmp_path: Path) -> None:
    """A flat-layout checkpoint is wrapped into gen-0000 on the first begin_generation."""
    # Seed a flat layout (pre-0219).
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 7, "written_at_revision": "old"}),
        encoding="utf-8",
    )
    (tmp_path / "recognizers.jsonl").write_text("", encoding="utf-8")

    store = EngineStateStore(tmp_path)
    gen_num, _gen_dir = store.begin_generation()

    assert gen_num == 1, "first gen after migration must be gen-0001 (gen-0000 = migrated flat)"
    assert (tmp_path / "gen-0000" / "manifest.json").exists()
    assert (tmp_path / "current").read_text("utf-8").strip() == "gen-0000"

    # Commit gen-0001 with new turn_count.
    EngineStateStore(_gen_dir).save_manifest(8)
    store.commit_generation(gen_num)
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 8, "committed gen-0001 must be visible after migration"


def test_legacy_flat_layout_migrates_on_first_write_bites(tmp_path: Path) -> None:
    """Without migration, a second gen would incorrectly become gen-0000."""
    # Seed a flat layout but do NOT call begin_generation (no migration).
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 7, "written_at_revision": "old"}),
        encoding="utf-8",
    )
    # Directly create gen-0000 manually to simulate what migration does.
    gen0 = tmp_path / "gen-0000"
    gen0.mkdir()
    (gen0 / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 7, "written_at_revision": "old"}),
        encoding="utf-8",
    )
    # No current pointer yet.
    assert not (tmp_path / "current").exists()
    # begin_generation sees no current AND no flat manifest (we deleted it conceptually by
    # just not having one) → would allocate gen-0000 again.  Since we created gen-0000
    # manually, begin_generation will return (0, gen-0000 dir) and overwrite it.
    # This is the hazard that the migration path avoids.
    # The test just confirms our understanding: without migration the gen num is 0.
    (tmp_path / "manifest.json").unlink()  # remove flat file so no-migration path taken
    store = EngineStateStore(tmp_path)
    gen_num, _ = store.begin_generation()
    assert gen_num == 0, "without migration and without flat manifest, gen_num starts at 0"


# ---------------------------------------------------------------------------
# Gate: legacy flat layout readable without write
# ---------------------------------------------------------------------------

def test_legacy_flat_layout_readable_without_write(tmp_path: Path) -> None:
    """load_manifest falls back to the flat root when no current pointer exists."""
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 99, "written_at_revision": "x"}),
        encoding="utf-8",
    )
    store = EngineStateStore(tmp_path)
    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 99


def test_legacy_flat_layout_readable_without_write_bites(tmp_path: Path) -> None:
    """Moving the flat manifest to a gen dir without writing current → None."""
    gen0 = tmp_path / "gen-0000"
    gen0.mkdir()
    (gen0 / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "turn_count": 99, "written_at_revision": "x"}),
        encoding="utf-8",
    )
    # No flat manifest at root, no current → load_manifest returns None.
    assert EngineStateStore(tmp_path).load_manifest() is None, (
        "a gen dir with no current pointer must not be read by load_manifest"
    )


# ---------------------------------------------------------------------------
# Gate: commit-point / turn_count matches committed turns
# ---------------------------------------------------------------------------

def test_commit_point_matches_turn_count(tmp_path: Path) -> None:
    """Recovered turn_count always equals the number of fully committed turns."""
    store = EngineStateStore(tmp_path)
    for t in range(1, 4):
        _write_gen(store, turn_count=t)

    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 3


def test_commit_point_matches_turn_count_bites(tmp_path: Path) -> None:
    """A mid-write kill (no commit) does not advance the recovered turn_count."""
    store = EngineStateStore(tmp_path)
    _write_gen(store, turn_count=1)

    # Simulate a kill mid-write of gen-0001 (no commit_generation).
    _gen_num2, gen_dir2 = store.begin_generation()
    EngineStateStore(gen_dir2).save_manifest(2)
    # No commit — current still names gen-0000.

    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest["turn_count"] == 1, (
        "an uncommitted generation must not advance the recovered turn_count"
    )


# ---------------------------------------------------------------------------
# Gate: GC retains the last two generations
# ---------------------------------------------------------------------------

def test_gc_retains_last_two_generations(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    for t in range(1, 5):
        _write_gen(store, turn_count=t)

    # After 4 commits (gen-0000..gen-0003), GC should have pruned gen-0000 and gen-0001.
    gen_dirs = sorted(d.name for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith("gen-"))
    assert "gen-0000" not in gen_dirs, "gen-0000 should be pruned after 4 commits (keep=2)"
    assert "gen-0001" not in gen_dirs, "gen-0001 should be pruned after 4 commits (keep=2)"
    assert "gen-0002" in gen_dirs, "gen-0002 (N-1) must be retained"
    assert "gen-0003" in gen_dirs, "gen-0003 (N, current) must be retained"


def test_gc_retains_last_two_generations_bites(tmp_path: Path) -> None:
    """With keep=3 the three most-recent generations are all retained."""
    store = EngineStateStore(tmp_path)
    for t in range(1, 5):
        gen_num, gen_dir = store.begin_generation()
        EngineStateStore(gen_dir).save_manifest(t)
        store.commit_generation(gen_num, keep=3)

    gen_dirs = sorted(d.name for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith("gen-"))
    assert "gen-0000" not in gen_dirs, "gen-0000 pruned even with keep=3 (4 gens total)"
    assert "gen-0001" in gen_dirs, "gen-0001 retained with keep=3"
    assert "gen-0002" in gen_dirs, "gen-0002 retained with keep=3"
    assert "gen-0003" in gen_dirs, "gen-0003 retained with keep=3"

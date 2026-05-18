"""ADR-0029 safety-pack tests.

Three concerns:

1. **Loader correctness.** Happy-path load of the shipping pack;
   bounds / envelope errors raise ``SafetyPackError`` (not the
   value-error-flavored ``IdentityPackError`` — safety failures are
   fail-closed runtime conditions).
2. **Fail-closed semantics.** A missing safety pack, tampered companion
   report, or unverified seal must prevent ``ChatRuntime`` startup.
3. **Composition.** The runtime ``IdentityManifold.boundary_ids`` is the
   union of identity-pack boundaries and safety-pack boundaries, every
   safety boundary is present regardless of which identity pack is
   selected, and identity-pack boundary additions do not remove safety
   boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.safety.loader import (
    DEFAULT_SAFETY_PACK,
    SafetyPackError,
    load_safety_pack,
)

SAFETY_BOUNDARIES: frozenset[str] = frozenset({
    "no_fabricated_source",
    "no_hot_path_repair",
    "no_identity_override",
    "no_silent_correction",
    "preserve_versor_closure",
})


# ---------- loader ----------


class TestLoader:
    def test_loads_shipping_pack(self) -> None:
        pack = load_safety_pack()
        assert pack.pack_id == DEFAULT_SAFETY_PACK
        assert pack.boundary_ids == SAFETY_BOUNDARIES
        assert pack.ratified is True
        # Descriptions exist for every boundary.
        for b in SAFETY_BOUNDARIES:
            assert pack.boundary_descriptions[b]

    def test_loads_in_production_mode_by_default(self) -> None:
        # Loader's default require_ratified=None resolves to production
        # mode unless CORE_ALLOW_UNRATIFIED_SAFETY=1 is set.  Shipping
        # pack is ratified so it loads cleanly.
        pack = load_safety_pack()
        assert pack.ratified is True

    def test_missing_pack_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(SafetyPackError, match="not found"):
            load_safety_pack(search_paths=[tmp_path])

    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(SafetyPackError, match="invalid safety pack_id"):
            load_safety_pack(pack_id="../../etc/passwd")

    def test_unratified_pack_refused_in_production(
        self, tmp_path: Path,
    ) -> None:
        bad = _write_pack(tmp_path, mastery_report_sha256="")
        with pytest.raises(SafetyPackError, match="not ratified"):
            load_safety_pack(
                pack_id=bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=True,
            )

    def test_missing_companion_report_refused(self, tmp_path: Path) -> None:
        bad = _write_pack(tmp_path, mastery_report_sha256="0" * 64)
        with pytest.raises(SafetyPackError, match="companion report"):
            load_safety_pack(
                pack_id=bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=True,
            )

    def test_companion_seal_failure_refused(self, tmp_path: Path) -> None:
        bogus = "d" * 64
        bad = _write_pack(tmp_path, mastery_report_sha256=bogus)
        report_path = tmp_path / f"{bad['pack_id']}.mastery_report.json"
        report_path.write_text(
            json.dumps({"report_sha256": bogus, "ratified": True, "x": 1}),
            encoding="utf-8",
        )
        with pytest.raises(SafetyPackError, match="self-seal"):
            load_safety_pack(
                pack_id=bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=True,
            )

    def test_empty_boundaries_refused(self, tmp_path: Path) -> None:
        bad = _write_pack(tmp_path, boundary_ids=[])
        with pytest.raises(SafetyPackError, match="boundary_ids"):
            load_safety_pack(
                pack_id=bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=False,
            )

    def test_duplicate_boundary_refused(self, tmp_path: Path) -> None:
        bad = _write_pack(
            tmp_path,
            boundary_ids=["a", "b", "a"],
        )
        with pytest.raises(SafetyPackError, match="duplicate"):
            load_safety_pack(
                pack_id=bad["pack_id"],
                search_paths=[tmp_path],
                require_ratified=False,
            )


# ---------- runtime composition ----------


class TestRuntimeComposition:
    def test_default_runtime_has_safety_pack(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert rt.safety_pack.pack_id == DEFAULT_SAFETY_PACK
        assert rt.safety_pack.boundary_ids == SAFETY_BOUNDARIES

    def test_safety_boundaries_present_under_default_identity(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert SAFETY_BOUNDARIES <= rt.identity_manifold.boundary_ids

    def test_safety_boundaries_present_under_precision_identity(self) -> None:
        rt = ChatRuntime(
            config=RuntimeConfig(identity_pack="precision_first_v1"),
        )
        assert SAFETY_BOUNDARIES <= rt.identity_manifold.boundary_ids

    def test_safety_boundaries_present_under_generosity_identity(self) -> None:
        rt = ChatRuntime(
            config=RuntimeConfig(identity_pack="generosity_first_v1"),
        )
        assert SAFETY_BOUNDARIES <= rt.identity_manifold.boundary_ids

    def test_precision_pack_adds_boundary_on_top(self) -> None:
        # precision_first_v1 declares ``no_overstatement`` in its
        # boundary_ids.  After composition with safety pack, both
        # safety boundaries AND ``no_overstatement`` must be present.
        rt = ChatRuntime(
            config=RuntimeConfig(identity_pack="precision_first_v1"),
        )
        assert "no_overstatement" in rt.identity_manifold.boundary_ids
        assert SAFETY_BOUNDARIES <= rt.identity_manifold.boundary_ids

    def test_identity_axes_unchanged_by_safety_pack(self) -> None:
        # Safety pack does not contribute value_axes.  Identity axis
        # set is exactly what the identity pack declares.
        rt = ChatRuntime(config=RuntimeConfig())
        axis_ids = {a.axis_id for a in rt.identity_manifold.value_axes}
        assert axis_ids == {"truthfulness", "coherence", "reverence"}


# ---------- helpers ----------


def _write_pack(
    tmp_path: Path,
    *,
    pack_id: str = "test_safety_pack",
    boundary_ids: list[str] | None = None,
    mastery_report_sha256: str = "",
) -> dict:
    body = {
        "pack_id": pack_id,
        "version": "1.0.0",
        "description": "test",
        "schema_version": "1.0.0",
        "mastery_report_sha256": mastery_report_sha256,
        "boundary_ids": ["test_boundary"] if boundary_ids is None else boundary_ids,
        "boundary_descriptions": {},
    }
    path = tmp_path / f"{pack_id}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return body

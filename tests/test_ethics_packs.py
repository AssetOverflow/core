"""ADR-0033 — ethics-pack loader, ratification, and composition."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.config import DEFAULT_ETHICS_PACK, RuntimeConfig
from packs.ethics.loader import (
    EthicsPack,
    EthicsPackError,
    available_packs,
    load_ethics_pack,
)


ETHICS_DIR = Path(__file__).resolve().parents[1] / "packs" / "ethics"
DEFAULT_PACK_PATH = ETHICS_DIR / f"{DEFAULT_ETHICS_PACK}.json"


# ---------- loader basics ----------


class TestLoaderHappyPath:
    def test_loads_default_pack(self) -> None:
        pack = load_ethics_pack()
        assert isinstance(pack, EthicsPack)
        assert pack.pack_id == DEFAULT_ETHICS_PACK
        assert pack.domain == "general"
        assert pack.commitment_ids
        assert pack.ratified

    def test_default_pack_has_expected_commitments(self) -> None:
        pack = load_ethics_pack()
        assert "acknowledge_uncertainty" in pack.commitment_ids
        assert "no_manipulation" in pack.commitment_ids
        assert "respect_user_autonomy" in pack.commitment_ids


# ---------- bounds checks ----------


class TestLoaderBounds:
    def test_missing_pack_raises(self) -> None:
        with pytest.raises(EthicsPackError, match="not found"):
            load_ethics_pack("nonexistent_pack_v999")

    def test_invalid_pack_id_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(EthicsPackError, match="invalid"):
            load_ethics_pack("../escape", search_paths=[tmp_path])

    def test_pack_id_mismatch_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "real_id.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "DIFFERENT",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "general",
                    "commitment_ids": ["a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="declares pack_id"):
            load_ethics_pack(
                "real_id", search_paths=[tmp_path], require_ratified=False,
            )

    def test_empty_commitments_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "bad",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "general",
                    "commitment_ids": [],
                    "commitment_descriptions": {},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="non-empty list"):
            load_ethics_pack(
                "bad", search_paths=[tmp_path], require_ratified=False,
            )

    def test_duplicate_commitment_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "dup.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "dup",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "general",
                    "commitment_ids": ["a", "a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="duplicate"):
            load_ethics_pack(
                "dup", search_paths=[tmp_path], require_ratified=False,
            )

    def test_unknown_domain_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "weird.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "weird",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "occult",
                    "commitment_ids": ["a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="domain"):
            load_ethics_pack(
                "weird", search_paths=[tmp_path], require_ratified=False,
            )

    def test_unsupported_schema_version_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "future.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "future",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "2.0.0",
                    "domain": "general",
                    "commitment_ids": ["a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="schema_version"):
            load_ethics_pack(
                "future", search_paths=[tmp_path], require_ratified=False,
            )


# ---------- ratification ----------


class TestRatification:
    def test_unratified_pack_rejected_in_production_mode(
        self, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "unratified.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "unratified",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "general",
                    "mastery_report_sha256": "",
                    "commitment_ids": ["a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        with pytest.raises(EthicsPackError, match="not ratified"):
            load_ethics_pack(
                "unratified",
                search_paths=[tmp_path],
                require_ratified=True,
            )

    def test_unratified_accepted_when_explicitly_overridden(
        self, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "ok.json"
        bad.write_text(
            json.dumps(
                {
                    "pack_id": "ok",
                    "version": "1.0.0",
                    "description": "x",
                    "schema_version": "1.0.0",
                    "domain": "general",
                    "commitment_ids": ["a"],
                    "commitment_descriptions": {"a": "x"},
                }
            )
        )
        pack = load_ethics_pack(
            "ok", search_paths=[tmp_path], require_ratified=False,
        )
        assert pack.pack_id == "ok"
        assert not pack.ratified

    def test_default_pack_is_ratified(self) -> None:
        pack = load_ethics_pack()
        assert pack.ratified
        assert len(pack.mastery_report_sha256) == 64


# ---------- discovery ----------


class TestAvailablePacks:
    def test_default_pack_discovered(self) -> None:
        listing = available_packs()
        ids = [p["pack_id"] for p in listing]
        assert DEFAULT_ETHICS_PACK in ids

    def test_mastery_report_not_listed(self) -> None:
        listing = available_packs()
        for p in listing:
            assert not str(p["pack_id"]).endswith(".mastery_report")
            assert not str(p["path"]).endswith(".mastery_report.json")


# ---------- ChatRuntime composition ----------


class TestChatRuntimeComposition:
    def test_runtime_exposes_ethics_pack(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert rt.ethics_pack.pack_id == DEFAULT_ETHICS_PACK
        assert rt.ethics_pack_id == DEFAULT_ETHICS_PACK

    def test_commitments_union_into_manifold_boundaries(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        # Every commitment id should be present in the composed manifold.
        for c in rt.ethics_pack.commitment_ids:
            assert c in rt.identity_manifold.boundary_ids

    def test_safety_boundaries_still_present_after_ethics_union(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        for b in rt.safety_pack.boundary_ids:
            assert b in rt.identity_manifold.boundary_ids

    def test_ethics_commitments_disjoint_from_safety_boundaries(self) -> None:
        # Sanity: ethics commitments and safety boundaries should not
        # share ids in v1.  Same id from two layers is legal (union) but
        # would indicate a naming collision worth surfacing.
        rt = ChatRuntime(config=RuntimeConfig())
        overlap = rt.ethics_pack.commitment_ids & rt.safety_pack.boundary_ids
        assert overlap == frozenset()

    def test_bad_ethics_pack_id_falls_back_to_default(self) -> None:
        rt = ChatRuntime(
            config=RuntimeConfig(ethics_pack="this_pack_does_not_exist_v1"),
        )
        assert rt.ethics_pack_id == DEFAULT_ETHICS_PACK

    def test_composition_under_each_identity_pack(self) -> None:
        for identity_pack in (
            "default_general_v1",
            "precision_first_v1",
            "generosity_first_v1",
        ):
            rt = ChatRuntime(
                config=RuntimeConfig(identity_pack=identity_pack),
            )
            for c in rt.ethics_pack.commitment_ids:
                assert c in rt.identity_manifold.boundary_ids, (
                    f"commitment {c!r} missing under identity={identity_pack}"
                )
            for b in rt.safety_pack.boundary_ids:
                assert b in rt.identity_manifold.boundary_ids

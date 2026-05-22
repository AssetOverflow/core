"""Unit tests for ProposalSource and ADR-0094 schema widening."""

from __future__ import annotations

import json
from pathlib import Path
from typing import assert_never

import pytest

from teaching.migrate_proposals_source_field import (
    DEFAULT_OPERATOR_SOURCE_PAYLOAD,
    PRE_MIGRATION_SENTINEL,
    migrate_file,
)
from teaching.source import (
    ALLOWED_KINDS,
    ProposalSource,
    ProposalSourceError,
)


class TestProposalSourceConstruction:
    def test_operator_default_constructor(self) -> None:
        src = ProposalSource.operator(emitted_at_revision="abc123")
        assert src.kind == "operator"
        assert src.source_id == ""
        assert src.emitted_at_revision == "abc123"

    def test_miner_requires_source_id(self) -> None:
        with pytest.raises(ProposalSourceError, match="non-empty source_id"):
            ProposalSource(kind="miner", source_id="", emitted_at_revision="abc")

    def test_curriculum_requires_source_id(self) -> None:
        with pytest.raises(ProposalSourceError, match="non-empty source_id"):
            ProposalSource(kind="curriculum", source_id="", emitted_at_revision="abc")

    def test_contemplation_requires_source_id(self) -> None:
        with pytest.raises(ProposalSourceError, match="non-empty source_id"):
            ProposalSource(kind="contemplation", source_id="", emitted_at_revision="abc")

    def test_operator_rejects_source_id(self) -> None:
        with pytest.raises(ProposalSourceError, match="empty source_id"):
            ProposalSource(kind="operator", source_id="something", emitted_at_revision="abc")

    def test_unknown_kind_rejected(self) -> None:
        with pytest.raises(ProposalSourceError, match="kind must be one of"):
            ProposalSource(
                kind="alien",  # type: ignore[arg-type]
                source_id="x",
                emitted_at_revision="abc",
            )

    def test_empty_revision_rejected(self) -> None:
        with pytest.raises(ProposalSourceError, match="emitted_at_revision"):
            ProposalSource(kind="operator", source_id="", emitted_at_revision="")

    def test_frozen(self) -> None:
        src = ProposalSource.operator(emitted_at_revision="abc")
        with pytest.raises((AttributeError, TypeError)):
            src.kind = "miner"  # type: ignore[misc]


class TestSerialization:
    def test_operator_serializes_to_kind_only(self) -> None:
        src = ProposalSource.operator(emitted_at_revision="abc")
        assert src.serialize() == "operator"

    def test_miner_serializes_kind_and_id(self) -> None:
        src = ProposalSource(
            kind="miner",
            source_id="articulation_quality",
            emitted_at_revision="abc",
        )
        assert src.serialize() == "miner:articulation_quality"

    def test_curriculum_serializes_kind_and_id(self) -> None:
        src = ProposalSource(
            kind="curriculum",
            source_id="math_logic_v1",
            emitted_at_revision="abc",
        )
        assert src.serialize() == "curriculum:math_logic_v1"

    def test_contemplation_serializes_kind_and_id(self) -> None:
        src = ProposalSource(
            kind="contemplation",
            source_id="frontier_compare",
            emitted_at_revision="abc",
        )
        assert src.serialize() == "contemplation:frontier_compare"

    def test_round_trip_operator(self) -> None:
        src = ProposalSource.operator(emitted_at_revision="abc")
        roundtrip = ProposalSource.from_dict(src.as_dict())
        assert roundtrip == src

    def test_round_trip_miner(self) -> None:
        src = ProposalSource(kind="miner", source_id="m1", emitted_at_revision="abc")
        roundtrip = ProposalSource.from_dict(src.as_dict())
        assert roundtrip == src

    def test_from_dict_rejects_unknown_field(self) -> None:
        with pytest.raises(ProposalSourceError, match="unknown fields"):
            ProposalSource.from_dict(
                {
                    "kind": "operator",
                    "source_id": "",
                    "emitted_at_revision": "abc",
                    "extra": "nope",
                }
            )

    def test_from_dict_rejects_missing_field(self) -> None:
        with pytest.raises(ProposalSourceError, match="missing required fields"):
            ProposalSource.from_dict({"kind": "operator", "source_id": ""})

    def test_from_dict_rejects_non_mapping(self) -> None:
        with pytest.raises(ProposalSourceError, match="must be a mapping"):
            ProposalSource.from_dict("operator")


class TestExhaustiveMatchPattern:
    """Demonstrate the exhaustive-match pattern enforced by ADR-0094.

    A consumer that branches on ``source.kind`` must cover all sealed
    values; ``assert_never`` on the catch-all guards against future
    additions without ADR widening.
    """

    @staticmethod
    def _describe(src: ProposalSource) -> str:
        match src.kind:
            case "operator":
                return "op"
            case "miner":
                return f"m:{src.source_id}"
            case "curriculum":
                return f"c:{src.source_id}"
            case "contemplation":
                return f"q:{src.source_id}"
            case _:  # pragma: no cover - exhaustiveness
                assert_never(src.kind)

    def test_covers_operator(self) -> None:
        assert self._describe(ProposalSource.operator(emitted_at_revision="x")) == "op"

    def test_covers_miner(self) -> None:
        src = ProposalSource(kind="miner", source_id="art", emitted_at_revision="x")
        assert self._describe(src) == "m:art"

    def test_covers_curriculum(self) -> None:
        src = ProposalSource(kind="curriculum", source_id="cur", emitted_at_revision="x")
        assert self._describe(src) == "c:cur"

    def test_covers_contemplation(self) -> None:
        src = ProposalSource(
            kind="contemplation",
            source_id="frontier_compare",
            emitted_at_revision="x",
        )
        assert self._describe(src) == "q:frontier_compare"

    def test_kinds_sealed_at_four(self) -> None:
        assert ALLOWED_KINDS == frozenset(
            {"operator", "miner", "curriculum", "contemplation"}
        )


class TestMigrationDeterminism:
    def _write_legacy_log(self, tmp_path: Path) -> Path:
        path = tmp_path / "proposals.jsonl"
        lines = [
            json.dumps(
                {
                    "event": "created",
                    "proposal": {
                        "proposal_id": "abc123",
                        "claim_domain": "factual",
                        "polarity": "affirms",
                    },
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            json.dumps(
                {"event": "replay", "proposal_id": "abc123", "replay_evidence": {}},
                sort_keys=True,
                separators=(",", ":"),
            ),
            json.dumps(
                {
                    "event": "created",
                    "proposal": {"proposal_id": "def456", "polarity": "falsifies"},
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_migration_attaches_default_source(self, tmp_path: Path) -> None:
        path = self._write_legacy_log(tmp_path)
        summary = migrate_file(path)
        assert summary["migrated_count"] == 2
        assert summary["already_had_source"] == 0
        assert summary["changed"] is True

        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        created_events = [e for e in events if e["event"] == "created"]
        for ev in created_events:
            assert ev["proposal"]["source"] == DEFAULT_OPERATOR_SOURCE_PAYLOAD

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        path = self._write_legacy_log(tmp_path)
        migrate_file(path)
        bytes_after_first = path.read_bytes()
        migrate_file(path)
        bytes_after_second = path.read_bytes()
        assert bytes_after_first == bytes_after_second

    def test_migration_deterministic_across_two_temps(self, tmp_path: Path) -> None:
        path_a = tmp_path / "a.jsonl"
        path_b = tmp_path / "b.jsonl"
        legacy = self._write_legacy_log(tmp_path)
        path_a.write_bytes(legacy.read_bytes())
        path_b.write_bytes(legacy.read_bytes())
        migrate_file(path_a)
        migrate_file(path_b)
        assert path_a.read_bytes() == path_b.read_bytes()

    def test_migration_skips_already_migrated(self, tmp_path: Path) -> None:
        path = tmp_path / "proposals.jsonl"
        line = json.dumps(
            {
                "event": "created",
                "proposal": {
                    "proposal_id": "abc",
                    "source": dict(DEFAULT_OPERATOR_SOURCE_PAYLOAD),
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(line + "\n", encoding="utf-8")
        before = path.read_bytes()
        summary = migrate_file(path)
        assert summary["already_had_source"] == 1
        assert summary["migrated_count"] == 0
        assert path.read_bytes() == before

    def test_migration_dry_run_does_not_write(self, tmp_path: Path) -> None:
        path = self._write_legacy_log(tmp_path)
        before = path.read_bytes()
        summary = migrate_file(path, dry_run=True)
        assert summary["migrated_count"] == 2
        assert path.read_bytes() == before

    def test_sentinel_revision_used(self) -> None:
        assert DEFAULT_OPERATOR_SOURCE_PAYLOAD["emitted_at_revision"] == (
            PRE_MIGRATION_SENTINEL
        )
        assert DEFAULT_OPERATOR_SOURCE_PAYLOAD["kind"] == "operator"
        assert DEFAULT_OPERATOR_SOURCE_PAYLOAD["source_id"] == ""


class TestProposalLogStrictParsing:
    """ADR-0094 requires that proposal load rejects missing source."""

    def test_strict_parse_rejects_missing_source(self, tmp_path: Path) -> None:
        from teaching.proposals import ProposalError, ProposalLog

        path = tmp_path / "proposals.jsonl"
        legacy_line = json.dumps(
            {"event": "created", "proposal": {"proposal_id": "abc", "polarity": "affirms"}},
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(legacy_line + "\n", encoding="utf-8")

        log = ProposalLog(path)
        with pytest.raises(ProposalError, match="missing required 'source'"):
            log.current_state()

    def test_strict_parse_accepts_migrated_source(self, tmp_path: Path) -> None:
        from teaching.proposals import ProposalLog

        path = tmp_path / "proposals.jsonl"
        line = json.dumps(
            {
                "event": "created",
                "proposal": {
                    "proposal_id": "abc",
                    "polarity": "affirms",
                    "source": dict(DEFAULT_OPERATOR_SOURCE_PAYLOAD),
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(line + "\n", encoding="utf-8")

        log = ProposalLog(path)
        view = log.current_state()
        assert "abc" in view
        assert view["abc"]["source"]["kind"] == "operator"

    def test_strict_parse_rejects_malformed_source(self, tmp_path: Path) -> None:
        from teaching.proposals import ProposalLog

        path = tmp_path / "proposals.jsonl"
        line = json.dumps(
            {
                "event": "created",
                "proposal": {
                    "proposal_id": "abc",
                    "polarity": "affirms",
                    "source": {"kind": "operator"},  # missing required fields
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(line + "\n", encoding="utf-8")

        log = ProposalLog(path)
        with pytest.raises(ProposalSourceError, match="missing required fields"):
            log.current_state()


class TestLiveLogParses:
    """Verify the in-tree proposals.jsonl parses under strict v1."""

    def test_live_log_loads(self) -> None:
        from teaching.proposals import DEFAULT_PROPOSAL_LOG_PATH, ProposalLog

        if not DEFAULT_PROPOSAL_LOG_PATH.exists():
            pytest.skip("live proposals log not present in this checkout")

        log = ProposalLog(DEFAULT_PROPOSAL_LOG_PATH)
        view = log.current_state()
        assert len(view) >= 1
        for pid, entry in view.items():
            assert "source" in entry, f"proposal {pid} missing source after migration"
            src = ProposalSource.from_dict(entry["source"])
            assert src.kind in ALLOWED_KINDS

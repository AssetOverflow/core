"""ADR-0099 Public Showcase Demo — unit tests."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from core.demos.showcase import (
    MAX_RUNTIME_SECONDS,
    SHOWCASE_VERSION,
    render_html,
    run_showcase,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def showcase_payload() -> Iterator[dict[str, Any]]:
    """Run the showcase once and share its payload across all tests.

    A full showcase run takes ~13s; running it per-test would balloon
    the suite. Module-scoped fixture keeps all assertions on one
    canonical artifact, which also better matches the production
    invariant (one artifact, many claims).
    """
    with tempfile.TemporaryDirectory(prefix="public_showcase_test_") as d:
        yield run_showcase(output_dir=Path(d))


class TestShowcaseExecution:
    def test_runs_and_returns_payload(self, showcase_payload: dict[str, Any]) -> None:
        assert showcase_payload["showcase_version"] == SHOWCASE_VERSION
        assert showcase_payload["claim_contract_version"] == 1
        assert showcase_payload["max_runtime_seconds"] == MAX_RUNTIME_SECONDS
        assert showcase_payload["all_claims_supported"] is True

    def test_four_scenes_in_canonical_order(
        self, showcase_payload: dict[str, Any]
    ) -> None:
        assert [s["scene_id"] for s in showcase_payload["scenes"]] == [
            "determinism",
            "honest_unknown",
            "reviewed_learning",
            "multi_hop_trace",
        ]

    def test_every_scene_has_at_least_one_supported_claim(
        self, showcase_payload: dict[str, Any]
    ) -> None:
        for scene in showcase_payload["scenes"]:
            assert scene["claims"], f"scene {scene['scene_id']} has no claims"
            for claim in scene["claims"]:
                assert claim["supported"] is True

    def test_runtime_within_budget(self, showcase_payload: dict[str, Any]) -> None:
        runtime_ms = showcase_payload["total_runtime_ms"]
        budget_ms = MAX_RUNTIME_SECONDS * 1000
        assert runtime_ms <= budget_ms, (
            f"showcase exceeded {budget_ms} ms budget; ran {runtime_ms} ms"
        )


class TestHtmlRender:
    def test_html_is_static_html(self, showcase_payload: dict[str, Any]) -> None:
        html = render_html(showcase_payload)
        assert html.startswith("<!doctype html>")
        assert "</html>" in html
        # No operator-supplied template path; no JS injection vector.
        assert "<script" not in html.lower()

    def test_html_renders_scene_ids(self, showcase_payload: dict[str, Any]) -> None:
        html = render_html(showcase_payload)
        for scene in showcase_payload["scenes"]:
            assert scene["scene_id"] in html


class TestPureCompositionGate:
    """ADR-0099 invariant: ``public_showcase_pure_composition``.

    Showcase imports must come from already-shipped packages
    (``core/``, ``chat/``, ``generate/``, ``language_packs/``,
    ``teaching/``, ``evals/``) plus the stdlib. Any other import is
    a new mechanism and must be blocked.
    """

    ALLOWED_PREFIXES = (
        "core.",
        "chat.",
        "generate.",
        "language_packs.",
        "teaching.",
        "evals.",
    )
    ALLOWED_STDLIB = frozenset(
        {
            "__future__",
            "subprocess",
            "time",
            "pathlib",
            "typing",
            "dataclasses",
            "html",
            "re",
            "hashlib",
            "json",
            "os",
            "sys",
        }
    )

    SHOWCASE_SOURCES = (
        REPO_ROOT / "core" / "demos" / "showcase.py",
        REPO_ROOT / "core" / "demos" / "showcase_adapters.py",
        REPO_ROOT / "core" / "demos" / "learning_loop_adapter.py",
    )

    def _imports_in(self, path: Path) -> list[str]:
        import re

        pattern = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")
        mods: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if match:
                mods.append(match.group(1) or match.group(2))
        return mods

    def test_no_forbidden_imports(self) -> None:
        forbidden: list[str] = []
        for source in self.SHOWCASE_SOURCES:
            for mod in self._imports_in(source):
                if mod.startswith(self.ALLOWED_PREFIXES):
                    continue
                if mod in self.ALLOWED_STDLIB:
                    continue
                if mod.split(".", 1)[0] in self.ALLOWED_STDLIB:
                    continue
                forbidden.append(f"{source.name}: {mod}")
        assert forbidden == [], (
            "ADR-0099 pure-composition violation: forbidden imports "
            f"{forbidden}"
        )


class TestRuntimeBudget:
    def test_budget_is_thirty_seconds(self) -> None:
        assert MAX_RUNTIME_SECONDS == 30

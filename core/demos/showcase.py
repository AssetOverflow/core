"""ADR-0099 Public Showcase Demo composer.

Composes four scenes — each delegating to an existing
:class:`core.demos.DemoCommand` adapter — into a single deterministic
JSON artifact plus an HTML render.

- Scene 1 (determinism): :class:`RegisterTourDemo` (ADR-0072)
- Scene 2 (honest unknown): :class:`FabricationControlPublicDemo` (ADR-0096)
- Scene 3 (reviewed learning): :class:`LearningLoopDemo` (ADR-0056)
- Scene 4 (multi-hop with trace): :class:`MultiHopTraceDemo`
  (ADR-0083 transitive surface against the cognition pack)

The composer reads each adapter's :class:`DemoResult` and produces a
single combined claim set. It does not re-implement any scene logic.

Public-safety: every surface emitted is already emitted by one of the
underlying demos. No new exposure of internal mechanisms.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.demos.contract import (
    CLAIM_CONTRACT_VERSION,
    DemoContractError,
    DemoResult,
    canonical_json,
)
from core.demos.learning_loop_adapter import LearningLoopDemo
from core.demos.showcase_adapters import (
    FabricationControlPublicDemo,
    MultiHopTraceDemo,
)
from core.demos.tour_adapters import RegisterTourDemo


SHOWCASE_VERSION: int = 1
MAX_RUNTIME_SECONDS: int = 30


@dataclass(frozen=True, slots=True)
class ShowcaseScene:
    """One scene in the public showcase."""

    scene_id: str
    demo_id: str
    statement: str
    result: DemoResult

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "demo_id": self.demo_id,
            "statement": self.statement,
            "all_claims_supported": self.result.all_claims_supported,
            "claims": [c.as_dict() for c in self.result.claims],
            "evidence": dict(sorted(self.result.evidence.items())),
            "trace_features": dict(sorted(self.result.trace_features.items())),
            "json_path": str(self.result.json_path),
        }


def _current_revision() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return sha or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def run_showcase(*, output_dir: Path, include_runtime_ms: bool = True) -> dict[str, Any]:
    """Run all four scenes and return the composite report.

    ``include_runtime_ms`` defaults to True for the CLI surface but is
    set to False for the byte-equality lane (timing is the one piece
    of legitimate non-determinism in the report).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir = output_dir / "scenes"

    started_at = time.perf_counter()
    scene_records: list[ShowcaseScene] = []

    # Scene 1 — determinism (register-tour adapter)
    r1 = RegisterTourDemo().run(output_dir=scenes_dir)
    scene_records.append(
        ShowcaseScene(
            scene_id="determinism",
            demo_id=r1.demo_id,
            statement=(
                "Identical prompts produce identical trace hashes "
                "across runs under each shipped register."
            ),
            result=r1,
        )
    )

    # Scene 2 — honest unknown (fabrication-control public split)
    r2 = FabricationControlPublicDemo().run(output_dir=scenes_dir)
    scene_records.append(
        ShowcaseScene(
            scene_id="honest_unknown",
            demo_id=r2.demo_id,
            statement=(
                "Composable-looking but unsupported prompts produce typed "
                "refusal with grounding_source = none."
            ),
            result=r2,
        )
    )

    # Scene 3 — reviewed learning (learning-loop adapter)
    r3 = LearningLoopDemo().run(output_dir=scenes_dir)
    scene_records.append(
        ShowcaseScene(
            scene_id="reviewed_learning",
            demo_id=r3.demo_id,
            statement=(
                "Speculative teaching is marked speculative until reviewed; "
                "after review, identical prompt produces a coherent answer."
            ),
            result=r3,
        )
    )

    # Scene 4 — multi-hop with trace (transitive cognition walk)
    r4 = MultiHopTraceDemo().run(output_dir=scenes_dir)
    scene_records.append(
        ShowcaseScene(
            scene_id="multi_hop_trace",
            demo_id=r4.demo_id,
            statement=(
                "Multi-hop reasoning produces an answer plus a verifiable "
                "operator trace via the transitive-chain surface."
            ),
            result=r4,
        )
    )

    total_runtime_ms = int((time.perf_counter() - started_at) * 1000)
    all_supported = all(s.result.all_claims_supported for s in scene_records)

    payload: dict[str, Any] = {
        "showcase_version": SHOWCASE_VERSION,
        "claim_contract_version": CLAIM_CONTRACT_VERSION,
        "generated_at_revision": _current_revision(),
        "scenes": [s.as_dict() for s in scene_records],
        "all_claims_supported": all_supported,
        "max_runtime_seconds": MAX_RUNTIME_SECONDS,
    }
    if include_runtime_ms:
        payload["total_runtime_ms"] = total_runtime_ms

    json_path = output_dir / "showcase.json"
    # Strip runtime_ms before pinning bytes — the byte-equality
    # invariant must hold against everything except wall-clock time.
    deterministic_payload = {k: v for k, v in payload.items() if k != "total_runtime_ms"}
    json_path.write_bytes(canonical_json(deterministic_payload))

    if total_runtime_ms > MAX_RUNTIME_SECONDS * 1000:
        raise DemoContractError(
            f"showcase exceeded ADR-0099 runtime budget: "
            f"{total_runtime_ms} ms > {MAX_RUNTIME_SECONDS * 1000} ms"
        )

    return payload


def render_html(payload: dict[str, Any]) -> str:
    """Render the showcase JSON as a static HTML document.

    The HTML is presentation-only; the JSON is the truth-path. HTML
    may differ across runs in formatting; JSON must not (enforced by
    the byte-equality invariant). No operator-supplied template path
    is accepted — the template is hard-coded here.
    """
    import html

    def esc(value: Any) -> str:
        return html.escape(str(value))

    rows: list[str] = []
    for scene in payload["scenes"]:
        mark = "✓" if scene["all_claims_supported"] else "✗"
        claims_html = "".join(
            f'<li class="claim {("ok" if c["supported"] else "fail")}">'
            f'<span class="mark">{("✓" if c["supported"] else "✗")}</span> '
            f"<code>{esc(c['claim_id'])}</code>: {esc(c['statement'])}"
            f"</li>"
            for c in scene["claims"]
        )
        rows.append(
            f"<section><h2>{mark} {esc(scene['scene_id'])} "
            f"<small>({esc(scene['demo_id'])})</small></h2>"
            f"<p>{esc(scene['statement'])}</p>"
            f"<ul>{claims_html}</ul></section>"
        )

    return (
        "<!doctype html><html><head>"
        "<meta charset='utf-8'>"
        f"<title>CORE Public Showcase v{payload['showcase_version']}</title>"
        "<style>"
        "body{font-family:system-ui;max-width:880px;margin:2rem auto;padding:0 1rem;}"
        "h1{font-size:1.5rem;}h2{font-size:1.1rem;margin-top:1.5rem;}"
        ".claim{margin:.25rem 0;list-style:none;}"
        ".claim.fail{color:#a33;}"
        ".mark{font-weight:bold;display:inline-block;width:1.2rem;}"
        "code{background:#f3f3f3;padding:.05rem .2rem;border-radius:3px;}"
        "footer{margin-top:2rem;color:#888;font-size:.85rem;}"
        "</style></head><body>"
        f"<h1>CORE Public Showcase v{payload['showcase_version']}</h1>"
        f"<p>all_claims_supported: <strong>{esc(payload['all_claims_supported'])}</strong></p>"
        + "".join(rows)
        + f"<footer>revision: <code>{esc(payload['generated_at_revision'])}</code></footer>"
        "</body></html>"
    )

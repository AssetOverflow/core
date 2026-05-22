"""Runner for evals/public_demo/ (ADR-0099).

Verifies the four ADR-0099 invariants in one pass:

- All claims supported on a single fresh run.
- Two runs produce byte-identical JSON (excluding ``total_runtime_ms``).
- Total runtime ≤ 30 seconds.
- Showcase imports only from already-shipped modules (no new mechanism).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SHOWCASE_PATH = REPO_ROOT / "core" / "demos" / "showcase.py"

# ADR-0099 §"Hard constraints" grep gate: showcase must compose only
# from these top-level packages plus its own sub-modules.
ALLOWED_IMPORT_PREFIXES: tuple[str, ...] = (
    "core.",
    "chat.",
    "generate.",
    "language_packs.",
    "teaching.",
    "evals.",
)
ALLOWED_STDLIB: tuple[str, ...] = (
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
)


def _case_all_claims_supported(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("all_claims_supported", False):
        return _fail("all_claims_supported", "showcase reports all_claims_supported=False")
    bad_scenes = [
        s["scene_id"] for s in payload["scenes"] if not s["all_claims_supported"]
    ]
    if bad_scenes:
        return _fail("all_claims_supported", f"failing scenes: {bad_scenes}")
    return _pass(
        "all_claims_supported",
        {"scene_count": len(payload["scenes"])},
    )


_VOLATILE_KEYS: frozenset[str] = frozenset(
    {
        "total_runtime_ms",  # wall-clock
        "json_path",  # adapter output paths (per-run temp dirs)
        "transient_corpus",  # learning-loop embeds its temp corpus path
        # ``generated_at_revision`` advances every commit; the lane's
        # invariant is "same code → same SHA," not "same HEAD → same
        # SHA." Stripping this here keeps the pinned lane SHA stable
        # across commits unless the underlying demos' content changes.
        "generated_at_revision",
    }
)


def _strip_volatile(node: Any) -> Any:
    """Recursively drop volatile keys so two runs can be compared.

    The deterministic content sits in: claims, evidence (sha256 prefixes),
    trace_features (each adapter's report_sha256), and the per-scene
    statement. Wall-clock and absolute paths are excluded.
    """
    if isinstance(node, dict):
        return {
            k: _strip_volatile(v)
            for k, v in node.items()
            if k not in _VOLATILE_KEYS
        }
    if isinstance(node, list):
        return [_strip_volatile(v) for v in node]
    return node


def _case_byte_equality(payload_a: dict, payload_b: dict) -> dict[str, Any]:
    a_stripped = _strip_volatile(payload_a)
    b_stripped = _strip_volatile(payload_b)
    a = json.dumps(a_stripped, sort_keys=True, indent=2).encode()
    b = json.dumps(b_stripped, sort_keys=True, indent=2).encode()
    if a != b:
        return _fail(
            "determinism_run_to_run_byte_equality",
            "showcase JSON bytes differ across two runs (after volatile-key strip)",
        )
    return _pass(
        "determinism_run_to_run_byte_equality",
        {"sha256": hashlib.sha256(a).hexdigest()},
    )


def _case_runtime_under_budget(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_ms = payload.get("total_runtime_ms")
    budget_ms = payload.get("max_runtime_seconds", 30) * 1000
    if runtime_ms is None:
        return _fail("runtime_under_budget", "payload missing total_runtime_ms")
    if runtime_ms > budget_ms:
        return _fail(
            "runtime_under_budget",
            f"{runtime_ms} ms > budget {budget_ms} ms",
        )
    # Don't include the exact runtime_ms in details — it varies per
    # run and would break the lane report's byte-equality even at
    # one-second bucket granularity for near-boundary runs. The case
    # passing already proves runtime ≤ budget; the exact ms is in the
    # showcase's own JSON for callers who want it.
    return _pass(
        "runtime_under_budget",
        {"budget_seconds": budget_ms // 1000},
    )


_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")


def _case_pure_composition() -> dict[str, Any]:
    """Grep gate: showcase imports only from shipped packages + stdlib."""
    sources = (
        SHOWCASE_PATH,
        REPO_ROOT / "core" / "demos" / "showcase_adapters.py",
        REPO_ROOT / "core" / "demos" / "learning_loop_adapter.py",
    )
    forbidden: list[str] = []
    for source in sources:
        if not source.exists():
            continue
        for line in source.read_text(encoding="utf-8").splitlines():
            match = _IMPORT_RE.match(line)
            if not match:
                continue
            mod = (match.group(1) or match.group(2)).strip()
            head = mod.split(".", 1)[0]
            if mod.startswith(ALLOWED_IMPORT_PREFIXES):
                continue
            if head in ALLOWED_STDLIB:
                continue
            if mod in ALLOWED_STDLIB:
                continue
            forbidden.append(f"{source.relative_to(REPO_ROOT)}: {mod}")
    if forbidden:
        return _fail(
            "pure_composition_no_new_mechanism",
            f"forbidden imports: {forbidden}",
        )
    return _pass(
        "pure_composition_no_new_mechanism",
        {"sources_checked": len(sources)},
    )


def _pass(case_id: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"case_id": case_id, "passed": True, "details": details, "divergence": None}


def _fail(case_id: str, divergence: str) -> dict[str, Any]:
    return {"case_id": case_id, "passed": False, "details": {}, "divergence": divergence}


def run() -> dict[str, Any]:
    from core.demos.showcase import run_showcase

    tmp_root = Path(tempfile.mkdtemp(prefix="public_demo_lane_"))
    try:
        run_a = run_showcase(output_dir=tmp_root / "run_a")
        run_b = run_showcase(output_dir=tmp_root / "run_b")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    cases = [
        _case_all_claims_supported(run_a),
        _case_byte_equality(run_a, run_b),
        _case_runtime_under_budget(run_a),
        _case_pure_composition(),
    ]
    return {
        "lane": "public_demo",
        "lane_version": "v1",
        "split": "dev",
        "adr": "ADR-0099",
        "invariants": [
            "public_showcase_pure_composition",
            "public_showcase_all_claims_supported",
            "public_showcase_json_byte_equality",
        ],
        "total_cases": len(cases),
        "passed_cases": sum(1 for c in cases if c["passed"]),
        "failed_cases": sum(1 for c in cases if not c["passed"]),
        "all_passed": all(c["passed"] for c in cases),
        "cases": cases,
    }


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="public_demo lane runner")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = run()
    lane_dir = Path(__file__).resolve().parent
    report_path = args.report or (lane_dir / "results" / "v1_dev.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = _canonical_json(summary)
    report_path.write_bytes(payload_bytes)

    print(f"report: {report_path}")
    print(f"sha256: {hashlib.sha256(payload_bytes).hexdigest()}")
    print(f"passed: {summary['passed_cases']}/{summary['total_cases']}")
    if not summary["all_passed"]:
        for c in summary["cases"]:
            if not c["passed"]:
                print(f"  FAIL {c['case_id']}: {c['divergence']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

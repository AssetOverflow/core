"""Run the Claude-to-CORE hybrid verification demo.

Replays every committed System 1 fixture scenario through the
``core.semantic_derivation.verify`` boundary, twice each through fresh output
directories, and proves three things per scenario:

1. **Determinism** — the two runs are byte-identical (canonical JSON).
2. **Replay** — the response byte-matches the committed reference artifact under
   ``expected/`` (the demo-local pin; the audit trail for any change is the
   artifact diff, mirroring ``scripts/verify_semantic_equivalence.py``).
3. **Authority** — the recorded status matches the scenario's expectation, so a
   verifier/pool/envelope bypass cannot hide behind a green run.

Usage:

    UV_PROJECT_ENVIRONMENT=/tmp/core-hybrid-demo-uv uv run \
        python demos/claude_hybrid_verification/run_demo.py
    python demos/claude_hybrid_verification/run_demo.py --json
    python demos/claude_hybrid_verification/run_demo.py --update-expected  # re-pin (reviewed diffs only)

Exit code: non-zero on any determinism break, expected-artifact drift, or
status mismatch.  ``--update-expected`` rewrites ``expected/*.json``; never use
it to silence a failure you cannot explain.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from demos.claude_hybrid_verification.verify_tool import (  # noqa: E402
    TOOL_NAME,
    load_tool_schema,
    run_tool,
)

_HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = _HERE / "scenarios.jsonl"
EXPECTED_DIR = _HERE / "expected"
DEFAULT_OUT_DIR = _HERE / "out"


def load_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    with SCENARIOS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                scenarios.append(json.loads(line))
    return scenarios


def expected_path(scenario_id: str) -> Path:
    return EXPECTED_DIR / f"{scenario_id}.json"


def render_artifact(response: dict[str, Any]) -> str:
    """Canonical committed-artifact encoding (diff-friendly, deterministic)."""
    return json.dumps(response, sort_keys=True, indent=2) + "\n"


def run_scenario(scenario: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    tool_call = scenario["system1"]["tool_call"]
    if tool_call["name"] != TOOL_NAME:
        raise ValueError(
            f"scenario {scenario['scenario_id']!r} names tool {tool_call['name']!r}; "
            f"this demo serves only {TOOL_NAME!r}"
        )
    run_a = run_tool(tool_call["arguments"], out_dir=out_dir / "run_a")
    run_b = run_tool(tool_call["arguments"], out_dir=out_dir / "run_b")
    if render_artifact(run_a) != render_artifact(run_b):
        raise AssertionError(
            f"scenario {scenario['scenario_id']!r}: two runs of identical arguments "
            "diverged — determinism contract broken"
        )
    return run_a


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true", help="machine-readable summary")
    parser.add_argument(
        "--update-expected",
        action="store_true",
        help="rewrite expected/*.json from live runs (the diff is the audit trail)",
    )
    args = parser.parse_args()

    out_dir: Path = args.out
    if out_dir.exists():
        # Refuse to delete a directory this demo did not produce: only the
        # default location or a directory carrying a prior run's summary.json
        # marker is cleared.  (A user-supplied --out pointing at unrelated data
        # must not be rm -rf'd.)
        if out_dir.resolve() != DEFAULT_OUT_DIR.resolve() and not (
            out_dir / "summary.json"
        ).exists():
            print(
                f"refusing to clear {out_dir}: not the default out dir and no "
                "summary.json marker from a prior demo run",
                file=sys.stderr,
            )
            return 2
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # The tool definition the System 1 side is shown — recorded alongside results.
    schema_doc = load_tool_schema()

    results: list[dict[str, Any]] = []
    all_passed = True
    for scenario in load_scenarios():
        scenario_id = scenario["scenario_id"]
        scenario_dir = out_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        response = run_scenario(scenario, scenario_dir)
        artifact = render_artifact(response)
        (scenario_dir / "response.json").write_text(artifact, encoding="utf-8")

        problems: list[str] = []
        if response["status"] != scenario["expected_status"]:
            problems.append(
                f"status {response['status']!r} != expected {scenario['expected_status']!r}"
            )
        ref = expected_path(scenario_id)
        if args.update_expected:
            EXPECTED_DIR.mkdir(exist_ok=True)
            ref.write_text(artifact, encoding="utf-8")
        elif not ref.exists():
            problems.append("no committed expected artifact (run --update-expected and review)")
        elif ref.read_text(encoding="utf-8") != artifact:
            problems.append("response drifted from committed expected artifact")

        all_passed &= not problems
        results.append(
            {
                "scenario_id": scenario_id,
                "status": response["status"],
                "surface": response["surface"],
                "trace_hash": response["trace_hash"],
                "replay_equivalence_status": response["replay_equivalence_status"],
                "passed": not problems,
                "problems": problems,
            }
        )

    summary = {
        "tool": schema_doc["name"],
        "scenarios": results,
        "all_passed": all_passed,
        "updated_expected": bool(args.update_expected),
    }
    summary_text = json.dumps(summary, sort_keys=True, indent=2) + "\n"
    (out_dir / "summary.json").write_text(summary_text, encoding="utf-8")

    if args.json:
        print(summary_text, end="")
    else:
        for row in results:
            mark = "PASS" if row["passed"] else "FAIL"
            print(f"[{mark}] {row['scenario_id']}: {row['status']}")
            print(f"       surface: {row['surface'][:96]}")
            print(f"       trace_hash: {row['trace_hash'][:16]}…  "
                  f"replay: {row['replay_equivalence_status']}")
            for problem in row["problems"]:
                print(f"       ✗ {problem}")
        print(f"{sum(r['passed'] for r in results)}/{len(results)} scenarios passed "
              f"-> {'OK' if all_passed else 'FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

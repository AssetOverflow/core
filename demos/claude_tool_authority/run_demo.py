"""Run the frontier-proposer-to-CORE tool-authority demo.

Each fixture is evaluated twice.  The run fails if any scenario drifts from its
committed expected artifact or if the two executions differ byte-for-byte.
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

from demos.claude_tool_authority.authority import TOOL_NAME, load_schema, run_authority  # noqa: E402

_HERE = Path(__file__).resolve().parent
FIXTURES_DIR = _HERE / "fixtures"
EXPECTED_DIR = _HERE / "expected"
DEFAULT_OUT_DIR = _HERE / "out"


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def fixture_paths() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.json"))


def expected_path(scenario_id: str) -> Path:
    return EXPECTED_DIR / f"{scenario_id}.json"


def _unsafe_clear_target(path: Path) -> bool:
    resolved = path.resolve()
    blocked = {
        REPO_ROOT.resolve(),
        _HERE.resolve(),
        Path.home().resolve(),
        Path("/").resolve(),
    }
    return resolved in blocked or resolved == resolved.parent


def _prepare_out_dir(out_dir: Path, *, allow_custom_out: bool) -> bool:
    resolved_out = out_dir.resolve()
    default_out = DEFAULT_OUT_DIR.resolve()
    if _unsafe_clear_target(out_dir):
        print(f"refusing unsafe output directory {out_dir}", file=sys.stderr)
        return False
    if resolved_out != default_out and not allow_custom_out:
        print(
            f"refusing custom output directory {out_dir}; pass --allow-custom-out to clear it",
            file=sys.stderr,
        )
        return False
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    return True


def run_fixture(path: Path, out_dir: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture["tool"] != TOOL_NAME:
        raise ValueError(f"{path.name} names {fixture['tool']!r}; expected {TOOL_NAME!r}")
    run_a = run_authority(fixture["arguments"])
    run_b = run_authority(fixture["arguments"])
    if _render(run_a) != _render(run_b):
        raise AssertionError(f"{path.name} is not deterministic across double-run execution")
    return run_a


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--allow-custom-out", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--update-expected", action="store_true")
    args = parser.parse_args()

    out_dir = args.out
    if not _prepare_out_dir(out_dir, allow_custom_out=bool(args.allow_custom_out)):
        return 2

    schema_doc = load_schema()
    results: list[dict[str, Any]] = []
    all_passed = True

    for fixture_path in fixture_paths():
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        scenario_id = fixture["arguments"]["scenario_id"]
        scenario_dir = out_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        response = run_fixture(fixture_path, scenario_dir)
        artifact = _render(response)
        (scenario_dir / "response.json").write_text(artifact, encoding="utf-8")

        problems: list[str] = []
        if response["status"] != fixture["expected_status"]:
            problems.append(
                f"status {response['status']!r} != expected {fixture['expected_status']!r}"
            )
        ref = expected_path(scenario_id)
        if args.update_expected:
            EXPECTED_DIR.mkdir(exist_ok=True)
            ref.write_text(artifact, encoding="utf-8")
        elif not ref.exists():
            problems.append("missing committed expected artifact")
        elif ref.read_text(encoding="utf-8") != artifact:
            problems.append("response drifted from committed expected artifact")

        all_passed &= not problems
        results.append(
            {
                "scenario_id": scenario_id,
                "status": response["status"],
                "decision_reason": response["decision_reason"],
                "trace_hash": response["trace_hash"],
                "passed": not problems,
                "problems": problems,
            }
        )

    summary = {
        "tool": schema_doc["name"],
        "all_passed": all_passed,
        "scenarios": results,
        "updated_expected": bool(args.update_expected),
    }
    summary_text = _render(summary)
    (out_dir / "summary.json").write_text(summary_text, encoding="utf-8")
    if args.json:
        print(summary_text, end="")
    else:
        for row in results:
            mark = "PASS" if row["passed"] else "FAIL"
            print(f"[{mark}] {row['scenario_id']}: {row['status']} ({row['decision_reason']})")
            print(f"       trace_hash: {row['trace_hash'][:16]}…")
            for problem in row["problems"]:
                print(f"       x {problem}")
        print(f"{sum(r['passed'] for r in results)}/{len(results)} scenarios passed")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

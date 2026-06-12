"""Run the model-proposer-to-CORE proof-carrying promotion demo (ADR-0218).

Each fixture is evaluated twice.  The run fails if any scenario drifts from
its committed expected artifact or if the two executions differ
byte-for-byte.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from demos.proof_carrying_promotion.authority import (  # noqa: E402
    TOOL_NAME,
    load_schema,
    run_authority,
)

_HERE = Path(__file__).resolve().parent
FIXTURES_DIR = _HERE / "fixtures"
EXPECTED_DIR = _HERE / "expected"
DEFAULT_OUT_DIR = _HERE / "out"
_TMP_ROOT = Path(tempfile.gettempdir()).resolve()


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def fixture_paths() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.json"))


def expected_path(scenario_id: str) -> Path:
    return EXPECTED_DIR / f"{scenario_id}.json"


def run_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture["tool"] != TOOL_NAME:
        raise ValueError(f"{path.name} names {fixture['tool']!r}; expected {TOOL_NAME!r}")
    run_a = run_authority(fixture["arguments"])
    run_b = run_authority(fixture["arguments"])
    if _render(run_a) != _render(run_b):
        raise AssertionError(f"{path.name} is not deterministic across double-run execution")
    return run_a


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _custom_out_allowed(out_dir: Path) -> bool:
    resolved = out_dir.resolve()
    if resolved in {
        Path("/"),
        REPO_ROOT.resolve(),
        _HERE.resolve(),
        _HERE.parent.resolve(),
        Path.home().resolve(),
        Path.cwd().resolve(),
    }:
        return False
    return _is_relative_to(resolved, _HERE.resolve()) or _is_relative_to(resolved, _TMP_ROOT)


def _clearable_out_dir(out_dir: Path) -> tuple[bool, str | None]:
    resolved = out_dir.resolve()
    default_resolved = DEFAULT_OUT_DIR.resolve()
    if resolved == default_resolved:
        return True, None
    if not _custom_out_allowed(out_dir):
        return False, (
            f"refusing to clear {out_dir}: custom out dir must resolve under "
            f"{_HERE} or {_TMP_ROOT}"
        )
    if not (out_dir / "summary.json").exists():
        return False, (
            f"refusing to clear {out_dir}: custom out dir requires demo summary.json marker"
        )
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--write-expected",
        action="store_true",
        help="explicitly rewrite the committed expected artifacts",
    )
    args = parser.parse_args()

    out_dir = args.out
    if out_dir.exists():
        allowed, reason = _clearable_out_dir(out_dir)
        if not allowed:
            assert reason is not None
            print(reason, file=sys.stderr)
            return 2
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    schema_doc = load_schema()
    results: list[dict[str, Any]] = []
    all_passed = True

    for fixture_path in fixture_paths():
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        scenario_id = fixture["arguments"]["scenario_id"]
        scenario_dir = out_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        response = run_fixture(fixture_path)
        artifact = _render(response)
        (scenario_dir / "response.json").write_text(artifact, encoding="utf-8")

        problems: list[str] = []
        if response["status"] != fixture["expected_status"]:
            problems.append(
                f"status {response['status']!r} != expected {fixture['expected_status']!r}"
            )
        ref = expected_path(scenario_id)
        if args.write_expected:
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
                "promoted": response["promoted"],
                "decision_reason": response["decision_reason"],
                "before_status": response.get("before_status"),
                "after_status": response.get("after_status"),
                "certificate_digest": response["certificate_digest"],
                "trace_hash": response["trace_hash"],
                "passed": not problems,
                "problems": problems,
            }
        )

    summary = {
        "tool": schema_doc["name"],
        "all_passed": all_passed,
        "scenarios": results,
        "updated_expected": bool(args.write_expected),
    }
    summary_text = _render(summary)
    (out_dir / "summary.json").write_text(summary_text, encoding="utf-8")
    if args.json:
        print(summary_text, end="")
    else:
        for row in results:
            mark = "PASS" if row["passed"] else "FAIL"
            transition = f"{row['before_status']} -> {row['after_status']}"
            print(
                f"[{mark}] {row['scenario_id']}: {row['status']}"
                f" ({row['decision_reason']}; {transition})"
            )
            digest = row["certificate_digest"]
            print(
                "       certificate_digest: "
                + (f"{digest[:16]}…" if digest else "null")
            )
            print(f"       trace_hash: {row['trace_hash'][:16]}…")
            for problem in row["problems"]:
                print(f"       x {problem}")
        print(f"{sum(r['passed'] for r in results)}/{len(results)} scenarios passed")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

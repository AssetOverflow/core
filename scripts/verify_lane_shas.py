"""Verify ADR-0092..0104 lane SHA-256 pins.

Each ADR lane writes a deterministic JSON report. This script runs
every pinned lane and asserts the SHA-256 of the report bytes matches
the value pinned below. Pinned SHAs come from the commits that landed
each ADR.

Update the pins with ``--update`` when an ADR-tracked change to the
lane is intentional. The diff between the in-tree pin and the freshly
computed SHA is the audit trail.

Usage:

    python scripts/verify_lane_shas.py            # verify, exit non-zero on mismatch
    python scripts/verify_lane_shas.py --update   # rewrite the pin block in this file
    python scripts/verify_lane_shas.py --json     # machine-readable report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent


PINNED_SHAS: dict[str, str] = {
    "reviewer_registry": "681a2aab5aa4ffd58cd837ce5673c8b2a9545b570117aec3c02726a12f6876e6",
    "miner_loop_closure": "9f071733abe7dcacf759f928548ce738fb639af3fd6e4c621a651b306d7e77ce",
    "curriculum_loop_closure": "b46d56b2d209172cc3ffaf3776dc8dcfe55093f13587c5cb67372be6dfa23e8d",
    "domain_contract_validation": "98ace04e3f02bbc5a8ad655bb6593c3f1ee64cb67014f1122fe6c3c85f48d22f",
    "fabrication_control_summary": "01e1b6b711141f2b4a14551d7df3ea482d8d6dd7b364a25c509f4f8d08cda8a8",
    "demo_composition": "3a3d09f3a87462737e615c2dd3481b9e13e5ff8fadee0043c37873494ded556d",
    "public_demo": "2895df080b91618aefc2df407c637ff419fbb6dae33233c90262688c103411ea",
    "math_teaching_corpus_v1": "eaf160d145da29f9050ede8d58bf111b0f651dd40aeae9201857d0b97e014dd4",
    "deductive_logic_v1": "97a230949016e38d5e3f37a69e4245b320575ee70e5af92ff7607f7b05f74b5f",
}


@dataclass(frozen=True, slots=True)
class LaneSpec:
    lane_id: str
    runner_module: str
    report_relative: str
    accepts_report_flag: bool = True
    extra_args: tuple[str, ...] = field(default_factory=tuple)
    # Run via ``python -m pkg.mod`` instead of ``python path/to/runner.py``.
    # Required when the runner's own directory holds a module that would shadow
    # an absolute import in script mode — e.g. the deductive lane's local
    # ``generate.py`` shadows the ``generate`` package when run as a script.
    run_as_module: bool = False

    @property
    def runner_path(self) -> Path:
        return REPO_ROOT / self.runner_module

    @property
    def runner_dotted(self) -> str:
        return self.runner_module.removesuffix(".py").replace("/", ".")

    @property
    def canonical_report(self) -> Path:
        return REPO_ROOT / self.report_relative


LANE_SPECS: tuple[LaneSpec, ...] = (
    LaneSpec(
        lane_id="reviewer_registry",
        runner_module="evals/reviewer_registry/runner.py",
        report_relative="evals/reviewer_registry/results/v1_dev.json",
    ),
    LaneSpec(
        lane_id="miner_loop_closure",
        runner_module="evals/miner_loop_closure/runner.py",
        report_relative="evals/miner_loop_closure/results/v1_dev.json",
    ),
    LaneSpec(
        lane_id="curriculum_loop_closure",
        runner_module="evals/curriculum_loop_closure/runner.py",
        report_relative="evals/curriculum_loop_closure/results/v1_dev.json",
        accepts_report_flag=False,
    ),
    LaneSpec(
        lane_id="domain_contract_validation",
        runner_module="evals/domain_contract_validation/runner.py",
        report_relative="evals/domain_contract_validation/results/v1_dev.json",
    ),
    LaneSpec(
        lane_id="fabrication_control_summary",
        runner_module="evals/fabrication_control/runner.py",
        report_relative="evals/fabrication_control/results/v1_summary.json",
        accepts_report_flag=False,
    ),
    LaneSpec(
        lane_id="demo_composition",
        runner_module="evals/demo_composition/runner.py",
        report_relative="evals/demo_composition/results/v1_dev.json",
    ),
    LaneSpec(
        lane_id="public_demo",
        runner_module="evals/public_demo/runner.py",
        report_relative="evals/public_demo/results/v1_dev.json",
    ),
    LaneSpec(
        lane_id="math_teaching_corpus_v1",
        runner_module="evals/math_teaching_corpus/v1/runner.py",
        report_relative="evals/math_teaching_corpus/v1/report.json",
        accepts_report_flag=False,
    ),
    LaneSpec(
        lane_id="deductive_logic_v1",
        runner_module="evals/deductive_logic/runner.py",
        report_relative="evals/deductive_logic/report.json",
        run_as_module=True,
    ),
)


def _invoke_runner(spec: LaneSpec, *, target_path: Path | None = None) -> Path:
    import os

    env = {"PYTHONPATH": str(REPO_ROOT), **os.environ}
    if spec.run_as_module:
        args = [sys.executable, "-m", spec.runner_dotted]
    else:
        args = [sys.executable, str(spec.runner_path)]
    if target_path is not None and spec.accepts_report_flag:
        args.extend(["--report", str(target_path)])
    args.extend(spec.extra_args)
    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"lane runner {spec.lane_id} exited non-zero "
            f"(code={result.returncode})\nSTDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    if target_path is not None and spec.accepts_report_flag:
        report_path = target_path
    else:
        report_path = spec.canonical_report
    if not report_path.exists():
        raise RuntimeError(
            f"lane {spec.lane_id} runner returned 0 but report not found at {report_path}"
        )
    return report_path


def _sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class LaneVerification:
    lane_id: str
    pinned_sha: str
    actual_sha: str
    matched: bool
    report_path: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "pinned_sha": self.pinned_sha,
            "actual_sha": self.actual_sha,
            "matched": self.matched,
            "report_path": self.report_path,
            "error": self.error,
        }


def verify_all(*, ephemeral: bool = True) -> list[LaneVerification]:
    results: list[LaneVerification] = []
    for spec in LANE_SPECS:
        pinned = PINNED_SHAS.get(spec.lane_id, "")
        try:
            if ephemeral:
                with tempfile.TemporaryDirectory(prefix=f"lane_{spec.lane_id}_") as d:
                    target = Path(d) / "report.json"
                    report_path = _invoke_runner(spec, target_path=target)
                    actual = _sha_of(report_path)
            else:
                report_path = _invoke_runner(spec)
                actual = _sha_of(report_path)
        except Exception as exc:
            results.append(
                LaneVerification(
                    lane_id=spec.lane_id,
                    pinned_sha=pinned,
                    actual_sha="",
                    matched=False,
                    report_path=str(spec.canonical_report),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        results.append(
            LaneVerification(
                lane_id=spec.lane_id,
                pinned_sha=pinned,
                actual_sha=actual,
                matched=(actual == pinned),
                report_path=str(report_path),
            )
        )
    return results


_PIN_BLOCK_START = "PINNED_SHAS: dict[str, str] = {"
_PIN_BLOCK_END = "}"


def _rewrite_pins(new_pins: dict[str, str]) -> None:
    text = Path(__file__).read_text(encoding="utf-8")
    start = text.index(_PIN_BLOCK_START)
    rel_end = text[start:].index(_PIN_BLOCK_END)
    end = start + rel_end + 1
    new_block_lines = [_PIN_BLOCK_START]
    for lane_id, sha in new_pins.items():
        new_block_lines.append(f'    "{lane_id}": "{sha}",')
    new_block_lines.append("}")
    new_block = "\n".join(new_block_lines)
    Path(__file__).write_text(text[:start] + new_block + text[end:], encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verify ADR lane SHAs")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.update:
        results = verify_all(ephemeral=False)
        new_pins = {r.lane_id: r.actual_sha for r in results if not r.error}
        _rewrite_pins(new_pins)
        if args.json:
            print(json.dumps({"updated": new_pins}, indent=2, sort_keys=True))
        else:
            print("Updated PINNED_SHAS:")
            for lane_id, sha in new_pins.items():
                print(f"  {lane_id:>32}: {sha}")
        return 0

    results = verify_all()
    if args.json:
        payload = {
            "total": len(results),
            "matched": sum(1 for r in results if r.matched),
            "mismatched": [r.as_dict() for r in results if not r.matched],
            "results": [r.as_dict() for r in results],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        width = max(len(r.lane_id) for r in results)
        for r in results:
            mark = "✓" if r.matched else "✗"
            print(f"  {mark} {r.lane_id:<{width}}  {r.actual_sha[:16]}..", end="")
            if not r.matched:
                if r.error:
                    print(f"  ERROR: {r.error}")
                else:
                    print(f"  expected {r.pinned_sha[:16]}..")
            else:
                print()
        total = len(results)
        matched = sum(1 for r in results if r.matched)
        print(f"\nlanes: {matched}/{total} match pinned SHAs")
        if matched < total:
            print(
                "\nremediation:\n"
                "  if the drift is intentional (e.g. you touched core/cognition/result.py,\n"
                "  chat/runtime.py, generate/realizer.py, capability registries, or other\n"
                "  lane-affecting code), re-pin with:\n"
                "      python scripts/verify_lane_shas.py --update\n"
                "  then run `python scripts/generate_claims.py` and commit both changes.\n"
                "  if the drift is unintentional, investigate the upstream change before re-pinning."
            )

    return 0 if all(r.matched for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

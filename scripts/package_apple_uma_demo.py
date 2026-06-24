#!/usr/bin/env python3
"""Build a shareable Apple UMA benchmark demo package.

The package is generated locally from the persisted Apple UMA benchmark report.
It is intentionally claim-safe: by default it refuses to package stale reports
where the MLX exact recall track is absent, skipped, or parity-failing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workbench.apple_uma_report import read_apple_uma_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON = REPO_ROOT / "evals" / "reports" / "apple_uma_mechanical_sympathy_latest.json"
DEFAULT_REPORT_MD = REPO_ROOT / "evals" / "reports" / "apple_uma_mechanical_sympathy_latest.md"
DEFAULT_OUT_ROOT = REPO_ROOT / "dist" / "apple-uma-demo"


class DemoPackageError(RuntimeError):
    """Raised when the demo package would overclaim or lack required evidence."""


@dataclass(frozen=True)
class PackagePaths:
    package_dir: Path
    report_json: Path
    report_md: Path
    manifest: Path
    readme: Path
    sharing_note: Path


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_report_refresh(*, core_backend: str) -> None:
    env = os.environ.copy()
    env["CORE_BACKEND"] = core_backend
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "benchmarks.apple_uma_mechanical_sympathy",
        "--write-report",
    ]
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def _mlx_summary(projection: dict[str, Any]) -> dict[str, Any]:
    return projection["tracks"]["mlx_exact_cga_recall"]


def validate_demo_report(projection: dict[str, Any], *, allow_stale: bool) -> list[str]:
    """Return warnings; raise when the report cannot be packaged safely."""

    warnings: list[str] = []
    if projection.get("read_only") is not True:
        raise DemoPackageError("Apple UMA report projection must be read-only")

    mlx = _mlx_summary(projection)
    if not mlx.get("present"):
        message = "MLX exact CGA recall track is absent from the report"
        if not allow_stale:
            raise DemoPackageError(message)
        warnings.append(message)
    if mlx.get("skipped"):
        message = f"MLX exact CGA recall track is skipped: {mlx.get('reason') or 'no reason'}"
        if not allow_stale:
            raise DemoPackageError(message)
        warnings.append(message)
    if not mlx.get("all_cases_parity_pass"):
        message = "MLX exact CGA recall parity did not pass for all cases"
        if not allow_stale:
            raise DemoPackageError(message)
        warnings.append(message)
    if int(mlx.get("case_count") or 0) <= 0:
        message = "MLX exact CGA recall emitted no measured cases"
        if not allow_stale:
            raise DemoPackageError(message)
        warnings.append(message)
    if mlx.get("serving_authorized") is True:
        raise DemoPackageError("MLX report unexpectedly claims serving authorization")

    non_claims = projection.get("non_claims") or []
    required_non_claim_fragments = [
        "MLX semantic",
        "ANN",
        "CoreML",
    ]
    missing = [
        fragment
        for fragment in required_non_claim_fragments
        if not any(fragment in str(item) for item in non_claims)
    ]
    if missing:
        warnings.append(
            "Non-claim list is missing expected fragments: " + ", ".join(missing)
        )

    return warnings


def _format_case_rows(mlx: dict[str, Any]) -> str:
    cases = mlx.get("cases") or []
    if not cases:
        return "- No MLX cases were emitted in this report."
    rows = []
    for case in cases:
        rows.append(
            "- N={N}: p50={p50} ms, rows/sec={rows_per_sec}, parity={parity}".format(
                N=case.get("N", "n/a"),
                p50=case.get("p50_ms", "n/a"),
                rows_per_sec=case.get("rows_per_sec", "n/a"),
                parity=(case.get("parity") or {}).get("parity_pass"),
            )
        )
    return "\n".join(rows)


def render_package_readme(projection: dict[str, Any], warnings: list[str]) -> str:
    mlx = _mlx_summary(projection)
    warning_block = "\n".join(f"- {warning}" for warning in warnings) or "- none"
    return f"""# CORE Apple UMA demo package

This package was generated from the persisted Apple UMA mechanical-sympathy benchmark report.

## Report identity

- Benchmark: {projection['benchmark_name']}
- Version: {projection['benchmark_version']}
- Source path: `{projection['source_path']}`
- Source digest: `{projection['source_digest']}`
- Read-only projection: {projection['read_only']}

## MLX exact CGA recall

- Track present: {mlx.get('present')}
- Track skipped: {mlx.get('skipped')}
- Case count: {mlx.get('case_count')}
- All cases parity pass: {mlx.get('all_cases_parity_pass')}
- Serving authorized: {mlx.get('serving_authorized')}

{_format_case_rows(mlx)}

## Copy boundaries

The MLX exact recall path copies NumPy inputs into MLX arrays and copies MLX scores back to NumPy for canonical stable top-k ordering. The package does not claim zero-copy everywhere.

## Warnings

{warning_block}

## Explicit non-claims

""" + "\n".join(f"- {item}" for item in projection.get("non_claims", [])) + "\n"


def render_sharing_note(projection: dict[str, Any]) -> str:
    mlx = _mlx_summary(projection)
    return f"""# Suggested sharing note

CORE now has a reproducible Apple Silicon UMA benchmark package that isolates exact CGA recall, Rust/native boundary behavior, MLX score-vector parity, copy boundaries, and Workbench report-card evidence.

The current package reports MLX exact recall as:

- present: {mlx.get('present')}
- skipped: {mlx.get('skipped')}
- cases: {mlx.get('case_count')}
- all cases parity pass: {mlx.get('all_cases_parity_pass')}

Important boundaries:

- This is benchmark-only evidence, not a serving-path integration.
- It does not claim CoreML or ANE acceleration.
- It does not claim approximate search or ANN recall.
- It does not claim zero-copy everywhere.
- It records copy-in and copy-out boundaries explicitly.
"""


def build_demo_package(
    *,
    report_json: Path,
    report_md: Path,
    out_root: Path,
    stamp: str,
    allow_stale: bool,
) -> PackagePaths:
    if not report_json.exists():
        raise DemoPackageError(f"missing report JSON: {report_json}")
    if not report_md.exists():
        raise DemoPackageError(f"missing report markdown: {report_md}")

    projection = read_apple_uma_report(report_json)
    warnings = validate_demo_report(projection, allow_stale=allow_stale)

    package_dir = out_root / stamp
    package_dir.mkdir(parents=True, exist_ok=True)
    report_json_out = package_dir / "apple_uma_mechanical_sympathy_latest.json"
    report_md_out = package_dir / "apple_uma_mechanical_sympathy_latest.md"
    manifest_out = package_dir / "package_manifest.json"
    readme_out = package_dir / "README.md"
    sharing_note_out = package_dir / "APPLE_SHARING_NOTE.md"

    shutil.copy2(report_json, report_json_out)
    shutil.copy2(report_md, report_md_out)

    manifest = {
        "package_kind": "apple_uma_demo_package",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "report_id": projection["report_id"],
        "benchmark_name": projection["benchmark_name"],
        "benchmark_version": projection["benchmark_version"],
        "source_report_digest": projection["source_digest"],
        "packaged_report_json_digest": sha256_file(report_json_out),
        "packaged_report_markdown_digest": sha256_file(report_md_out),
        "allow_stale": allow_stale,
        "warnings": warnings,
        "mlx_summary": _mlx_summary(projection),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
        "non_claims": projection.get("non_claims", []),
    }

    manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_out.write_text(render_package_readme(projection, warnings), encoding="utf-8")
    sharing_note_out.write_text(render_sharing_note(projection), encoding="utf-8")

    return PackagePaths(
        package_dir=package_dir,
        report_json=report_json_out,
        report_md=report_md_out,
        manifest=manifest_out,
        readme=readme_out,
        sharing_note=sharing_note_out,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--stamp", default=utc_stamp())
    parser.add_argument("--allow-stale", action="store_true")
    parser.add_argument("--refresh-report", action="store_true")
    parser.add_argument("--core-backend", default="rust")
    args = parser.parse_args(argv)

    if args.refresh_report:
        run_report_refresh(core_backend=args.core_backend)

    paths = build_demo_package(
        report_json=args.report_json,
        report_md=args.report_md,
        out_root=args.out_root,
        stamp=args.stamp,
        allow_stale=args.allow_stale,
    )
    print(paths.package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

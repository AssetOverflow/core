"""Read-only Apple UMA benchmark report projection for Workbench.

This module projects the latest persisted Apple UMA benchmark JSON into a stable
UI-facing read model. It never runs benchmarks, imports MLX, imports Rust, or
mutates report artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPLE_UMA_REPORT = (
    REPO_ROOT / "evals" / "reports" / "apple_uma_mechanical_sympathy_latest.json"
)
REPORT_ID = "apple_uma_mechanical_sympathy_latest"
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "benchmark_name",
        "benchmark_version",
        "backend_status",
        "tracks",
        "claim_safety_audit",
        "copy_zero_copy_truth_table",
    }
)


class AppleUmaReportMalformed(ValueError):
    """Raised when a persisted Apple UMA report cannot be projected safely."""


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AppleUmaReportMalformed(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AppleUmaReportMalformed(f"{label} must be a list")
    return value


def _timing_summary(case: dict[str, Any]) -> dict[str, Any]:
    timing = _require_mapping(case.get("timing", {}), "MLX case timing")
    return {
        "N": case.get("N"),
        "top_k": case.get("top_k"),
        "p50_ms": timing.get("p50_ms"),
        "p95_ms": timing.get("p95_ms"),
        "mean_ms": timing.get("mean_ms"),
        "rows_per_sec": case.get("rows_per_sec"),
        "parity": _require_mapping(case.get("parity", {}), "MLX case parity"),
        "copy_in_boundary": case.get("copy_in_boundary"),
        "copy_out_boundary": case.get("copy_out_boundary"),
    }


def _mlx_track_projection(track: object) -> dict[str, Any]:
    if not isinstance(track, dict):
        return {
            "present": False,
            "skipped": True,
            "reason": "MLX exact CGA recall track absent from report",
            "case_count": 0,
            "all_cases_parity_pass": False,
            "cases": [],
        }

    skipped = bool(track.get("skipped", False))
    cases_raw = _require_list(track.get("cases", []), "MLX cases") if not skipped else []
    cases = [_timing_summary(_require_mapping(case, "MLX case")) for case in cases_raw]
    parity_values = [bool(case["parity"].get("parity_pass", False)) for case in cases]
    return {
        "present": True,
        "skipped": skipped,
        "reason": track.get("reason"),
        "benchmark_only": bool(track.get("benchmark_only", False)),
        "serving_authorized": bool(track.get("serving_authorized", False)),
        "semantic_backend": track.get("semantic_backend"),
        "score_computation": track.get("score_computation"),
        "top_k_ordering": track.get("top_k_ordering"),
        "copy_boundary": track.get("copy_boundary"),
        "mlx_status": track.get("mlx_status", {}),
        "case_count": len(cases),
        "all_cases_parity_pass": bool(cases) and all(parity_values),
        "cases": cases,
    }


def _track_inventory(tracks: dict[str, Any]) -> dict[str, Any]:
    required = [
        "cl41_scalar_ops",
        "exact_cga_recall",
        "mlx_exact_cga_recall",
        "diffusion_step",
        "frame_verdict_ttfv",
        "array_codec_replay",
    ]
    return {
        "available": sorted(tracks.keys()),
        "required": required,
        "missing_required": [name for name in required if name not in tracks],
        "mlx_exact_cga_recall": _mlx_track_projection(tracks.get("mlx_exact_cga_recall")),
    }


def project_apple_uma_report(report: dict[str, Any], *, source_path: Path) -> dict[str, Any]:
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(report.keys()))
    if missing:
        raise AppleUmaReportMalformed(
            f"Apple UMA report missing required keys: {', '.join(missing)}"
        )

    tracks = _require_mapping(report.get("tracks"), "tracks")
    claim_safety = _require_mapping(report.get("claim_safety_audit"), "claim_safety_audit")
    truth_table = _require_list(
        report.get("copy_zero_copy_truth_table"), "copy_zero_copy_truth_table"
    )
    non_claims = _require_list(
        claim_safety.get("unsafe_claims_not_made", []), "unsafe_claims_not_made"
    )

    return {
        "read_only": True,
        "report_id": REPORT_ID,
        "source_path": _relative(source_path),
        "source_digest": _sha256_file(source_path),
        "benchmark_name": report["benchmark_name"],
        "benchmark_version": report["benchmark_version"],
        "metadata": report.get("_metadata", {}),
        "backend_status": _require_mapping(report.get("backend_status"), "backend_status"),
        "tracks": _track_inventory(tracks),
        "copy_boundaries": truth_table,
        "non_claims": non_claims,
        "claim_safety": {
            "safe_claims": claim_safety.get("safe_claims", []),
            "rust_backend_notes": claim_safety.get("rust_backend_notes", []),
            "known_copy_paths": claim_safety.get("known_copy_paths", []),
            "known_zero_copy_input_paths": claim_safety.get(
                "known_zero_copy_input_paths", []
            ),
            "future_work": claim_safety.get("future_work", []),
        },
    }


def read_apple_uma_report(path: Path | None = None) -> dict[str, Any]:
    source_path = DEFAULT_APPLE_UMA_REPORT if path is None else path
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    report = _require_mapping(raw, "Apple UMA report")
    return project_apple_uma_report(report, source_path=source_path)

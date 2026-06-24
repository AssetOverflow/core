from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.apple_uma_report import (
    AppleUmaReportMalformed,
    project_apple_uma_report,
    read_apple_uma_report,
)


def _base_report() -> dict:
    return {
        "benchmark_name": "CORE Apple Silicon UMA Mechanical Sympathy Benchmark",
        "benchmark_version": "1.0.3",
        "backend_status": {
            "native_status": "rust_active",
            "using_rust": True,
            "requested_backend": "rust",
            "core_rs_import_succeeded": True,
        },
        "tracks": {
            "cl41_scalar_ops": {"skipped": False},
            "exact_cga_recall": {"skipped": False},
            "diffusion_step": {"skipped": False},
            "frame_verdict_ttfv": {"skipped": False},
            "array_codec_replay": {"skipped": False},
        },
        "claim_safety_audit": {
            "safe_claims": ["Exact CGA recall via algebra.backend.vault_recall — no ANN."],
            "rust_backend_notes": [],
            "known_copy_paths": [],
            "known_zero_copy_input_paths": [],
            "future_work": ["Metal kernel experiment requires separate ADR/parity lane."],
            "unsafe_claims_not_made": [
                "No MLX semantic-backend claim.",
                "No ANN/approximate-search benchmark.",
            ],
        },
        "copy_zero_copy_truth_table": [
            {
                "path": "benchmarks.apple_uma_mlx_exact_recall",
                "input": "NumPy contiguous float32 matrix/query copied into MLX arrays",
                "output": "MLX score vector copied to NumPy for canonical stable top-k",
                "zero_copy_input": "no",
            }
        ],
    }


def _write_report(tmp_path: Path, report: dict) -> Path:
    path = tmp_path / "apple_uma_mechanical_sympathy_latest.json"
    path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_project_old_report_without_mlx_track_does_not_fabricate_success(
    tmp_path: Path,
) -> None:
    report = _base_report()
    path = _write_report(tmp_path, report)

    projected = read_apple_uma_report(path)

    assert projected["read_only"] is True
    assert projected["source_path"].endswith("apple_uma_mechanical_sympathy_latest.json")
    assert projected["source_digest"].startswith("sha256:")
    mlx = projected["tracks"]["mlx_exact_cga_recall"]
    assert mlx["present"] is False
    assert mlx["skipped"] is True
    assert mlx["case_count"] == 0
    assert mlx["all_cases_parity_pass"] is False
    assert "mlx_exact_cga_recall" in projected["tracks"]["missing_required"]


def test_project_mlx_present_report_summarizes_parity_and_boundaries(
    tmp_path: Path,
) -> None:
    report = _base_report()
    report["tracks"]["mlx_exact_cga_recall"] = {
        "skipped": False,
        "benchmark_only": True,
        "serving_authorized": False,
        "semantic_backend": "python/rust canonical exact recall",
        "score_computation": "MLX exact diagonal CGA score vector; no ANN or approximate search",
        "top_k_ordering": "canonical NumPy stable ordering after score copy-out",
        "copy_boundary": {
            "input": "NumPy -> MLX array copy at benchmark boundary",
            "output": "MLX score vector -> NumPy copy for stable top-k",
            "zero_copy_input": "no",
        },
        "mlx_status": {"import_succeeded": True, "default_device": "Device(gpu, 0)"},
        "cases": [
            {
                "N": 128,
                "top_k": 5,
                "rows_per_sec": 123.4,
                "copy_in_boundary": "NumPy contiguous float32 matrix/query copied into MLX arrays",
                "copy_out_boundary": "MLX score vector copied to NumPy for canonical stable top-k ordering",
                "timing": {"p50_ms": 1.0, "p95_ms": 1.5, "mean_ms": 1.2},
                "parity": {
                    "parity_pass": True,
                    "top_k_indices_match": True,
                    "scores_close": True,
                    "max_abs_score_delta": 0.0,
                },
            }
        ],
    }
    path = _write_report(tmp_path, report)

    projected = read_apple_uma_report(path)

    mlx = projected["tracks"]["mlx_exact_cga_recall"]
    assert mlx["present"] is True
    assert mlx["skipped"] is False
    assert mlx["benchmark_only"] is True
    assert mlx["serving_authorized"] is False
    assert mlx["semantic_backend"] == "python/rust canonical exact recall"
    assert mlx["case_count"] == 1
    assert mlx["all_cases_parity_pass"] is True
    assert mlx["cases"][0]["parity"]["parity_pass"] is True
    assert mlx["cases"][0]["copy_in_boundary"].startswith("NumPy")
    assert mlx["cases"][0]["copy_out_boundary"].startswith("MLX")
    assert projected["tracks"]["missing_required"] == []
    assert any("No MLX semantic-backend" in item for item in projected["non_claims"])
    assert projected["copy_boundaries"][0]["zero_copy_input"] == "no"


def test_project_mlx_skipped_report_preserves_reason(tmp_path: Path) -> None:
    report = _base_report()
    report["tracks"]["mlx_exact_cga_recall"] = {
        "skipped": True,
        "reason": "MLX unavailable: No module named 'mlx'",
        "benchmark_only": True,
        "serving_authorized": False,
        "semantic_backend": "python/rust canonical exact recall",
        "non_claims": ["No serving integration."],
    }
    path = _write_report(tmp_path, report)

    projected = read_apple_uma_report(path)

    mlx = projected["tracks"]["mlx_exact_cga_recall"]
    assert mlx["present"] is True
    assert mlx["skipped"] is True
    assert mlx["reason"] == "MLX unavailable: No module named 'mlx'"
    assert mlx["case_count"] == 0
    assert mlx["all_cases_parity_pass"] is False
    assert mlx["serving_authorized"] is False


def test_malformed_report_fails_closed(tmp_path: Path) -> None:
    path = _write_report(tmp_path, {"benchmark_name": "missing required fields"})

    with pytest.raises(AppleUmaReportMalformed, match="missing required keys"):
        read_apple_uma_report(path)


def test_project_rejects_non_object_report(tmp_path: Path) -> None:
    path = tmp_path / "apple_uma_mechanical_sympathy_latest.json"
    path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(AppleUmaReportMalformed, match="must be an object"):
        read_apple_uma_report(path)


def test_project_uses_supplied_source_path_for_digest(tmp_path: Path) -> None:
    report = _base_report()
    path = _write_report(tmp_path, report)

    projected_a = project_apple_uma_report(report, source_path=path)
    projected_b = read_apple_uma_report(path)

    assert projected_a["source_digest"] == projected_b["source_digest"]
    assert projected_a["source_path"] == projected_b["source_path"]

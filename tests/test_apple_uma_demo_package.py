from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.package_apple_uma_demo import DemoPackageError, build_demo_package


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
            "mlx_exact_cga_recall": {
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
                "mlx_status": {
                    "import_succeeded": True,
                    "default_device": "Device(gpu, 0)",
                },
                "cases": [
                    {
                        "N": 128,
                        "top_k": 5,
                        "rows_per_sec": 130088.678,
                        "copy_in_boundary": "NumPy contiguous float32 matrix/query copied into MLX arrays",
                        "copy_out_boundary": "MLX score vector copied to NumPy for canonical stable top-k ordering",
                        "timing": {"p50_ms": 0.977, "p95_ms": 1.2, "mean_ms": 1.0},
                        "parity": {
                            "parity_pass": True,
                            "top_k_indices_match": True,
                            "scores_close": True,
                            "max_abs_score_delta": 0.0,
                        },
                    }
                ],
            },
        },
        "claim_safety_audit": {
            "safe_claims": ["Exact CGA recall via algebra.backend.vault_recall — no ANN."],
            "rust_backend_notes": [],
            "known_copy_paths": ["MLX score vector copied to NumPy for stable top-k."],
            "known_zero_copy_input_paths": [],
            "future_work": ["Metal kernel experiment requires separate ADR/parity lane."],
            "unsafe_claims_not_made": [
                "No MLX semantic-backend claim.",
                "No ANN/approximate-search benchmark.",
                "No CoreML acceleration claim.",
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


def _write_report_pair(tmp_path: Path, report: dict) -> tuple[Path, Path]:
    json_path = tmp_path / "apple_uma_mechanical_sympathy_latest.json"
    md_path = tmp_path / "apple_uma_mechanical_sympathy_latest.md"
    json_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text("# Apple UMA report\n\nMLX exact CGA recall present.\n", encoding="utf-8")
    return json_path, md_path


def test_package_builder_refuses_stale_report_by_default(tmp_path: Path) -> None:
    report = _base_report()
    del report["tracks"]["mlx_exact_cga_recall"]
    json_path, md_path = _write_report_pair(tmp_path, report)

    with pytest.raises(DemoPackageError, match="MLX exact CGA recall track is absent"):
        build_demo_package(
            report_json=json_path,
            report_md=md_path,
            out_root=tmp_path / "dist",
            stamp="demo",
            allow_stale=False,
        )


def test_package_builder_allows_stale_report_only_when_explicit(tmp_path: Path) -> None:
    report = _base_report()
    del report["tracks"]["mlx_exact_cga_recall"]
    json_path, md_path = _write_report_pair(tmp_path, report)

    paths = build_demo_package(
        report_json=json_path,
        report_md=md_path,
        out_root=tmp_path / "dist",
        stamp="demo",
        allow_stale=True,
    )

    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    assert manifest["allow_stale"] is True
    assert manifest["warnings"]
    assert manifest["mlx_summary"]["present"] is False
    assert paths.readme.read_text(encoding="utf-8").count("Track present: False") == 1


def test_package_builder_emits_claim_safe_mlx_present_bundle(tmp_path: Path) -> None:
    report = _base_report()
    json_path, md_path = _write_report_pair(tmp_path, report)

    paths = build_demo_package(
        report_json=json_path,
        report_md=md_path,
        out_root=tmp_path / "dist",
        stamp="demo",
        allow_stale=False,
    )

    assert paths.report_json.exists()
    assert paths.report_md.exists()
    assert paths.readme.exists()
    assert paths.sharing_note.exists()

    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    assert manifest["package_kind"] == "apple_uma_demo_package"
    assert manifest["allow_stale"] is False
    assert manifest["warnings"] == []
    assert manifest["mlx_summary"]["present"] is True
    assert manifest["mlx_summary"]["all_cases_parity_pass"] is True
    assert manifest["mlx_summary"]["serving_authorized"] is False
    assert manifest["source_report_digest"].startswith("sha256:")
    assert manifest["packaged_report_json_digest"].startswith("sha256:")

    readme = paths.readme.read_text(encoding="utf-8")
    assert "All cases parity pass: True" in readme
    assert "No MLX semantic-backend claim." in readme
    assert "does not claim zero-copy everywhere" in readme

    sharing_note = paths.sharing_note.read_text(encoding="utf-8")
    assert "benchmark-only evidence" in sharing_note
    assert "does not claim CoreML" in sharing_note
    assert "does not claim approximate search" in sharing_note


def test_package_builder_refuses_serving_authorization_claim(tmp_path: Path) -> None:
    report = _base_report()
    report["tracks"]["mlx_exact_cga_recall"]["serving_authorized"] = True
    json_path, md_path = _write_report_pair(tmp_path, report)

    with pytest.raises(DemoPackageError, match="serving authorization"):
        build_demo_package(
            report_json=json_path,
            report_md=md_path,
            out_root=tmp_path / "dist",
            stamp="demo",
            allow_stale=False,
        )

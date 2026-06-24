"""Tests for the Apple Silicon UMA mechanical sympathy benchmark."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

from benchmarks.apple_uma_mechanical_sympathy import (
    BENCHMARK_NAME,
    REPORT_JSON_NAME,
    build_claim_safety_audit,
    build_copy_zero_copy_truth_table,
    deterministic_closed_frame,
    run_benchmark,
    rust_backend_status,
    synthetic_matrix,
    track_array_codec_replay,
    track_frame_verdict_ttfv,
    write_json_report,
    write_reports,
)
from core.array_codec import decode_array, encode_array
from generate.frame_verdict.evaluate import evaluate_frame_verdict
from generate.frame_verdict.types import FrameVerdictKind


REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "benchmark_name",
        "benchmark_version",
        "machine",
        "backend_status",
        "tracks",
        "claim_safety_audit",
        "copy_zero_copy_truth_table",
    }
)

REQUIRED_TRACK_KEYS = frozenset(
    {
        "cl41_scalar_ops",
        "exact_cga_recall",
        "diffusion_step",
        "frame_verdict_ttfv",
        "array_codec_replay",
    }
)


@pytest.fixture
def fast_bench_kwargs() -> dict[str, int]:
    return {"warmup": 1, "measured": 3}


def test_report_has_stable_top_level_keys(fast_bench_kwargs: dict[str, int]) -> None:
    report = run_benchmark(**fast_bench_kwargs)
    assert REQUIRED_TOP_LEVEL_KEYS <= set(report.keys())
    assert REQUIRED_TRACK_KEYS <= set(report["tracks"].keys())
    assert report["benchmark_name"] == BENCHMARK_NAME


def test_no_rust_required_for_basic_report(fast_bench_kwargs: dict[str, int]) -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
        report = run_benchmark(**fast_bench_kwargs)
    assert "machine" in report
    assert report["tracks"]["cl41_scalar_ops"]["skipped"] is False
    assert report["tracks"]["exact_cga_recall"]["skipped"] is False


def test_skipped_tracks_include_explicit_reasons(fast_bench_kwargs: dict[str, int]) -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
        report = run_benchmark(**fast_bench_kwargs)
    diffusion = report["tracks"]["diffusion_step"]
    if diffusion.get("skipped"):
        assert "reason" in diffusion
        assert diffusion["reason"]
        assert diffusion.get("native_status") in {
            "python_fallback",
            "rust_importable_python_fallback",
        }
        assert "backend_status" in diffusion


def test_backend_status_present_and_python_fallback(
    fast_bench_kwargs: dict[str, int],
) -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
        report = run_benchmark(**fast_bench_kwargs)
    status = report["backend_status"]
    assert status["using_rust"] is False
    assert status["native_status"] in {
        "python_fallback",
        "rust_importable_python_fallback",
    }
    assert status["diffusion_step_eligible"] is False
    assert status["activation_hint"]
    assert report["machine"]["backend_status"] == status
    notes = report["claim_safety_audit"]["rust_backend_notes"]
    assert notes
    assert any("Python" in n or "diffusion_step" in n for n in notes)


def test_rust_backend_status_requested_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORE_BACKEND", "rust")
    with mock.patch(
        "benchmarks.apple_uma_mechanical_sympathy._core_rs_import_status",
        return_value={"import_succeeded": False, "reason": "No module named 'core_rs'"},
    ):
        with mock.patch("algebra.backend.using_rust", return_value=False):
            status = rust_backend_status()
    assert status["native_status"] == "rust_requested_unavailable"
    assert status["rust_backend_requested"] is True
    assert status["core_rs_import_succeeded"] is False
    assert status["activation_hint"]


def test_rust_backend_status_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORE_BACKEND", "rust")
    with mock.patch(
        "benchmarks.apple_uma_mechanical_sympathy._core_rs_import_status",
        return_value={"import_succeeded": True},
    ):
        with mock.patch("algebra.backend.using_rust", return_value=True):
            status = rust_backend_status()
    assert status["native_status"] == "rust_active"
    assert status["using_rust"] is True
    assert status["diffusion_step_eligible"] is True
    assert status["activation_hint"] is None


def test_claim_safety_audit_rust_active_notes() -> None:
    status = {
        "rust_backend_requested": True,
        "core_rs_import_succeeded": True,
        "using_rust": True,
        "native_status": "rust_active",
    }
    audit = build_claim_safety_audit(using_rust=True, backend_status=status)
    assert audit["rust_backend_notes"]
    assert any("PyReadonlyArray1" in n for n in audit["rust_backend_notes"])
    assert audit["known_zero_copy_input_paths"]
    assert any("vault_recall" in n for n in audit["known_zero_copy_input_paths"])
    assert any("vault_recall" in n for n in audit["safe_claims"])


def test_copy_truth_table_includes_rust_zero_copy_rows_when_active() -> None:
    table = build_copy_zero_copy_truth_table(using_rust=True)
    paths = {row["path"] for row in table}
    assert "algebra.backend.vault_recall (Rust)" in paths
    assert "algebra.backend.diffusion_step (Rust)" in paths
    vault_row = next(r for r in table if r["path"] == "algebra.backend.vault_recall (Rust)")
    assert vault_row["zero_copy_input"] == "yes (contiguous float32)"
    gp_row = next(
        r for r in table if r["path"] == "algebra.backend.geometric_product (Rust)"
    )
    assert gp_row["zero_copy_input"] == "yes (contiguous float32)"
    va_row = next(
        r for r in table if r["path"] == "algebra.backend.versor_apply (Rust f64 closure)"
    )
    assert va_row["zero_copy_input"] == "yes (contiguous float64)"


def test_rust_active_backend_status_scalar_zero_copy_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORE_BACKEND", "rust")
    with mock.patch(
        "benchmarks.apple_uma_mechanical_sympathy._core_rs_import_status",
        return_value={"import_succeeded": True},
    ):
        with mock.patch("algebra.backend.using_rust", return_value=True):
            status = rust_backend_status()
    assert status["scalar_rust_zero_copy_input_eligible"] is True
    assert status["scalar_rust_output_allocations_remain"] is True


def test_deterministic_synthetic_sanity_checks_stable(
    fast_bench_kwargs: dict[str, int],
) -> None:
    report_a = run_benchmark(**fast_bench_kwargs)
    report_b = run_benchmark(**fast_bench_kwargs)
    for track_name in ("cl41_scalar_ops", "array_codec_replay", "frame_verdict_ttfv"):
        if track_name == "cl41_scalar_ops":
            for op_a, op_b in zip(
                report_a["tracks"][track_name]["operations"],
                report_b["tracks"][track_name]["operations"],
            ):
                assert op_a["sanity"]["deterministic_repeat"] is True
                assert op_b["sanity"]["deterministic_repeat"] is True
        else:
            assert report_a["tracks"][track_name]["sanity"] == report_b["tracks"][track_name]["sanity"]


def test_claim_safety_audit_contents() -> None:
    audit = build_claim_safety_audit(using_rust=False)
    assert audit["safe_claims"]
    assert audit["unsafe_claims_not_made"]
    assert any("CoreML" in s for s in audit["unsafe_claims_not_made"])
    assert any("MLX" in s for s in audit["unsafe_claims_not_made"])
    assert any("zero-copy everywhere" in s for s in audit["unsafe_claims_not_made"])
    assert audit["known_copy_paths"]
    assert audit["future_work"]


def test_array_codec_replay_byte_exact_roundtrip() -> None:
    track = track_array_codec_replay(warmup=1, measured=2)
    assert track["skipped"] is False
    assert track["sanity"]["byte_exact_roundtrip"] is True
    assert track["sanity"]["writable_decode"] is True
    arr = synthetic_matrix(8, seed=1)
    assert np.array_equal(arr, decode_array(encode_array(arr)))


def test_frame_verdict_ttfv_returns_frame_verdict_not_determine() -> None:
    frame, query = deterministic_closed_frame()
    verdict = evaluate_frame_verdict(frame, query)
    assert verdict.verdict is FrameVerdictKind.ENTAILED_TRUE
    track = track_frame_verdict_ttfv(warmup=1, measured=2)
    assert track["skipped"] is False
    assert track["sanity"]["is_frame_verdict"] is True
    assert track["sanity"]["expected_entailed_true"] is True
    # Guard: open-world determine() must not be imported by this track module.
    import benchmarks.apple_uma_mechanical_sympathy as bench_mod

    source = Path(bench_mod.__file__).read_text(encoding="utf-8")
    assert "determine(" not in source
    assert "from generate.determine" not in source


def test_report_writer_creates_json_under_evals_reports(
    fast_bench_kwargs: dict[str, int],
    tmp_path: Path,
) -> None:
    report = run_benchmark(**fast_bench_kwargs)
    path = write_json_report(report, root=tmp_path)
    assert path.name == REPORT_JSON_NAME
    assert path.parent == tmp_path
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert "_metadata" in loaded
    if "report_path" in loaded["_metadata"]:
        assert not loaded["_metadata"]["report_path"].startswith("/")
    assert loaded["benchmark_name"] == BENCHMARK_NAME


def test_write_reports_creates_json_and_markdown(
    fast_bench_kwargs: dict[str, int],
    tmp_path: Path,
) -> None:
    report = run_benchmark(**fast_bench_kwargs)
    json_path, md_path = write_reports(report, root=tmp_path)
    assert json_path.exists()
    assert md_path.exists()
    md_text = md_path.read_text(encoding="utf-8")
    assert "Explicit non-claims" in md_text
    assert "zero-copy" in md_text.lower()


def test_benchmark_module_makes_no_network_calls(
    fast_bench_kwargs: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _blocked(*_a: object, **_k: object) -> None:
        raise AssertionError("network access attempted during benchmark")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    run_benchmark(**fast_bench_kwargs)

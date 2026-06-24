"""Tests for the optional Apple UMA MLX exact recall experiment."""

from __future__ import annotations

import socket
from unittest import mock

import numpy as np

from benchmarks.apple_uma_mlx_exact_recall import (
    BENCHMARK_NAME,
    _parity_report,
    _stable_top_k_from_scores,
    run_mlx_exact_recall_experiment,
)


def test_mlx_unavailable_skips_with_explicit_reason() -> None:
    report = run_mlx_exact_recall_experiment(
        warmup=1,
        measured=1,
        mlx_status={"import_succeeded": False, "reason": "No module named 'mlx'"},
    )

    assert report["benchmark_name"] == BENCHMARK_NAME
    assert report["track"] == "mlx_exact_cga_recall"
    assert report["skipped"] is True
    assert "MLX unavailable" in report["reason"]
    assert report["benchmark_only"] is True
    assert report["serving_authorized"] is False
    assert report["semantic_backend"] == "python/rust canonical exact recall"
    assert any("No ANN" in item for item in report["non_claims"])
    assert any("No serving" in item for item in report["non_claims"])


def test_stable_top_k_orders_by_score_then_index() -> None:
    scores = np.array([0.5, 2.0, 2.0, -1.0, 1.5], dtype=np.float32)

    assert _stable_top_k_from_scores(scores, 3) == [
        (1, float(scores[1])),
        (2, float(scores[2])),
        (4, float(scores[4])),
    ]


def test_parity_report_requires_indices_and_scores_close() -> None:
    canonical = [(2, 1.25), (5, 0.75)]
    candidate = [(2, 1.25001), (5, 0.75001)]

    report = _parity_report(canonical=canonical, candidate=candidate)

    assert report["top_k_indices_match"] is True
    assert report["scores_close"] is True
    assert report["parity_pass"] is True


def test_parity_report_rejects_index_mismatch() -> None:
    canonical = [(2, 1.25), (5, 0.75)]
    candidate = [(5, 0.75), (2, 1.25)]

    report = _parity_report(canonical=canonical, candidate=candidate)

    assert report["top_k_indices_match"] is False
    assert report["parity_pass"] is False


def test_experiment_makes_no_network_calls(monkeypatch) -> None:
    def _blocked(*_a: object, **_k: object) -> None:
        raise AssertionError("network access attempted during MLX experiment")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    run_mlx_exact_recall_experiment(
        warmup=1,
        measured=1,
        mlx_status={"import_succeeded": False, "reason": "No module named 'mlx'"},
    )


def test_mlx_score_vector_is_not_called_when_mlx_unavailable() -> None:
    with mock.patch(
        "benchmarks.apple_uma_mlx_exact_recall.mlx_exact_score_vector",
        side_effect=AssertionError("MLX score path should not run when unavailable"),
    ):
        report = run_mlx_exact_recall_experiment(
            warmup=1,
            measured=1,
            mlx_status={"import_succeeded": False, "reason": "No module named 'mlx'"},
        )
    assert report["skipped"] is True

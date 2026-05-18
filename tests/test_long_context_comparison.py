"""ADR-0045 — long-context recall comparison vs transformer baselines.

CORE's vault recall is exact by construction: there is no approximate
index, no embedding compression, no attention bottleneck.  The
comparison runner publishes:

1. A needle-in-a-haystack measurement at multiple N showing CORE
   returns the planted needle at top-1.
2. Frozen citations of published transformer long-context recall
   numbers (Claude 2.1, GPT-4 Turbo 128k, Gemini 1.5 Pro, NVIDIA
   RULER) as the comparator.

If a future change to the vault breaks exact recall, this suite fails.
"""
from __future__ import annotations

from evals.long_context_cost.comparison_runner import (
    DEFAULT_N_VALUES,
    run_comparison,
)


class TestComparisonRunner:
    def test_report_schema_is_stable(self) -> None:
        report = run_comparison(n_values=(100, 1_000))
        assert report["schema_version"] == 1
        assert "core_measurements" in report
        assert "transformer_baselines" in report
        core = report["core_measurements"]
        assert set(core.keys()) >= {
            "n_values",
            "recall_pct",
            "exact_by_construction",
            "per_n",
        }

    def test_core_exact_recall_holds(self) -> None:
        """The load-bearing claim: top-1 needle recall is correct at every N."""
        report = run_comparison(n_values=(100, 1_000, 10_000))
        assert report["claim_supported"] is True
        assert report["core_measurements"]["recall_pct"] == 100.0
        for entry in report["core_measurements"]["per_n"]:
            assert entry["top1_correct"] is True, entry

    def test_transformer_baselines_are_frozen_citations(self) -> None:
        report = run_comparison(n_values=(100,))
        baselines = report["transformer_baselines"]["baselines"]
        assert len(baselines) >= 3
        for b in baselines:
            assert "source" in b
            assert "url" in b
            assert "context_window_tokens" in b

    def test_default_n_values_include_at_least_100k(self) -> None:
        """Ensure the comparison exercises a large-N regime by default."""
        assert max(DEFAULT_N_VALUES) >= 100_000


class TestCoreGuaranteeAdvertised:
    def test_baseline_file_records_core_guarantee(self) -> None:
        report = run_comparison(n_values=(100,))
        guarantee = report["transformer_baselines"]["core_guarantee"]
        assert guarantee["recall_pct"] == 100.0
        assert guarantee["recall_kind"] == "exact_cga_inner_scan"

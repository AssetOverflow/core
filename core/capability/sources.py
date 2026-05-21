from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LedgerSources:
    eval_results: str = "evals/*/results/v*_*.json"
    mastery_reports: str = "packs/**/*.mastery_report.json"
    pack_measurements: str = "evals/results/phase2_pack_measurements.json"
    identity_div: str = "evals/identity_divergence/results/*.json"
    refusal_cal: str = "evals/refusal_calibration/results/*.json"
    audit_tour: str = "evals/audit_tour/results/*.json"
    gaps: str = "docs/gaps.md"
    reviewers: str = "docs/reviewers.yaml"
    teaching_corpora_registered: str = "chat/teaching_grounding.py::TEACHING_CORPORA"
    cross_pack_corpus: str = "chat/cross_pack_grounding.py::CROSS_PACK_CORPUS_ID"

    def resolve(self, repo_root: Path) -> dict[str, Path]:
        return {
            "pack_measurements": repo_root / self.pack_measurements,
            "gaps": repo_root / self.gaps,
            "reviewers": repo_root / self.reviewers,
        }


LEDGER_SOURCES = LedgerSources()

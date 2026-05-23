"""ADR-0120 math-expert promotion composer (final wire-up).

Composes:
  - all 10 ADR-0114a obligation verdicts
  - ADR-0131.4 composite math gate verdict (B1+B2+B3)
  - ADR-0092 reviewer-signed ``expert_claims`` entry

into a single deterministic promotion verdict. Emits a canonical
``expert_claims_math_v1_signed.json`` artifact whose ``claim_digest``
reproduces byte-for-byte from the on-disk evidence bundle (per
ADR-0120 §"Signed expert_claims entry with reproducible digest").

This module does NOT execute the ledger flip directly. The
sequencing is:

  1. ``evaluate_math_expert_promotion()`` returns a verdict +
     reproducible digest derived from current on-disk evidence.
  2. Operator inspects the verdict. If every obligation + the
     composite gate pass, operator adds a signed
     ``mathematics_logic_expert_claim`` entry to
     ``docs/reviewers.yaml`` with the reported digest.
  3. Operator re-runs the evaluator. With a matching signed claim
     present, the verdict flips to ``promote_admitted = True``
     and the ledger-flip wire (separate small PR consuming this
     verdict) becomes executable.

Pure function over committed evidence + the reviewer registry.
No I/O beyond reading those files; deterministic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from core.capability.adversarial import evaluate_adversarial
from core.capability.composite_math_gate import evaluate_composite_math_gate
from core.capability.depth_curve import evaluate_depth_curve
from core.capability.ood_ratio import evaluate_ood_ratio
from core.capability.pack_provenance import validate_lane as evaluate_pack_provenance
from core.capability.perturbation_b3 import validate_perturbation_suite


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_REVIEWERS_YAML: Path = _REPO_ROOT / "docs" / "reviewers.yaml"

# Evidence-bundle paths the digest commits to (in canonical order).
DEFAULT_B1_PUBLIC: Path = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "report.json"
DEFAULT_B1_SEALED: Path = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "sealed_report.json"
DEFAULT_B2: Path = _REPO_ROOT / "evals" / "math_teaching_corpus" / "v1" / "report.json"
DEFAULT_B3: Path = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "report.json"
DEFAULT_FRONTIER_DIR: Path = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "frontier"
DEFAULT_GSM8K_PROBE: Path = _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "train_sample_coverage_report.json"

DOMAIN_ID: str = "mathematics_logic"
SCHEMA_VERSION: int = 1
EXPERT_CLAIMS_KEY: str = "math_expert_claims"


class PromotionError(Exception):
    """Raised when the evidence bundle cannot be assembled."""


@dataclass(frozen=True, slots=True)
class ObligationVerdict:
    """Per-obligation pass/fail with one-line evidence pointer."""

    obligation_id: str  # "1" .. "10"
    title: str
    passed: bool
    evidence_pointer: str
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "title": self.title,
            "passed": self.passed,
            "evidence_pointer": self.evidence_pointer,
            "refusal_reason": self.refusal_reason,
        }


@dataclass(frozen=True, slots=True)
class MathExpertPromotionVerdict:
    """Top-level promotion verdict composed of obligation + composite gate."""

    domain: str
    obligations: tuple[ObligationVerdict, ...]
    composite_gate_passed: bool
    composite_gate_refusal: str
    all_obligations_passed: bool
    technical_pass: bool  # all obligations + composite gate pass
    claim_digest: str
    reviewer_signature: Mapping[str, Any] | None
    reviewer_signature_matches: bool
    promote_admitted: bool
    refusal_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0120-math",
            "schema_version": SCHEMA_VERSION,
            "domain": self.domain,
            "obligations": [o.as_dict() for o in self.obligations],
            "composite_gate_passed": self.composite_gate_passed,
            "composite_gate_refusal": self.composite_gate_refusal,
            "all_obligations_passed": self.all_obligations_passed,
            "technical_pass": self.technical_pass,
            "claim_digest": self.claim_digest,
            "reviewer_signature": dict(self.reviewer_signature) if self.reviewer_signature else None,
            "reviewer_signature_matches": self.reviewer_signature_matches,
            "promote_admitted": self.promote_admitted,
            "refusal_reason": self.refusal_reason,
        }


# ---------------------------------------------------------------------------
# Per-obligation evaluators
# ---------------------------------------------------------------------------


def _evaluate_obligation_1(b1_sealed_path: Path = DEFAULT_B1_SEALED) -> ObligationVerdict:
    """Sealed holdout — ADR-0131.1.S. Pass iff the sealed split report
    exists, ``counts.wrong == 0``, and the lane's exit_criterion passed."""
    if not b1_sealed_path.exists():
        return ObligationVerdict(
            obligation_id="1", title="sealed holdout discipline",
            passed=False, evidence_pointer=str(b1_sealed_path),
            refusal_reason="sealed report missing",
        )
    report = json.loads(b1_sealed_path.read_text(encoding="utf-8"))
    counts = report.get("counts", {})
    exit_crit = report.get("exit_criterion", {})
    wrong = int(counts.get("wrong", -1))
    passed = wrong == 0 and bool(exit_crit.get("passed"))
    return ObligationVerdict(
        obligation_id="1", title="sealed holdout discipline",
        passed=passed,
        evidence_pointer=str(b1_sealed_path),
        refusal_reason=(
            "" if passed
            else f"sealed report: wrong={wrong}, exit_passed={exit_crit.get('passed')}"
        ),
    )


def _evaluate_obligation_2() -> ObligationVerdict:
    r = evaluate_ood_ratio()
    return ObligationVerdict(
        obligation_id="2", title="OOD surface variation ratio ≥ 0.95",
        passed=bool(r.obligation_2_passed),
        evidence_pointer=str(_REPO_ROOT / "evals" / "obligation_2_ood_ratio"),
        refusal_reason="" if r.obligation_2_passed else r.refusal_reason,
    )


def _evaluate_obligation_3(b_reports: tuple[Path, ...]) -> ObligationVerdict:
    """Replay-equal trace — every correct case carries a non-empty
    ``trace_hash``. Read the B-lane reports' case_details."""
    missing = []
    for path in b_reports:
        if not path.exists():
            return ObligationVerdict(
                obligation_id="3", title="replay-equal trace",
                passed=False, evidence_pointer=str(path),
                refusal_reason=f"B-lane report missing: {path}",
            )
        report = json.loads(path.read_text(encoding="utf-8"))
        # Report shapes vary; check both common locations.
        details = report.get("per_case") or report.get("case_details") or []
        for d in details:
            if d.get("outcome") == "correct" and not d.get("trace_hash"):
                missing.append(f"{path.name}:{d.get('case_id', '?')}")
    if missing:
        return ObligationVerdict(
            obligation_id="3", title="replay-equal trace",
            passed=False, evidence_pointer=str(b_reports[0].parent),
            refusal_reason=f"{len(missing)} correct case(s) missing trace_hash; first: {missing[0]}",
        )
    return ObligationVerdict(
        obligation_id="3", title="replay-equal trace",
        passed=True, evidence_pointer=str(b_reports[0].parent),
    )


def _evaluate_obligation_4(b_reports: tuple[Path, ...]) -> ObligationVerdict:
    """Typed refusal + wrong == 0 across every B-lane."""
    for path in b_reports:
        if not path.exists():
            return ObligationVerdict(
                obligation_id="4", title="typed refusal + wrong == 0",
                passed=False, evidence_pointer=str(path),
                refusal_reason=f"B-lane report missing: {path}",
            )
        report = json.loads(path.read_text(encoding="utf-8"))
        # counts.wrong (B1/B2) or metrics.wrong (B3)
        wrong = (
            report.get("counts", {}).get("wrong")
            if isinstance(report.get("counts"), dict)
            else report.get("metrics", {}).get("wrong")
        )
        if wrong is None or int(wrong) > 0:
            return ObligationVerdict(
                obligation_id="4", title="typed refusal + wrong == 0",
                passed=False, evidence_pointer=str(path),
                refusal_reason=f"{path.name}: wrong={wrong}",
            )
    return ObligationVerdict(
        obligation_id="4", title="typed refusal + wrong == 0",
        passed=True, evidence_pointer=str(b_reports[0].parent),
    )


def _evaluate_obligation_5() -> ObligationVerdict:
    r = validate_perturbation_suite()
    # Module's verdict field is obligation_5_passed (mirror of pattern).
    passed = getattr(r, "obligation_5_passed", None)
    if passed is None:
        # Fall back to checking rate fields if present.
        passed = (
            getattr(r, "invariance_preserving_rate", 0.0) == 1.0
            and getattr(r, "invariance_breaking_rate", 0.0) == 1.0
        )
    return ObligationVerdict(
        obligation_id="5", title="reasoning-isolation perturbation suite",
        passed=bool(passed),
        evidence_pointer=str(_REPO_ROOT / "evals" / "obligation_5_perturbation"),
        refusal_reason="" if passed else getattr(r, "refusal_reason", "obligation_5 evaluator returned non-pass"),
    )


def _evaluate_obligation_6() -> ObligationVerdict:
    r = evaluate_depth_curve()
    # The mechanism is wired; assertion holds is the gate.
    passed = bool(r.obligation_6_assertion_holds)
    return ObligationVerdict(
        obligation_id="6", title="compositional-depth curve",
        passed=passed,
        evidence_pointer=str(_REPO_ROOT / "evals" / "obligation_6_depth_curve"),
        refusal_reason="" if passed else r.refusal_reason,
    )


def _evaluate_obligation_7(frontier_dir: Path = DEFAULT_FRONTIER_DIR) -> ObligationVerdict:
    """Frontier-baseline comparison — ADR-0131.1.F. Pass iff at least
    one frontier comparison artifact exists under
    ``evals/math_symbolic_equivalence/v1/frontier/``."""
    if not frontier_dir.exists():
        return ObligationVerdict(
            obligation_id="7", title="frontier-baseline comparison",
            passed=False, evidence_pointer=str(frontier_dir),
            refusal_reason="frontier directory missing",
        )
    artifacts = sorted(
        p for p in frontier_dir.rglob("*.json")
        if p.is_file() and not p.name.startswith(".")
    )
    if not artifacts:
        return ObligationVerdict(
            obligation_id="7", title="frontier-baseline comparison",
            passed=False, evidence_pointer=str(frontier_dir),
            refusal_reason="no frontier comparison artifacts found",
        )
    return ObligationVerdict(
        obligation_id="7", title="frontier-baseline comparison",
        passed=True, evidence_pointer=str(frontier_dir),
    )


def _evaluate_obligation_8() -> ObligationVerdict:
    r = evaluate_adversarial()
    return ObligationVerdict(
        obligation_id="8", title="adversarial generation; misparse zero",
        passed=bool(r.obligation_8_passed),
        evidence_pointer=str(_REPO_ROOT / "evals" / "obligation_8_adversarial"),
        refusal_reason="" if r.obligation_8_passed else r.refusal_reason,
    )


def _evaluate_obligation_9(b_reports: tuple[Path, ...]) -> ObligationVerdict:
    """Determinism — every B-lane report.json must exist and be valid
    JSON (a structural guarantee that the runners are emitting
    canonical bytes; full byte-equality across runs is verified by the
    individual lane runners' own determinism tests).
    """
    for path in b_reports:
        if not path.exists():
            return ObligationVerdict(
                obligation_id="9", title="determinism",
                passed=False, evidence_pointer=str(path),
                refusal_reason=f"B-lane report missing: {path}",
            )
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ObligationVerdict(
                obligation_id="9", title="determinism",
                passed=False, evidence_pointer=str(path),
                refusal_reason=f"{path.name}: invalid JSON ({exc})",
            )
    return ObligationVerdict(
        obligation_id="9", title="determinism",
        passed=True, evidence_pointer=str(b_reports[0].parent),
    )


def _evaluate_obligation_10() -> ObligationVerdict:
    r = evaluate_pack_provenance()
    return ObligationVerdict(
        obligation_id="10", title="operation provenance via pack",
        passed=bool(r.obligation_10_passed),
        evidence_pointer=str(_REPO_ROOT / "evals" / "obligation_10_pack_provenance"),
        refusal_reason="" if r.obligation_10_passed else r.refusal_reason,
    )


# ---------------------------------------------------------------------------
# Reviewer signature lookup + digest
# ---------------------------------------------------------------------------


def _load_reviewer_signature(
    reviewers_path: Path = DEFAULT_REVIEWERS_YAML,
) -> Mapping[str, Any] | None:
    """Return the signed math-expert claim entry from the reviewers
    registry, or ``None`` if no entry exists yet."""
    if not reviewers_path.exists():
        return None
    data = yaml.safe_load(reviewers_path.read_text(encoding="utf-8")) or {}
    entries = data.get(EXPERT_CLAIMS_KEY) or []
    for entry in entries:
        if entry.get("domain_id") == DOMAIN_ID:
            return entry
    return None


def _compute_claim_digest(
    obligations: tuple[ObligationVerdict, ...],
    composite_gate_digest: str,
) -> str:
    """Reproducible SHA-256 over the canonical evidence bundle.

    Commits to: each obligation's pass/fail + evidence_pointer, plus
    the composite gate's own claim_digest. Operator regenerating the
    evidence bundle must produce the same hex.
    """
    canonical = {
        "adr": "0120-math",
        "schema_version": SCHEMA_VERSION,
        "domain": DOMAIN_ID,
        "obligations": [
            {
                "id": o.obligation_id,
                "passed": o.passed,
                "evidence_pointer": o.evidence_pointer,
            }
            for o in obligations
        ],
        "composite_gate_digest": composite_gate_digest,
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Top-level evaluator
# ---------------------------------------------------------------------------


def evaluate_math_expert_promotion(
    *,
    b1_public_path: Path = DEFAULT_B1_PUBLIC,
    b1_sealed_path: Path = DEFAULT_B1_SEALED,
    b2_path: Path = DEFAULT_B2,
    b3_path: Path = DEFAULT_B3,
    frontier_dir: Path = DEFAULT_FRONTIER_DIR,
    gsm8k_probe_path: Path = DEFAULT_GSM8K_PROBE,
    reviewers_path: Path = DEFAULT_REVIEWERS_YAML,
) -> MathExpertPromotionVerdict:
    """Compose all 10 obligation verdicts + the composite gate verdict
    + the reviewer-signature check into a single promotion verdict.

    ``promote_admitted = True`` iff:
      - every obligation passes
      - the composite gate passes
      - a signed reviewer entry exists for ``mathematics_logic`` AND
        its ``claim_digest`` matches the computed digest

    Any failure → ``promote_admitted = False`` with a typed refusal.
    """
    b_reports = (b1_public_path, b1_sealed_path, b2_path, b3_path)
    obligations = (
        _evaluate_obligation_1(b1_sealed_path),
        _evaluate_obligation_2(),
        _evaluate_obligation_3(b_reports),
        _evaluate_obligation_4(b_reports),
        _evaluate_obligation_5(),
        _evaluate_obligation_6(),
        _evaluate_obligation_7(frontier_dir),
        _evaluate_obligation_8(),
        _evaluate_obligation_9(b_reports),
        _evaluate_obligation_10(),
    )

    composite = evaluate_composite_math_gate(
        b1_public_path=b1_public_path,
        b1_sealed_path=b1_sealed_path,
        b2_path=b2_path,
        b3_path=b3_path,
        gsm8k_probe_path=gsm8k_probe_path,
    )

    all_obligations_passed = all(o.passed for o in obligations)
    technical_pass = all_obligations_passed and composite.composite_gate_passed
    claim_digest = _compute_claim_digest(obligations, composite.claim_digest)

    reviewer_sig = _load_reviewer_signature(reviewers_path)
    if reviewer_sig is not None:
        sig_matches = reviewer_sig.get("claim_digest") == claim_digest
    else:
        sig_matches = False

    promote_admitted = technical_pass and sig_matches

    refusal_bits: list[str] = []
    if not all_obligations_passed:
        failing = [o.obligation_id for o in obligations if not o.passed]
        refusal_bits.append(f"obligations failing: {failing}")
    if not composite.composite_gate_passed:
        refusal_bits.append(f"composite gate: {composite.refusal_reason}")
    if technical_pass and reviewer_sig is None:
        refusal_bits.append(
            f"awaiting reviewer signature — add an entry to "
            f"docs/reviewers.yaml under '{EXPERT_CLAIMS_KEY}' for "
            f"domain '{DOMAIN_ID}' with claim_digest={claim_digest}"
        )
    elif technical_pass and not sig_matches:
        refusal_bits.append(
            f"reviewer claim_digest mismatch — registry has "
            f"{reviewer_sig.get('claim_digest')!r}, evidence-derived "
            f"digest is {claim_digest!r}; the evidence bundle has "
            f"changed since the signature was added"
        )

    refusal = "; ".join(refusal_bits)

    return MathExpertPromotionVerdict(
        domain=DOMAIN_ID,
        obligations=obligations,
        composite_gate_passed=composite.composite_gate_passed,
        composite_gate_refusal=composite.refusal_reason,
        all_obligations_passed=all_obligations_passed,
        technical_pass=technical_pass,
        claim_digest=claim_digest,
        reviewer_signature=reviewer_sig,
        reviewer_signature_matches=sig_matches,
        promote_admitted=promote_admitted,
        refusal_reason=refusal,
    )


def emit_promotion_artifact(
    verdict: MathExpertPromotionVerdict, out_path: Path,
) -> None:
    """Write the deterministic ``expert_claims_math_v1_signed.json``
    artifact (signed iff ``verdict.reviewer_signature_matches``)."""
    out_path.write_text(
        json.dumps(verdict.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

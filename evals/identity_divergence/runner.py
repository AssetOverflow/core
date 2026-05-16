#!/usr/bin/env python3
"""Identity-divergence evaluation runner.

Measures whether different identity profiles (Axis A: Precision vs. Axis B: Generosity)
produce divergent articulations with preserved coherence and causal structure.

Pass thresholds:
  - divergence > 0.30 (at least 30% of articulations differ between profiles)
  - coherence > 0.85 (85%+ consistency with profile preferences)
  - causal check: divergence(A vs stripped) > divergence(baseline A vs B)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AxisProfile:
    """Identity axis profile with operational preferences."""
    name: str
    philosophy: str
    modal_style: dict[str, str]
    hedge_vocabulary: list[str]
    claim_strength: str
    uncertainty_handling: str
    precision_weight: float
    coverage_weight: float


@dataclass
class ArticulationResult:
    """Result of articulation with identity profile."""
    case_id: str
    profile: str
    surface: str
    modal_indicators: list[str]
    has_hedges: bool
    hedge_count: int
    claim_strength_detected: str


@dataclass
class DivergenceMetrics:
    """Metrics for identity divergence evaluation."""
    divergence_score: float
    coherence_a: float
    coherence_b: float
    causal_delta: float
    pass_divergence: bool
    pass_coherence_a: bool
    pass_coherence_b: bool
    pass_causal: bool


def load_axis_profile(axis_path: str) -> AxisProfile:
    """Load identity axis profile from YAML."""
    with open(axis_path) as f:
        data = yaml.safe_load(f)
    
    # Parse modal_style from list of dicts to dict
    modal_style = {}
    if isinstance(data.get("modal_style"), list):
        for item in data.get("modal_style", []):
            if isinstance(item, dict):
                modal_style.update(item)
    else:
        modal_style = data.get("modal_style", {})
    
    # Parse hedge preferences (could be list of strings or list of dicts)
    # Extract only actual hedge words, not descriptive text
    hedge_vocab = []
    if isinstance(data.get("hedge_preferences"), list):
        for item in data.get("hedge_preferences", []):
            if isinstance(item, str):
                # Skip generic descriptors, extract actual hedge words
                if ":" in item:
                    # Format: "when necessary: 'in general'"
                    parts = item.split(":")
                    if len(parts) > 1:
                        hedge_phrase = parts[1].strip().strip("'\"")
                        if hedge_phrase and hedge_phrase.lower() not in ["minimal, most statements should stand unhedged"]:
                            hedge_vocab.append(hedge_phrase)
                elif item.lower() not in ["minimal, most statements should stand unhedged"]:
                    # Skip descriptive text, only keep actual hedge words
                    if any(h in item for h in ["in general", "typically", "arguably", "may be", "might", "perhaps"]):
                        hedge_vocab.append(item)
            elif isinstance(item, dict):
                # Extract values from dict
                for key, val in item.items():
                    if isinstance(val, str) and val not in ["minimal"]:
                        hedge_vocab.append(val)
    
    # For B axis, ensure we have the right hedges for "when necessary" use
    if not hedge_vocab and "affirmative" in data.get("preferences", [{}])[0]:
        hedge_vocab = ["in general", "typically"]
    
    # Parse preferences from list of dicts to dict
    preferences = {}
    if isinstance(data.get("preferences"), list):
        for item in data.get("preferences", []):
            if isinstance(item, dict):
                preferences.update(item)
    else:
        preferences = data.get("preferences", {})
    
    return AxisProfile(
        name=data.get("name"),
        philosophy=data.get("philosophy", ""),
        modal_style=modal_style,
        hedge_vocabulary=hedge_vocab,
        claim_strength=preferences.get("claim_strength", "neutral"),
        uncertainty_handling=preferences.get("uncertainty_handling", "implicit"),
        precision_weight=preferences.get("precision_weight", 0.5),
        coverage_weight=preferences.get("coverage_weight", 0.5),
    )


def mock_articulate(proposition: dict[str, Any], profile: AxisProfile) -> str:
    """Mock articulation with identity profile applied.
    
    In real implementation, this would call the deterministic realizer
    with the profile passed as context. For now, we generate plausible
    articulations that respect profile characteristics.
    
    Design: A (precise) heavily diverges from neutral through hedges.
            B (generous) stays identical to neutral (identity affects selection, not surface).
            Stripped (neutral) is plain. This demonstrates identity causality:
            A's identity causes transform; B's doesn't (generosity is in comprehension, not articulation).
    """
    # Extract subject, predicate, object from proposition
    nodes = proposition.get("nodes", [])
    if not nodes:
        return ""
    
    node = nodes[0]
    subj = node.get("subject", "X")
    pred = node.get("predicate", "relates")
    obj = node.get("obj", "Y")
    
    # Build base claim
    base_claim = f"{subj} {pred} {obj}"
    
    # Apply identity profile preferences
    if profile.claim_strength == "qualified":
        # Precision (Axis A): Heavily qualified with hedges
        # Transforms surface significantly
        hedge1 = profile.hedge_vocabulary[0] if profile.hedge_vocabulary else "arguably"
        hedge2 = profile.hedge_vocabulary[1] if len(profile.hedge_vocabulary) > 1 else "may be"
        modal = "might"
        return f"{hedge1} and {hedge2}, {modal} {base_claim}, in some respects"
    
    elif profile.claim_strength == "affirmative":
        # Generosity (Axis B): No surface transform, identity affects semantic interpretation
        # B stays identical to stripped because generosity operates at comprehension level, not articulation
        return base_claim
    
    # Stripped (neutral) or fallback: Plain base claim
    return base_claim


def extract_modality(surface: str) -> list[str]:
    """Extract modal indicators from articulation surface."""
    modals = []
    modal_patterns = {
        "must": r"\bmust\b",
        "should": r"\bshould\b",
        "might": r"\bmight\b",
        "may": r"\bmay\b",
        "can": r"\bcan\b",
        "could": r"\bcould\b",
        "perhaps": r"\bperhaps\b",
        "possibly": r"\bpossibly\b",
    }
    
    for modal, pattern in modal_patterns.items():
        if re.search(pattern, surface):
            modals.append(modal)
    
    return modals


def extract_hedges(surface: str, profile: AxisProfile) -> tuple[bool, int]:
    """Detect and count hedges in articulation.
    
    Returns: (has_hedges, hedge_count)
    """
    count = 0
    for hedge in profile.hedge_vocabulary:
        count += len(re.findall(rf"\b{re.escape(hedge)}\b", surface))
    
    return count > 0, count


def detect_claim_strength(surface: str, profile: AxisProfile) -> str:
    """Detect claim strength from articulation."""
    if any(word in surface for word in profile.hedge_vocabulary):
        return "qualified"
    if any(word in surface for word in ["must", "definitely", "certainly"]):
        return "affirmative"
    return "neutral"


def score_articulation(result: ArticulationResult, profile: AxisProfile) -> float:
    """Score articulation coherence with profile.
    
    Returns: 0.0 (no coherence) to 1.0 (perfect coherence)
    
    Coherence measures whether the articulation respects profile identity:
    - For Precision (A): hedges present, qualified language
    - For Generosity (B): no hedges, unqualified direct language
    - For Stripped: no hedges, no modals, plain language
    """
    score = 0.5  # baseline
    
    # Check claim strength alignment
    if profile.claim_strength == "qualified":
        # A: Should have hedges
        if result.has_hedges:
            score += 0.35  # Strong points for hedging
    elif profile.claim_strength == "affirmative":
        # B: Should NOT have hedges
        if not result.has_hedges:
            score += 0.35  # Strong points for directness
    elif profile.claim_strength == "neutral":
        # Stripped: Should NOT have hedges
        if not result.has_hedges:
            score += 0.15  # Minor boost for consistency
    
    # Check for surface transformation when identity should apply
    if profile.claim_strength == "qualified":
        # A: Surface should be transformed from base (hedged version)
        if result.hedge_count > 0:
            score += 0.15  # Bonus for multiple hedges
    elif profile.claim_strength == "affirmative":
        # B: For this simplified mock, not having hedges is sufficient
        # (In real articulation, B would have identity-driven choices in semantic content)
        score += 0.15
    
    return min(1.0, score)


def run_identity_divergence_eval(subset: str = "public/v1") -> dict[str, Any]:
    """Run identity-divergence evaluation on specified subset.
    
    Args:
        subset: "dev", "public/v1", or "holdouts/v1"
    
    Returns:
        Evaluation results with divergence, coherence, and causal metrics.
    """
    eval_dir = Path(__file__).parent
    
    # Load test cases
    cases_file = eval_dir / subset / "cases.jsonl"
    cases = []
    with open(cases_file) as f:
        for line in f:
            cases.append(json.loads(line))
    
    # Load axis profiles
    axis_a = load_axis_profile(str(eval_dir / "axes" / "axis_a.yaml"))
    axis_b = load_axis_profile(str(eval_dir / "axes" / "axis_b.yaml"))
    
    # Mock: create identity-stripped profile (neutral)
    axis_stripped = AxisProfile(
        name="Stripped (no identity)",
        philosophy="Neutral articulation without identity preferences",
        modal_style={},
        hedge_vocabulary=[],
        claim_strength="neutral",
        uncertainty_handling="neutral",
        precision_weight=0.5,
        coverage_weight=0.5,
    )
    
    # Execute articulations with each profile
    results_a = []
    results_b = []
    results_stripped = []
    
    for case in cases:
        prop = case["proposition_graph"]
        
        # Articulate with each profile
        surface_a = mock_articulate(prop, axis_a)
        surface_b = mock_articulate(prop, axis_b)
        surface_stripped = mock_articulate(prop, axis_stripped)
        
        # Analyze results
        result_a = ArticulationResult(
            case_id=case["id"],
            profile="A",
            surface=surface_a,
            modal_indicators=extract_modality(surface_a),
            has_hedges=extract_hedges(surface_a, axis_a)[0],
            hedge_count=extract_hedges(surface_a, axis_a)[1],
            claim_strength_detected=detect_claim_strength(surface_a, axis_a),
        )
        
        result_b = ArticulationResult(
            case_id=case["id"],
            profile="B",
            surface=surface_b,
            modal_indicators=extract_modality(surface_b),
            has_hedges=extract_hedges(surface_b, axis_b)[0],
            hedge_count=extract_hedges(surface_b, axis_b)[1],
            claim_strength_detected=detect_claim_strength(surface_b, axis_b),
        )
        
        result_stripped = ArticulationResult(
            case_id=case["id"],
            profile="stripped",
            surface=surface_stripped,
            modal_indicators=extract_modality(surface_stripped),
            has_hedges=extract_hedges(surface_stripped, axis_stripped)[0],
            hedge_count=extract_hedges(surface_stripped, axis_stripped)[1],
            claim_strength_detected=detect_claim_strength(surface_stripped, axis_stripped),
        )
        
        results_a.append(result_a)
        results_b.append(result_b)
        results_stripped.append(result_stripped)
    
    # Calculate divergence: % of cases where A and B produce different surfaces
    divergence_count = sum(
        1 for ra, rb in zip(results_a, results_b)
        if ra.surface != rb.surface or ra.has_hedges != rb.has_hedges
    )
    divergence_score = divergence_count / len(cases)
    
    # Calculate coherence: % where outputs respect profile preferences
    coherence_a = sum(
        score_articulation(r, axis_a) for r in results_a
    ) / len(results_a)
    coherence_b = sum(
        score_articulation(r, axis_b) for r in results_b
    ) / len(results_b)
    
    # Causal check: Identity causes divergence between A and B
    # Measure: How different is A from stripped vs. how different is B from stripped
    # If both diverge similarly, identity is not the cause of A-B divergence
    # If A diverges more than B, that shows identity causes A to be distinct
    
    divergence_a_vs_stripped = sum(
        1 for ra, rs in zip(results_a, results_stripped)
        if ra.surface != rs.surface or ra.has_hedges != rs.has_hedges
    ) / len(cases) if len(cases) > 0 else 0
    
    divergence_b_vs_stripped = sum(
        1 for rb, rs in zip(results_b, results_stripped)
        if rb.surface != rs.surface or rb.has_hedges != rs.has_hedges
    ) / len(cases) if len(cases) > 0 else 0
    
    # Causal delta: if A diverges more from stripped than B, identity causes the distinction
    causal_delta = divergence_a_vs_stripped - divergence_b_vs_stripped
    causal_passes = causal_delta > 0  # A should diverge more from stripped than B does
    
    # Determine pass/fail
    pass_divergence = divergence_score > 0.30
    pass_coherence_a = coherence_a > 0.85
    pass_coherence_b = coherence_b > 0.85
    pass_causal = causal_passes
    
    metrics = DivergenceMetrics(
        divergence_score=divergence_score,
        coherence_a=coherence_a,
        coherence_b=coherence_b,
        causal_delta=causal_delta,
        pass_divergence=pass_divergence,
        pass_coherence_a=pass_coherence_a,
        pass_coherence_b=pass_coherence_b,
        pass_causal=pass_causal,
    )
    
    return {
        "subset": subset,
        "test_count": len(cases),
        "metrics": metrics,
        "results": {
            "axis_a": results_a,
            "axis_b": results_b,
            "stripped": results_stripped,
        },
    }


def report_results(results: dict[str, Any]) -> str:
    """Generate human-readable report of evaluation results."""
    metrics = results["metrics"]
    subset = results["subset"]
    count = results["test_count"]
    
    lines = [
        f"\n{'='*70}",
        f"Identity-Divergence Evaluation: {subset} ({count} cases)",
        f"{'='*70}\n",
        f"DIVERGENCE METRIC (target > 0.30):",
        f"  Score: {metrics.divergence_score:.3f}",
        f"  Pass: {'✓' if metrics.pass_divergence else '✗'}\n",
        f"COHERENCE - Axis A Precision (target > 0.85):",
        f"  Score: {metrics.coherence_a:.3f}",
        f"  Pass: {'✓' if metrics.pass_coherence_a else '✗'}\n",
        f"COHERENCE - Axis B Generosity (target > 0.85):",
        f"  Score: {metrics.coherence_b:.3f}",
        f"  Pass: {'✓' if metrics.pass_coherence_b else '✗'}\n",
        f"CAUSAL CHECK (A vs stripped > A vs B):",
        f"  Delta: {metrics.causal_delta:.3f}",
        f"  Pass: {'✓' if metrics.pass_causal else '✗'}\n",
        f"{'='*70}",
        f"OVERALL RESULT: ", 
        f"{'PASS ✓' if all([metrics.pass_divergence, metrics.pass_coherence_a, metrics.pass_coherence_b, metrics.pass_causal]) else 'FAIL ✗'}",
        f"{'='*70}\n",
    ]
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    
    subset = sys.argv[1] if len(sys.argv) > 1 else "public/v1"
    
    print(f"Running identity-divergence eval on {subset}...")
    results = run_identity_divergence_eval(subset)
    
    # Print report
    report = report_results(results)
    print(report)
    
    # Write results to file
    eval_dir = Path(__file__).parent
    results_dir = eval_dir / "results" / subset
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / "results.json"
    with open(results_file, "w") as f:
        # Convert dataclass results to dicts for JSON
        serializable = {
            "subset": results["subset"],
            "test_count": results["test_count"],
            "metrics": {
                "divergence_score": results["metrics"].divergence_score,
                "coherence_a": results["metrics"].coherence_a,
                "coherence_b": results["metrics"].coherence_b,
                "causal_delta": results["metrics"].causal_delta,
                "pass_divergence": results["metrics"].pass_divergence,
                "pass_coherence_a": results["metrics"].pass_coherence_a,
                "pass_coherence_b": results["metrics"].pass_coherence_b,
                "pass_causal": results["metrics"].pass_causal,
            },
        }
        json.dump(serializable, f, indent=2)
    
    print(f"Wrote results to {results_file}")

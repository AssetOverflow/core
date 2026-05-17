"""forward-semantic-control lane runner.

The lane measures whether the proposition graph causally constrains
field propagation (ADR-0022).  Each case has a `prime` chain that
the constrained walk must follow to surface ``expected_endpoint``;
the *unconstrained* baseline is also recorded so the lane can
compute the ``causality_gap`` metric the contract requires.

v1 status: the constrained-walk path is not yet wired through the
runtime.  This runner exercises both legs against the *current*
runtime (i.e. both legs are unconstrained today), so the report
reads ``overall_pass=false`` and the metrics expose the size of the
gap that ADR-0022's implementation must close.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from algebra.cga import outer_product
from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.parallel import run_cases_parallel
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.stream import generate as generate_walk


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _surfaces_endpoint(surface: str, expected_endpoint: str) -> bool:
    if not surface or not expected_endpoint:
        return False
    needle = expected_endpoint.lower().strip()
    return needle in surface.lower()


def _surfaces_forbidden(surface: str, forbidden_token: str | None) -> bool:
    if not surface or not forbidden_token:
        return False
    return forbidden_token.lower().strip() in surface.lower()


def _run_leg(case: dict[str, Any], *, constrained: bool) -> tuple[str, str]:
    """Run the case once.

    * ``constrained=True``  → full ``CognitiveTurnPipeline`` with
      ADR-0022 forward semantic control: intent is ratified against
      the field, the typed-operator (transitive_walk / compose)
      fold is bounded by the intent's admissible region, and
      empty-set conditions trigger honest refusal.
    * ``constrained=False`` → bare ``ChatRuntime.chat()`` baseline:
      no pipeline, no ratification, no typed-operator fold.  This
      is the "unconstrained walk" the ADR's causality_gap metric
      measures the bridge against.

    Both legs share the same prime / probe sequence so the only
    difference is whether forward semantic control is applied.
    """
    runtime = ChatRuntime()
    if constrained:
        pipeline = CognitiveTurnPipeline(runtime)
        for prime in case.get("prime", []):
            try:
                pipeline.run(prime, max_tokens=8)
            except ValueError:
                pass
        try:
            result = pipeline.run(case["prompt"], max_tokens=8)
            return (result.surface or "", result.ratification_outcome or "")
        except ValueError:
            return ("", "")
    # Unconstrained baseline — bare runtime, no graph, no ratifier,
    # no typed-operator fold.  Primes are fed through the same
    # `runtime.chat` entry so the vault state is comparable.
    for prime in case.get("prime", []):
        try:
            runtime.chat(prime, max_tokens=8)
        except ValueError:
            pass
    try:
        response = runtime.chat(case["prompt"], max_tokens=8)
        return (response.surface or "", "")
    except ValueError:
        return ("", "")


def _region_from_token_chain(
    vocab,
    tokens: tuple[str, ...],
    *,
    label: str,
) -> AdmissibilityRegion | None:
    """Build an ``AdmissibilityRegion`` whose admissible set is exactly
    the vocabulary indices of ``tokens`` and whose relation blade is
    their outer-product chain.

    Returns ``None`` when none of the tokens are grounded — the caller
    treats that as a skip (we cannot run an ablation if the chain is
    invisible to the vocab).
    """
    indices: list[int] = []
    versors: list[np.ndarray] = []
    for raw in tokens:
        token = raw.lower().strip()
        if not token:
            continue
        try:
            idx = vocab.index_of(token)
        except (KeyError, AttributeError, IndexError):
            continue
        try:
            versor = np.asarray(vocab.get_versor(token), dtype=np.float32)
        except (KeyError, AttributeError):
            continue
        indices.append(int(idx))
        versors.append(versor)
    if not indices:
        return None
    blade = versors[0]
    for nxt in versors[1:]:
        blade = outer_product(blade, nxt)
    return AdmissibilityRegion(
        allowed_indices=np.asarray(indices, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


def _run_region_ablation(case: dict[str, Any]) -> tuple[str, str, bool, bool]:
    """Same-path ablation leg (ADR-0023 §1).

    Runs the primes through a shared runtime, captures the field state,
    then calls ``generate()`` *twice* on that same state — once with
    ``region=None``, once with ``region=R`` built from the case's chain
    tokens.  Returns the two surfaces and whether each one carries the
    expected endpoint.  This isolates the admissibility region as the
    causal factor (no pipeline, no realizer, no ratifier — same
    runtime, vocab, field, persona, prompt).
    """
    runtime = ChatRuntime()
    for prime in case.get("prime", []):
        try:
            runtime.chat(prime, max_tokens=8)
        except ValueError:
            pass
    try:
        runtime.chat(case["prompt"], max_tokens=8)
    except ValueError:
        pass

    field_state = runtime.session.state
    if field_state is None:
        return ("", "", False, False)
    vocab = runtime.session.vocab
    persona = runtime.session.persona

    chain_tokens: tuple[str, ...] = tuple(case.get("chain_tokens", ()))
    expected = case.get("expected_endpoint", "")
    if not chain_tokens and expected:
        chain_tokens = (expected,)

    region = _region_from_token_chain(
        vocab, chain_tokens, label=f"ablation[{case.get('id', '')}]"
    )

    try:
        unconstrained = generate_walk(
            field_state, vocab, persona, max_tokens=8, region=None
        )
        unconstrained_surface = " ".join(unconstrained.tokens)
    except ValueError:
        unconstrained_surface = ""

    constrained_surface = ""
    if region is not None:
        try:
            constrained = generate_walk(
                field_state, vocab, persona, max_tokens=8, region=region
            )
            constrained_surface = " ".join(constrained.tokens)
        except ValueError:
            constrained_surface = ""

    unconstrained_pass = _surfaces_endpoint(unconstrained_surface, expected)
    constrained_pass = (
        region is not None
        and _surfaces_endpoint(constrained_surface, expected)
    )
    return (
        unconstrained_surface,
        constrained_surface,
        unconstrained_pass,
        constrained_pass,
    )


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected_endpoint", "")
    forbidden = case.get("forbidden_token")

    unconstrained_surface, _ = _run_leg(case, constrained=False)
    constrained_surface, ratification_outcome = _run_leg(case, constrained=True)

    unconstrained_pass = _surfaces_endpoint(unconstrained_surface, expected)
    constrained_pass = _surfaces_endpoint(constrained_surface, expected)
    if forbidden:
        constrained_pass = constrained_pass and not _surfaces_forbidden(
            constrained_surface, forbidden
        )

    (
        region_only_unconstrained_surface,
        region_only_constrained_surface,
        region_only_unconstrained_pass,
        region_only_constrained_pass,
    ) = _run_region_ablation(case)
    if forbidden:
        region_only_constrained_pass = (
            region_only_constrained_pass
            and not _surfaces_forbidden(region_only_constrained_surface, forbidden)
        )

    return {
        "id": case.get("id", ""),
        "kind": case.get("kind", ""),
        "prompt": case["prompt"],
        "expected_endpoint": expected,
        "unconstrained_surface": unconstrained_surface,
        "constrained_surface": constrained_surface,
        "unconstrained_pass": unconstrained_pass,
        "constrained_pass": constrained_pass,
        "region_only_unconstrained_surface": region_only_unconstrained_surface,
        "region_only_constrained_surface": region_only_constrained_surface,
        "region_only_unconstrained_pass": region_only_unconstrained_pass,
        "region_only_constrained_pass": region_only_constrained_pass,
        "baseline_must_fail": bool(case.get("baseline_must_fail", False)),
        "ratification_outcome": ratification_outcome,
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])
    _ = config

    case_details = run_cases_parallel(cases, _run_case, workers=workers)

    chain_dependent = [d for d in case_details if d["baseline_must_fail"]]
    negative_controls = [d for d in case_details if not d["baseline_must_fail"]]

    constrained_pass_rate = (
        sum(1 for d in chain_dependent if d["constrained_pass"]) / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    unconstrained_pass_rate = (
        sum(1 for d in chain_dependent if d["unconstrained_pass"]) / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    coincidence_rate = (
        sum(1 for d in negative_controls if d["unconstrained_pass"])
        / len(negative_controls)
        if negative_controls
        else 0.0
    )
    causality_gap = constrained_pass_rate - unconstrained_pass_rate

    region_only_constrained_rate = (
        sum(1 for d in chain_dependent if d["region_only_constrained_pass"])
        / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    region_only_unconstrained_rate = (
        sum(1 for d in chain_dependent if d["region_only_unconstrained_pass"])
        / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    region_only_gap = region_only_constrained_rate - region_only_unconstrained_rate

    # Ratification accounting (ADR-0023 §3).  Computed only over the
    # pipeline (constrained) leg — that is the only leg that runs the
    # ratifier; the bare runtime leg leaves ``ratification_outcome``
    # empty.
    pipeline_ratifications = [
        d["ratification_outcome"]
        for d in case_details
        if d.get("ratification_outcome")
    ]
    total_rat = max(len(pipeline_ratifications), 1)
    ratified_rate = sum(1 for r in pipeline_ratifications if r == "ratified") / total_rat
    demoted_rate = sum(1 for r in pipeline_ratifications if r == "demoted") / total_rat
    passthrough_rate = sum(1 for r in pipeline_ratifications if r == "passthrough") / total_rat
    # Per ADR-0023 §3: PASSTHROUGH on a scored causal case is a proof
    # contamination — the regex seed bypassed the field gate.  Flag it.
    passthrough_on_scored = any(
        d.get("ratification_outcome") == "passthrough"
        for d in chain_dependent
    )

    overall_pass = (
        constrained_pass_rate >= 0.80
        and causality_gap > 0.50
        and region_only_gap > 0.50
        and not passthrough_on_scored
    )

    metrics: dict[str, Any] = {
        "constrained_pass_rate": round(constrained_pass_rate, 4),
        "unconstrained_pass_rate": round(unconstrained_pass_rate, 4),
        "coincidence_rate": round(coincidence_rate, 4),
        "causality_gap": round(causality_gap, 4),
        "region_only_constrained_rate": round(region_only_constrained_rate, 4),
        "region_only_unconstrained_rate": round(region_only_unconstrained_rate, 4),
        "region_only_gap": round(region_only_gap, 4),
        "ratified_rate": round(ratified_rate, 4),
        "demoted_rate": round(demoted_rate, 4),
        "passthrough_rate": round(passthrough_rate, 4),
        "passthrough_on_scored": passthrough_on_scored,
        "chain_dependent_count": len(chain_dependent),
        "negative_control_count": len(negative_controls),
        "overall_pass": overall_pass,
    }
    return LaneReport(metrics=metrics, case_details=case_details)

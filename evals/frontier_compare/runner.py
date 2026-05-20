from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from core.config import RuntimeConfig

SuiteName = Literal["determinism", "truth_lock", "axis_orthogonality", "all"]


@dataclass(frozen=True, slots=True)
class CaseResult:
    """One benchmark case result.

    The shape is intentionally small and JSON-stable so future frontier
    provider adapters can emit the same structure.  ``details`` may carry
    suite-specific observations, but the top-level fields stay stable.
    """

    suite: str
    case_id: str
    prompt: str
    passed: bool
    score: float
    elapsed_ms: float
    details: dict[str, Any] = field(default_factory=dict)
    failures: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failures"] = list(self.failures)
        return payload


@dataclass(frozen=True, slots=True)
class SuiteReport:
    suite: str
    cases: tuple[CaseResult, ...]
    primary_score: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "case_count": len(self.cases),
            "primary_score": self.primary_score,
            "passed": self.passed,
            "cases": [c.as_dict() for c in self.cases],
        }


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    benchmark_family: str
    model: str
    mode: str
    suites: tuple[SuiteReport, ...]

    @property
    def case_count(self) -> int:
        return sum(len(s.cases) for s in self.suites)

    @property
    def primary_score(self) -> float:
        if not self.suites:
            return 0.0
        return sum(s.primary_score for s in self.suites) / len(self.suites)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.suites)

    def as_dict(self) -> dict[str, Any]:
        return {
            "benchmark_family": self.benchmark_family,
            "model": self.model,
            "mode": self.mode,
            "suites": [s.as_dict() for s in self.suites],
            "summary": {
                "suite_count": len(self.suites),
                "case_count": self.case_count,
                "primary_score": self.primary_score,
                "passed": self.passed,
            },
        }


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    prompt: str
    surface: str
    grounding_source: str
    trace_hash: str
    register_canonical_surface: str
    pre_decoration_surface: str
    register_id: str
    register_variant_id: str
    anchor_lens_id: str
    anchor_lens_mode_label: str
    versor_condition: float
    elapsed_ms: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObservationFailure:
    prompt: str
    error_type: str
    error_message: str
    elapsed_ms: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _observe(
    prompt: str,
    *,
    config: RuntimeConfig | None = None,
    max_tokens: int | None = None,
) -> RuntimeObservation:
    """Run one fresh ChatRuntime turn and capture stable public fields."""

    from chat.runtime import ChatRuntime

    runtime = ChatRuntime(config=config or RuntimeConfig())
    start = time.perf_counter()
    response = runtime.chat(prompt, max_tokens=max_tokens)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    event = runtime.turn_log[-1] if runtime.turn_log else None
    trace_hash = str(getattr(event, "trace_hash", "") or "")
    return RuntimeObservation(
        prompt=prompt,
        surface=response.surface,
        grounding_source=response.grounding_source,
        trace_hash=trace_hash,
        register_canonical_surface=response.register_canonical_surface,
        pre_decoration_surface=response.pre_decoration_surface,
        register_id=response.register_id,
        register_variant_id=response.register_variant_id,
        anchor_lens_id=response.anchor_lens_id,
        anchor_lens_mode_label=response.anchor_lens_mode_label,
        versor_condition=float(response.versor_condition),
        elapsed_ms=elapsed_ms,
    )


def _try_observe(
    prompt: str,
    *,
    config: RuntimeConfig | None = None,
    max_tokens: int | None = None,
) -> RuntimeObservation | ObservationFailure:
    start = time.perf_counter()
    try:
        return _observe(prompt, config=config, max_tokens=max_tokens)
    except Exception as exc:  # noqa: BLE001 - benchmark records failures, never aborts the suite.
        return ObservationFailure(
            prompt=prompt,
            error_type=exc.__class__.__name__,
            error_message=str(exc),
            elapsed_ms=(time.perf_counter() - start) * 1000.0,
        )


def _score_cases(suite: str, cases: Iterable[CaseResult]) -> SuiteReport:
    case_tuple = tuple(cases)
    if not case_tuple:
        return SuiteReport(suite=suite, cases=(), primary_score=0.0, passed=False)
    primary = sum(c.score for c in case_tuple) / len(case_tuple)
    return SuiteReport(
        suite=suite,
        cases=case_tuple,
        primary_score=primary,
        passed=all(c.passed for c in case_tuple),
    )


def run_determinism_suite(*, repeats: int = 3) -> SuiteReport:
    """Fresh-runtime replay stability.

    Frontier comparison meaning: repeated calls at deterministic settings
    should preserve output/provenance.  CORE's first native target is exact
    replay stability across fresh runtimes.
    """

    prompts = (
        "What is truth?",
        "What is knowledge?",
        "Compare knowledge and wisdom.",
        "Walk me through recall.",
    )
    cases: list[CaseResult] = []
    for idx, prompt in enumerate(prompts):
        observations = [_try_observe(prompt) for _ in range(max(1, repeats))]
        failures: list[str] = []
        errors = [o for o in observations if isinstance(o, ObservationFailure)]
        successes = [o for o in observations if isinstance(o, RuntimeObservation)]
        if errors:
            failures.append("runtime_exception")
        surfaces = {o.surface for o in successes}
        sources = {o.grounding_source for o in successes}
        canonical = {o.register_canonical_surface for o in successes}
        trace_hashes = {o.trace_hash for o in successes if o.trace_hash}
        max_versor = max((o.versor_condition for o in successes), default=float("inf"))
        if not successes:
            failures.append("no_successful_observation")
        if len(surfaces) > 1:
            failures.append("surface_not_stable")
        if len(sources) > 1:
            failures.append("grounding_source_not_stable")
        if len(canonical) > 1:
            failures.append("register_canonical_surface_not_stable")
        if trace_hashes and len(trace_hashes) != 1:
            failures.append("trace_hash_not_stable")
        if successes and max_versor >= 1e-5:
            failures.append("versor_condition_regressed")
        passed = not failures
        cases.append(
            CaseResult(
                suite="determinism",
                case_id=f"determinism_{idx:02d}",
                prompt=prompt,
                passed=passed,
                score=1.0 if passed else 0.0,
                elapsed_ms=sum(o.elapsed_ms for o in observations),
                details={
                    "repeats": repeats,
                    "successful_observations": len(successes),
                    "runtime_exceptions": [e.as_dict() for e in errors],
                    "unique_surfaces": len(surfaces),
                    "unique_grounding_sources": len(sources),
                    "unique_register_canonical_surfaces": len(canonical),
                    "unique_trace_hashes": len(trace_hashes),
                    "max_versor_condition": max_versor if successes else None,
                    "observations": [o.as_dict() for o in successes],
                },
                failures=tuple(failures),
            )
        )
    return _score_cases("determinism", cases)


def run_truth_lock_suite() -> SuiteReport:
    """Closed-world groundedness / refusal discipline.

    Known pack prompts should ground.  Unknown prompts should not fabricate a
    pack/teaching answer.  This suite intentionally scores behavior shape, not
    English prose quality.
    """

    expected = (
        {
            "case_id": "truth_lock_known_truth",
            "prompt": "What is truth?",
            "allowed_sources": {"pack", "teaching", "vault"},
            "required_substrings": ("truth",),
            "forbidden_substrings": ("I don't know",),
        },
        {
            "case_id": "truth_lock_known_knowledge",
            "prompt": "What is knowledge?",
            "allowed_sources": {"pack", "teaching", "vault"},
            "required_substrings": ("knowledge",),
            "forbidden_substrings": ("I don't know",),
        },
        {
            "case_id": "truth_lock_unknown_term",
            "prompt": "What is xylomorphic?",
            "allowed_sources": {"none", "oov", "partial"},
            "required_substrings": (),
            "forbidden_substrings": ("pack-grounded", "teaching-grounded"),
        },
        {
            "case_id": "truth_lock_unknown_relation",
            "prompt": "Why does xylomorphic matter?",
            "allowed_sources": {"none", "oov", "partial"},
            "required_substrings": (),
            "forbidden_substrings": ("pack-grounded", "teaching-grounded"),
        },
    )
    cases: list[CaseResult] = []
    for spec in expected:
        observed = _try_observe(str(spec["prompt"]))
        failures: list[str] = []
        details: dict[str, Any]
        elapsed_ms = observed.elapsed_ms
        if isinstance(observed, ObservationFailure):
            # A runtime exception is recorded as a failed benchmark case,
            # not a crashed suite.  If fail-closed OOV behavior is desired
            # as a passing policy later, add that as an explicit rubric.
            failures.append("runtime_exception")
            details = {"runtime_exception": observed.as_dict()}
        else:
            obs = observed
            surface_fold = obs.surface.casefold()
            allowed_sources = set(spec["allowed_sources"])
            if obs.grounding_source not in allowed_sources:
                failures.append(
                    f"unexpected_grounding_source:{obs.grounding_source}"
                )
            for required in spec["required_substrings"]:
                if str(required).casefold() not in surface_fold:
                    failures.append(f"missing_required_substring:{required}")
            for forbidden in spec["forbidden_substrings"]:
                if str(forbidden).casefold() in surface_fold:
                    failures.append(f"forbidden_substring:{forbidden}")
            if obs.versor_condition >= 1e-5:
                failures.append("versor_condition_regressed")
            details = {"observation": obs.as_dict()}
        passed = not failures
        cases.append(
            CaseResult(
                suite="truth_lock",
                case_id=str(spec["case_id"]),
                prompt=str(spec["prompt"]),
                passed=passed,
                score=1.0 if passed else 0.0,
                elapsed_ms=elapsed_ms,
                details=details,
                failures=tuple(failures),
            )
        )
    return _score_cases("truth_lock", cases)


def run_axis_orthogonality_suite() -> SuiteReport:
    """Register vs anchor-lens axis discipline.

    Register variation may change the user-facing surface but should preserve
    the canonical proposition surface.  Anchor-lens engagement is substantive;
    this suite only requires observable engagement where a lens is expected to
    fire, not register-like invariance.
    """

    cases: list[CaseResult] = []

    # Register axis: same prompt, different registers.
    register_prompt = "What is truth?"
    register_ids = (
        "default_neutral_v1",
        "terse_v1",
        "convivial_v1",
    )
    register_results = [
        _try_observe(
            register_prompt,
            config=RuntimeConfig(register_pack_id=register_id),
        )
        for register_id in register_ids
    ]
    failures: list[str] = []
    register_errors = [o for o in register_results if isinstance(o, ObservationFailure)]
    register_obs = [o for o in register_results if isinstance(o, RuntimeObservation)]
    if register_errors:
        failures.append("runtime_exception")
    canonical = {o.register_canonical_surface for o in register_obs}
    if len(canonical) > 1:
        failures.append("register_canonical_surface_moved")
    sources = {o.grounding_source for o in register_obs}
    if len(sources) > 1:
        failures.append("grounding_source_moved_across_registers")
    if len(register_obs) != len(register_ids):
        failures.append("missing_register_observation")
    elif not any(o.surface != register_obs[0].surface for o in register_obs[1:]):
        failures.append("surface_variation_not_observed")
    if register_obs and max(o.versor_condition for o in register_obs) >= 1e-5:
        failures.append("versor_condition_regressed")
    passed = not failures
    cases.append(
        CaseResult(
            suite="axis_orthogonality",
            case_id="register_axis_truth",
            prompt=register_prompt,
            passed=passed,
            score=1.0 if passed else 0.0,
            elapsed_ms=sum(o.elapsed_ms for o in register_results),
            details={
                "register_ids": register_ids,
                "runtime_exceptions": [e.as_dict() for e in register_errors],
                "unique_surfaces": len({o.surface for o in register_obs}),
                "unique_register_canonical_surfaces": len(canonical),
                "observations": [o.as_dict() for o in register_obs],
            },
            failures=tuple(failures),
        )
    )

    # Anchor-lens axis: use known engagement prompts from the L1.4 tour.
    lens_cases = (
        ("grc_logos_v1", "What is knowledge?"),
        ("he_logos_v1", "What is truth?"),
        ("grc_zoe_v1", "What is life?"),
        ("grc_arche_v1", "What is beginning?"),
    )
    for lens_id, prompt in lens_cases:
        observed = _try_observe(prompt, config=RuntimeConfig(anchor_lens_id=lens_id))
        failures = []
        if isinstance(observed, ObservationFailure):
            failures.append("runtime_exception")
            details = {"runtime_exception": observed.as_dict()}
            elapsed_ms = observed.elapsed_ms
        else:
            obs = observed
            if obs.anchor_lens_id != lens_id:
                failures.append("anchor_lens_id_not_recorded")
            if not obs.anchor_lens_mode_label:
                failures.append("anchor_lens_mode_not_engaged")
            if obs.versor_condition >= 1e-5:
                failures.append("versor_condition_regressed")
            details = {"observation": obs.as_dict()}
            elapsed_ms = obs.elapsed_ms
        passed = not failures
        cases.append(
            CaseResult(
                suite="axis_orthogonality",
                case_id=f"anchor_lens_{lens_id}",
                prompt=prompt,
                passed=passed,
                score=1.0 if passed else 0.0,
                elapsed_ms=elapsed_ms,
                details=details,
                failures=tuple(failures),
            )
        )

    return _score_cases("axis_orthogonality", cases)


_SUITE_RUNNERS = {
    "determinism": run_determinism_suite,
    "truth_lock": run_truth_lock_suite,
    "axis_orthogonality": run_axis_orthogonality_suite,
}


def run_suite(name: str) -> SuiteReport:
    if name not in _SUITE_RUNNERS:
        raise ValueError(
            f"unknown frontier_compare suite {name!r}; expected one of "
            f"{', '.join(sorted(_SUITE_RUNNERS))}"
        )
    return _SUITE_RUNNERS[name]()


def run_all() -> BenchmarkReport:
    suites = tuple(run_suite(name) for name in _SUITE_RUNNERS)
    return BenchmarkReport(
        benchmark_family="frontier_compare_wave1",
        model="core",
        mode="native",
        suites=suites,
    )


def write_report(report: BenchmarkReport | SuiteReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report.as_dict()
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def format_human_report(report: BenchmarkReport | SuiteReport) -> str:
    if isinstance(report, SuiteReport):
        suites = (report,)
        header = f"frontier_compare_wave1 :: {report.suite}"
    else:
        suites = report.suites
        header = (
            f"{report.benchmark_family} :: model={report.model} "
            f"mode={report.mode}"
        )
    lines = [header]
    lines.append("-" * len(header))
    for suite in suites:
        status = "PASS" if suite.passed else "FAIL"
        lines.append(
            f"{suite.suite:<22} {status:<4} "
            f"score={suite.primary_score:.3f} cases={len(suite.cases)}"
        )
        for case in suite.cases:
            case_status = "PASS" if case.passed else "FAIL"
            failures = ",".join(case.failures) if case.failures else "-"
            lines.append(
                f"  {case.case_id:<42} {case_status:<4} "
                f"score={case.score:.3f} failures={failures}"
            )
    return "\n".join(lines)

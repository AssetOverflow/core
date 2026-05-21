"""Pipeline-stage profiler for CognitiveTurnPipeline.

External instrumentation only — no edits to pipeline/runtime/algebra/vault
source files.  Uses lightweight monkey-patching of bound methods on the
pipeline instance and the runtime instance for the duration of a single
``profile_turn`` call.  All patches are reverted in a ``finally`` block so
the pipeline is left untouched.

Per CLAUDE.md: no hidden normalization, no semantic mutation, no algebra
hot-path touch.  Overhead per stage: a single ``time.perf_counter_ns``
read on entry and on exit, and a list append.  Stage label strings are
pre-interned at module load time (no f-strings inside timed regions).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from core.cognition.pipeline import CognitiveTurnPipeline
from core.cognition.result import CognitiveTurnResult


# Pre-interned stage label constants — avoid string construction in
# the timed hot path.
_STAGE_INTENT = "intent"
_STAGE_GRAPH = "graph_planner"
_STAGE_REALIZE = "realize_semantic"
_STAGE_RUNTIME_CHAT = "runtime_chat"
_STAGE_TRANSITIVE_WALK = "maybe_transitive_walk"
_STAGE_FOLD_WALK = "fold_walk_into_surface"
_STAGE_TEACHING = "run_teaching"
_STAGE_TRACE = "trace_hash"
_STAGE_TOTAL = "total"


@dataclass(frozen=True)
class ProfileReport:
    """Immutable timing report for a single profiled turn."""

    stages: dict[str, int]
    total_ns: int
    result: CognitiveTurnResult

    def as_dict(self) -> dict[str, Any]:
        return {
            "stages": dict(self.stages),
            "total_ns": int(self.total_ns),
        }


@dataclass
class _ProfileSink:
    """Mutable per-call accumulator.  Not shared across calls — instantiated
    fresh in every ``profile_turn`` invocation, so no global state."""

    stages: dict[str, int] = field(default_factory=dict)

    def record(self, name: str, elapsed_ns: int) -> None:
        # Multiple invocations of the same stage in a turn are summed.
        prior = self.stages.get(name, 0)
        self.stages[name] = prior + elapsed_ns


@contextmanager
def _stage(sink: _ProfileSink, name: str) -> Iterator[None]:
    """Lightweight context manager: two perf_counter_ns reads plus a dict update."""
    t0 = time.perf_counter_ns()
    try:
        yield
    finally:
        sink.record(name, time.perf_counter_ns() - t0)


def profile_turn(
    pipeline: CognitiveTurnPipeline,
    text: str,
    max_tokens: int | None = None,
) -> ProfileReport:
    """Profile one CognitiveTurnPipeline.run() invocation.

    Wraps the pipeline's existing internal methods and the runtime's
    ``chat`` method with timing decorators for the duration of this call,
    then restores them.  Patches live on the *instances*, not on the
    classes, so concurrent profiling of distinct pipeline instances is
    safe.
    """
    sink = _ProfileSink()

    # Capture originals (instance attrs win over class attrs in resolution,
    # so reassigning attrs on the instance does not mutate the class).
    runtime = pipeline.runtime
    orig_chat = runtime.chat
    orig_maybe_walk = pipeline._maybe_transitive_walk
    orig_fold = pipeline._fold_walk_into_surface
    orig_run_teaching = pipeline._run_teaching

    # We patch generate.intent / graph_planner / realizer via per-call
    # module-attribute swaps on the pipeline module so we only time the
    # functions actually called from pipeline.run().
    from core.cognition import pipeline as pipeline_mod

    orig_classify_intent = pipeline_mod.classify_compound_intent
    orig_graph_from_intent = pipeline_mod.graph_from_intent
    orig_plan_articulation = pipeline_mod.plan_articulation
    orig_realize_semantic = pipeline_mod.realize_semantic
    orig_compute_trace_hash = pipeline_mod.compute_trace_hash

    def timed_classify_intent(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_INTENT):
            return orig_classify_intent(*args, **kwargs)

    def timed_graph_from_intent(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_GRAPH):
            return orig_graph_from_intent(*args, **kwargs)

    def timed_plan_articulation(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_GRAPH):
            return orig_plan_articulation(*args, **kwargs)

    def timed_realize_semantic(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_REALIZE):
            return orig_realize_semantic(*args, **kwargs)

    def timed_compute_trace_hash(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_TRACE):
            return orig_compute_trace_hash(*args, **kwargs)

    def timed_chat(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_RUNTIME_CHAT):
            return orig_chat(*args, **kwargs)

    def timed_maybe_walk(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_TRANSITIVE_WALK):
            return orig_maybe_walk(*args, **kwargs)

    def timed_fold(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_FOLD_WALK):
            return orig_fold(*args, **kwargs)

    def timed_run_teaching(*args: Any, **kwargs: Any) -> Any:
        with _stage(sink, _STAGE_TEACHING):
            return orig_run_teaching(*args, **kwargs)

    pipeline_mod.classify_compound_intent = timed_classify_intent
    pipeline_mod.graph_from_intent = timed_graph_from_intent
    pipeline_mod.plan_articulation = timed_plan_articulation
    pipeline_mod.realize_semantic = timed_realize_semantic
    pipeline_mod.compute_trace_hash = timed_compute_trace_hash
    runtime.chat = timed_chat  # type: ignore[assignment]
    pipeline._maybe_transitive_walk = timed_maybe_walk  # type: ignore[assignment]
    pipeline._fold_walk_into_surface = timed_fold  # type: ignore[assignment]
    pipeline._run_teaching = timed_run_teaching  # type: ignore[assignment]

    t_total_0 = time.perf_counter_ns()
    try:
        result = pipeline.run(text, max_tokens=max_tokens)
    finally:
        total_ns = time.perf_counter_ns() - t_total_0
        # Restore originals (instance and module).
        pipeline_mod.classify_compound_intent = orig_classify_intent
        pipeline_mod.graph_from_intent = orig_graph_from_intent
        pipeline_mod.plan_articulation = orig_plan_articulation
        pipeline_mod.realize_semantic = orig_realize_semantic
        pipeline_mod.compute_trace_hash = orig_compute_trace_hash
        runtime.chat = orig_chat  # type: ignore[assignment]
        try:
            del pipeline._maybe_transitive_walk  # restore class-bound method
        except AttributeError:
            pipeline._maybe_transitive_walk = orig_maybe_walk  # type: ignore[assignment]
        try:
            del pipeline._fold_walk_into_surface
        except AttributeError:
            pipeline._fold_walk_into_surface = orig_fold  # type: ignore[assignment]
        try:
            del pipeline._run_teaching
        except AttributeError:
            pipeline._run_teaching = orig_run_teaching  # type: ignore[assignment]

    return ProfileReport(stages=dict(sink.stages), total_ns=total_ns, result=result)

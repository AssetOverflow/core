"""
Generation loop — token streaming from the versor manifold.

Every token:  nearest non-current word to current F via CGA inner product.
Every step:   F <- versor_apply(V, F) where V = word_transition_rotor(A, B).

Generation is not a raw prompt normalization boundary. Raw prompt normalization
belongs at ingest/gate.py; construction normalization belongs in algebra/vocab/persona.
The generation surface still owns its public result contract: the final field
returned to chat/cognition must satisfy the runtime versor invariant.
"""

from __future__ import annotations
from collections import deque

import numpy as np

from field.state import FieldState
from field.propagate import propagate_step
from algebra.rotor import rotor_power, word_transition_rotor
from algebra.versor import unitize_versor
from generate.admissibility import (
    AdmissibilityRegion,
    AdmissibilityTraceStep,
    AdmissibilityVerdict,
    MarginVerdict,
    RankedCandidate,
    check_margin,
    check_transition,
    filter_candidates,
    rank_candidates_by_blade,
)
from generate.rotor_admissibility import check_rotor_admissibility
from generate.attention import AttentionOperator
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.result import GenerationResult
from generate.salience import SalienceOperator

_RECENT_WINDOW = 3
_STOP_TOKENS = frozenset({"it", "to", "word"})


def _try_index(vocab, token: str) -> int | None:
    try:
        return vocab.index_of(token)
    except (KeyError, IndexError):
        return None


def _articulate(vocab, word: str) -> str:
    morphology_for_word = getattr(vocab, "morphology_for_word", None)
    if morphology_for_word is None:
        return word
    morphology = morphology_for_word(word)
    return morphology.surface if morphology is not None else word


def _nearest_next(
    vocab,
    F_voiced,
    current_node: int,
    recent_nodes: tuple[int, ...] = (),
    stop_nodes: frozenset[int] = frozenset(),
    candidate_indices: np.ndarray | None = None,
) -> tuple[str, int]:
    if len(vocab) <= 1:
        return vocab.nearest(F_voiced, candidate_indices=candidate_indices)

    recent = set(recent_nodes)
    stop = set(stop_nodes)
    fallback_orders = (
        recent | stop,
        stop,
        recent,
        set(),
    )
    for extra in fallback_orders:
        try:
            return _nearest_with_optional_candidates(
                vocab,
                F_voiced,
                current_node,
                extra,
                candidate_indices,
            )
        except ValueError:
            continue
    return _nearest_with_optional_candidates(
        vocab,
        F_voiced,
        -1,
        set(),
        candidate_indices,
    )


def _nearest_with_optional_candidates(
    vocab,
    F_voiced,
    current_node: int,
    exclude_indices: set[int],
    candidate_indices: np.ndarray | None,
) -> tuple[str, int]:
    try:
        return vocab.nearest(
            F_voiced,
            exclude_idx=current_node,
            exclude_indices=exclude_indices,
            candidate_indices=candidate_indices,
        )
    except TypeError:
        if candidate_indices is not None:
            raise
        return vocab.nearest(
            F_voiced,
            exclude_idx=current_node,
            exclude_indices=exclude_indices,
        )


def _voiced_state(state: FieldState, persona) -> FieldState:
    return FieldState(
        F=persona.apply(state.F),
        node=state.node,
        step=state.step,
        holonomy=state.holonomy,
        energy=state.energy,
        valence=state.valence,
    )


def _close_final_state(state: FieldState) -> FieldState:
    return FieldState(
        F=unitize_versor(state.F),
        node=state.node,
        step=state.step,
        holonomy=state.holonomy,
        energy=state.energy,
        valence=state.valence,
    )


def _softmax(scores: list[float]) -> list[float]:
    """Numerically stable softmax over a list of floats."""
    if not scores:
        return []
    arr = np.asarray(scores, dtype=np.float64)
    arr -= arr.max()
    exp = np.exp(arr)
    total = float(exp.sum())
    if total < 1e-12:
        return [1.0 / len(scores)] * len(scores)
    return (exp / total).tolist()


def _recall_state(state: FieldState, vault, top_k: int) -> tuple[FieldState, int]:
    if vault is None or top_k <= 0:
        return state, 0

    # INV-24 recall role: EVIDENCE_TELEMETRY.  Hits become rotor transitions
    # on the generation walk, but the walk feeds `walk_surface` (telemetry-
    # only per docs/runtime_contracts.md) — not the user-facing surface.
    # User-facing surface comes from realize(proposition, vocab), which is
    # pack-grounded.  SPECULATIVE walk influence remains visible in trace
    # evidence and is bounded by the recall score floor; no min_status
    # filter is applied here.  If a future change routes walk output into
    # the user-facing surface, this site must be re-categorized to
    # EVIDENCE_USER_FACING and pass min_status=COHERENT.
    hits = vault.recall(state.F, top_k=top_k)
    if not hits:
        return state, 0

    # Drift fix 2: score-weighted vault recall transitions.
    #
    # Previously every recalled versor was applied as a full rotor transition
    # regardless of its recall score, giving a stale turn-3 hit the same
    # influence as a high-confidence recent hit.
    #
    # Now each rotor is scaled by its softmax-normalised score weight, so the
    # field moves proportionally to how strongly each hit was recalled.
    # Hits with infinite score (exact self-matches) receive full weight 1.0
    # and short-circuit the softmax path.
    finite_hits = [h for h in hits if h["score"] != float("inf")]
    exact_hits = [h for h in hits if h["score"] == float("inf")]

    current = state
    hits_applied = 0

    # Exact self-matches are applied at full weight first.
    for hit in exact_hits:
        recalled_F = np.asarray(hit["versor"], dtype=np.float64)
        try:
            V = word_transition_rotor(current.F, recalled_F)
        except ValueError:
            continue
        current = propagate_step(current, V)
        current = FieldState(
            F=current.F,
            node=state.node,
            step=current.step,
            holonomy=state.holonomy,
            energy=state.energy,
            valence=state.valence,
        )
        hits_applied += 1

    if finite_hits:
        raw_scores = [h["score"] for h in finite_hits]
        weights = _softmax(raw_scores)
        for hit, weight in zip(finite_hits, weights):
            recalled_F = np.asarray(hit["versor"], dtype=np.float64)
            try:
                V = word_transition_rotor(current.F, recalled_F)
            except ValueError:
                continue
            # Scale the rotor toward identity by raising it to the (weight)
            # power on the rotor manifold. ``rotor_power`` stays on the manifold
            # by construction (versor_condition stays < 1e-6), unlike a linear
            # blend ``weight·V + (1-weight)·identity`` which violates closure.
            V_scaled = rotor_power(V, float(weight))
            current = propagate_step(current, V_scaled)
            current = FieldState(
                F=current.F,
                node=state.node,
                step=current.step,
                holonomy=state.holonomy,
                energy=state.energy,
                valence=state.valence,
            )
            hits_applied += 1

    return current, hits_applied


def _candidate_indices_for_language(vocab, output_lang: str | None) -> np.ndarray | None:
    if output_lang is None:
        return None
    indices_for_language = getattr(vocab, "indices_for_language", None)
    if indices_for_language is None:
        return None
    indices = indices_for_language(output_lang)
    if len(indices) == 0:
        raise ValueError(f"No generation candidates for output language {output_lang!r}.")
    return indices


def _intersect_candidates(a: np.ndarray | None, b: np.ndarray | None) -> np.ndarray | None:
    if a is None:
        return b
    if b is None:
        return a
    if len(a) == 0 or len(b) == 0:
        return np.asarray([], dtype=np.int64)
    b_set = {int(idx) for idx in b}
    return np.asarray([int(idx) for idx in a if int(idx) in b_set], dtype=np.int64)


def _attention_candidates(
    state: FieldState,
    vocab,
    use_salience: bool,
    salience_top_k: int,
    inhibition_threshold: float,
) -> tuple[np.ndarray | None, int | None, int | None]:
    if not use_salience:
        return None, None, None
    salience = SalienceOperator().compute(state, vocab, top_k=salience_top_k)
    attention = AttentionOperator(inhibition_threshold).plan(salience, vocab)
    return attention.allowed_indices, salience.budget, len(attention.allowed_indices)


def generate(
    state: FieldState,
    vocab,
    persona,
    max_tokens: int = 128,
    record_trajectory: bool = False,
    vault=None,
    recall_top_k: int = 3,
    output_lang: str | None = None,
    allow_cross_language_generation: bool = True,
    use_salience: bool = False,
    salience_top_k: int = 16,
    inhibition_threshold: float = 0.3,
    region: AdmissibilityRegion | None = None,
    inner_loop_admissibility: bool = False,
    admissibility_threshold: float = 0.0,
    inner_loop_force_admit: bool = False,
    admissibility_mode: str = "threshold",
    admissibility_margin: float = 0.4,
    stop_tokens: frozenset[str] | None = None,
) -> GenerationResult:
    """Generate a token sequence.

    ``region`` is the ADR-0022 admissibility region.  Default
    ``None`` preserves existing behavior during the transition
    window (§TBD-3).  When supplied, its allowed-index set is
    intersected with language/salience candidates before each step;
    an empty intersection raises ``ValueError`` so the caller can
    route through the unknown-domain surface (§2 honest refusal).

    ``inner_loop_admissibility`` (ADR-0024) — when ``True`` and a
    real region is supplied, each per-step selection is re-evaluated
    against ``check_transition`` with ``admissibility_threshold``.
    Rejected candidates are excluded and the walk re-selects; if every
    candidate in the admissible set is rejected, the walk raises
    ``ValueError`` (honest refusal).  Default ``False`` preserves
    ADR-0023 boundary-only behavior so existing trace hashes remain
    byte-identical.  The rotor ``V`` is only constructed for the
    admitted candidate, so the ``versor_condition < 1e-6`` invariant
    is unaffected.

    ``inner_loop_force_admit`` (Phase 2 null control) — only meaningful
    when ``inner_loop_admissibility=True``.  Exercises the inner-loop
    code path (same attempt-loop scaffolding, same telemetry side
    effects) but force-breaks on the first candidate regardless of
    verdict.  This isolates rejection as the causal factor: any
    delta between boundary-only and inner-loop-on runs that vanishes
    under the null control is attributable to code-path differences,
    not to rejection.  Not exposed to RuntimeConfig — eval-only.
    """
    tokens = []
    trajectory = [] if record_trajectory else None
    vault_hits = 0
    current = state
    recent_nodes = deque([state.node], maxlen=_RECENT_WINDOW)
    language_candidates = None if allow_cross_language_generation else _candidate_indices_for_language(vocab, output_lang)
    salience_candidates, salience_budget, candidates_used = _attention_candidates(
        state,
        vocab,
        use_salience=use_salience,
        salience_top_k=salience_top_k,
        inhibition_threshold=inhibition_threshold,
    )
    candidate_indices = _intersect_candidates(language_candidates, salience_candidates)
    if candidate_indices is not None and len(candidate_indices) == 0:
        candidate_indices = salience_candidates if salience_candidates is not None else language_candidates
        candidates_used = None if candidate_indices is None else len(candidate_indices)

    region_was_unconstrained = region is None or region.is_unconstrained()
    effective_region_label = (
        region.label if region is not None else "unconstrained"
    )
    effective_region_source = (
        region.source.value if region is not None else "intent"
    )
    candidates_before_region = candidate_indices
    if region is not None and not region.is_unconstrained():
        candidate_indices = filter_candidates(region, candidate_indices)
        if candidate_indices is not None and len(candidate_indices) == 0:
            # ADR-0024 Phase 2 — pre-walk exhaustion site.  The region's
            # allowed-index intersection with the candidate set is empty
            # before any step ran.  ``step_index = -1`` and
            # ``rejected_attempts = ()`` distinguish this site from the
            # in-walk exhaustion site below; no inner-loop rejections were
            # issued because the region was already empty.  Subclasses
            # ValueError so existing handlers continue to catch it.
            raise InnerLoopExhaustion(
                reason=RefusalReason.INNER_LOOP_EXHAUSTION,
                region_label=region.label,
                step_index=-1,
                rejected_attempts=(),
            )
        candidates_used = None if candidate_indices is None else len(candidate_indices)
    admissibility_trace: list[AdmissibilityTraceStep] = []
    pre_tuple: tuple[int, ...] = (
        tuple(int(i) for i in candidates_before_region)
        if candidates_before_region is not None
        else ()
    )
    post_tuple: tuple[int, ...] = (
        tuple(int(i) for i in candidate_indices)
        if candidate_indices is not None
        else ()
    )

    # Finding 6 (audit 2026-05-20) — stop tokens are now caller-overridable.
    # ``None`` preserves the historical default (``_STOP_TOKENS``); explicit
    # overrides can free pack-specific content words like λόγος or "to" that
    # would otherwise be permanently inhibited regardless of pack semantics.
    effective_stop_tokens: frozenset[str] = (
        stop_tokens if stop_tokens is not None else _STOP_TOKENS
    )
    stop_nodes = frozenset(
        idx for token in effective_stop_tokens
        if (idx := _try_index(vocab, token)) is not None
    )

    token_budget = min(max_tokens, int(candidates_used)) if candidates_used is not None else max_tokens
    region_active = region is not None and not region.is_unconstrained()
    active_region: AdmissibilityRegion | None = region if region_active else None
    inner_loop_active = inner_loop_admissibility and region_active
    # ADR-0026 / Phase 3 — margin mode is opt-in.  When active it
    # replaces the per-candidate threshold check with a ranked
    # admissibility test on the candidate set, admitting the top
    # blade-ranked candidate iff its margin over the second-ranked
    # is at least ``admissibility_margin``.  Falls back to threshold
    # mode (ADR-0024) on any unrecognised value so a config typo
    # cannot silently disable admissibility.
    margin_mode_active = (
        inner_loop_active
        and admissibility_mode == "margin"
        and active_region is not None
    )
    for step_index in range(token_budget):
        current, hits_applied = _recall_state(_voiced_state(current, persona), vault, recall_top_k)
        vault_hits += hits_applied

        rejected_attempts: list[tuple[int, str, float]] = []
        # Per-step exclude set seeded with stop/recent via _nearest_next;
        # inner-loop rejections accumulate into a step-local exclude that
        # we union with stop_nodes for the retry call.
        step_exclude: set[int] = set()
        word: str
        word_idx: int
        verdict: AdmissibilityVerdict

        if margin_mode_active:
            # ADR-0026 / Phase 3 — rank the admissible candidate set by
            # blade-score and admit the top iff margin >= delta.  The
            # rotor V is only constructed for the admitted candidate
            # below, preserving the versor_condition invariant.
            assert active_region is not None  # margin_mode_active gates this
            ranked = rank_candidates_by_blade(
                active_region,
                candidate_indices=candidate_indices,
                versor_lookup=vocab.get_versor_at,
                word_lookup=vocab.get_word_at,
            )
            margin_verdict = check_margin(
                active_region, ranked, delta=admissibility_margin
            )
            # rejected_attempts carries the full ranked list as evidence
            # — index, word, score — so refusal traces show the entire
            # blade-ordering at the failed step, not just one rejection.
            rejected_attempts = [
                (r.index, r.word, r.score) for r in margin_verdict.ranked
            ]
            if not margin_verdict.admitted:
                raise InnerLoopExhaustion(
                    reason=RefusalReason.INNER_LOOP_EXHAUSTION,
                    region_label=effective_region_label,
                    step_index=step_index,
                    rejected_attempts=tuple(rejected_attempts),
                )
            assert margin_verdict.top is not None  # admitted => non-None
            word_idx = int(margin_verdict.top.index)
            word = str(margin_verdict.top.word)
            # Phase 4 / ADR-0025 — rotor admissibility on the top-
            # ranked candidate.  If the rotor would push the field
            # outside the frame's admissible cone, refuse with a
            # distinct ROTOR_REJECTION reason so the trace shows
            # *which* axis ran out (destination-blade vs rotor-frame).
            # The ranked list is preserved as evidence, with the
            # rotor score appended as the failed candidate's score.
            if active_region is not None and active_region.frame_versor is not None:
                A_now = vocab.get_versor_at(current.node)
                B_cand = vocab.get_versor_at(word_idx)
                V_hyp = word_transition_rotor(A_now, B_cand)
                rv = check_rotor_admissibility(
                    active_region,
                    field_current=current.F,
                    rotor=V_hyp,
                )
                if not rv.admitted:
                    rotor_attempt = (
                        int(word_idx),
                        str(word),
                        float(rv.score),
                    )
                    raise InnerLoopExhaustion(
                        reason=RefusalReason.ROTOR_REJECTION,
                        region_label=effective_region_label,
                        step_index=step_index,
                        rejected_attempts=tuple(rejected_attempts) + (rotor_attempt,),
                    )
            # Build a legacy AdmissibilityVerdict for trace storage so
            # the AdmissibilityTraceStep shape is unchanged.  Margin
            # info is encoded into ``reason`` for human inspection;
            # the structured ranking lives in ``rejected_attempts``.
            verdict = AdmissibilityVerdict(
                admitted=True,
                score=float(margin_verdict.top.score),
                region_label=margin_verdict.region_label,
                reason=(
                    f"margin {margin_verdict.margin:.6f} >= "
                    f"delta {margin_verdict.delta:.6f}"
                ),
            )
        else:
            max_attempts = (
                len(candidate_indices) if (inner_loop_active and candidate_indices is not None)
                else 1
            )
            # Phase 4 — track whether any rotor rejection occurred this
            # step so the exhaustion exception can carry the right
            # ``RefusalReason`` (rotor-side vs destination-side).
            step_had_rotor_rejection = False
            for _attempt in range(max(max_attempts, 1)):
                word, word_idx = _nearest_next(
                    vocab,
                    current.F,
                    current.node,
                    recent_nodes=tuple(recent_nodes),
                    stop_nodes=stop_nodes | frozenset(step_exclude),
                    candidate_indices=candidate_indices,
                )
                if active_region is not None:
                    verdict = check_transition(
                        active_region,
                        candidate_index=int(word_idx),
                        candidate_versor=vocab.get_versor_at(word_idx),
                        threshold=admissibility_threshold,
                    )
                else:
                    verdict = AdmissibilityVerdict(
                        admitted=True,
                        score=0.0,
                        region_label=effective_region_label,
                        reason="unconstrained",
                    )
                # Phase 4 / ADR-0025 — if the destination admits and the
                # region carries a frame versor, also check rotor-side
                # admissibility: would the rotor applied to current.F
                # land in the frame's admissible cone?  On reject, treat
                # as a per-candidate rejection like the destination side
                # — log the rotor score and retry the next candidate.
                rotor_admitted = True
                rotor_score_for_log: float | None = None
                if (
                    active_region is not None
                    and verdict.admitted
                    and inner_loop_active
                    and active_region.frame_versor is not None
                ):
                    A_now = vocab.get_versor_at(current.node)
                    B_cand = vocab.get_versor_at(word_idx)
                    V_hyp = word_transition_rotor(A_now, B_cand)
                    rv = check_rotor_admissibility(
                        active_region,
                        field_current=current.F,
                        rotor=V_hyp,
                    )
                    rotor_admitted = rv.admitted
                    if not rv.admitted:
                        rotor_score_for_log = float(rv.score)
                if not inner_loop_active or (
                    verdict.admitted and rotor_admitted
                ) or inner_loop_force_admit:
                    # `inner_loop_force_admit` is the Phase 2 null control:
                    # exercises the inner-loop code path (same attempt loop,
                    # same telemetry side effects) but force-breaks on the
                    # first candidate so any pass-rate delta vs the true
                    # inner-loop run is causally attributable to rejection,
                    # not to incidental code-path differences.
                    break
                # Inner loop is on and either destination or rotor
                # rejected this candidate.  Log the rejection with the
                # score that produced it.
                if rotor_score_for_log is not None:
                    step_had_rotor_rejection = True
                    rejected_attempts.append(
                        (int(word_idx), str(word), rotor_score_for_log)
                    )
                else:
                    rejected_attempts.append(
                        (int(word_idx), str(word), float(verdict.score))
                    )
                if int(word_idx) in step_exclude:
                    # Selector returned the same exhausted candidate — no
                    # further admissible destinations.  Honest refusal.
                    # ADR-0024 Phase 2 — in-walk exhaustion site; carries the
                    # ordered ``rejected_attempts`` accumulated this step so
                    # downstream layers can read refusal evidence without
                    # re-parsing the exception message.  Phase 4 / ADR-0025
                    # — if any rotor rejection occurred this step, the
                    # exhaustion is reported under ROTOR_REJECTION so the
                    # trace names the load-bearing axis.
                    raise InnerLoopExhaustion(
                        reason=(
                            RefusalReason.ROTOR_REJECTION
                            if step_had_rotor_rejection
                            else RefusalReason.INNER_LOOP_EXHAUSTION
                        ),
                        region_label=effective_region_label,
                        step_index=step_index,
                        rejected_attempts=tuple(rejected_attempts),
                    )
                step_exclude.add(int(word_idx))
            else:
                # max_attempts exhausted without break — every admissible
                # candidate was rejected by the inner-loop threshold (or
                # rotor frame, Phase 4).  Same refusal shape, with the
                # reason routed to the load-bearing axis.
                raise InnerLoopExhaustion(
                    reason=(
                        RefusalReason.ROTOR_REJECTION
                        if step_had_rotor_rejection
                        else RefusalReason.INNER_LOOP_EXHAUSTION
                    ),
                    region_label=effective_region_label,
                    step_index=step_index,
                    rejected_attempts=tuple(rejected_attempts),
                )

        tokens.append(_articulate(vocab, word))
        admissibility_trace.append(
            AdmissibilityTraceStep(
                step_index=step_index,
                region_label=effective_region_label,
                region_source=effective_region_source,
                candidates_before=pre_tuple,
                candidates_after=post_tuple,
                selected_index=int(word_idx),
                selected_word=str(word),
                verdict=verdict,
                rejected_attempts=tuple(rejected_attempts),
            )
        )

        if record_trajectory:
            trajectory.append(current)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(
            F=current.F,
            node=word_idx,
            step=current.step,
            holonomy=current.holonomy,
            energy=current.energy,
            valence=current.valence,
        )
        recent_nodes.append(word_idx)

    return GenerationResult(
        tokens=tokens,
        final_state=_close_final_state(current),
        trajectory=trajectory,
        salience_top_k=salience_budget,
        candidates_used=candidates_used,
        vault_hits=vault_hits,
        admissibility_trace=tuple(admissibility_trace),
        region_was_unconstrained=region_was_unconstrained,
    )

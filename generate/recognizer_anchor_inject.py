"""ADR-0163.D.2 — per-category recognizer anchor injection.

When the candidate-graph pipeline's existing parser yields no candidates
for a statement AND the ratified recognizer registry recognizes the
statement, this module is consulted to build typed solver primitives
(``CandidateInitial`` / future ``CandidateOperation`` values) from the
recognizer's ``parsed_anchors``.  The output extends ``per_sentence_choices``
the same way the existing parser's output does, so the downstream
solver runs unchanged.

Doctrine
--------
- Pure, deterministic injectors.  Same ``(match, sentence)`` → same
  ``SentenceChoice`` tuple, byte-equal.
- Refusal-preferring: each injector returns ``()`` when it cannot build
  a primitive that passes the existing ``_initial_admissible``
  structural check (the wrong=0 safety net the candidate-graph already
  enforces).
- No LLM / embeddings / learned classifiers; the injection is rules-only
  same discipline as Phase A/C/D detection.
- Per-category boundary: v1 implements only ``discrete_count_statement``.
  Every other category routes to the empty-tuple fallback (skip-only,
  identical to the round-2 Phase D wiring) and lands in follow-up
  D.2.x PRs after the framework's empirical lift is operator-reviewed.

Five-layer wrong=0 safety net (the Phase D.2 brief's load-bearing
section) is preserved across this module:

  1. Matcher narrowness — ``recognizer_match._try_extract_discrete_count_anchor``
     refuses on any ambiguity.
  2. Extraction correctness — anchor fields ground in the literal
     statement surface.
  3. Injection correctness — the per-category injector returns a
     ``CandidateInitial`` that passes ``_initial_admissible``; failure
     to ground yields ``()``.
  4. Replay gate — propose-time ``run_admissibility_replay_gate``
     auto-rejects any extraction change that lifts the GSM8K wrong
     count.
  5. Multi-branch decision rule — when an injected candidate disagrees
     with another branch's answer, the candidate-graph refuses.
"""

from __future__ import annotations

from typing import Mapping, Union

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_parser import CandidateInitial, CandidateOperation
from generate.math_problem_graph import (
    InitialPossession,
    MathGraphError,
    Operation,
    Quantity,
)
from generate.recognizer_match import RecognizerMatch

# ADR-0170 — the widened injector emission type. Per-category injectors
# may emit a tuple of ``CandidateInitial`` (existing) or
# ``CandidateOperation`` (new, ADR-0170). The downstream
# ``per_sentence_choices`` aggregator dispatches admissibility on the
# concrete type (``_initial_admissible`` vs ``roundtrip_admissible``).
# No new admission paths are introduced by the widening itself; new
# emission shapes ship in subsequent per-injector PRs (ADR-0170 §"impl
# outline" W2/W3/W4/W5).
InjectorEmission = Union[CandidateInitial, CandidateOperation]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def inject_from_match(
    match: RecognizerMatch,
    sentence: str,
    *,
    sealed: bool = False,
) -> tuple[InjectorEmission, ...]:
    """Dispatch a recognizer match to its per-category injector.

    Returns an empty tuple when the category has no v1 injector or when
    the v1 injector refused. Per ADR-0170, the return type is now
    ``tuple[InjectorEmission, ...]`` (``CandidateInitial | CandidateOperation``)
    so per-category injectors can emit operations as well as initials.
    The v1 ``discrete_count_statement`` injector continues to emit only
    ``CandidateInitial`` — the widening is type-level only in this PR.

    ADR-0186 — the **sealed injector lane**. When ``sealed=True`` the
    dispatch first consults :data:`_SEALED_INJECTORS` (the in-development
    W2-W5 injectors); a sealed injector that emits short-circuits and
    returns its emission. When ``sealed=False`` (the default, and the
    value the frozen serving path / ``train_sample`` runner always pass)
    ``_SEALED_INJECTORS`` is **not** consulted at all, so the frozen
    ``3/47/0`` metric is byte-identical until a reviewed Phase-5 promotion
    moves an entry into :data:`_INJECTORS`. The seal is injector
    *eligibility*, not a forked reader: every emission still passes the
    unchanged admissibility gate downstream.

    CW-2 (ADR-0169 consumption) — when the per-category injector
    returns empty AND the matcher published a ``composition_shape`` key
    in ``parsed_anchors``, the composition registry is consulted: an
    ``affirms`` entry under :data:`SAFE_COMPOSITION_CATEGORIES` admits
    the composition; a ``falsifies`` entry continues to refuse;
    absence continues to refuse. The composition path is read-only
    over the reviewed math pack — it cannot weaken any existing
    admission gate. See :mod:`generate.comprehension.composition_registry`.
    """
    if sealed:
        sealed_injector = _SEALED_INJECTORS.get(match.category)
        if sealed_injector is not None:
            emitted = sealed_injector(match, sentence)
            if emitted:
                return emitted
    injector = _INJECTORS.get(match.category)
    if injector is not None:
        emitted = injector(match, sentence)
        if emitted:
            return emitted
    return _consult_composition_registry(match, sentence)


# ---------------------------------------------------------------------------
# CW-2 — composition registry consultation (ADR-0169 consumption)
# ---------------------------------------------------------------------------


def _consult_composition_registry(
    match: RecognizerMatch,
    sentence: str,
) -> tuple[InjectorEmission, ...]:
    """Composition-registry consultation fallback for ``inject_from_match``.

    Contract (the contract a matcher extension must honor to enable
    composition admission via this path):

    - ``match.parsed_anchors`` carries at least one anchor mapping with a
      key ``"composition_shape"`` whose value is the surface pattern
      string used by ratified composition registry entries (e.g.
      ``"bound(count) × bound(unit_cost)"``).
    - The same anchor carries a pre-composed payload the registry only
      gates: either ``"composed_initial"`` (a fully-constructed
      :class:`CandidateInitial`) or ``"composed_operation"`` (a
      :class:`CandidateOperation`). This module does NOT perform
      arithmetic — the matcher / matcher-extension owns the math; the
      registry owns the admissibility decision.

    Semantics:

    - registry empty OR no entry for shape → return ``()`` (refusal-preferring)
    - entry exists, polarity ``"affirms"`` → admit the pre-composed payload
    - entry exists, polarity ``"falsifies"`` → return ``()`` (suppressed)

    This is a registry-driven *gate*, not a registry-driven arithmetic
    primitive. Per ADR-0169 §"Mutation boundary" the registry never
    rewrites solver / arithmetic semantics; it ratifies whether a
    given structural shape may admit.

    No matcher currently publishes ``composition_shape`` — at land time
    this path is dormant infrastructure. The case-0019 truth-test will
    fire only after a matcher extension binds quantity-shape composition
    anchors (out of scope for this PR; see follow-up brief).
    """
    if not match.parsed_anchors:
        return ()

    # Lazy import — composition_registry import chain pulls
    # SAFE_COMPOSITION_CATEGORIES from teaching/, and the load path may
    # not be needed on every recognizer call. Module-level loader cache
    # keeps the repeat-call cost at one dict hit after the first load.
    from generate.comprehension.composition_registry import (
        is_affirmed,
        is_falsified,
        load_composition_registry,
    )

    registry = load_composition_registry()
    if registry.is_empty():
        return ()

    out: list[InjectorEmission] = []
    for anchor in match.parsed_anchors:
        shape = anchor.get("composition_shape") if isinstance(anchor, Mapping) else None
        if not isinstance(shape, str):
            continue
        if is_falsified(registry, shape):
            # Falsifying entry — suppress any admission that would have
            # fired from this anchor; refusal-preferring discipline.
            return ()
        if not is_affirmed(registry, shape):
            continue
        composed_initial = anchor.get("composed_initial")
        composed_operation = anchor.get("composed_operation")
        if isinstance(composed_initial, CandidateInitial):
            out.append(composed_initial)
        elif isinstance(composed_operation, CandidateOperation):
            out.append(composed_operation)
        else:
            # The registry affirms the shape but no pre-composed payload
            # is attached — under-admit. The matcher owns producing the
            # payload; we never invent arithmetic here.
            return ()
    return tuple(out)


# ---------------------------------------------------------------------------
# Per-category injectors
# ---------------------------------------------------------------------------


def inject_discrete_count_statement(
    match: RecognizerMatch,
    sentence: str,
) -> tuple[InjectorEmission, ...]:
    """Build CandidateInitial OR CandidateOperation from ``discrete_count``
    parsed anchors, dispatched on the matcher's ``anchor_kind``.

    Per ADR-0170 W2 — the matcher records ``anchor_kind`` as either
    ``"possession"`` (verbs ``has/have/had``) or ``"acquisition"``
    (verbs in ``_ACQUISITION_VERBS``).

    - ``possession`` → ``CandidateInitial`` (existing behavior; the
      sentence asserts an initial state)
    - ``acquisition`` → ``CandidateOperation(kind='add')`` (new in W2;
      the sentence asserts an add-operation, preserving
      ADR-0131.G.1's branch-disagreement discipline — the regex
      parser's ADD_VERBS path emits the same kind of operation for
      single-word units, so the injector path complements it on
      multi-word units without conflicting)

    v1 narrowness: at most one anchor per match; absent or
    unconstructable anchors return ``()``.
    """
    if not match.parsed_anchors:
        return ()

    out: list[InjectorEmission] = []
    for anchor in match.parsed_anchors:
        anchor_kind = anchor.get("anchor_kind", "possession")
        if anchor_kind == "possession":
            cand: InjectorEmission | None = _build_initial_from_discrete_count(
                anchor, sentence
            )
        elif anchor_kind == "acquisition":
            cand = _build_operation_from_discrete_count_acquisition(
                anchor, sentence
            )
        else:
            # Unknown anchor_kind — under-admit. Future widenings (e.g.
            # "depletion" verbs as CandidateOperation(subtract)) extend
            # this branch.
            return ()
        if cand is None:
            # Under-admit on any failure to construct.  Partial
            # admission would mean the downstream Cartesian product
            # enumerates a graph missing state.
            return ()
        out.append(cand)
    return tuple(out)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_initial_from_discrete_count(
    anchor: Mapping[str, object],
    sentence: str,
) -> CandidateInitial | None:
    """Construct one CandidateInitial from a discrete_count anchor.

    Refuses (returns ``None``) when any field cannot be coerced or when
    the constructed value would violate ``CandidateInitial`` /
    ``InitialPossession`` invariants.  The resulting CandidateInitial is
    structurally verified upstream by ``_initial_admissible``.

    Anchor schema:
        {
          "kind": "discrete_count",
          "subject_role": <str>,
          "count_token": <str>,         # '20' or 'two'
          "count_kind": <"integer"|"word">,
          "counted_noun": <str>,        # 'paperclips' / 'Pokemon cards'
        }
    """
    subject_role = anchor.get("subject_role")
    count_token = anchor.get("count_token")
    count_kind = anchor.get("count_kind")
    counted_noun = anchor.get("counted_noun")

    if (
        not isinstance(subject_role, str) or not subject_role
        or not isinstance(count_token, str) or not count_token
        or not isinstance(count_kind, str)
        or not isinstance(counted_noun, str) or not counted_noun
    ):
        return None

    # Resolve the count token to a numeric value.  v1 supports integer
    # and single-word cardinals; hyphenated compounds defer to a follow-up
    # PR because their resolution requires the language pack's
    # parse_compound_cardinal helper which is not on this hot path.
    value = _resolve_count_value(count_token, count_kind)
    if value is None:
        return None

    # CandidateInitial requires an anchor verb token recognized in its
    # post-init whitelist (has/have/had/owns/owned/holds/held/contains/
    # contained — matched by the recognizer's narrowness rule).  We pick
    # the literal verb token from the sentence so the round-trip ground
    # check inside _initial_admissible succeeds.  Falls back to 'has' when
    # the verb cannot be located in the surface; that fallback only fires
    # when the recognizer's match diverges from the sentence and is the
    # under-admit path.
    verb_in_sentence = _locate_possession_verb(sentence)
    if verb_in_sentence is None:
        return None

    try:
        quantity = Quantity(value=value, unit=counted_noun)
        initial = InitialPossession(entity=subject_role, quantity=quantity)
    except MathGraphError:
        return None

    try:
        return CandidateInitial(
            initial=initial,
            source_span=sentence,
            matched_anchor=verb_in_sentence,
            matched_value_token=count_token,
            matched_unit_token=counted_noun,
            matched_entity_token=subject_role,
        )
    except ValueError:
        return None


def _build_operation_from_discrete_count_acquisition(
    anchor: Mapping[str, object],
    sentence: str,
) -> CandidateOperation | None:
    """Construct one CandidateOperation(kind='add') from a discrete_count
    anchor whose ``anchor_kind == "acquisition"``.

    Per ADR-0170 W2 — acquisition verbs (``collected``, ``received``,
    ``bought``, ``got``) are routed to operations, not initials, in
    accordance with ADR-0131.G.1's branch-disagreement discipline. The
    solver's defaults-from-zero rule resolves single-statement
    acquisitions correctly (``0 + N = N``).

    Refuses (returns ``None``) when any field cannot be coerced, when
    the literal verb token cannot be located in the surface, or when
    the constructed ``CandidateOperation`` would violate its post-init
    invariants. The result is admissibility-checked upstream by
    ``roundtrip_admissible``.

    Anchor schema (same as possession, with ``anchor_kind`` discriminator):
        {
          "kind": "discrete_count",
          "anchor_kind": "acquisition",
          "subject_role": <str>,
          "count_token": <str>,
          "count_kind": <"integer"|"word">,
          "counted_noun": <str>,
          "verb_token": <str>,  # e.g. "collected"
        }
    """
    subject_role = anchor.get("subject_role")
    count_token = anchor.get("count_token")
    count_kind = anchor.get("count_kind")
    counted_noun = anchor.get("counted_noun")
    verb_token = anchor.get("verb_token")

    if (
        not isinstance(subject_role, str) or not subject_role
        or not isinstance(count_token, str) or not count_token
        or not isinstance(count_kind, str)
        or not isinstance(counted_noun, str) or not counted_noun
        or not isinstance(verb_token, str) or not verb_token
    ):
        return None

    value = _resolve_count_value(count_token, count_kind)
    if value is None:
        return None

    # Locate the literal verb surface in the sentence so the
    # round-trip ground check in ``roundtrip_admissible`` succeeds.
    # The matcher already confirmed ``verb_token`` is in
    # ``_ACQUISITION_VERBS`` (which is itself a subset of
    # ``ADD_VERBS``), so the downstream CandidateOperation post-init
    # whitelist accepts the matched_verb token.
    located_verb = _locate_token(sentence, verb_token)
    if located_verb is None:
        return None

    try:
        operand = Quantity(value=value, unit=counted_noun)
        op = Operation(
            actor=subject_role,
            kind="add",
            operand=operand,
        )
    except MathGraphError:
        return None

    try:
        return CandidateOperation(
            op=op,
            source_span=sentence,
            matched_verb=located_verb,
            matched_value_token=count_token,
            matched_unit_token=counted_noun,
            matched_actor_token=subject_role,
        )
    except ValueError:
        return None


def _locate_token(sentence: str, target_lc: str) -> str | None:
    """Return the literal-surface form of ``target_lc`` (lowercased) in
    ``sentence`` whitespace-tokenized, or ``None`` if absent.

    Used by the acquisition-verb path to extract the matched verb
    surface for ``CandidateOperation.matched_verb``. Falls back to
    ``None`` only when the matcher's recorded ``verb_token`` somehow
    diverges from the sentence surface — the under-admit path.
    """
    for raw in sentence.split():
        tok = raw.strip(".,;:!?\"'()[]{}").lower()
        if tok == target_lc:
            return tok
    return None


def _resolve_count_value(count_token: str, count_kind: str) -> int | None:
    """Map ``count_token`` to a numeric value.

    Integer tokens parse with ``int``.  Word-form tokens look up
    ``WORD_NUMBERS`` from the language pack; unknown words refuse.
    Hyphenated compounds (``twenty-five``) defer to D.2.x — v1 returns
    ``None`` for them.
    """
    if count_kind == "integer":
        try:
            return int(count_token)
        except ValueError:
            return None
    if count_kind == "word":
        # Local import to keep module import-time cheap and to avoid a
        # circular import via the math_candidate_parser surface.
        from generate.math_roundtrip import WORD_NUMBERS

        token_lc = count_token.lower()
        if token_lc in WORD_NUMBERS:
            return int(WORD_NUMBERS[token_lc])
        # Hyphenated compound: defer to D.2.x.
        return None
    return None


def _locate_possession_verb(sentence: str) -> str | None:
    """Return the first possession-anchor verb (lowercased) found in
    ``sentence`` whitespace-tokenized, or ``None`` when absent.

    The verb is the surface token that ``CandidateInitial.__post_init__``
    validates against its registered anchor whitelist.  Returning the
    LITERAL surface keeps the round-trip ground check in
    ``_initial_admissible`` honest.
    """
    possession_verbs = ("has", "have", "had")
    for raw in sentence.split():
        tok = raw.strip(".,;:!?\"'()[]{}").lower()
        if tok in possession_verbs:
            return tok
    return None


# ---------------------------------------------------------------------------
# Dispatch table — keep deterministic and explicit.
# Adding a category here is the SINGLE place a new D.2.x category
# registers its injector.  No global state, no side effects.
# ---------------------------------------------------------------------------

_WAVE_A_INJECTABLE_ANCHOR_KINDS: frozenset[str] = frozenset({
    "multiplicative_aggregate_each_weighing",
})


def inject_multiplicative_aggregation(
    match: RecognizerMatch,
    sentence: str,
) -> tuple[InjectorEmission, ...]:
    """WAVE-A — inject the pre-composed CandidateInitial for the
    specific value-extracted multiplicative_aggregate shapes.

    Narrow by anchor ``kind`` to avoid intercepting ME-3 / ME-4
    additive/subtractive anchors that share the same matcher entry
    point but require the composition_registry consult path. Only
    anchors whose ``kind`` is in
    :data:`_WAVE_A_INJECTABLE_ANCHOR_KINDS` emit here; everything else
    returns () and falls through to ``_consult_composition_registry``.
    """
    if not match.parsed_anchors:
        return ()
    out: list[InjectorEmission] = []
    for anchor in match.parsed_anchors:
        if not isinstance(anchor, Mapping):
            continue
        kind = anchor.get("kind")
        if kind not in _WAVE_A_INJECTABLE_ANCHOR_KINDS:
            continue
        composed = anchor.get("composed_initial")
        if isinstance(composed, CandidateInitial):
            out.append(composed)
    return tuple(out)


_INJECTORS: Mapping[ShapeCategory, "type"] = {
    ShapeCategory.DISCRETE_COUNT_STATEMENT: inject_discrete_count_statement,  # type: ignore[dict-item]
    # WAVE-A — multiplicative_aggregation now has a per-category
    # injector that consumes value-extracted anchors. Specs without
    # ``extract_values=True`` continue to return empty parsed_anchors
    # (detection-only) so the existing wrong=0 path is byte-identical.
    ShapeCategory.MULTIPLICATIVE_AGGREGATION: inject_multiplicative_aggregation,  # type: ignore[dict-item]
    # All other recognizer categories route to the empty-tuple fallback
    # in ``inject_from_match`` — `_INJECTORS.get(category)` returns
    # ``None`` and the dispatcher returns ``()``, which the
    # candidate-graph then treats as "recognizer matched but produced
    # no injection" → explicit refusal (the wrong=0 fix from #359).
    #
    # Categories deferred to follow-up PRs:
    #
    # ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY — by design (no quantity)
    # ShapeCategory.RATE_WITH_CURRENCY           — needs CandidateRate
    #                                              (SentenceChoice union
    #                                              extension; ADR-0171)
    # ShapeCategory.TEMPORAL_AGGREGATION         — needs apply_rate primitive
    #                                              in the algebra
    # ShapeCategory.MULTIPLICATIVE_AGGREGATION   — emits
    #                                              CandidateInitial(product)
    #                                              after ADR-0170 widens
    #                                              return type
    # ShapeCategory.CURRENCY_AMOUNT              — A1 currency_amount;
    #                                              CandidateInitial-shaped,
    #                                              ships after ADR-0170
    #
    # See docs/decisions/ADR-0170-injector-contract-widening.md for the
    # contract widening that unblocks DCS-S1 / A1 / A3.
}


# ADR-0186 — the sealed injector lane (resume ADR-0170 W2-W5 under the
# ADR-0175 serving seal). Entries here are consulted **only** when
# ``inject_from_match(..., sealed=True)`` — i.e. by the sealed eval runner,
# never by the frozen serving path or the ``train_sample`` runner (both pass
# ``sealed=False``). This keeps the frozen ``3/47/0`` metric byte-identical
# until a reviewed Phase-5 promotion moves an entry into ``_INJECTORS``.
#
# It is intentionally empty at land time: this PR ships the seal *mechanism*
# (the dispatch + the byte-identical guarantee), validated by
# tests/test_adr_0186_sealed_injector_lane.py. The first sealed *capability*
# (per ADR-0186 §5.3, the CandidateRate schema unblocking the matcher-complete
# rate_with_currency / temporal_aggregation categories) is its own follow-up.
_SEALED_INJECTORS: Mapping[ShapeCategory, "type"] = {}


__all__ = [
    "InjectorEmission",
    "inject_from_match",
    "inject_discrete_count_statement",
]

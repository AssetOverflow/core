from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    # ADR-0063 — ``en_core_relations_v1`` (kinship starter pack) joins the
    # default mount once the cross-pack surface resolver lands.  Pack
    # composers in :mod:`chat.pack_grounding` now consult
    # :mod:`chat.pack_resolver`, so kinship lemmas ground deterministically
    # without a separate composer module.
    input_packs: tuple[str, ...] = (
        "en_minimal_v1",
        "en_core_cognition_v1",
        "en_core_meta_v1",
        "en_core_attitude_v1",
        "en_core_temporal_v1",
        "en_core_action_v1",
        "en_core_quantitative_v1",
        "en_core_spatial_v1",
        "en_core_causation_v1",
        "en_core_polarity_v1",
        "en_core_relations_v1",
        "en_core_relations_v2",
        "he_logos_micro_v1",
        "grc_logos_micro_v1",
    )
    output_language: str = "en"
    frame_pack: str = "en"
    max_tokens: int = 32
    allow_cross_language_recall: bool = True
    allow_cross_language_generation: bool = False
    vault_reproject_interval: int = 20
    use_salience: bool = True
    salience_top_k: int = 16
    inhibition_threshold: float = 0.3
    inner_loop_admissibility: bool = False
    admissibility_threshold: float = 0.0
    # ADR-0026 / Phase 3 — margin-based admissibility.  ``mode``
    # selects between ADR-0024's per-candidate threshold check and
    # the ranked-with-margin check.  Default "threshold" preserves
    # ADR-0024 acceptance evidence; opt-in "margin" replaces the
    # static-threshold gate with a scale-invariant margin.
    admissibility_mode: str = "threshold"
    admissibility_margin: float = 0.4
    # ADR-0027 — Identity pack id loaded at runtime startup.  Empty string
    # resolves to ``DEFAULT_IDENTITY_PACK``.  CLI override on chat:
    # ``core chat --identity <pack_id>``.  See docs/identity_packs.md.
    identity_pack: str = ""
    # ADR-0033 — Ethics pack id loaded at runtime startup.  Empty string
    # resolves to ``DEFAULT_ETHICS_PACK``.  See docs/ethics_packs.md.
    ethics_pack: str = ""
    # ADR-0046 / ADR-0047 — forward graph constraint.  When True, the
    # PropositionGraph built from the classified intent + articulation
    # plan is converted into an AdmissibilityRegion BEFORE generate()
    # runs (Pillar 1→2→3 coupling closes on the live path).  Default
    # False preserves existing behavior during the transition window —
    # ADR-0024's honest-refusal exhaustion is the correct response when
    # the constraint geometry and the walk candidate pool do not
    # intersect, but operators must opt in to observing that behavior
    # on their workloads.  Enable to live the forward constraint;
    # disable to retain the pre-ADR-0046 unconstrained walk.
    forward_graph_constraint: bool = False

    # ADR-0062 — composed teaching-grounded surface.  When enabled,
    # the teaching-grounded composer extends a single-chain surface
    # with a follow-up chain whose subject equals the initial chain's
    # object — producing surfaces like "light reveals truth, which
    # grounds knowledge" instead of just "light reveals truth".
    # Default False preserves all pre-ADR-0062 behaviour.  Cycle-safe
    # (won't follow if the next subject has been visited), bounded
    # depth (max one follow-up chain in v1).
    composed_surface: bool = False

    # ADR-0083 — transitive (multi-hop) teaching-grounded surface.
    # Strict superset of ADR-0062's depth-1 composer: iterates the
    # per-hop follow-up resolution under a visited-set guard, so the
    # surface can extend beyond a single follow-up chain.
    # ``transitive_max_depth`` is the maximum number of follow-up hops
    # to append beyond the initial chain.  At ``max_depth=0``
    # byte-identical to the single-chain surface; at ``max_depth=1``
    # byte-identical to ADR-0062's composed surface; at
    # ``max_depth=2`` byte-identical to ADR-0062 when no second hop
    # exists, strict superset when one does.  When True, this
    # supersedes ``composed_surface``.  Cycle-safe across every depth
    # (visited-set covers ADR-0062's 1-step cycle guard).  Single-
    # corpus traversal in v1; cross-corpus transitive is deferred to
    # a follow-up ADR.
    transitive_surface: bool = False
    transitive_max_depth: int = 2

    # ADR-0085 — gloss-aware CAUSE surface.  When True, IntentTag.CAUSE
    # consults the subject lemma's gloss first and emits an explanation-
    # shaped sentence drawn from the gloss text, falling through to
    # the chain-walk ``teaching_grounded_surface*`` only when no gloss
    # exists for the lemma.  Default False preserves the pre-ADR-0085
    # chain-walk surface byte-identically (null-drop invariant).
    gloss_aware_cause: bool = False

    # ADR-0087 — rhetorical-style selection axis (substrate phase).
    # ``None`` resolves to ``DEFAULT_RHETORICAL_STYLE_PACK`` per the
    # mounting discipline, which is the null-lift baseline.  No
    # composer or realizer reads this field yet — that wiring is the
    # consumer ADR's job.  The field is declared here so the runtime
    # interface is stable when the consumer lands.
    rhetorical_style_id: str | None = None

    # ADR-0066 / P3.2 — opt-in thread anaphora.  When enabled, the
    # runtime prepends a deterministic backreference to a recent
    # grounded turn when the current turn's subject lemma matches
    # one in the bounded session-thread context.  Engages only on
    # pack/teaching-tier turns (both prior and current); weaker
    # tiers do not anchor.  Default False preserves every pre-P3.2
    # surface byte-identically.
    thread_anaphora: bool = False

    # Discourse planner (step 5 of the discourse-planner sequencing).
    # When True, the runtime builds a deterministic DiscoursePlan via
    # ``generate.discourse_planner.plan_discourse`` from a
    # ``GroundingBundle`` assembled by ``generate.grounding_accessors``
    # and renders it as multi-clause output.  Mode selection comes from
    # ``generate.intent.classify_response_mode``; BRIEF mode is
    # byte-identical to today's single-sentence pack-grounded surface
    # because the runtime hook (``_maybe_apply_discourse_planner``)
    # returns ``None`` when the rendered plan has <= 1 move — single-
    # fact prompts get exactly the same surface and trace_hash as
    # the planner-off path.
    #
    # Default flipped to True 2026-05-21: cognition eval (45 cases)
    # was verified byte-identical across both projections (surface
    # AND trace_hash) flag-OFF vs flag-ON, so single-fact prompts are
    # not perturbed.  The flag's value shows up on NARRATIVE / EXAMPLE
    # / PARAGRAPH / EXPLAIN modes and compound prompts that the flat
    # classifier currently misclassifies as OOV — those turns become
    # multi-clause grounded articulations rather than single-fragment
    # disclosures or OOV refusals.
    discourse_planner: bool = True

    # Phase 3 — plan-level contemplation pre-flight.  When True, after
    # the discourse planner produces a plan (and before the renderer
    # fires) the runtime runs ``core.contemplation.plan_preflight.
    # contemplate_plan`` over the plan and stores any SPECULATIVE
    # findings on the runtime for downstream consumption.  Per
    # ADR-0080: contemplation is read-only and SPECULATIVE-only — no
    # plan mutation, no autonomous memory promotion.  Findings flow
    # into the offline contemplation miner (Phase 5) for review-gated
    # pack-mutation candidates.  Default False keeps the contemplation
    # opt-in until the operator wires the downstream sink.
    discourse_contemplation: bool = False

    # ADR-0068 / ADR-0069 — register pack id loaded at runtime startup.
    # ``None`` resolves to ``RegisterPack.unregistered()`` (the in-memory
    # null-register sentinel; structurally identical to
    # ``default_neutral_v1``).  At R2 the register is loaded, stored, and
    # threaded through every realizer call site, but no composer consumes
    # it — the three byte-identity invariants (None ≡ default_neutral_v1
    # ≡ pre-R2 output) are CI-pinned by ``test_register_null_lift.py``.
    # R3 widens composers to dispatch on ``register.realizer_overrides``.
    register_pack_id: str | None = None
    # ADR-0073b — anchor-lens pack id loaded at runtime startup.
    # ``None`` resolves to ``AnchorLens.unanchored()`` (the in-memory
    # null-lens sentinel; structurally identical to
    # ``default_unanchored_v1``).  At L1.2 the lens is loaded and
    # stored on the runtime, but no composer consumes it — the
    # ``anchor_lens_byte_identity_null_lift`` invariant (None ≡
    # default_unanchored_v1) is CI-pinned by
    # ``test_anchor_lens_null_lift.py``.  L1.3 will widen composers
    # to dispatch on ``anchor_lens.semantic_domain_preferences``.
    anchor_lens_id: str | None = None

    # Finding 6 (audit 2026-05-20) — generation stop tokens.
    #
    # ``None`` resolves to ``generate.stream._STOP_TOKENS`` (the
    # historical ``frozenset({"it", "to", "word"})``) so every
    # pre-Finding-6 caller preserves byte-identity.  Operators that
    # mount a pack where one of the historical stop tokens carries
    # meaningful content (e.g. a philosophy pack where ``word`` maps
    # to λόγος, a syntax pack where ``to`` is a content node) can
    # override the set here to free them.  Manifest-driven
    # per-pack override (``generation_stop_tokens`` field in the pack
    # manifest) is the natural next step; that requires a pack-
    # schema ADR and re-ratification so the wiring lands first.
    stop_tokens: tuple[str, ...] | None = None

    # ADR-0088 Phase B (audit Finding 2, 2026-05-20) — realizer becomes
    # a real surface authority by grounding the proposition graph from
    # the recall step's walk tokens before invoking
    # ``realize_semantic``.  Default ``False`` preserves byte-identity
    # for every existing pack and test — the pipeline's
    # ``realize_semantic`` call continues to fire on the ungrounded
    # graph, which produces ``<pending>`` / ``...`` surfaces that the
    # ``_is_useful_surface`` gate rejects, leaving the runtime path's
    # ADR-0085-polished pack-grounded surface as the user-visible
    # answer (same as today).
    #
    # When True the pipeline reorders ``realize_semantic`` to run
    # AFTER ``runtime.chat``, calls ``ground_graph(graph,
    # response.recalled_words)`` to fill the ``<pending>`` slots, then
    # re-invokes ``realize_semantic`` on the grounded graph.  The
    # surface resolver (PR #76) then picks the realizer's grounded
    # output when it clears ``_is_useful_surface`` and the unknown-
    # domain gate did not fire.
    #
    # NOTE — Phase A (realizer fluency parity: gloss-aware templates,
    # 3sg verb agreement, pack-provenance tag) is the prerequisite
    # for enabling this flag in production.  The known fluency gap
    # (e.g. ``"Light is a visible medium that reveal truth"``,
    # subject-verb disagreement) is documented in ADR-0088 §Phase A.
    # The wiring lands first so the runtime contract is stable when
    # Phase A's realizer fluency upgrade ships.
    realizer_grounded_authority: bool = False

    # ADR-0090 (audit Findings 6 + 7, 2026-05-21) — unified-ingest path.
    # Default ``False`` preserves bit-identical behavior with the
    # historical probe-then-commit path:
    #
    #   1. ``chat()`` calls ``probe_ingest(filtered)`` first.
    #   2. The gate observes ``probe_state.F``.
    #   3. If the gate fires, ``commit_ingest`` runs and a stub
    #      response returns.  If not, ``commit_ingest`` runs and
    #      drive bias is applied, producing a different field
    #      from the one the gate saw.
    #
    # The probe/commit distinction means the gate decides on one
    # manifold position and the walk navigates a slightly different
    # one — a coherence gap the second-opinion audit named.
    #
    # When ``True``:
    #
    #   1. ``chat()`` calls ``commit_ingest(filtered)`` first.
    #   2. Drive bias is applied immediately.
    #   3. The gate observes ``committed.F`` (the same field the walk
    #      will navigate on the non-stub path).
    #   4. ``probe_ingest`` is skipped entirely on this path.
    #
    # **Semantic change when True:** stub-path turns commit before
    # the stub response is generated.  Under ``False`` stub turns do
    # not commit at the time of the gate check (today's behavior).
    # Operators opt into the cleaner coherence by flipping the flag;
    # the unified path is not the default until validated against a
    # live workload.
    unified_ingest: bool = False


    # ADR-0144 — recognition-grounded articulation graph.  When True and a
    # DerivedRecognizer is attached to CognitiveTurnPipeline, the articulation
    # graph is derived from the admitted EpistemicNode via the connector rather
    # than from intent classification.  Default False preserves byte-identity
    # for every existing surface and trace_hash.
    recognition_grounded_graph: bool = False

    # W-016 — wire session vault (T1) into discovery contemplation.
    # When True, ChatRuntime builds a vault probe from the live session
    # vault and passes it to contemplate() in _emit_discovery_candidates.
    # The probe queries the vault at EpistemicStatus.COHERENT so only
    # reviewed-coherent session entries contribute evidence; SPECULATIVE /
    # CONTESTED / FALSIFIED entries are filtered by the vault layer per
    # ADR-0021 §3.  Default False preserves all pre-W-016 discovery
    # output byte-identically (null-drop invariant on discovery lanes).
    vault_probe_discoveries: bool = False
    # ADR-0148 — wire VaultPromotionPolicy into turn boundary.
    # When True, ChatRuntime calls vault.promote_eligible_entries() after each
    # finalize_turn(), scanning SPECULATIVE entries for crystallization to
    # COHERENT based on their energy profile (EnergyClass E0/E1, coherence_residual
    # ≤ 0.05).  Fresh entries written in the current turn are E2+ and will not
    # promote yet — the policy fires on entries that have cooled across turns.
    # Default False: zero behavior change when disabled (null-drop invariant).
    # Unlocks W-007 (DerivedRecognizer derivation from promoted COHERENT entries).
    vault_promotion_enabled: bool = False

    # ADR-0150 — run contemplation on pending discovery candidates at checkpoint.
    # Activates ADR-0056 Phase C1. Null-drop when False.
    auto_contemplate: bool = False

    # ADR-0151 — generate TeachingChainProposals from enriched candidates on load.
    auto_proposal_enabled: bool = False

    # ADR-0164 Phase 1 — incremental comprehension reader for question sentences.
    # When True, the candidate-graph path uses the comprehension reader
    # (generate/comprehension/lifecycle.py) to parse question sentences BEFORE
    # consulting the regex question patterns (Pattern A/B/C in
    # generate/math_candidate_parser.py).  On reader refusal, falls through to
    # the existing regex parser — the reader is purely additive at Phase 1.
    # Default False: flag-OFF behaviour is byte-identical to today.
    # Phase 3 (per ADR-0164 §Phasing) removes the regex question parser entirely;
    # that work is deferred — this PR is the Phase 1 stopgap.
    comprehension_reader_questions: bool = False


DEFAULT_IDENTITY_PACK: str = "default_general_v1"
DEFAULT_ETHICS_PACK: str = "default_general_ethics_v1"
DEFAULT_REGISTER_PACK: str = "default_neutral_v1"
DEFAULT_ANCHOR_LENS: str = "default_unanchored_v1"
DEFAULT_CONFIG = RuntimeConfig()

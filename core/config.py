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
    # so the default-False path is fully preserved.
    discourse_planner: bool = False

    # ADR-0068 / ADR-0069 — register pack id loaded at runtime startup.
    # ``None`` resolves to ``RegisterPack.unregistered()`` (the in-memory
    # null-register sentinel; structurally identical to
    # ``default_neutral_v1``).  At R2 the register is loaded, stored, and
    # threaded through every realizer call site, but no composer consumes
    # it — the three byte-identity invariants (None ≡ default_neutral_v1
    # ≡ pre-R2 output) are CI-pinned by ``test_register_null_lift.py``.
    # R3 widens composers to dispatch on ``register.realizer_overrides``.
    register_pack_id: str | None = None


DEFAULT_IDENTITY_PACK: str = "default_general_v1"
DEFAULT_ETHICS_PACK: str = "default_general_ethics_v1"
DEFAULT_REGISTER_PACK: str = "default_neutral_v1"
DEFAULT_CONFIG = RuntimeConfig()

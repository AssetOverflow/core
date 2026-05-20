# ADR-0078 Phase 1 — Pre-Implementation Planning Note

1. Where composer atoms come from.
- On DEFINITION/RECALL pack-grounded paths, composer provenance is available from existing pack candidate metadata (`build_pack_surface_candidate(...).semantic_domains`) and from the existing `_maybe_pack_grounded_surface(...)->pack_semantic_domains` return channel.
- Other composer paths do not always expose explicit atom provenance today; those will report `composer_no_atoms` when telemetry is applicable and grounded but atom provenance is absent.

2. Where graph-side atoms/indices are derived.
- Graph topology comes from `build_graph_from_input(text, articulation)` and forward constraints from `build_graph_constraint(graph, vocab)`.
- Phase 1 graph atom telemetry will be observational and derived by resolving graph node surfaces (`subject/predicate/obj`) through `chat.pack_resolver.resolve_lemma`, unioning resolved semantic domains.
- If no graph nodes resolve to atoms (or graph constraint is unconstrained), graph hash remains empty and status can become `graph_unconstrained`.

3. Exact telemetry hook location.
- Hook in `chat/runtime.py` after final composer surface / grounding source are known (cold/stub and warm paths) and after pre-generation graph context is known, but before `TurnEvent` and `ChatResponse` are finalized.
- Keep this observational only: compute status/hash/overlap and attach fields; do not alter surface selection, guard outcomes, grounding source, or trace behavior.

4. Why register variation does not affect atom hashes.
- Register decoration/substantive transforms operate on rendered surface layers (`register_canonical_surface` -> pre-decoration -> decorated surface).
- Composer atom provenance and graph atoms come from pack/graph structures, not register text transforms; therefore register changes should not perturb atom-set hashes/status for same prompt/lens/runtime state.

5. Why anchor-lens engagement may affect substantive/proposition telemetry.
- Anchor-lens changes composer proposition selection by engaging substrate-aligned semantic preferences (ADR-0073c/0073d), so resulting semantic domains and graph realization can legitimately differ when lens changes.
- This is substantive-axis movement, not register-style presentation variation; telemetry must allow divergence/equivalence outcomes without forcing false invariants.

6. Confirmation that no final surface prose parsing will be added.
- No parsing of `ChatResponse.surface`/final prose will be introduced for atom inference.
- No helpers like `extract_candidate_surface_lemmas`, `surface_lemma`, or `parse_surface_atoms` will be added.
- If a grounded composer path lacks explicit atom provenance, status will be `composer_no_atoms`.

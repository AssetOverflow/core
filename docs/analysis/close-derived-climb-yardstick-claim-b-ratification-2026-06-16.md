# Ratification: Harden evals/close_derived_climb Yardstick Toward Full Lived-Runtime Claim B

**Date:** 2026-06-16  
**Author:** Grok (per brief)  
**Context:** Post-merge hardening audit (on main cf1e7371) of the CLOSE flywheel yardstick established that it delivers strong lived-runtime proof of **Claim A** (direct closure-growth via real `ChatRuntime.idle_tick()` + `consolidate_once` + `realize_derived`, with strict/monotone growth 1→5→8, `wrong_total=0`, boundaries preserved) but only partial evidence for **Claim B** (full lived flywheel yardstick).

**The three gaps identified (verbatim from audit):**
1. `_proposal_flag_effect()` uses explicit simulation (direct `consolidate_once` + `emit`) instead of real `ChatRuntime.idle_tick()`.
2. Positive growth metrics are scored via vault-direct `recall_realized` counts (`_count_answerable`) rather than semantic `determine()` calls on the grown facts.
3. `replay_checksum` only hashes aggregate sizes + wrong_total + flag-isolation and does not match its own documentation (which claims coverage of "closure sets" and "exact trajectories").

All core mechanics, invariants (INV-21/29/30/31), `wrong_total=0` behavior, SPECULATIVE-only, proposal-only boundary, and determinism are already solid.

## Ratification Decision
**The single recommended (and only correct) path is exactly the four targeted, minimal high-leverage improvements specified in the brief:**

1. **Semantic Answerability**: After reaching fixed point in the climb scenarios, explicitly call `determine()` (or `_ask_rel` equivalent) on the positive probe queries and assert `Determined(True)` with `rule='direct'`.
2. **Lived Flag Path**: Replace or augment `_proposal_flag_effect` with a version that uses real `ChatRuntime` + `idle_tick()` (flag enabled) and captures `IdleTickResult.derived_close_proposals_emitted`. Remove any dependence on direct simulation for the yardstick’s reported "proposals_only_with_flag" metric.
3. **Checksum Fidelity**: Extend `replay_checksum` (or add a parallel `content_replay_checksum`) to include canonical representations of actual closure sets (structure_key + `Derivation` with premise keys) and proposal bodies. Align implementation with existing module/contract documentation.
4. **Documentation**: Update `evals/close_derived_climb/contract.md` and relevant module docstrings to accurately reflect what the yardstick now measures (lived flag via `IdleTickResult`, semantic via `determine()`, content-level replay) versus prior claims.

**Why this is the only correct path (and must not be broadened or altered):**
- It directly, precisely, and minimally closes each of the three gaps from the audit without introducing new scenarios, metrics, harnesses, or capabilities.
- It makes *the yardstick code itself* (not external tests or side harnesses) exercise and report the full lived flywheel behaviors required for Claim B.
- It is the smallest set of changes that allow the yardstick to pass the original audit checklist under *both* Claim A *and* full Claim B criteria.
- Any other approach (e.g., a separate "Claim B" runner, larger refactor of recall/determine paths, adding new proposal families, or non-minimal content in checksum) would violate the "minimal + high-leverage", "do not broaden scope", and "preserve all existing invariants/behavior" constraints.
- Ratifying this exact path ensures subsequent implementation stays focused, the PR can reference this artifact as the justified direction, and no unrelated work is mixed in.

**Ratification Status:** Explicitly ratified as the sole authorized direction before any implementation code is written. Implementation will now proceed strictly to these four items (plus the required workflow steps: branch already created, PR at end with mandated description elements).

This ratification artifact will be referenced in the eventual PR description. 

(End of ratification. No implementation code has been written to the yardstick yet.)
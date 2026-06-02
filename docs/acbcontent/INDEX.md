# acbcontent / CORE — Document Index

*Canonical = the latest settled drafts. Superseded files are in `archive/` for history.*

## Canonical

### Architecture / conscience
- **[ADR-0200 — Conscience & Graduated-Autonomy Architecture](../decisions/ADR-0200-conscience-and-graduated-autonomy.md)** — *Proposed* capstone: four-pillar conscience, autonomy ceiling, pack-vs-safety layering. The most complete word on the architecture. Assigned ADR-0200 and relocated to `docs/decisions/` on placement; status is *Proposed* (not yet signed via the review-gated path).
- **[CORE_boundary_lock_buildplan.md](CORE_boundary_lock_buildplan.md)** — the engineering plan: HAVE / PARTIAL / NET-NEW tagging, trilingual anchoring in §1.3.

### Governance / entities
- **acbcontent_charter.md** — nonprofit (parent) governance instrument.
- **CORE_operating_constraints.md** — for-profit (child) governance instrument.

### Action / filing
- **Founding_and_Filing_Guide_acbcontent_CORE.md** — full filing guide (federal + California, current 2026 fees).
- **acbcontent_nocar_lowcash_checklist.md** — staged, no-car/low-cash launch checklist.

### Prep
- **CORE_unified_prep_BrainCorp_and_CasualtyCare.md** — unified study/prep plan.

### Repo to-do
- ~~**readme_accuracy_sync.patch**~~ — **SUPERSEDED, not applied.** The patch promoted `mathematics_logic` to `expert` in the README, but the live `core capability ledger` reports **`audit-passed`**: the ADR-0120 expert signature went *stale* when the GSM8K evidence advanced (#488 → 4/46/0, #500 → 6/44/0), so the signed `claim_digest` (`4c46f530…`) no longer matches the recomputed evidence digest (`02f6d3c8…`) and the composer correctly **refuses** the promotion. Applying the patch would have made the README assert a capability the engine's own ledger refuses to assert. The accurate parts of the patch (the "three distinct GSM8K numbers" clarification, train-sample 6/44/0) were folded into a **truthful hand-authored README sync** instead. To make `expert` genuinely live: re-sign the claim over the *current* evidence (operator action by `shay-j`) — the composite gate itself passes (B1 185/185, B2 40/40, B3 50/50, all wrong=0).

## How they relate
- **ADR** = the *decision record* + single consolidation point (currently *Proposed* — "ratified" means signed via the review-gated path, which has not yet happened).
- **charter + constraints** = the *governance instruments* the decisions get encoded into at filing.
- **buildplan** = the *engineering* path.
- **guide + checklist** = *how you stand it up*.

## archive/ (superseded — kept for history)
- **CORE_boundary_lock_spec.md** → became `CORE_boundary_lock_buildplan.md`
- **CORE_robotics_prep_3wk.md** → became `CORE_unified_prep_BrainCorp_and_CasualtyCare.md`
- **acbcontent_CORE_founding_doctrine.md** → distilled into charter + constraints + ADR (origin/manifesto; keep for the original mission language)

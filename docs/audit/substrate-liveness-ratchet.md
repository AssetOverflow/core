# Substrate Liveness Ratchet — v1 (partial; informed by L0-L3 + L10 scope)

**Scope:** [substrate-liveness-audit-scope](../decisions/substrate-liveness-audit-scope.md) (v2)
**Companion:** [substrate-liveness-registry](./substrate-liveness-registry.md)
**Status:** Active — append-only; revised as audit findings (L4-L9) and operator review refine the sequence.

---

## Purpose

The substrate-liveness audit produces evidence; the ratchet derives **the
order in which wiring debt should be paid down**. Each entry names a
wiring gap surfaced by the audit, identifies the dependencies that must
land first, and points at the ADR (existing or proposed) that will
close it.

The ratchet is not a roadmap of features. It is the dependency-ordered
playbook for transitioning CORE from "subset of design executes" to
"design executes" — what the operator and the audit-scope call **live
mode readiness**.

**This is v1, drafted with L0-L3 + L10 scope landed.** L4-L9 audits are
either in flight or pending; the ratchet will be revised as their
findings land. Wiring items that touch unaudited layers carry an
explicit *audit-dependency* flag.

---

## Wiring debt registry (current)

Each entry: **W-NNN** | what's broken | source | dependency | proposed
home (ADR-XXXX or new).

### W-001 — Versor-condition threshold rot (FIXED)

- **Surfaced by:** L1 audit (PR #237).
- **Gap:** `ingest/gate.py` documented contract `versor_condition < 1e-6`
  but raised only at `> 1e-5`; architectural-invariants test pinned the
  weaker threshold.
- **Resolution:** PR #239 (Codex). Threshold tightened to `< 1e-6`;
  test updated. Verified by full audit-spectrum suite runs.
- **Status:** ✅ CLOSED. Recorded here for completeness — the ratchet
  retains its history.

### W-002 — ADR-0097 ledger-status test orphan (FIXED)

- **Surfaced by:** PR #239 verification (Codex's full-suite run).
- **Gap:** `test_status_meets_reasoning_capable_at_minimum` accepted
  `{reasoning-capable, audit-passed}` but ADR-0120 had promoted
  `mathematics_logic` to `expert` without updating the test.
- **Resolution:** PR #240. One-token extension.
- **Status:** ✅ CLOSED. Cleanup discipline applied per
  [[feedback-cleanup-as-you-find]].

### W-003 — `VaultPromotionPolicy` dormant

- **Surfaced by:** L2 audit (PR #238); also flagged in
  recognizer-storage-scope v2 (PR #232).
- **Gap:** `core/physics/learning.py` defines `VaultPromotionPolicy`
  (ADR-0014). 0 live callers, 0 test callers outside `core/physics/`.
  The field-energy/promotion lattice has its energy half wired (L1
  audit confirms `FieldEnergyOperator` is live at three callers) but
  the promotion half is dormant.
- **Dependency:** L10 (runtime model) — promotion timing depends on
  when the field→vault transition is decided to fire (per-turn?
  per-session boundary? long-lived process?).
- **Proposed home:** new ADR after L10 commits — *"wire
  `VaultPromotionPolicy` into the runtime promotion path"*. Sized for
  a small focused ADR once L10's process-shape decision is made.
- **Recognizer-storage dependency:** the recognizer-storage ADR
  explicitly depends on this wiring (its content cannot crystallize
  if the lattice's promotion gate isn't running).
- **Status:** ⏳ OPEN — audit-dependency on L10.

### W-004 — Vault re-thaw path specified-not-verified-live

- **Surfaced by:** L2 audit (PR #238); L1 audit (PR #237) forward-noted
  the same concern.
- **Gap:** ADR-0006 §"Integration Points" specifies "Vault recall
  transiently raises region to E2, then lets it cool again." L2 audit
  traced `vault.recall` callers and found that recall does NOT update
  or re-raise the energy class/profile of recalled entries. The
  re-thaw is design-only; nothing in code does it.
- **Dependency:** L1 (energy operator, live) — already in place. The
  wiring is at L2's recall path, not at L1.
- **Cross-layer consequence:** L3 audit (PR #241) confirmed that
  downstream language readback receives recalled-as-E0 regions and
  silently treats them as if E2 — a load-bearing inconsistency
  (W-005).
- **Proposed home:** new ADR — *"wire vault-recall energy re-thaw per
  ADR-0006 integration spec"*. Small focused ADR; doesn't require L10.
- **Status:** ⏳ OPEN — can land independently of L10.

### W-005 — E0/E2 readback modulation absent

- **Surfaced by:** L3 audit (PR #241), confirming L2's forward note,
  confirming L1's note about energy → surface coupling.
- **Gap:** `packs/common/runtime_rules.py:readback_from_intent` receives
  `field_state.energy` but silently treats E0 (vault crystal),
  E1 (warm), E2 (active), E3 (peak) identically. ADR-0006/0007
  specify energy-class-dependent tense, framing, and hedging
  modulation that is not implemented.
- **Dependency:** W-004 first (until vault recall re-thaws, E0 vs E2
  distinction is moot at runtime — every recalled region is stuck at
  E0 anyway). Could be specified-and-implemented before W-004 but the
  user-visible behavior change requires W-004.
- **Proposed home:** new ADR — *"energy-modulated surface readback per
  ADR-0006/0007"*. Likely an extension of `generate/realizer.py` since
  L3 audit confirmed surface generation is done there, not in pack
  readback rules.
- **Status:** ⏳ OPEN — sequence: W-004 → W-005.

### W-006 — Local pack readback rules dormant

- **Surfaced by:** L3 audit (PR #241).
- **Gap:** `packs/<lang>/readback_rules.py` files (en, el, grc, he)
  exist with 0 live callers. Surface generation goes through
  `generate/realizer.py` instead. The per-language readback path is
  spec-in-code that nothing uses.
- **Dependency:** none (independent).
- **Resolution path:** either (a) wire pack-readback into surface
  generation per original intent, or (b) accept that
  `generate/realizer.py` superseded the design and DELETE the dormant
  pack-readback modules per [[feedback-cleanup-as-you-find]].
- **Recommended:** decision belongs to operator review. If (b), it's a
  cleanup PR, not a wiring ADR. If (a), it's a new ADR explaining why
  pack-readback regains primacy.
- **Status:** ⏳ OPEN — operator decision required before sequencing.

### W-007 — `DerivedRecognizer` integration into live turn loop

- **Surfaced by:** ADR-0144 commit body + recognizer-storage-scope v2.
- **Gap:** `core/cognition/pipeline.py:121` accepts
  `recognizer: DerivedRecognizer | None = None`. Nothing in main
  constructs or passes a recognizer. The anti-unifier (ADR-0143) and
  the carrier (ADR-0144) are live in isolation; they are not yet wired
  into the turn loop.
- **Dependency:** recognizer-storage-scope's question must be answered
  first (where do recognizers come from at turn time? — see W-003 for
  the storage-layer dependency).
- **Proposed home:** new ADR after recognizer-storage decision lands.
  Likely titled *"integrate `DerivedRecognizer` into
  `CognitiveTurnPipeline`"*. Sized after the storage ADR commits.
- **Note for L4 audit:** verify this gap survives a fresh audit.
- **Status:** ⏳ OPEN — chained: W-003 → recognizer-storage ADR →
  W-007.

### W-008 — Runtime model (L10) scope adoption

- **Surfaced by:** recognizer-storage-scope v2 and audit-scope v2 both
  named runtime model as missing prerequisite.
- **Gap:** No ADR specifies the process shape for forever-running
  CORE. Today: `core` CLI is one-shot; no long-lived process;
  capability does not accumulate across invocations. The audit-scope
  flagged L10 as "not an audit target — prerequisite the audit will
  surface need for." That prerequisite is now load-bearing.
- **Resolution path:** PR #236 landed the L10 scope. Next: ADR (or ADR
  cluster) committing to process shape A/B/C (per L10 scope
  sub-question 1), state partitioning, reboot recovery, HITL async.
- **Dependency:** none for the scope→ADR transition; informed by L4-L9
  audit findings as they land.
- **Proposed home:** new ADR — *"runtime model for forever-running
  CORE (L10 commit)"*. Large; may split into ADR cluster.
- **Status:** ⏳ OPEN — scope landed (#236); spike/ADR pending.

### W-009 — HITL async queue surface

- **Surfaced by:** recognizer-storage v2 (drop-off ADR named); L10
  scope sub-question 4.
- **Gap:** ADR-0057 establishes append-only proposal log + operator
  review machinery. Currently consumed only by `core teaching_*` CLI
  commands (synchronous). For forever-running engine, the queue
  becomes async: operator reviews while engine continues serving
  turns.
- **Dependency:** W-008 (runtime model) — async queue shape depends on
  process model.
- **Proposed home:** new ADR after W-008. Per recognizer-storage v2,
  *"the drop-off ADR's load-bearing originality is the trigger
  (recency) and the gate (not replay-equivalence). The review-and-log
  half is a small extension to existing machinery."*
- **Status:** ⏳ OPEN — chained: W-008 → W-009.

---

## Dependency graph (Mermaid-style, ASCII)

```
W-001 ✅ ──── (independent, FIXED)
W-002 ✅ ──── (independent, FIXED)

W-004 ⏳ ──── (independent) ────→ W-005 ⏳
                                       ↑
W-006 ⏳ ──── (operator decision) ─────┘ (may merge / supersede)

W-008 (L10 ADR) ⏳
   ├──→ W-003 (VaultPromotionPolicy wiring) ⏳
   │       └──→ recognizer-storage ADR
   │              └──→ W-007 (recognizer integration) ⏳
   └──→ W-009 (HITL async queue) ⏳
            └──→ drop-off sibling ADR
```

---

## Suggested next ADRs (sequence)

In dependency order, given current findings:

1. **W-004 — Wire vault-recall energy re-thaw per ADR-0006.** Smallest,
   most independent. Closes one of the load-bearing inconsistencies.
   No runtime-model dependency.

2. **W-006 — Operator decision on pack readback (wire or delete).**
   Either direction is small. Should happen before deeper L3 work.

3. **W-008 — Runtime model ADR (or ADR cluster).** Largest unit. Gates
   W-003, W-007, W-009 and informs every layer above L3. Scope
   already exists (#236); spike + ADR is the next phase.

4. **W-005 — Energy-modulated surface readback.** Becomes
   user-observable once W-004 is in place.

5. **W-003 — `VaultPromotionPolicy` wiring.** Small ADR once W-008
   commits to process shape.

6. **Recognizer-storage ADR** — answers the open question in
   `recognizer-storage-scope.md` against W-008's process shape and
   W-003's wired promotion.

7. **W-007 — `DerivedRecognizer` integration into turn loop.** Small
   once the storage ADR commits.

8. **W-009 — HITL async queue.** Concurrent with or after W-008
   depending on ADR cluster shape.

This order is a suggestion. The operator decides; the ratchet records.

---

## Items deliberately deferred / not in scope

- **EngineIdentity (DNA-analog hash).** Shelved candidate per
  [[project-engine-identity-candidate]]. Trigger to un-shelve: L10
  runtime-model ADR commits to cross-reboot identity verification as
  a sub-question 3 requirement.
- **L4-L9 wiring debt.** Audit findings pending. Ratchet will be
  revised as L4-L9 entries land in the registry.
- **Drop-off sibling ADR for recognizers.** Named in recognizer-
  storage-scope v2; depends on W-008 + recognizer-storage ADR + W-009.
  Not added to the ratchet as a standalone entry yet because it's a
  derived consequence of items already listed.

---

## How the ratchet evolves

Per the audit-scope: "the ratchet is revisable as the registry changes.
Each completed wiring updates the ratchet and (likely) reveals new
wiring debt in layers above."

Revision discipline:
- **New audit finding ⇒ new W-NNN entry.** Append, don't renumber.
- **Wiring completed ⇒ mark ✅ in-place + retain entry.** History is
  the value; renumbering destroys it.
- **Dependency learned later ⇒ amend in-place + date the amendment.**
- **Operator decision ⇒ amend "proposed home" or "resolution path"
  with citation.**

This file should grow over the substrate-liveness program. When the
ratchet shows all entries closed, **live mode is reached**.

---

## Cross-references

- [substrate-liveness-audit-scope](../decisions/substrate-liveness-audit-scope.md) — defines the audit shape
- [substrate-liveness-registry](./substrate-liveness-registry.md) — per-layer evidence
- [L10-runtime-model-scope](../decisions/L10-runtime-model-scope.md) — gates W-003, W-007, W-009
- [recognizer-storage-scope](../decisions/recognizer-storage-scope.md) — gates W-007
- [teaching-derived-recognition-scope](../decisions/teaching-derived-recognition-scope.md) — parent of recognition arc
- [project-engine-identity-candidate](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/project-engine-identity-candidate.md) — shelved candidate
- [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md) — discipline applied
- [feedback-cleanup-as-you-find](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-cleanup-as-you-find.md) — applies to W-006 if delete-path is chosen

# Substrate Liveness Ratchet — v2 (partial; informed by L0-L5 + L10 scope)

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

### W-010 — L4 recognition bypasses L3 vocabulary

- **Surfaced by:** L4 audit (PR #243), confirming L3 audit's forward
  question (PR #241).
- **Gap:** `derive_recognizer()` and `recognize()` operate on raw token
  sequences and taught `FeatureBundle` evidence without consuming L3's
  compiled `VocabManifold`, domain namespaces, or pack-resident
  lexicon. Grep across `recognition/` confirms no `VocabManifold` /
  `language_packs` / `load_pack` / `compiled` / `lexicon` / `vocab`
  references except a prose comment in `outcome.py`.
- **Dependency:** operator decision — is the token-level spike
  intentional (raw tokens are the right substrate for anti-unification)
  or transitional (recognition will eventually plug into L3 vocabulary
  for richer typed slots)?
- **Resolution paths:**
  - **(a)** Document as intentional in ADR-0143 amendment. No code
    change. Recognition stays token-level by design.
  - **(b)** Wire `VocabManifold` consumption into `derive_recognizer()`
    via new ADR. Larger change; would let recognition reference
    pack-resident domain types in feature slots.
- **Recommended:** operator decision. Per the thesis, token-level may
  be the right level (anti-unification doesn't *need* pack vocabulary
  — it derives its own structure); pack consumption may be premature
  generalization.
- **Status:** ⏳ OPEN — operator decision required.

### W-011 — Typed recognition refusals dropped at pipeline boundary

- **Surfaced by:** L4 audit (PR #243).
- **Gap:** `CognitiveTurnPipeline` calls `recognize()` and, on
  admission, wraps the outcome in an `EpistemicGraph` carrier. On
  refusal, `_rec_outcome.refusal_reason` is **discarded** —
  `CognitiveTurnResult.refusal_reason` is populated from
  `ChatResponse.refusal_reason` (the generation path), not from the
  typed recognition refusal. The teaching loop is supposed to consume
  typed recognizer refusals as learning signals (per ADR-0143's
  refusal-first design); today the signals are dropped.
- **Dependency:** light — requires extending the pipeline's recognition
  branch to fold `_rec_outcome.refusal_reason` into the turn result.
- **Proposed home:** small ADR amendment to ADR-0144 or new tiny ADR
  *"propagate recognition refusal_reason into CognitiveTurnResult"*.
  Mechanical change; should not require L10 or storage decisions.
- **Status:** ⏳ OPEN — independent, can land soon.

### W-012 — `InnerLoopExhaustion` not caught in `ChatRuntime.chat()`

- **Surfaced by:** L5 audit (PR #244).
- **Gap:** Inner-loop refusal exceptions (`InnerLoopExhaustion`,
  ADR-0024) are raised during generation but **never caught in the
  main `ChatRuntime.chat()` execution**. The plumbing to materialize
  `RefusalReason` taxonomy into `ChatResponse.refusal_reason` exists
  (W-011-adjacent), but the live run propagates as unhandled exception
  instead of materialized refusal.
- **Cross-reference:** ADR-0142 implementation debt #3 lists this as
  the blocker for full epistemic refusal tracking.
- **Dependency:** light — requires `try/except InnerLoopExhaustion` in
  `ChatRuntime.chat()` with refusal materialization.
- **Proposed home:** small ADR or fix-PR directly. Likely titled
  *"catch InnerLoopExhaustion and materialize refusal_reason in
  ChatRuntime"*.
- **Status:** ⏳ OPEN — independent, can land soon. Sibling to W-011
  (both about refusal materialization at different boundaries).

### W-013 — `core/cognition/explain.py` dormant

- **Surfaced by:** L5 audit (PR #244).
- **Gap:** `core/cognition/explain.py` (124 lines) has 0 live
  production callers outside its test file. It is re-exported in
  `core/cognition/__init__.py` but unused.
- **Dependency:** operator decision — wire to live REPL / CLI
  proposal commands, or accept that it's offline-only audit tooling
  and either delete or relocate to `evals/` / `scripts/`.
- **Resolution paths:**
  - **(a)** Wire into `core chat` for "explain this turn" interactive
    command. Live integration.
  - **(b)** Move to `evals/` if intended as offline audit tool.
  - **(c)** Delete if neither (a) nor (b) is desired per
    [[feedback-cleanup-as-you-find]] — the audit's "unambiguously
    dead" bar is not met here because the module is well-formed and
    test-covered, just unwired. Operator call.
- **Status:** ⏳ OPEN — operator decision required.

### W-014 — `core/cognition/provenance.py` partially live (evals-only)

- **Surfaced by:** L5 audit (PR #244).
- **Gap:** `core/cognition/provenance.py` (101 lines) is consumed only
  by `evals/provenance/runner.py` and tests. No live runtime caller.
- **Dependency:** independent. Same operator decision as W-013 (wire,
  relocate, or accept as evals-only).
- **Resolution paths:**
  - **(a)** Wire into live turn result for per-turn provenance
    surfacing.
  - **(b)** Relocate to `evals/` and accept as offline-only.
  - **(c)** Leave as-is and document explicitly as evals-only.
- **Status:** ⏳ OPEN — lighter than W-013 because there IS a live
  consumer (evals); the question is whether it should be promoted to
  runtime use.

---

## Dependency graph (Mermaid-style, ASCII)

```
W-001 ✅ ──── (independent, FIXED)
W-002 ✅ ──── (independent, FIXED)

W-004 ⏳ ──── (independent) ────→ W-005 ⏳
                                       ↑
W-006 ⏳ ──── (operator decision) ─────┘ (may merge / supersede)

W-011 ⏳ ──── (independent, mechanical)
W-012 ⏳ ──── (independent, mechanical)  — sibling of W-011

W-010 ⏳ ──── (operator decision: intentional or wire L3 vocab)
W-013 ⏳ ──── (operator decision: wire, relocate, or delete)
W-014 ⏳ ──── (operator decision: lighter than W-013)

W-008 (L10 ADR) ⏳
   ├──→ W-003 (VaultPromotionPolicy wiring) ⏳
   │       └──→ recognizer-storage ADR
   │              └──→ W-007 (recognizer integration) ⏳
   └──→ W-009 (HITL async queue) ⏳
            └──→ drop-off sibling ADR
```

---

## Suggested next ADRs (sequence)

In dependency order, given current findings. **Quick wins first
(mechanical, independent, small diffs), then operator decisions, then
the bigger L10 unit.**

### Quick wins — independent, mechanical, small diffs

1. **W-011 — Propagate recognition `refusal_reason` into
   `CognitiveTurnResult`.** ~Small pipeline change. Closes a load-
   bearing audit-trail gap in recognition.
2. **W-012 — Catch `InnerLoopExhaustion` in `ChatRuntime.chat()`.**
   Sibling of W-011 — both about refusal materialization. Closes
   ADR-0142 implementation debt #3.
3. **W-004 — Wire vault-recall energy re-thaw per ADR-0006.** No
   runtime-model dependency. Closes the field/vault re-injection gap.

### Operator-decision items — small either way, just need a call

4. **W-006 — Pack readback: wire or delete.** Per
   [[feedback-cleanup-as-you-find]], operator decides; the audit is
   waiting on the answer.
5. **W-013 / W-014 — `explain.py` / `provenance.py`: wire, relocate,
   or delete.** Same shape as W-006.
6. **W-010 — L4 recognition vocabulary: token-level intentional, or
   wire L3 vocab.** Operator decision; affects whether recognition
   pulls in pack-resident domain types.

### Then user-observable second-order changes

7. **W-005 — Energy-modulated surface readback.** Becomes user-
   observable once W-004 is in place. Closes E0/E2 readback rot.

### Bigger units (gated on or co-evolving with L10)

8. **W-008 — Runtime model ADR (or cluster).** Largest unit. Gates
   W-003, W-007, W-009. Scope landed (#236); spike + ADR next.
9. **W-003 — `VaultPromotionPolicy` wiring.** Small ADR once W-008
   commits to process shape.
10. **Recognizer-storage ADR** — answers `recognizer-storage-scope.md`
    against W-008's process shape and W-003's wired promotion.
11. **W-007 — `DerivedRecognizer` integration into turn loop.** Small
    once the storage ADR commits.
12. **W-009 — HITL async queue.** Concurrent with or after W-008.

This order is a suggestion. The operator decides; the ratchet records.

**Why quick wins first changed in v2:** v1 led with W-004 (a vault
fix). The L4/L5 audits surfaced W-011 and W-012, which are even
smaller and close load-bearing audit-trail gaps. Pulling them forward
gets early measurable progress with no architectural risk, and
demonstrates the audit-to-fix loop actually closes.

---

## Items deliberately deferred / not in scope

- **EngineIdentity (DNA-analog hash).** Shelved candidate per
  [[project-engine-identity-candidate]]. Trigger to un-shelve: L10
  runtime-model ADR commits to cross-reboot identity verification as
  a sub-question 3 requirement.
- **L6-L9 wiring debt.** L0-L5 audited (5 of 9 layers); L6-L9 pending.
  Ratchet will be revised as remaining entries land.
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

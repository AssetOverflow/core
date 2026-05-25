# Substrate Liveness Ratchet — v5 (quick-wins lane cleared: W-011/W-012/W-015/W-016 closed)

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

### W-004 — Vault re-thaw path specified-not-verified-live (FIXED)

- **Surfaced by:** L2 audit (PR #238); L1 audit (PR #237) forward-noted
  the same concern.
- **Gap:** ADR-0006 §"Integration Points" specifies "Vault recall
  transiently raises region to E2, then lets it cool again." L2 audit
  traced `vault.recall` callers and found that recall did NOT update
  or re-raise the energy class/profile of recalled entries.
- **Resolution:** PR #251. `vault/store.py` now stamps each
  `recall()` / `recall_batch()` result with a module-level
  `_VAULT_RECALL_RETHAW_ENERGY` singleton (raw=0.50, E2 mid-band).
  Cool-down remains downstream propagation's responsibility. 6 new
  tests in `tests/test_vault_recall_rethaw.py` pin the contract; lane
  SHAs preserved (byte-identity intact).
- **Unlocks:** W-005 — E0/E2 distinction now exists at the runtime
  data shape, so energy-modulated surface readback becomes
  meaningful.
- **Status:** ✅ CLOSED.

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

### W-011 — Typed recognition refusals dropped at pipeline boundary (FIXED)

- **Surfaced by:** L4 audit (PR #243).
- **Gap:** `CognitiveTurnPipeline` called `recognize()` and, on
  admission, wrapped the outcome in an `EpistemicGraph` carrier. On
  refusal, `_rec_outcome.refusal_reason` was **discarded** —
  `CognitiveTurnResult.refusal_reason` was populated from
  `ChatResponse.refusal_reason` (the generation path), not from the
  typed recognition refusal. The teaching loop is supposed to consume
  typed recognizer refusals as learning signals (per ADR-0143's
  refusal-first design); the signals were being dropped.
- **Resolution:** PR #258 (Opus 4.6). `core/cognition/pipeline.py`
  now captures `_recognition_refusal_reason` in the recognize branch
  and folds it into `CognitiveTurnResult.refusal_reason` with
  recognition-wins precedence (earlier-fail boundary). New enum
  value `RefusalReason.RECOGNITION_REFUSED` added to
  `generate/exhaustion.py`. Test `tests/test_recognition_refusal_propagates.py`
  pins the contract.
- **Status:** ✅ CLOSED.

### W-012 — `InnerLoopExhaustion` not caught in `ChatRuntime.chat()` (FIXED)

- **Surfaced by:** L5 audit (PR #244).
- **Gap:** Inner-loop refusal exceptions (`InnerLoopExhaustion`,
  ADR-0024) were raised during generation but **never caught in the
  main `ChatRuntime.chat()` execution**. The plumbing to materialize
  `RefusalReason` taxonomy into `ChatResponse.refusal_reason` exists
  (W-011-adjacent), but the live run propagated as unhandled exception
  instead of materialized refusal.
- **Cross-reference:** ADR-0142 implementation debt #3 listed this as
  the blocker for full epistemic refusal tracking.
- **Resolution:** PR #258 (Opus 4.6, paired with W-011). `chat/runtime.py`
  wraps `generate()` in `try/except InnerLoopExhaustion`; on catch,
  calls `finalize_turn` with `{"exhaustion": True, "refusal_reason": ...}`
  metadata (so the failed turn still hits the audit trail) and
  returns a typed refusal `ChatResponse` via `replace(stub,
  refusal_reason=exc.reason.value)`. Test
  `tests/test_inner_loop_exhaustion_materializes.py` pins the contract.
- **Status:** ✅ CLOSED.

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

### W-015 — `session/context.py` post-generation unitize undocumented (FIXED)

**Resolution:** PR #255 (Sonnet). `session/context.py` now uses
`word_transition_rotor` + `rotor_power` (Lie group exponential map)
in `_anchor_pull`, which stays on the Spin manifold by construction.
`_slerp_toward` (34 lines) deleted; `unitize_versor` call in
`_anchor_pull` removed. Test `tests/test_session_coherence.py`
pins the manifold-preserving invariant. Smoke 67/67, teaching 17/17,
lane SHAs 7/7 unchanged.

**Investigation (preserved for history):**

Sonnet's investigation (PR #252) produced
verdict **(c) — upstream construction violation**, with mechanical
evidence: bimodal distribution across 4,138 samples (either
`vc < 1e-6` for near-identity slerp, or `vc >> 1e-3` with median 0.19
and max 38.58; nothing in `[1e-6, 1e-5)`). The `unitize_versor` at
`session/context.py:236` was repairing off-manifold state produced
by `_slerp_toward` (lines 38-64). Slerp interpolates on **S³¹**
(the 32D unit sphere) but the versor manifold (Spin group embedded
in Cl(4,1)) is a **proper subset** of S³¹ — the geodesic doesn't
stay on it.

**Original ratchet entry (preserved for history):**

- **Surfaced by:** L6 audit (PR #246), answering L1 audit's forward
  note (PR #237).
- **Gap:** `session/context.py:207-246` performs final-turn hemisphere
  correction and anchor pull with `unitize_versor()`. The site is
  test-covered, but no ADR documents it as an allowed normalization
  boundary. Per CLAUDE.md normalization rules, the only sanctioned
  unitize sites are `ingest/gate.py`, `language_packs/compiler.py`,
  and `algebra/versor.py`. The `session/context.py` site does not
  appear in that list — it is either an undocumented allowed boundary
  or a discipline violation.
- **Dependency:** none — purely a documentation/discipline question.
- **Resolution paths:**
  - **(a)** Write a small ADR amendment or new ADR sanctioning
    `session/context.py:207-246` as an allowed normalization boundary
    (the "final-turn anchor pull" boundary), with rationale.
  - **(b)** If the site is NOT a sanctioned boundary, refactor to
    remove the unitize call and surface any resulting closure
    failures rather than silently repairing them. Per CLAUDE.md:
    *"Do not add drift repair... whose only purpose is to repair
    another function."*
  - **(c)** Investigate whether the unitize is masking an upstream
    construction violation. If so, fix upstream and remove the
    site.
- **Recommended:** start with (c) — investigate root cause. (a) is the
  fallback if the unitize turns out to be a legitimate boundary.
  (b) is the fallback if it's pure drift repair.
- **Status:** ✅ CLOSED — see resolution at top of this entry.

### W-016 — Contemplation operates without vault probe (FIXED)

- **Surfaced by:** L8 audit (PR #250).
- **Gap:** `teaching.contemplation.contemplate` accepted an
  injectable `vault_probe` parameter, and tests proved coherent vault
  evidence could contribute to discovery candidate enrichment. But
  `ChatRuntime._emit_discovery_candidates` called `contemplate(c)`
  with **no probe**. Inline contemplation therefore operated on pack
  + reviewed corpus only, ignoring the session vault — exactly the
  Tier 1 evidence the four-tier model intends contemplation to
  consume.
- **Resolution:** PR #257 (Sonnet). Adds opt-in
  `RuntimeConfig.vault_probe_discoveries: bool = False` and
  `_build_vault_probe(vault, vocab)` factory in `chat/runtime.py`.
  When flag is on, builds a closure over the live session vault that
  queries at `EpistemicStatus.COHERENT` (ADR-0021 §3 excludes
  SPECULATIVE/CONTESTED/FALSIFIED), and passes the probe to
  `contemplate()`. Pure read; no field mutations, no vault writes.
  Default off preserves byte-identical pre-W-016 discovery JSONL.
  Test `tests/test_discovery_contemplation_vault_probe.py` pins
  4 contracts (off-default; on-call; evidence-reachable;
  raise-doesn't-crash). Lane SHAs 7/7 unchanged.
- **Unlocks:** Halves the W-017 dependency chain (W-016 now done; still
  gated on W-009).
- **Status:** ✅ CLOSED.

**Process note:** First attempt PR #256 was opened on the wrong head
branch (the W-015 branch, which still contained pre-#255 W-015
content). Closed; clean PR #257 opened from the actual W-016 branch
after rebasing onto post-#255+#251 main. Same wrong-branch pattern
that hit Gemini in L2/L3/L5/L7 and Sonnet's PR #254 earlier. Logged
in [[feedback-parallel-agent-worktrees]] — future briefs should
emphasize the rebase-onto-current-main step before PR creation.

### W-017 — Automated T1/T2 → T3 promotion absent

- **Surfaced by:** L8 audit (PR #250); ADR-0055's own "what is
  missing" section names this gap explicitly.
- **Gap:** The four-tier memory model (ADR-0055) specifies discovery
  evidence from T1 (session vault) and T2 (turn-event audit) should
  feed into proposed promotions to T3 (reviewed teaching corpus).
  Today, discovery candidates ARE emitted (W-016 caveat aside) and
  ARE written to disk via `DiscoveryMonthlyFileSink`, but no
  automated path turns them into proposals. Promotion to T3 still
  requires L7's synchronous operator `core teaching propose` command.
- **Dependency:** chained — depends on W-009 (HITL async queue) to
  give automated promotion a place to deposit candidates without
  blocking the engine. (W-016 vault-probe dependency satisfied by
  PR #257 — candidates can now carry T1 evidence on opt-in.)
- **Proposed home:** new ADR — *"automated T1/T2 → T3 promotion
  pipeline"*. Sized after W-009 commits.
- **Status:** ⏳ OPEN — chained: W-009 → W-017 (W-016 portion now
  satisfied).

### W-018 — ADR-0080 contemplation not autonomous

- **Surfaced by:** L8 audit (PR #250).
- **Gap:** ADR-0080 contemplation runs as a CLI operator command
  (`core contemplation`) over explicit report files, not as an
  autonomous runtime loop. Live plan contemplation exists in
  `ChatRuntime` but is opt-in via
  `RuntimeConfig.discourse_contemplation=True` (default off).
  "Autonomous" contemplation that runs without operator invocation
  doesn't exist.
- **Dependency:** chained — autonomous contemplation needs a runtime
  shape to live in (W-008 — L10 runtime model), and an event source
  (likely tied to W-017 promotion triggers).
- **Proposed home:** ADR amendment to ADR-0080 or new ADR — *"runtime-
  resident autonomous contemplation"*. Sized after W-008 commits.
- **Status:** ⏳ OPEN — chained: W-008 → W-018.

### W-019 — `from_miner.py` / `from_curriculum.py` test-live only

- **Surfaced by:** L8 audit (PR #250).
- **Gap:** `teaching/from_miner.py` (370 lines) and
  `teaching/from_curriculum.py` (275 lines) correctly build
  source-stamped proposals per ADR-0094 / ADR-0095 / ADR-0104, but
  no CLI command or live runtime path invokes them. Test-live
  only — the miner and curriculum candidate-conversion paths exist
  but produce nothing in production.
- **Dependency:** operator decision — wire to a CLI command (small),
  invoke from a runtime path (medium, depends on W-008 / W-017), or
  document as offline-only library code for evals.
- **Resolution paths:**
  - **(a)** Wire CLI: `core teaching propose --from-miner <dir>` and
    `--from-curriculum <dir>`. Small, no architectural commitment.
  - **(b)** Wire into W-017's automated promotion pipeline when that
    lands.
  - **(c)** Leave as test-live library and document explicitly.
- **Recommended:** (a) first as the smallest reachability fix; (b)
  follows naturally if W-017 materializes.
- **Status:** ⏳ OPEN — operator decision required.

---

## Dependency graph (Mermaid-style, ASCII)

```
W-001 ✅ ──── (independent, FIXED — PR #239)
W-002 ✅ ──── (independent, FIXED — PR #240)
W-004 ✅ ──── (independent, FIXED — PR #251)  ────→ W-005 ⏳ (unlocked, next)
                                                          ↑
W-006 ⏳ ──── (operator decision) ────────────────────────┘ (may merge / supersede)

W-011 ✅ ──── (FIXED — PR #258, paired with W-012)
W-012 ✅ ──── (FIXED — PR #258, paired with W-011)
W-015 ✅ ──── (FIXED — PR #255)
W-016 ✅ ──── (FIXED — PR #257)

W-010 ⏳ ──── (operator decision: intentional or wire L3 vocab)
W-013 ⏳ ──── (operator decision: wire, relocate, or delete)
W-014 ⏳ ──── (operator decision: lighter than W-013)
W-019 ⏳ ──── (operator decision: CLI, runtime, or library-only)

W-008 (L10 ADR) ⏳
   ├──→ W-003 (VaultPromotionPolicy wiring) ⏳
   │       └──→ recognizer-storage ADR
   │              └──→ W-007 (recognizer integration) ⏳
   ├──→ W-009 (HITL async queue) ⏳
   │       ├──→ drop-off sibling ADR
   │       └──→ W-017 (automated T1/T2→T3 promotion) ⏳
   │              ↑
   │              ├── W-016 ✅ (vault probe — DONE)
   │              └── W-019 (miner/curriculum wiring) — if path (b) chosen
   └──→ W-018 (autonomous contemplation) ⏳
```

---

## Suggested next ADRs (sequence)

In dependency order, given current findings. **Quick wins first
(mechanical, independent, small diffs), then operator decisions, then
the bigger L10 unit.**

### Quick wins — independent, mechanical, small diffs

**Quick-wins lane is now cleared.** W-011 (#258), W-012 (#258),
W-015 (#255), and W-016 (#257) all closed in v5. W-001/W-002/W-004
closed earlier. The only mechanical-independent entry left is W-005,
now unlocked by W-004.

### User-observable second-order changes (W-004 unlocks W-005)

1. **W-005 — Energy-modulated surface readback.** Now meaningful
   since W-004 closed (vault recall declares E2). Closes E0/E2
   readback rot. Touches `generate/realizer.py` per L3 audit's
   finding that surface generation lives there, not in
   `packs/common/runtime_rules.py`. **Next in queue.**

### Operator-decision items — small either way, just need a call

2. **W-006 — Pack readback: wire or delete.** Per
   [[feedback-cleanup-as-you-find]], operator decides.
3. **W-013 / W-014 — `explain.py` / `provenance.py`: wire, relocate,
   or delete.** Same shape as W-006.
4. **W-010 — L4 recognition vocabulary: token-level intentional, or
   wire L3 vocab.** Affects whether recognition pulls in
   pack-resident domain types.
5. **W-019 — `from_miner.py` / `from_curriculum.py`: CLI, runtime,
   or library-only.** Smallest fix is CLI wiring (path a).

### Bigger units (gated on or co-evolving with L10)

6. **W-008 — Runtime model ADR (or cluster).** Largest unit. Gates
   W-003, W-007, W-009, W-017, W-018. Scope landed (#236); spike +
   ADR next.
7. **W-003 — `VaultPromotionPolicy` wiring.** Small ADR once W-008
   commits to process shape.
8. **Recognizer-storage ADR** — answers `recognizer-storage-scope.md`
   against W-008's process shape and W-003's wired promotion.
9. **W-007 — `DerivedRecognizer` integration into turn loop.** Small
   once the storage ADR commits.
10. **W-009 — HITL async queue.** Concurrent with or after W-008.
11. **W-017 — Automated T1/T2 → T3 promotion.** After W-009 (W-016
    portion already satisfied by #257).
12. **W-018 — Autonomous contemplation.** After W-008.

This order is a suggestion. The operator decides; the ratchet records.

**Why the v5 reorder:** v4 led with the quick-wins lane (W-011,
W-012, W-015, W-016). All four landed in a single working session
(W-015 → #255, W-016 → #257, W-011+W-012 → #258), so v5 promotes
W-005 (the only remaining mechanical-independent item) to the top of
the queue. After W-005, the ratchet is operator-decision-bound on
W-006/W-010/W-013/W-014/W-019 and L10-bound on the bigger units.
Five total closures since v4: W-004, W-015, W-016, W-011, W-012.

---

## Items deliberately deferred / not in scope

- **EngineIdentity (DNA-analog hash).** Shelved candidate per
  [[project-engine-identity-candidate]]. Trigger to un-shelve: L10
  runtime-model ADR commits to cross-reboot identity verification as
  a sub-question 3 requirement.
- **Audit complete.** All 9/9 layers audited. L8 added W-016/W-017/
  W-018/W-019; L9 confirmed W-011 and W-012 from the verdict-surface
  side without adding new entries (the refusal-reason matrix is a
  consolidation of prior findings, not new debt). Future ratchet
  revisions are wiring-progress driven, not audit-driven.
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

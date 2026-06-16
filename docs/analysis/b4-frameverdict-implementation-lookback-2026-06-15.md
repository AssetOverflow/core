# B4 FrameVerdict — implementation lookback (PR-1..4 + hardening)

**Date:** 2026-06-15
**Scope:** the complete B4 closed-world-verdict substrate (ADR-0222 §10), shipped as one
PR carrying six logical commits, on `feat/b4-frameverdict-complete` rebased onto
`origin/main` @ `af4db1f7` (#786, the suite-speed lane registry).
**Trigger:** mandatory lookback before merging a multi-slice sequence on one architectural
surface (CLAUDE.md "Lookback Review Discipline", triggers 2 + 3).

## Commits audited

| SHA | Slice | What it ships |
|-----|-------|---------------|
| `8be51296` | pre-1 | lift `_basis` -> `generate/epistemic_basis.py` (behavior-preserving; lets `frame_verdict` compute standing without importing `determine`) |
| `fac1c0b1` | PR-1 | `FrameVerdict` sealed type + isolated off-serving text evaluator + INV-31 two-part firewall + `_basis` lift wiring |
| `22b8a540` | PR-2 | text closed-world (CWA) eval lane + disjoint truth-table oracle (INV-25/27) |
| `1a0e8cd8` | PR-3 | perception changed-slot falsification adapter (ADR-0211 integration) |
| `0244703b` | PR-4 | default-dark `FrameVerdict -> response_governance` disposition (the only lawful surface path) |
| `f8fab528` | hardening | folds in the 4-skeptic adversarial-review findings (see §Hazards) |

**Net:** 18 files, **+1728 / −7** vs `origin/main`. The only deletions are 7 lines in
`generate/determine/determine.py` (the `_basis` body moved out; the three INV-30
`Determined(answer=True)` sites are byte-unchanged).

## Verification state

- The 4 dedicated B4 test files (`test_frame_verdict`, `test_frame_verdict_text_cwa_lane`,
  `test_frame_verdict_perception_adapter`, `test_response_governance_frame_verdict`) **+** the
  full `tests/test_architectural_invariants.py` (INV-30 and INV-31 included): **128 passed**
  on the rebased base.
- Fast smoke lane (`-m "not quarantine and not slow"`): green (no new reds vs the known
  pre-existing baseline — those only surface under `--suite full`).
- CWA lane: 12 correct / 0 wrong; cases SHA pinned
  `519e9b0de4bf43a5766593f61107b74dc4debb619e53dbba9011d0674bc8c1d4`; independent oracle
  agrees on all 12; 4000-formula differential fuzz: 0 oracle-vs-engine mismatches.

---

## Findings

### Solid (verified non-vacuous)

- **INV-30 untouched.** `determine.py` still constructs exactly three `Determined(answer=True)`
  sites and references no `FrameVerdict`. The `_basis` lift removed a body, not a site; INV-30a/b/c
  remain green. The open-world gear is still True-only — no `answer=False`, ever.
- **entailed_false is provably positive-refutation-only.** Text path: `REFUTED` (ROBDD
  refutation) is the *sole* route; `UNKNOWN -> UNDETERMINED`, `INCONSISTENT_PREMISES ->
  CONTRADICTION`, malformed -> `SCOPE_BOUNDARY`. Perception path: only a `residual.changed` slot
  (a positively observed declared-expected contradiction) reaches `entailed_false`; missing
  (absence), unexpected (over-observation), and whole-frame-missing all refuse. The construction
  invariant (`__post_init__`) rejects a generic `FALSIFIED`, a `None` kind, a producer/outcome
  mismatch, and an empty `proof_sha256`. Mutation tests trip each.
- **INV-31 firewall is real.** A3 transitive-import containment independently recomputed: the
  closures of `chat.runtime`, `session.context`, `vault.store` (159 / 36 / 29 modules) reach
  neither `generate.frame_verdict` nor `core.response_governance.frame_verdict`. A1 (determine
  ↛ frame_verdict), A2 (single construction site), B1 (`determine(ClosedFrame, None)` refuses at
  the eligibility gate, ctx untouched), B2 (forged/untagged object -> `TypeError`) all hold
  non-vacuously, each with its own mis-root anchor.
- **Default-dark holds.** `git diff` touches zero existing governance/serving files;
  `core/response_governance/__init__` imports only `.policy`; `disposition_for_frame_verdict`
  has zero production callers. The STRICT open-world path is byte-identical.
- **Replay determinism.** `trace_hash` / `proof_sha256` are order-invariant under premise
  reordering (built from ROBDD canonical keys, not order-sensitive `premise_keys`) and stable
  across processes under randomized `PYTHONHASHSEED` (sha256_json `sort_keys=True`).

### Hazards found by adversarial review — ALL fixed in `f8fab528`

1. **(major) Perception negation was not frame-gated.** The text evaluator refuses OPEN /
   undeclared-closure (-> `SCOPE_BOUNDARY`); the perception adapter did not, so a
   `PERCEPTION + OPEN + changed-slot` input produced `entailed_false` with
   `world_assumption=OPEN` — a verdict that self-contradicts the type's own invariant. **Fix
   (defense in depth):** the perception adapter now gates OPEN / `not closure_declared` ->
   `SCOPE_BOUNDARY` (graceful), **and** `FrameVerdict.__post_init__ §(0)` raises on
   `ENTAILED_FALSE + OPEN` — a *frame-general* structural backstop that fires for any producer
   (text, perception, or future modality) that forgets the gate. New parametrized perception
   test covers OPEN / undeclared / both.
2. **(minor) `entailed_true` was admissibility-asymmetric.** Only `entailed_false` was
   proof-gated at construction, so a committed "Yes." leaned entirely on the INV-31-A2 allowlist.
   **Fix:** symmetric `__post_init__ §(2)` requires a positive entailment/support proof
   (`proof_chain.entail/ENTAILED` or `sensorium.falsification/SUPPORTED`), non-empty sha, and no
   refutation kind. A mutation test now trips a forged positive.
3. **(minor) A2 detector blind to factory construction.** The matcher keyed only on
   `FrameVerdict(...)` call-name. **Fix:** it now also flags `FrameVerdict.<factory>(...)`
   classmethods and module-qualified `mod.FrameVerdict(...)`; non-vacuity test extended.
4. **(minor) A3 fired on the adapter only indirectly.** It barred `generate.frame_verdict`, not
   the lowering-to-serving module. **Fix:** `core.response_governance.frame_verdict` is now in the
   barred-prefix set directly, plus a new test proving the `response_governance` `__init__` stays
   default-dark (does not re-export the adapter).
5. **(minor) Oracle grammar is a strict SUBSET of `proof_chain.entail`** (it mis-parses `false`
   as a free atom; rejects `|`, `<->`, `&&`, keyword ops, unicode). **Fix:** docstring corrected;
   a lane guard now requires every *decided* `cases.jsonl` formula to stay inside the subset, so a
   future out-of-subset case fails the SHA-add review with a clear message rather than as a
   confusing engine-vs-oracle red. (SCOPE_BOUNDARY garbage is exempt — both solvers reject it.)

### Recorded gaps (deferred honestly, NOT faked — per CLAUDE.md "do not fake an obligation")

- **`dataclasses.replace(fv, ...)` is not flagged by the A2 construction detector.** A blanket
  `replace(...)` match would false-positive on every other dataclass tree-wide, and the
  first-arg type is only known by inference. No such call exists in non-test source today. The
  obligation is recorded in `_frame_verdict_constructions`' docstring and here: **the deferred
  closed-world serving-wiring PR MUST add a typed-replace guard before it lands** (lookback
  "build the defensive refusal NOW"). This is the one structural A2 hole; it is latent, not live.
- **`__post_init__` admissibility is construction-time only.** A post-construction
  `object.__setattr__` bypass on a frozen+slots instance is out of scope (not reachable from any
  input). Documented in `__post_init__`: any future codec / deserialization path must
  re-construct through `build_frame_verdict`, never reassign fields.

### Documentation / drift

- The implemented type shapes (`PositiveRefutationKind` enum; `ClosedFrame.closure_declared` +
  `source`/`provenance`; `FrameVerdict.provenance`) are a *consistent refinement* of ADR-0222 §3's
  illustrative block, adopted from the operator master brief. The ADR's invariants (§5.1 verdict
  table, §8 INV-31, the positive-refutation discriminator from §14) are unchanged. **No ADR
  amendment required**; the §3 block was explicitly illustrative.
- **One ADR note worth filing (non-blocking):** ADR-0222 §3 should gain a one-line statement of
  the symmetric `entailed_true` admissibility invariant and the OPEN-world structural backstop,
  since both are now load-bearing construction guards (currently only `entailed_false` is named in
  the ADR). Tracked here; not gating this PR.

### Cross-slice consistency

- The single construction funnel (`_construct.build_frame_verdict`) means both the text evaluator
  and the perception adapter share one trace-hash recipe and one admissibility gate — no
  divergence between modalities. The disposition adapter maps all five verdict kinds through the
  *existing* `choose_served_disposition` table (no parallel disposition object); `entailed_false`
  is a committed grounded "No." at `INFERRED + DisclosureClaim.NONE`, never VERIFIED/EVIDENCED,
  never a new `LimitationKind`.

## Global red-line ledger (B4 master brief)

| Red line | Status |
|----------|--------|
| `determine()` stays open-world True-only; no `answer=False`; absence never False | ✅ INV-30 green |
| `FrameVerdict` distinct from `Determined`; no closed-world result masquerades as open-world | ✅ distinct type + INV-31 A1/B1 |
| No stochastic fallback / lexical guessing / ANN / similarity | ✅ composes ROBDD + ADR-0211 only |
| No default runtime/chat/session/vault wiring | ✅ default-dark; A3 + zero callers |
| All closed-world serving passes through `response_governance` | ✅ sole adapter path |
| Every PR keeps INV-30 green; every post-PR-1 keeps INV-31 green | ✅ full INV suite passes |
| ProofWriter-OWA floor stays green | ✅ untouched (no `generate.derivation` import) |
| `wrong_total == 0` wherever capability-index is touched | ✅ CWA lane 12/0; not wired to serving |
| If an obligation can't be made non-vacuous, defer it explicitly | ✅ two recorded gaps above |

## Conclusion

No live hazard remains. The one major finding (OPEN-world perception negation) is closed two
ways; the four minor findings are closed; two structural gaps are deferred with an explicit
guard obligation on the future serving-wiring PR. The substrate is sealed and off-serving —
nothing here can widen runtime behavior until the explicitly gated serving PR (which must
discharge the recorded `dataclasses.replace` obligation first).

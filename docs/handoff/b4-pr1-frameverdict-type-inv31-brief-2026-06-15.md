# Brief — B4 PR-1: FrameVerdict type + isolated evaluator + INV-31 firewall (gated)

> **Red line.**
> PR-1 is **not** a closed-world serving feature. It introduces a **sealed type +
> isolated evaluator** and the **INV-31 firewall** only. **No** runtime caller, **no**
> response-governance integration, **no** session/vault/chat wire, **no** perception
> adapter, **no** CWA lane, **no** prose lowering. The evaluator exists for tests and
> future PR-2/PR-3 callers — never for `chat`/`runtime`/`session`/`governance`.

**Gate:** ADR-0222 ratified (#780) ✅ + ProofWriter-OWA floor landed (#779) ✅ → PR-1 is
**authorized**. It ships the type **with** INV-31, never after. **No serving wire, no
lane, no perception adapter, no governance integration** (those are PR-2/3/4).

**Open with:**

```
git fetch origin main && git worktree add ../core-frameverdict-pr1 origin/main -b feat/b4-pr1-frameverdict-type
```

## Why

ADR-0222 §10 PR-1 is the *first and only* implementation step authorized now: the
closed-world `FrameVerdict` envelope + its text-frame **isolated evaluator** + the
**INV-31** two-part firewall that makes a closed-world `False` unable to reach the
open-world runtime. It composes existing sound producers (`proof_chain.entail`), adds
**no** `answer=False`, and leaves `determine.py` untouched.

## Scope (exactly this)

1. **Lift `_basis` → `generate/epistemic_basis.py`** (ADR §3 note, §8 A3). Move `_basis`
   **byte-identically** out of `generate/determine/determine.py` into a new shared module;
   `determine.py` imports it from there (no behavior change — its three `Determined` sites
   and INV-30 stay intact). This removes the open/closed package coupling so `frame_verdict`
   can import `_basis` without importing `determine`.

2. **New package `generate/frame_verdict/`** with the §3 types verbatim:
   - `FrameKind` / `WorldAssumption` / `FrameVerdictKind` enums.
   - `ClosedWorldProof` (incl. `positive_refutation_kind`).
   - `FrameVerdict` **with the `__post_init__` admissibility invariant** — `entailed_false`
     requires `(producer, outcome, positive_refutation_kind)` =
     `proof_chain.entail/REFUTED/robdd_refutation` **or**
     `sensorium.falsification/FALSIFIED/perception_changed_slot`, and a non-empty
     `proof_sha256`.
   - `ClosedFrame` (§3.1).
   - `evaluate_frame_verdict(frame: ClosedFrame, query: str) -> FrameVerdict` (§4) — the
     **isolated evaluator**, the **only** `FrameVerdict` constructor. **Text frame only.**
     Treat `frame.propositions` + `query` as propositional-formula strings (the existing
     `entail.py` grammar — prose→proposition lowering is **PR-2**), delegate to the
     **unchanged** `evaluate_entailment_with_trace(premises, query)`, and map per the §5.1
     table:

     | `entail` outcome | verdict |
     |---|---|
     | ENTAILED | `entailed_true` |
     | REFUTED | `entailed_false` (proof: `proof_chain.entail` / `REFUTED` / `robdd_refutation`; `proof_keys` = conjunction / query / refutation_check keys) |
     | UNKNOWN | `undetermined` |
     | REFUSED(INCONSISTENT_PREMISES) | `contradiction` |
     | REFUSED(OUT_OF_REGIME_OR_MALFORMED) | `scope_boundary` |

     `world_assumption == OPEN`, a missing closure declaration, or `frame_kind != TEXT` →
     **`scope_boundary`** (never `entailed_false`). Perception (`frame_kind = PERCEPTION`)
     is **PR-3** → `scope_boundary` here.
   - **Serialization:** `trace_hash` and `proof_sha256` via the existing `sha256_json`
     (canonical, order-invariant); `basis` via the lifted `_basis`.

3. **INV-31 in `tests/test_architectural_invariants.py`** (ADR §8) — lands **with** the type:
   - **Part A (import containment).** A1: `determine.py` neither imports nor constructs
     `FrameVerdict`. A2: `FrameVerdict` (and every alternate constructor — factory /
     `dataclasses.replace` into `verdict`) is built only inside an **exact**
     `ALLOWED_FRAME_VERDICT_SITES` frozenset; **the construction scan must include `evals/`**
     (INV-30's walk excludes it). A3: `generate/frame_verdict` is unreachable from the
     **transitive** first-party import closure of each spine file (`chat/runtime.py`,
     `session/context.py`, `vault/store.py`) — reuse INV-27's
     `_transitive_first_party_imports`; forbid re-export through `generate/proof_chain`; the
     scan is **directional** (spine ↛ frame_verdict; frame_verdict → entail / epistemic_basis
     is sanctioned).
   - **Part B (data-flow).** B1: feeding a `ClosedFrame`-derived provenance into `determine()`
     raises/refuses. B2: the open-world render/disposition path type-rejects a `FrameVerdict`
     absent an explicit closed-world tag.
   - **Six non-vacuity anchors** (§8 table) — each fails loudly under its own violation,
     mirroring INV-30b / INV-30c.

## Acceptance gates (ADR §12 — the obligations PR-1 discharges)

- §12.1 — each of the 6 INV-31 anchors **meaningfully fails** (a fixture-injected violation
  per scan); not one fixture covering all.
- §12.2 — `entailed_false` is proof-backed: a mutation test constructs
  `FrameVerdict(ENTAILED_FALSE, …)` with a mismatched/None proof (incl. a **generic
  FALSIFIED with `positive_refutation_kind=None`**) → asserts `ValueError`.
- §12.3 — inconsistent premises → `contradiction`, **never** `entailed_false`.
- §12.4 — absence never yields `entailed_false`: a text `UNKNOWN` query → `undetermined`;
  `OPEN` / unlicensed frame → `scope_boundary`.
- §12.5 — replay determinism: identical `trace_hash` across two runs **and** under premise
  reordering.
- INV-30 still exactly its pinned `Determined` count, all `answer=True`; ProofWriter-OWA
  floor green; full smoke green.

## Do NOT

- touch `generate/determine/determine.py` except the one-line `_basis` import.
- add any `answer=False` / `Determined` site anywhere.
- wire `evaluate_frame_verdict` into `chat/runtime`, the session loop, governance, or the vault.
- build a CWA lane (PR-2), a perception adapter (PR-3), or a disposition/renderer mapping (PR-4).
- implement prose→proposition lowering or NAF.

## Budget / verify

~45–60 tool calls. **Run in the worktree with `python -m pytest`** (the `core` script
resolves to the main checkout). Verify: the new `frame_verdict` tests +
`tests/test_architectural_invariants.py` (INV-30 **and** INV-31) +
`tests/test_proofwriter_owa_lane.py` + `tests/test_determine_*` (the `_basis` lift is inert)
+ full smoke.

## Honest flags for the operator

- **B2 anchor scoping.** The open-world disclosure path isn't wired to take a `FrameVerdict`
  until PR-4. Install B2 as a **pre-emptive defensive guard** (the render/disposition entry
  type-rejects a `FrameVerdict`) and make its anchor non-vacuous against that guard. **If B2
  cannot be made meaningfully-failing without PR-4's wiring, do NOT ship a vacuous anchor** —
  flag it, scope B2 to PR-4, and add a one-line ADR-0222 §8 amendment noting the deferral.
  A1/A2/A3/B1 are the firm PR-1 firewall.
- **Propositional-input contract.** PR-1's isolated evaluator consumes propositional-formula
  strings; document this on the evaluator so PR-2's prose front-end has a clean seam.
- **EpistemicState / governance is out of scope** — the `FrameVerdict` carries `basis` only;
  the `INFERRED` / `DisclosureClaim.NONE` mapping (§7 / §14) is PR-4.

## Ratified design choices this brief locks in

- `_basis` lift **first**, behavior-preserving.
- `FrameVerdict` **distinct** from `Determined` (no `answer` field; INV-30 scan can't match it).
- `entailed_false` **requires** `positive_refutation_kind`.
- a **generic `FALSIFIED` cannot** prove false.
- `OPEN` / missing closure / non-`TEXT` frame ⇒ `scope_boundary`.
- perception frame ⇒ `scope_boundary` in PR-1.
- **INV-31 ships with the type**, not later.
- the **B2 data-flow anchor may be deferred** if it cannot be made non-vacuous in PR-1.

---

**Source of truth:** `docs/decisions/ADR-0222-frame-verdict-closed-world.md` (ratified #780).
Where this brief and the ADR ever disagree, the ADR wins — open an amendment rather than
diverging silently.

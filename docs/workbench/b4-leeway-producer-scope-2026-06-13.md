# B4 leeway producer — engine-side scope (2026-06-13)

Status: **scoping** (Shay reviews; not yet built). Predecessor:
`b4-leeway-feasibility-gate.md` (the B4a nullable `LeewayEvidence` read model
that renders honest absence today). This brief answers the gate's open question:
*what engine-owned producer populates `LeewayEvidence`, and where.*

## The finding (verified against source)

The leeway decision **already exists** in the serving path — it is computed and
then **discarded**, never threaded to the turn result. That, plus the
import-firewall (the workbench may not import `core.reliability_gate` /
`generate.derivation`), is the entire reason B4 is blocked.

Concretely:

- **The decision is made at `chat/runtime.py::_surface_estimate`** (≈ line 1057).
  At that point the runtime holds:
  - `accrual.license` — a real `core.reliability_gate.LicenseDecision`
    (`class_name, action, checker, measured, required, ratio, licensed`),
    produced by `generate/determine/estimation_license.py::serve_license(predicate)`
    (`license_for(tally, Action.SERVE, Ceilings.default())`, or `None` when the
    converse-class is absent from the ratified ledger).
  - `policy` — a `core.response_governance.ReachPolicy`
    (`level, admissible_states, rationale, license_ratio`) from
    `govern_response(...)`.
  - the disclosed surface (`shape_surface` adds the `[approximate]` prefix).
- **It is discarded.** The only governance residue on the response is
  `reach_level=policy.level.value` (a string). `accrual.license` (the class, θ,
  ratio) and the disclosure semantics never leave the function.
- **`CognitiveTurnResult` carries no governance/leeway/license field** (grep:
  empty). So nothing downstream — including the workbench — can see it.
- **`workbench/api.py::_run_chat_turn` never sets `leeway_evidence`** (grep:
  empty) → the workbench `ChatTurnResult.leeway_evidence` defaults to `None` →
  the B4a UI shows "No leeway evidence recorded."

So this is genuinely **engine work**: the producer must live where the
`LicenseDecision` is made (the serving path), attach a plain record to the
result, and let the workbench map it. The workbench cannot reach across the
firewall to compute it.

## The data is already a near-perfect match

`LicenseDecision` + `ReachPolicy` map almost one-to-one onto the B4a
`workbench/schemas.py::LeewayEvidence` tuple
(`class_name, license, theta, claim_disclosure, source_digest, calibration_evidence_ref`):

| `LeewayEvidence` field | Engine source |
|---|---|
| `class_name` | `LicenseDecision.class_name` (the `converse_class_name(predicate)`); `"none"` when no estimate was attempted |
| `license` | `SERVE` if a licensed `Action.SERVE`; `PROPOSE` if a licensed `Action.PROPOSE`; `"blocked"` if a decision exists but `licensed == False`; `"unknown"` if no decision (no ratified tally) |
| `theta` | `LicenseDecision.required` (the θ ceiling — `0.99` for SERVE) |
| `claim_disclosure` | `"approximate"` when `ReachLevel.APPROXIMATE`; `"none"` when `STRICT` (no latitude granted); `"proposal_only"` in PROPOSE contexts; `"verified"` **reserved** (see open Q3) |
| `source_digest` | sha256 of the ratified `ClassTally` bytes the decision read — provenance of the calibration evidence |
| `calibration_evidence_ref` | `class_name`, resolvable to the workbench Calibration subject (`/calibration?inspect=<class>`) |

## Proposed seam

1. **Engine (the producer).** Add an engine-owned `@dataclass(frozen=True)`
   `LeewayRecord` to `core/cognition/result.py` (NOT the workbench schema — the
   engine must not import workbench). Populate it at the `govern_response` seam
   in `chat/runtime.py`. It carries the six fields above, derived from the
   `LicenseDecision` + `ReachPolicy` the runtime already computes.
2. **Result.** Thread `leeway: LeewayRecord | None` onto `CognitiveTurnResult`
   (additive, default `None`), the same way `versor_condition` / `trace_hash`
   already ride the result.
3. **Workbench (thin mapping).** `workbench/api.py::_run_chat_turn` maps
   `result.leeway` → `workbench/schemas.py::LeewayEvidence`
   (`leeway_evidence=_leeway_from_result(result)`). This is a pure projection of
   a plain dataclass off the result — **no `reliability_gate` import**, so the
   firewall holds. The journal already persists `leeway_evidence`; the B4a UI
   already renders it. **No workbench schema or UI change is required** — only
   the mapping is wired.

## Two honest layers

The "engine earns the right to guess" path (`APPROXIMATE`) is **off by default**
and only fires on a converse-guess estimate whose predicate-class holds a
ratified `SERVE` license. So most served turns are `STRICT`. The producer should
be honest at both levels:

- **Layer 1 — governance-level (every governed turn, STRICT today).** Emit a
  truthful "no latitude granted" record: `level=strict`, `license` ∈
  {`blocked`, `unknown`}, `claim_disclosure=none`, `theta` = the SERVE ceiling
  it would have had to clear. This **immediately unblocks** the B4 UI from "No
  leeway evidence recorded" to "STRICT governance — no latitude; fully-grounded
  commits only," which is itself the impressive discipline (the engine refuses
  to widen). Fully additive; byte-identical serving.
- **Layer 2 — earned-leeway (the real B4 story).** When `_surface_estimate`
  widens to `APPROXIMATE` because `serve_license(predicate)` returned a licensed
  `SERVE`, emit the full record: real `class_name`, `license=SERVE`,
  `theta=0.99`, `claim_disclosure=approximate`, the ratio. This is where a
  reviewer sees *which class earned latitude, at which θ, with the `[approximate]`
  disclosure* — the B4 intent verbatim.

## Non-negotiable constraints (CLAUDE.md)

- **Observational, not authorizing.** The producer only *reports* the decision
  the runtime already made. It must never call `license_for` itself, mutate
  `Ceilings`, or alter the served surface. Ceilings stay human-set.
- **`wrong == 0` untouched.** `STRICT` stays the load-bearing default and
  byte-identical; the record is evidence-only. A licensed `APPROXIMATE` estimate
  is already a *disclosed* `[approximate]` surface (so a wrong estimate is a
  disclosed wrong, not a silent one) — the producer adds no new commit path.
- **Firewall.** Engine emits a plain dataclass; the workbench maps it. The
  workbench gains no `reliability_gate` / `generate.derivation` import.
- **Determinism.** `LicenseDecision` is already pure/deterministic; the
  `source_digest` must hash the ledger bytes, not a timestamp.

## Minimal first PR

Layer 1 only — smallest safe slice that clears the gate:

1. `LeewayRecord` dataclass on `core/cognition/result.py`; `leeway` field on
   `CognitiveTurnResult` (default `None`).
2. Populate it for **every governed turn** at the `chat/runtime.py` seam
   (STRICT-honest; the `_surface_estimate` widening path fills the full record).
3. `workbench/api.py` mapping `result.leeway` → `LeewayEvidence`.
4. Tests (non-vacuous): a STRICT turn yields `license=blocked/unknown`,
   `claim_disclosure=none`, surface unchanged; a constructed `APPROXIMATE` turn
   (licensed-class fixture) yields `license=SERVE`, `claim_disclosure=approximate`;
   the record never alters the served surface; `source_digest` reproducible.

Layer 2's earned path is exercised by the same seam; the only added cost is a
fixture with a ratified SERVE-licensed converse-class to drive `APPROXIMATE`.

## Open questions for Shay

1. **First-PR scope:** Layer 1 only (unblocks the UI, fully safe, no behavior
   change), or Layer 1 + the Layer 2 earned-path test (needs a SERVE-licensed
   fixture)? Recommendation: **ship Layer 1, then Layer 2 as a follow-up** so the
   UI unblocks on a zero-behavior-change PR.
2. **Record home:** `LeewayRecord` on `CognitiveTurnResult` (clean for the
   workbench seam) vs. a turn-event/telemetry channel? Recommendation: on the
   result, symmetric with `versor_condition` / `pipeline_record`.
3. **`claim_disclosure` for STRICT-grounded commits:** `"none"` (no latitude was
   needed) vs. `"verified"`. Recommendation: **`"none"`** — `VERIFIED` is a
   RESERVED `EpistemicState` (canonical-comparison pass not built), so claiming
   `"verified"` leeway would over-state. `level=strict` already carries the
   "fully grounded" story.
4. **`calibration_evidence_ref` format:** raw `class_name`, or a resolvable
   subject URL (`/calibration?inspect=<class>`)? Recommendation: store the
   `class_name`; let the UI build the link (keeps the engine UI-agnostic).

## Why this finally moves the blocker

B4a deliberately shipped a *nullable* read model and gated the rest precisely
because the producer is engine-side and the decision wasn't on the result. This
brief shows the decision already exists at a single, well-understood seam, maps
cleanly onto the existing schema, and unblocks with an additive, byte-identical
Layer-1 PR. No new schema, no new UI, no firewall breach.

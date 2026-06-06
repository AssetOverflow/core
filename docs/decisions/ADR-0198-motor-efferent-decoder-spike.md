# ADR-0198: Motor as Efferent Modality — Protocol Gap & Governance (Design Spike)

**Status:** Accepted (design spike) — Gap A protocol change + a baseline efferent gate have landed; the §3 verdict-lowering and the motor compiler/decoder remain deferred. See **Implementation Status** below.
**Date:** 2026-05-31
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `sensorium/protocol.py`, `sensorium/registry.py`, `packs/motor/` *(future)*, governance packs (ADR-0029/0033/0036/0037)
**Depends on:** ADR-0013 (Sensorium Multimodal Protocol), ADR-0017 (Agency Scope), ADR-0018 (Tool-Use Scope)
**Relationship to vision:** intentionally runs **in parallel** with `vision_core_v1` implementation (ADR-0197 / vision-compiler-spec) because it may force a `sensorium/` protocol change, and that change is cheaper to land before vision concrete sets.

---

## Implementation Status (reconciled 2026-06-04; amended 2026-06-06)

**Gap A has landed.** `ModalityRegistry.decode(pack_id, mv, *, authority)` with a required, never-optional `AuthorityToken`, plus a baseline `DefaultEfferentGate` (`sensorium/efferent.py`, PR #541). The §1.2 Gap B ordering is **proven**: `tests/test_efferent_gate.py::test_registry_uses_default_efferent_gate_before_decoder` asserts `decoder.calls == 0` on refusal — the gate refuses *in the manifold*, before any command is formed. Traces are hash-only (no `mv`, no ndarray/bytes).

**2026-06-06 amendment — the §3 verdict-enforcing *gate mechanism* has landed (still fail-closed, still no decoder).** `sensorium/efferent.py` now ships a concrete `VerdictEnforcingEfferentGate` (`enforces_action_verdicts=True`) plus `MotorActionIntent` (a hash-only semantic predicate lowering — *not* an actuator command) and `lower_motor_action_intent`. The gate admits only when authority carries the `decode:<pack_id>` capability AND a present-and-admitted `ActionVerdictRecord` covers each of `(safety, ethics, tool_scope)` for that exact intent hash; empty/missing/failed verdicts refuse before the decoder runs (`tests/test_efferent_gate.py::test_verdict_enforcing_gate_*`). This closes item 1's "the §3 verdict-lowering gate must be built" — the *gate* exists. What remains deferred: (a) the §3 **lowering itself** — the gate validates *caller-supplied* verdict coverage; it does not yet derive those verdicts from the ADR-0029/0033/0036/0037 governance packs; (b) the motor compiler/decoder (every shipped adapter is `decoder=None`); (c) ratification by the dedicated motor governance ADR, now drafted as **[ADR-0216](ADR-0216-motor-verdict-lowering.md)** (Status: Proposed). No physical motor decode is authorized.

**Deferred — blocking obligations before any motor decoder mounts:**

1. **§3 verdict-lowering is NOT implemented — but is now enforced fail-closed.** `DefaultEfferentGate` admits on capability-token + `(32,)` vector-shape only (`enforces_action_verdicts` is `False`); it does **not** lower the decoded motor versor into the safety/ethics pack verdicts of ADR-0029/0033/0036/0037. To keep §1.2 Gap B from silently degrading, `ModalityRegistry.decode`/`decode_batch` now **refuse fail-closed** any emission through a gate whose `enforces_action_verdicts` is False, unless an explicit `allow_unverified_efferent=True` sandbox opt-in is set (tests only). A real motor decoder therefore *cannot* emit through the capability-only gate — the §3 verdict-lowering gate must be built and installed first. Proven by `tests/test_efferent_gate.py::test_registry_fails_closed_for_actuating_decode_through_capability_only_gate` (the decoder never runs) and `::test_registry_admits_decode_through_verdict_enforcing_gate`. Implementing the §3 lowering itself remains deferred behind the dedicated motor governance ADR (item 3).
2. **The motor compiler/decoder itself remains out of scope** (per §5).
3. **A dedicated motor governance ADR** ratifying the §3 lowering against ADR-0029/0033/0036/0037 remains a prerequisite (per §5). Drafted 2026-06-06 as **[ADR-0216: Motor Verdict Lowering Prerequisite](ADR-0216-motor-verdict-lowering.md)** (Status: Proposed) — it names the lowering pipeline and its Non-Goals (no actuator driver, no robot interface, no trajectory executor, no sandbox opt-in on a physical path) and must be Accepted before any motor decoder mounts.

## 1. Why motor is not "just another modality"

Every modality landed so far is **afferent**: signal comes *in*, crosses the `ProjectionHead` boundary, becomes a `(32,)` versor. Motor is **efferent**: meaning leaves the manifold and becomes action in the world. The protocol already anticipates this asymmetry — `sensorium/protocol.py` defines:

```python
@runtime_checkable
class SurfaceDecoder(Protocol[S]):
    modality: Modality
    def decode(self, mv: np.ndarray) -> S: ...
    def decode_batch(self, mvs: np.ndarray) -> list[S]: ...
```

and `ModalityPack` already carries a `decoder: SurfaceDecoder | None` slot. So the *type-level* substrate is ready. But the spike's finding is that the **runtime substrate is not**, in two concrete ways.

### 1.1 Gap A — the registry has no efferent path

`ModalityRegistry` (`sensorium/registry.py`) implements `mount`, `get`, `project`, `project_batch`. There is **no `decode` / `decode_batch`**. `project()` refuses a closed gate and validates output shape; nothing analogous exists for emission. A motor pack could be *mounted* today, but there is no governed call site through which a `(32,)` versor could become an action. Adding one is a `sensorium/` protocol change — the thing this spike exists to surface before vision implementation locks the layer.

### 1.2 Gap B — the input mount-gate does not transfer to output

For afferent modalities the mount-time gate is `verify_unitarity` — a property of the *projection's construction* (`V·reverse(V) = ±1`). It is correctly run once, at mount, never in the hot path.

**An efferent gate cannot be mount-time only.** Whether an action is admissible depends on the *content of the decoded command*, not on whether the decoder was built correctly. A decoder can be perfectly unitary-inverse and still emit an action that must be refused. Therefore motor needs **two** gates, not one:

| Gate | When | Checks | Analog |
|---|---|---|---|
| **Decoder validity** | mount-time | decoder is well-formed; round-trips within tolerance on a probe (`project(decode(mv)) ≈ mv`) | `verify_unitarity` |
| **Efferent admissibility** | **runtime, per-decode** | the *decoded action* is within authority + passes safety/ethics verdicts before it leaves the boundary | **(new — no afferent analog)** |

Gap B is the load-bearing governance finding: **output gating is per-action, afferent gating is per-mount.** Any design that reuses `verify_unitarity`'s shape for motor is wrong.

## 2. Proposed protocol change (minimal, additive)

Add an efferent path to `ModalityRegistry` that mirrors `project()`'s refusal discipline and adds the runtime admissibility gate:

```python
def decode(self, pack_id: str, mv: np.ndarray, *, authority: AuthorityToken) -> Any:
    pack = self.get(pack_id)
    if not pack.gate_engaged:
        raise RuntimeError(f"Pack '{pack_id}' gate is not engaged.")
    if pack.decoder is None:
        raise RuntimeError(f"Pack '{pack_id}' has no SurfaceDecoder.")
    # NEW: runtime efferent admissibility — BEFORE any surface action is produced.
    verdict = self._efferent_gate.admit(pack_id, mv, authority)   # §3
    if not verdict.admitted:
        raise EfferentRefusal(pack_id, verdict)                    # fail closed
    return pack.decoder.decode(mv)
```

Notes:
- `gate_engaged` / `decoder is None` refusals mirror `project()` exactly — no new gating *machinery* there, just the symmetric method.
- `authority: AuthorityToken` is required, never optional — there is no unauthenticated emission path. This is the wiring point for ADR-0017 (agency scope) and ADR-0018 (tool-use scope).
- The admissibility check runs **before** `decoder.decode` — the boundary refuses *in the manifold*, not after a command has been formed.

## 3. The efferent gate reuses existing governance — it is not a new bespoke checker

The repo already has the verdict machinery this needs; the spike's recommendation is to **route decoded-action admissibility through it**, not invent a parallel system:

- **ADR-0029 (safety packs) / ADR-0036 (safety-refusal policy)** — the decoded action is checked against safety packs; refusal is the existing fail-closed path.
- **ADR-0033 (ethics packs) / ADR-0037 (per-predicate ethics refusal)** — per-predicate ethics verdicts apply to the action predicate, not to text.
- **ADR-0017 / ADR-0018** — authority and tool-use scope bound *what* the `AuthorityToken` may authorize.

`_efferent_gate.admit()` is therefore a thin adapter that lowers a `(32,)` motor versor into the action predicate(s) those packs already evaluate, collects their verdicts, and fails closed on any refusal or on absent authority. The novel surface is the *lowering + fail-closed composition*, not the ethics logic.

## 4. Open questions to red-line (this is a spike — these are the decisions, not conclusions)

1. **`S` for motor.** Is the surface type a single action command, a bounded trajectory, or a parameterized skill invocation? This determines whether `decode` is one-shot or streaming, and whether a proprioceptive feedback loop is in-scope for v1.
2. **Feedback is afferent.** Proprioception/result-of-action re-enters as a *sensor* modality. Decision: is the loop **composed at a higher layer** (motor-decode + sensor-encode) or **internal** to the motor pack? Recommendation: composed at a higher layer, to keep `SurfaceDecoder` one-directional and the protocol symmetric.
3. **`AuthorityToken` shape & lifetime.** Per-call, per-session, or capability-scoped? How does it bind to ADR-0017/0018 scopes?
4. **Decoder-validity round-trip tolerance.** What is the mount-time `project(decode(mv)) ≈ mv` tolerance, and is round-trip even required for actions that are intentionally lossy?
5. **Control rate.** Does v1 emit at a fixed control rate (and therefore need a clock/barrier story like the compilers), or is it event-driven one-shot? Recommendation: event-driven one-shot in v1; rate-controlled emission deferred.
6. **Does the protocol change touch the CRDT substrate at all?** Efferent actions are *emitted*, not stored as afferent deltas — but their *occurrence* is trace evidence. Decision: motor writes a `TurnEvent` emission record (hashes + authority + verdict), never a Vault delta. Confirm this keeps ADR-0180 untouched.

## 5. Sequencing recommendation

- This spike's **Gap A protocol change** (the `decode()` method + `AuthorityToken`) should be reviewed **before** `vision_core_v1` PR-2, because it modifies `sensorium/registry.py` / `sensorium/protocol.py` — the layer vision builds against. If accepted, vision implements against the post-change protocol and avoids a later migration.
- The **motor compiler/decoder itself** is explicitly **out of scope** here and must not begin until: (a) this protocol change is merged, and (b) a dedicated **motor governance ADR** ratifies the §3 efferent-gate lowering against ADR-0029/0033/0036/0037. Per the project's order, governance precedes the efferent compiler — not because of politeness, but because §1.2 Gap B means there is no gate to engage until it exists.

## 6. Cross-References

- ADR-0013 — projection boundary; `SurfaceDecoder` / `ModalityPack.decoder` slot this spike activates.
- ADR-0017, ADR-0018 — agency and tool-use scope; the authority model `decode()` requires.
- ADR-0029, ADR-0033, ADR-0036, ADR-0037 — safety/ethics pack verdicts the efferent gate reuses.
- ADR-0197 — vision compiler; runs in parallel and consumes the protocol change this spike proposes.
- `sensorium/protocol.py`, `sensorium/registry.py` — the contracts amended in §2.
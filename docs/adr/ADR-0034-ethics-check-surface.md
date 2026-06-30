# ADR-0034: EthicsCheck — Structural Surface for Ethics-Pack Commitments

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`../ethics_packs.md`](../ethics_packs.md), [`ADR-0032-safety-check-surface.md`](ADR-0032-safety-check-surface.md), [`ADR-0033-ethics-packs.md`](ADR-0033-ethics-packs.md)

## Context

[ADR-0033](ADR-0033-ethics-packs.md) introduced ethics packs as the third pack-layer sibling to identity and safety. The pack contributes `commitment_ids` to the runtime manifold's `boundary_ids`. What ADR-0033 did *not* establish was a structural surface for *evaluating* those commitments per turn — the parallel to `SafetyCheck` (ADR-0032) for the ethics layer.

The argument for adding the surface now (rather than deferring) is the same as it was for safety:

- Commitments without an observation surface decay into labels. The runtime declares it commits to `acknowledge_uncertainty`, but nothing produces a per-turn verdict on whether the commitment held.
- Downstream domain deployments need a registration point to add deployment-specific predicates (`informed_consent_required_before_disclosure` for a medical pack, etc.). Without `EthicsCheck`, the registration point doesn't exist.
- The shape of the surface is already known and tested (SafetyCheck is the precedent). Building the parallel keeps the architecture coherent.

## Decision

`EthicsCheck` is a registry of named predicates, one per commitment id, with defaults for the five v1 commitments. **Observational** at v1: it produces an `EthicsVerdict`; it does not refuse and does not auto-invoke in the turn loop. Wiring verdicts into refusal / re-articulation paths is a future ADR (parallel scope to the future safety-auto-invocation ADR).

### Why a parallel surface rather than a shared one

The temptation to fold ethics into `SafetyCheck` is real — same shape, same registry pattern, same fallback semantics. We resist it for the same reason ethics is a separate pack layer:

- Safety verdicts are **floor violations**. A safety violation is a system fault.
- Ethics verdicts are **pledge failures**. An ethics violation is a deployment-commitment failure, not a fault of the floor.

Conflating them in a single surface would obscure the structural difference. An auditor reviewing a turn benefits from reading two distinct verdicts: "did the floor hold?" and "did the deployment honor its pledges?" One verdict object mixing both flattens that distinction.

### Default predicates per v1 commitment

| Commitment | Runtime-checkable? | What it checks |
|---|---|---|
| `acknowledge_uncertainty` | Yes (when `alignment_score` + `hedge_emitted` supplied) | `alignment < hedge_threshold_soft` requires `hedge_emitted=True` |
| `defer_high_stakes_to_human_review` | Yes (when flags supplied) | `high_stakes_topic=True` requires `recommended_human_review=True` |
| `disclose_limitations` | Yes (when flags supplied) | `grounded_in_evidence=False` requires `disclosure_emitted=True` |
| `no_manipulation` | **No** | aggregate property; enforced by realizer design + review |
| `respect_user_autonomy` | Yes (when flags supplied) | `prescribed_single_answer=True` requires `presented_options_count >= 2` |

`no_manipulation` is the structural analogue of `no_hot_path_repair` in SafetyCheck: an aggregate property that cannot be evaluated from per-turn evidence. A predicate that silently reported `upheld=True` would be the kind of small lie CLAUDE.md forbids. The honest answer is `runtime_checkable=False, upheld=True` with a reason that names where enforcement actually lives.

### API shape

```python
@dataclass(frozen=True, slots=True)
class EthicsContext:
    # acknowledge_uncertainty
    alignment_score: float | None = None
    hedge_threshold_soft: float = 0.65
    hedge_emitted: bool | None = None
    # defer_high_stakes_to_human_review
    high_stakes_topic: bool | None = None
    recommended_human_review: bool | None = None
    # disclose_limitations
    grounded_in_evidence: bool | None = None
    disclosure_emitted: bool | None = None
    # respect_user_autonomy
    prescribed_single_answer: bool | None = None
    presented_options_count: int | None = None

@dataclass(frozen=True, slots=True)
class EthicsCheckResult:
    commitment_id: str
    upheld: bool
    reason: str
    runtime_checkable: bool
    evidence: tuple[tuple[str, str], ...] = ()

@dataclass(frozen=True, slots=True)
class EthicsVerdict:
    pack_id: str
    results: tuple[EthicsCheckResult, ...]   # lex order on commitment_id
    upheld: bool
    violated_commitments: frozenset[str]
    runtime_checkable_count: int

class EthicsCheck:
    def __init__(self, predicates: Mapping[str, EthicsPredicate] | None = None) -> None: ...
    def register(self, commitment_id: str, predicate: EthicsPredicate) -> None: ...
    def check(self, ctx: EthicsContext, ethics_pack: EthicsPack) -> EthicsVerdict: ...
```

Every field on `EthicsContext` is optional; `None` defaults express "caller did not supply this evidence." Predicates over absent evidence return `upheld=True, runtime_checkable=False` — absence of evidence is not evidence of commitment violation. This is the same composability discipline as SafetyCheck.

### Unknown-commitment behavior

When a pack declares a commitment for which no predicate is registered, the verdict records `upheld=True, runtime_checkable=False, reason="no predicate registered for commitment"`. Downstream domain deployments can author packs with novel commitments; the runtime doesn't crash, the audit surfaces the gap.

### Defensive: predicate-result rebinding

Identical to SafetyCheck: if a registered predicate returns a `EthicsCheckResult` whose `commitment_id` doesn't match the slot it was registered under, `EthicsCheck.check` rebinds the id. A buggy predicate should not silently misroute its verdict in audit.

### ChatRuntime integration

`ChatRuntime` instantiates `self.ethics_check = EthicsCheck()` alongside `self.safety_check`. The turn loop **does not** auto-invoke either surface at v1. Callers (audit / logging / future enforcement) call `runtime.ethics_check.check(ctx, runtime.ethics_pack)` whenever they want a verdict.

## Consequences

### Positive

- **Three observation surfaces, three orthogonal verdicts.** Identity (manifold score), safety (boundary verdict), ethics (commitment verdict). An auditor reviewing a turn can answer three distinct questions independently.
- **Honest reporting on `no_manipulation`.** Following the precedent set by `no_hot_path_repair` in SafetyCheck — structural commitments report `runtime_checkable=False` rather than passing silently.
- **Extensible.** Domain packs ship custom predicates that register without touching CORE code.
- **Forward-compatible with auto-invocation.** When the future ADR wires ethics evaluation into the turn loop, the surface won't need to change.

### Negative / risks

- **Observation isn't enforcement.** A violation reported by EthicsCheck at v1 has no automatic consequence. Deliberate (same scope discipline as ADR-0032).
- **Predicate authoring is per-deployment work** for any commitment beyond the five v1 defaults. Domain packs will need their own predicates — documentation in `docs/ethics_packs.md` covers the authoring pattern.
- **Two parallel surfaces (Safety + Ethics) is more API.** Mitigated by the fact that they share *exactly* the same shape; a caller who understands one understands the other. A future "unified verdict bundle" type could group both verdicts for callers that want a single pass.

### Scope limits (explicit non-goals)

- No auto-invocation in the turn loop.
- No refusal / re-articulation wiring.
- No cross-surface aggregation (one unified verdict object combining safety + ethics + identity).
- No structural difference between "violated" and "would-have-been-violated-if-checkable" within the verdict — same as ADR-0032.

## Verification

- `tests/test_ethics_check.py` — 27 tests covering each default predicate (positive / negative / not-supplied paths), the unknown-commitment fallback, custom predicate registration, defensive rebinding, verdict aggregation, and `ChatRuntime` integration.
- Existing pack-layer suites unaffected; combined identity/safety/ethics surface suite is now 108 tests across loader + check surfaces, all green at this revision.
- Cognition (121), teaching (17), runtime (19), smoke (67), formation suites continue green.

# ADR-0032: SafetyCheck — Structural Surface for Safety-Pack Boundaries

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`safety_packs.md`](../safety_packs.md), [`ADR-0029-safety-packs.md`](ADR-0029-safety-packs.md)

## Context

[ADR-0029](ADR-0029-safety-packs.md) established the safety pack as an always-loaded, never-replaceable, fail-closed sibling to identity packs. The pack contributes `boundary_ids` to the runtime manifold; identity packs may add to that set but never remove from it.

What ADR-0029 did *not* establish was a centralized surface for *checking* the boundaries at runtime. Today, the boundaries are enforced (where they are runtime-enforceable) by scattered call sites: source allowlists in the forge, typed exceptions in `generate/exhaustion.py`, the versor-condition halt in `formation/runner.py` and elsewhere. The boundary ids exist as labels; their enforcement is implicit, distributed, and hard to audit.

`IdentityCheck` (ADR-0010) provides a clean precedent: a structural surface that takes a trajectory and a manifold, produces an `IdentityScore` with `deviation_axes`, and lets downstream callers (assembler, refusal paths, logging) decide what to do with the verdict. The natural follow-up is a parallel surface for safety boundaries: `SafetyCheck`.

But the parallel is shape-only, not mechanism. Identity check is geometric — projection onto value axes. Safety boundaries are propositional — each is a different kind of constraint, and several are not even runtime-checkable.

## Decision

SafetyCheck is a registry of named predicates, one per boundary id, with sensible defaults for the five v1 boundaries. It is **observational**: it produces a verdict; it does not refuse. Wiring verdicts into refusal paths is a future ADR.

### What's runtime-checkable

| Boundary | Predicate evaluates | Runtime-checkable? |
|---|---|---|
| `preserve_versor_closure` | `field_state.versor_condition < 1.0e-6` | Yes — direct attribute read |
| `no_fabricated_source` | `cited_source_shas ⊆ allowed_source_shas` | Yes — set membership |
| `no_silent_correction` | `last_refusal_was_typed` flag | Yes — bookkeeping by the runtime |
| `no_identity_override` | `identity_manifold_hash_before == identity_manifold_hash_after` | Yes — hash comparison |
| `no_hot_path_repair` | code-path constraint; no runtime evidence available | **No** — static-analysis + code-review boundary |

The last row is the architecturally interesting one: `no_hot_path_repair` is a *code-path* boundary. It forbids normalization / drift-repair operators in `field/propagate.py`, `generate/stream.py`, and `vault/store.py`. There is no runtime evidence that could prove or disprove it. The honest answer is `runtime_checkable=False`, with `upheld=True` and a clear `reason` explaining that enforcement lives in static analysis and code review.

A predicate that *silently* reported `upheld=True` for `no_hot_path_repair` would be a small lie, exactly the kind of thing CLAUDE.md forbids ("no silent correction"). The structural surface acknowledges what it cannot judge.

### API shape

```python
@dataclass(frozen=True, slots=True)
class SafetyContext:
    field_state: object | None = None              # for versor closure
    versor_halt_threshold: float = 1.0e-6
    cited_source_shas: frozenset[str] = frozenset()
    allowed_source_shas: frozenset[str] = frozenset()
    last_refusal_was_typed: bool = True
    identity_manifold_hash_before: str = ""
    identity_manifold_hash_after: str = ""

@dataclass(frozen=True, slots=True)
class SafetyCheckResult:
    boundary_id: str
    upheld: bool
    reason: str
    runtime_checkable: bool
    evidence: tuple[tuple[str, str], ...] = ()

@dataclass(frozen=True, slots=True)
class SafetyVerdict:
    pack_id: str
    results: tuple[SafetyCheckResult, ...]      # lex order on boundary_id
    upheld: bool                                # all results upheld
    violated_boundaries: frozenset[str]
    runtime_checkable_count: int

class SafetyCheck:
    def __init__(self, predicates: Mapping[str, SafetyPredicate] | None = None) -> None: ...
    def register(self, boundary_id: str, predicate: SafetyPredicate) -> None: ...
    def check(self, ctx: SafetyContext, safety_pack: SafetyPack) -> SafetyVerdict: ...
```

Every field on `SafetyContext` is optional. Predicates over fields the caller didn't populate default to `upheld=True, runtime_checkable=False`. The interpretation is deliberate: SafetyCheck is observational, so absence of evidence is not evidence of violation. This keeps the surface composable — callers populate whatever they have access to, without crashing on what they don't.

### Unknown-boundary behavior

When a pack declares a boundary id for which no predicate is registered, the verdict records `upheld=True, runtime_checkable=False, reason="no predicate registered for boundary"`. This lets downstream deployments add custom boundaries without crashing the runtime, while still surfacing in audit that the runtime had no opinion on them.

A future production deployment can choose to treat unknown-but-declared boundaries more strictly (e.g., `require_runtime_checkable=True` flag that turns unknowns into errors). That's a deployment policy decision, not a surface-shape decision.

### Custom predicate registration

```python
check = SafetyCheck()
check.register("my_robotics_safety_boundary", my_predicate)
```

A robotics deployment ships a custom safety pack with deployment-specific boundary ids and a `SafetyCheck` constructed with predicates for each. The five default predicates remain registered unless explicitly replaced.

### Defensive: predicate-result rebinding

If a registered predicate returns a `SafetyCheckResult` whose `boundary_id` field doesn't match the boundary it was registered under, `SafetyCheck.check` rebinds the result to the correct boundary id. This is defensive — a buggy predicate should not silently associate a verdict with the wrong boundary in audit logs.

### ChatRuntime integration

`ChatRuntime` instantiates `self.safety_check = SafetyCheck()` alongside `self._identity_check`. The turn loop **does not** auto-invoke it at v1. Callers (audit / logging / future enforcement) can call `runtime.safety_check.check(ctx, runtime.safety_pack)` whenever they want a verdict. Auto-invocation is a future ADR with its own scope:

- Where in the turn loop does the check fire (before / after articulation, or both)?
- What does the runtime do with a violation (log, refuse, escalate)?
- How does refusal interact with ADR-0028 / ADR-0030 / ADR-0031 surface preferences?

None of those questions are settled by ADR-0032 and shouldn't be settled in the same pass that establishes the surface.

## Consequences

### Positive

- **Boundary checks are now centralized**, queryable, and uniformly shaped. An auditor reviewing a turn no longer has to traverse five scattered call sites to confirm boundaries held; they read one `SafetyVerdict`.
- **Honest about what's runtime-checkable.** `runtime_checkable=False` for code-path boundaries is the truth, not a silent pass.
- **Extensible.** Custom predicates for deployment-specific safety boundaries register without touching CORE code.
- **Forward-compatible with enforcement.** When a future ADR wires SafetyCheck into refusal paths, the surface won't need to change — only the call site will.
- **No regression.** Existing scattered enforcement continues to do its job; SafetyCheck is additive.

### Negative / risks

- **Observation isn't enforcement.** A violation reported by SafetyCheck at v1 has no automatic consequence — it lives in audit. This is deliberate (the surface lands first; refusal wiring comes later) but worth naming.
- **Predicate authoring is per-deployment work** for any boundary beyond the five v1 defaults. Documentation in `docs/safety_packs.md` will need to grow as deployment patterns emerge.
- **Defensive boundary-id rebinding masks predicate bugs.** A predicate that returns the wrong boundary id gets its result rebinding-corrected, with no warning by default. We accept this trade for safety — better to have the audit verdict reach the right boundary than to crash on a misbehaving predicate. A future debug-mode flag could surface the bug visibly.

### Scope limits (explicit non-goals for this ADR)

- No auto-invocation in the turn loop.
- No refusal wiring.
- No refactoring of the existing scattered enforcement sites to delegate to SafetyCheck.
- No structural difference between "violated" and "would-have-been-violated-if-checkable".

## Verification

- `tests/test_safety_check.py` — 20 tests covering each of the five default predicates (positive + negative paths where applicable), the unknown-boundary fallback, custom predicate registration, defensive boundary-id rebinding, verdict aggregation, and `ChatRuntime` integration.
- Cognition (121), teaching (17), runtime (19), formation (182), smoke (67) suites green at the same revision.
- The full identity/safety surface suite (`test_identity_packs`, `test_safety_pack`, `test_identity_surface_divergence`, `test_identity_surface_divergence_depth`, `test_identity_score_decomposition`, `test_safety_check`) is 108 tests, all green.

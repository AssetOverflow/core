# ADR-0098 — Demo Composition Contract

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers

---

## Context

CORE has shipped a growing set of operator-facing demos:

- `core demo audit-tour` (ADR-0042)
- `core demo anti-regression` (ADR-0055)
- `core demo learning-loop` (ADR-0056)
- `core demo register-tour` (ADR-0072)
- `core demo anchor-lens-tour` (ADR-0073d)
- `core demo orthogonality-tour` (ADR-0074)
- `core bench --suite teaching-loop` (ADR-0057)

Each one is correct in isolation. Each one stands as its own evidence
of a specific invariant. The problem the next ADR (ADR-0099 public
showcase) faces is that there is no shared contract that lets one
demo safely embed another.

Without a contract, the showcase has two bad options:
1. Reimplement portions of each demo inline (drift, duplication,
   doctrine violation).
2. Subprocess-spawn each demo and parse stdout (fragile, breaks the
   trace-hash discipline).

The right answer is a small protocol that the existing demos retrofit
to, and that the showcase consumes.

---

## Decision

Introduce `DemoCommand` as a typed protocol. Existing demos are
retrofitted to it in the same PR (mechanical, small). Future demos
implement it from the start.

### Protocol

```python
class DemoCommand(Protocol):
    demo_id: str               # stable identifier, kebab-case
    claim_contract_version: int  # currently 1

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult: ...

@dataclass(frozen=True, slots=True)
class DemoResult:
    demo_id: str
    claims: tuple[Claim, ...]
    evidence: Mapping[str, str]   # claim_id -> evidence locator (path or sha)
    all_claims_supported: bool
    json_path: Path
    trace_features: Mapping[str, str]  # canonical, for showcase composition

@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    statement: str
    supported: bool
    evidence_locator: str
```

### Rules

1. **Deterministic JSON.** Two runs with the same inputs and seed
   produce byte-identical `json_path` contents. HTML may differ
   in formatting; JSON is the truth-path.
2. **No global state mutation.** A demo's `run()` may not mutate
   process-global registries (runtime singletons, telemetry sinks
   attached at module load, environment variables outside its own
   scope). Demos that need a telemetry sink attach a local one and
   detach it before returning.
3. **Declared output paths only.** A demo writes only under
   `output_dir`. Path traversal rejected via `safe_pack_id`-class
   sanitization.
4. **Composability is read-only.** A composing demo (the showcase)
   may read another demo's `DemoResult` but never mutates it.

### Retrofit scope

Each shipped demo gains a thin adapter in
`core/commands/demo_<name>.py` that conforms to `DemoCommand`. The
adapter does not change demo behavior; it wraps the existing entry
point and produces a `DemoResult`.

### What this ADR does not do

- Does not change demo behavior.
- Does not change demo CLI surface. `core demo audit-tour` runs the
  same way; the protocol is internal.
- Does not introduce a registry. Demos remain discoverable via the
  existing CLI subparser.

---

## Invariant

`demo_composition_no_side_effects` — a grep gate on the showcase's
import graph refuses any symbol that mutates runtime singletons or
attaches telemetry sinks at module load. The protocol contract is
enforced by structure, not by hope.

`demo_json_byte_equality` — for each demo retrofitted under this ADR,
running it twice with identical inputs produces byte-identical JSON.
CI lane verifies.

---

## Lane

`evals/demo_composition/` (new):

- positive: each retrofitted demo runs twice → identical JSON
- negative: a deliberately stateful test fixture → composition
  detector rejects it
- composition: showcase reads two demo results → produces composite
  claim set without mutating either

---

## Trust Boundary

Demos write only to operator-specified `output_dir`. Path traversal
rejection inherits from ADR-0051. No dynamic imports. No network. No
shell.

---

## Consequences

- ADR-0099 public showcase becomes mechanically possible without
  reimplementing demo logic.
- Future demos cost less: implement the protocol once, gain
  composability for free.
- The shipped demos gain a small adapter layer but no behavioral
  change.

---

## PR Checklist

- Capability added: composition protocol for demos.
- Invariants proved: `demo_composition_no_side_effects`, `demo_json_byte_equality`.
- Lane proving it: `evals/demo_composition/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none.
- Trust boundary: demos write only under declared output paths; no global state mutation.

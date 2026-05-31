# Zig Adoption Gates

**Status:** doctrine  
**Applies to:** all future Zig work in CORE

Zig may enter CORE only through evidence. This page defines the proof ladder for any Zig component.

---

## Gate ladder

```text
G0 doctrine
G1 reference contract locked
G2 prototype behind explicit selector
G3 parity proof
G4 determinism proof
G5 mechanical advantage proof
G6 operational proof
G7 supported backend
G8 default backend, only by later ADR
```

No component skips a gate because it is small, native, or easy to write.

---

## G0 — Doctrine

Before implementation, document:

- exact component boundary;
- current source of truth;
- why Zig is being considered;
- why Python or Rust may be insufficient for this boundary;
- non-goals;
- fallback path;
- proof obligations.

The document must name the governing ADRs/specs. Current anchors include ADR-0013, ADR-0019, ADR-0020, ADR-0054, ADR-0180, and ADR-0181.

---

## G1 — Reference contract locked

A Zig implementation must trail a locked reference contract.

Valid references:

- tested Python behavior;
- tested Rust behavior;
- an ADR/spec/eval plan with executable acceptance gates;
- fixture corpus plus expected hashes.

Invalid references:

- performance hope;
- preference for a language;
- untested native behavior;
- implementation-first semantics.

---

## G2 — Explicit prototype selector

A Zig prototype must be unreachable unless deliberately selected.

Acceptable selectors:

```text
CORE_NATIVE_BACKEND=zig
CORE_CRDT_BACKEND=zig
CORE_AUDIO_COMPILER_BACKEND=zig
core doctor --zig
```

A local Zig library being present must not automatically alter runtime behavior.

---

## G3 — Parity

Parity means the Zig component preserves the reference contract.

| Component | Required parity |
|---|---|
| CRDT merge | same canonical order, same dedup result, same merge hash for all input permutations |
| Audio compiler | same AudioIR hash, projection hash, merge key, and declared `(32,)` output contract |
| Algebra kernel | bit-identical result, or ADR-approved numeric tolerance |
| Batch recall | identical top-k indices, scores, and tie-break behavior |
| FFI boundary | same typed errors at Python surface |

The parity gate must fail loudly if ordering, hashing, closure, or recall semantics drift.

---

## G4 — Determinism

A Zig component must prove repeatability across:

- repeated calls;
- reordered inputs when order-invariance is claimed;
- concurrent calls when thread-safety is claimed;
- cold and warm startup;
- supported target platforms.

CRDT minimum:

```text
join(a, b) == join(b, a)
join(join(a, b), c) == join(a, join(b, c))
join(a, a) == a
hash(merge(permutation(deltas))) == hash(merge(deltas))
```

Audio minimum:

```text
same canonical bytes
+ same compiler version
+ same pack manifest
+ same operator registry
= same AudioIR
= same projection hash
= same CRDT merge key
```

---

## G5 — Mechanical advantage

Zig must prove at least one real advantage:

- clearer C ABI;
- simpler edge-native deployment;
- lower memory footprint;
- lower latency on representative workloads;
- explicit allocation/lifecycle control;
- reduced binding overhead;
- safer ownership at a native boundary.

Performance data without parity does not count.

---

## G6 — Operational proof

A supported Zig backend needs:

- build command;
- diagnostic command;
- backend selector;
- ABI version check;
- memory free contract;
- error contract;
- fallback behavior;
- CI or local verification command.

---

## G7/G8 — Supported and default

Supported backend status requires parity, determinism, operational proof, and documented advantage.

Default backend status requires a separate ADR. Default-by-availability is not allowed.

---

## Review checklist

Every Zig PR must answer:

1. What behavior is being ported or introduced?
2. Where is the reference contract?
3. How is Zig selected?
4. What is the fallback?
5. Who owns each buffer?
6. How are allocations released?
7. What errors are surfaced?
8. What proves deterministic replay?
9. What benchmark or deployment evidence justifies the component?
10. What test fails if semantics drift?

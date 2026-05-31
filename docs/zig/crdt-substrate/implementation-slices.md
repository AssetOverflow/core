# Zig CRDT Substrate — Implementation Slices

**Status:** doctrine / implementation plan  
**Depends on:** `docs/zig/crdt-substrate/README.md`

This document breaks the Zig CRDT candidate into small, reviewable slices.

No slice should touch production runtime behavior until the explicit backend selector and parity gates exist.

---

## ZC-0 — Contract pinning

Purpose: prove the current CRDT law before adding Zig.

Deliverables:

```text
tests/test_crdt_semilattice_contract.py
tests/test_crdt_content_ordering.py
tests/test_crdt_no_global_write_from_arena.py
```

Required checks:

- join commutativity;
- join associativity;
- join idempotence;
- stable content ordering;
- duplicate deduplication;
- push-to-arena does not mutate Vault;
- canonical merge independent of arena flush order.

Exit gate: Python/Rust reference behavior is locked.

---

## ZC-1 — Zig skeleton

Purpose: create an inert Zig crate/library with no runtime wiring.

Deliverables:

```text
core-zig/build.zig
core-zig/src/version.zig
core-zig/src/crdt/entry.zig
core-zig/src/crdt/delta.zig
core-zig/src/crdt/arena.zig
core-zig/src/crdt/merge.zig
core-zig/src/crdt/ffi.zig
core-zig/include/core_crdt.h
```

Allowed:

- local Zig unit tests;
- no Python runtime dispatch;
- no core CLI integration except maybe future `core doctor --zig` planning.

Exit gate: Zig library builds and tests locally.

---

## ZC-2 — C ABI self-test

Purpose: prove the FFI is stable before Python binding.

Deliverables:

```text
core-zig/tests/crdt_ffi_test.zig
core-zig/examples/crdt_smoke.c
```

Required checks:

- create/free arena;
- push entries;
- snapshot delta;
- join deltas;
- merge many deltas;
- hash delta;
- reject bad pointers/lengths gracefully where possible.

Exit gate: C ABI round-trip passes without Python.

---

## ZC-3 — Python binding behind selector

Purpose: expose Zig CRDT only when explicitly requested.

Deliverables:

```text
core_native/zig_loader.py
core_native/crdt_zig.py
tests/test_crdt_zig_binding.py
```

Selector:

```text
CORE_CRDT_BACKEND=zig
```

Required checks:

- missing library produces clear unavailable status;
- bad ABI version is rejected;
- errors become typed Python errors;
- no automatic selection by importability.

Exit gate: Python can call Zig CRDT functions in isolation.

---

## ZC-4 — Parity fixtures

Purpose: prove Zig equals the reference.

Deliverables:

```text
tests/test_crdt_zig_parity.py
```

Required checks:

- same merged entries as reference;
- same hash as reference;
- same behavior under input permutations;
- same dedup behavior;
- same provenance distinction behavior;
- same handling of `-0.0`, `+0.0`, and NaN bit patterns if fixtures include them.

Exit gate: parity green.

---

## ZC-5 — Benchmark and memory profile

Purpose: prove Zig has a reason to exist.

Deliverables:

```text
benchmarks/crdt_merge.py
bench_reports/crdt_merge_zig.json
```

Metrics:

- latency by entry count;
- latency by delta count;
- memory allocation profile;
- peak RSS if measured from Python;
- merge hash equality check included before timing is trusted.

Exit gate: Zig wins a named mechanical criterion or remains prototype-only.

---

## ZC-6 — Runtime integration proposal

Purpose: decide whether to wire Zig into actual modality ingestion.

Allowed only after ZC-0 through ZC-5.

Deliverables:

```text
ADR: Zig CRDT backend promotion
runtime integration plan
telemetry fields
fallback plan
CI lane
```

No production runtime integration is authorized before this slice.

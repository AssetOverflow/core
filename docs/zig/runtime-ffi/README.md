# Zig Guidance — Runtime FFI Boundary

**Status:** doctrine  
**Component:** C ABI and runtime backend boundary

Zig should enter CORE through stable FFI surfaces, not through ad-hoc runtime imports. This document defines the shape of that boundary.

---

## Why FFI discipline matters

The risk of adding Zig is not the language itself. The risk is boundary confusion:

```text
Who owns this buffer?
Who frees this allocation?
Is this function allowed to mutate global state?
Is the backend selected intentionally?
Are errors typed or just logged?
Can replay identify which backend ran?
```

If those questions are ambiguous, Zig should not be merged.

---

## ABI principles

### 1. C ABI first

All Zig substrate components should expose a C ABI first.

Python, Rust, Swift, or future edge binaries may bind to that ABI, but the ABI itself should not depend on Python object semantics.

### 2. Explicit versioning

Every library should expose:

```c
unsigned int core_native_abi_version(void);
const char* core_native_build_id(void);
```

Runtime bindings must reject unknown ABI versions.

### 3. Caller-owned inputs

Input buffers should usually be caller-owned. Zig must treat them as borrowed unless the API explicitly copies them.

### 4. Explicit output ownership

If Zig allocates output, Zig must provide the matching free function.

Pattern:

```c
int component_do_work(..., ComponentOutput** out, ComponentError* err);
void component_output_free(ComponentOutput* out);
```

No output allocation should be freed by Python, Rust, or libc unless the ABI explicitly says so.

### 5. Typed error surface

Do not print errors from Zig as the only failure signal. Return structured error codes and bounded messages.

Example:

```c
typedef struct CoreNativeError {
    int code;
    char message[256];
} CoreNativeError;
```

Python bindings should translate these to typed Python exceptions.

---

## Backend selection

Native backends must be selected explicitly.

Recommended environment variables:

```text
CORE_NATIVE_BACKEND=python|rust|zig
CORE_CRDT_BACKEND=python|rust|zig
CORE_AUDIO_COMPILER_BACKEND=python|zig
CORE_RECALL_BACKEND=python|rust|zig
```

Rules:

- absence of Zig library must not break the Python path;
- presence of Zig library must not silently change runtime behavior;
- backend identity must be visible in diagnostics;
- backend identity should be recorded in replay evidence where behavior/performance could matter.

---

## Memory ownership table

| Case | Preferred ownership |
|---|---|
| input NumPy matrix | Python owns; pass pointer/shape/stride only after contiguity check |
| audio input samples | caller owns unless canonicalizer explicitly copies |
| CRDT provenance bytes | Zig may copy into arena-owned storage |
| CRDT delta output | Zig owns; caller frees through Zig free function |
| AudioCompilationUnit output | Zig owns; caller frees through Zig free function |
| error message | caller passes error struct pointer; Zig writes bounded message |
| returned slices | avoid raw borrowed slices unless lifetime is obvious and documented |

---

## Shape and dtype validation

All FFI surfaces must validate shape and dtype before computation.

Examples:

```text
versor: exactly 32 f32 values
matrix: N x 32 f32, row-major contiguous
queries: B x 32 f32, row-major contiguous
audio samples: declared dtype, channel count, sample rate, length
edges: E x 2 i32 if graph diffusion is used
```

Invalid shape is a typed error, not undefined behavior.

---

## Forbidden FFI behaviors

Zig FFI must not:

- hold Python object pointers;
- assume NumPy memory remains valid after caller scope ends;
- spawn hidden background threads;
- mutate global CORE state;
- allocate without a free path;
- panic across FFI boundary;
- return borrowed memory with unclear lifetime;
- reinterpret non-contiguous buffers as contiguous;
- hide fallback after partial mutation;
- suppress errors and continue.

---

## Python binding shape

Python binding modules should be thin and boring:

```text
core_native/zig_loader.py
core_native/crdt_zig.py
core_native/audio_zig.py
core_native/recall_zig.py
```

Responsibilities:

- locate library;
- check ABI version;
- check buffer contiguity;
- call C ABI;
- translate errors;
- free outputs;
- expose Pythonic wrappers;
- never define semantics not present in the reference contract.

---

## Diagnostic command

A future CLI diagnostic should report:

```text
core doctor --zig
  library found: yes/no
  ABI version: ...
  build id: ...
  enabled selectors: ...
  CRDT backend available: yes/no
  audio compiler backend available: yes/no
  recall backend available: yes/no
  last self-test: pass/fail
```

If a user asks for a required Zig backend and it is unavailable, fail fast with a clear error.

---

## Runtime trace policy

Any turn/event affected by Zig-backed native behavior should be able to report:

```text
native_backend: zig
native_component: crdt|audio|recall|algebra
abi_version: N
build_id: sha/hash/version
```

This does not mean every trace needs verbose native metadata. But replay-critical paths must not hide which substrate executed.

---

## Recommendation

Add the FFI contract before adding serious Zig code.

A clean FFI boundary lets CORE evaluate Zig without infecting Python semantics, Rust parity work, or Workbench/operator flows.

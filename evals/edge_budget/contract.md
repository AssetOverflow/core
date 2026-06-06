# Edge-budget lane — contract (A2)

**Status:** GATE (the edge axis made falsifiable). **Telos:** [[project-core-is-one-continuous-life]] deployed at the edge — offline, no-GPU, deterministic, on a constrained device (clinic / disaster-center / rural-school box).

## What it proves

That a long-running CORE life stays **affordable to persist per turn** on a constrained device — *measured deterministically*, not asserted. The metric is the bytes the Shape B+ checkpoint writes each turn (`engine_state/session_state.json`), captured over the real turn loop (`CognitiveTurnPipeline` + `ChatRuntime(persist_session_state=True)`). Bytes, **not wall-clock latency**: latency is machine-dependent and would make the gate flaky in CI; the snapshot bytes are reproducible (proven by `test_cost_metric_is_deterministic`).

## The cliff (measured, 24-turn soak)

`save_session_state` re-serializes the **full** snapshot every turn, so per-turn cost is **O(n) in the accumulated life** (the vault):

| turn | vault | `session_state.json` bytes |
|----:|----:|----:|
| 0 | 2 | 3,811 |
| 2 | 8 | 11,884 |
| 4 | 14 | 20,228 |
| 8 | 25 | 32,831 |
| 12 | 37 | 48,993 |
| 16 | 48 | 62,965 |
| 20 | 60 | 78,564 |
| 23 | 68 | 88,189 |

Per-turn bytes grow ~linearly with vault size (~1.3 KB/entry, re-written *every* turn): **growth ratio 23× over 24 turns**, cumulative ~1.1 MB. Extrapolated, a life of 1,000 turns writes multiple MB **per turn**; 10,000 turns, tens of MB per turn. That is the edge-deployability blocker for continuous life.

## The gate

- **`test_per_turn_checkpoint_cost_is_within_edge_budget`** — `xfail(strict=True)`. The edge **requirement**: `max_per_turn_bytes ≤ 16 KiB` regardless of session length (a bounded device budget; an O(Δ) implementation writes only the turn's delta, ~a few KB). Today's O(n) snapshot breaches it by turn ~4, so it is an **expected failure that documents the cliff**. When incremental/append-only persistence lands and per-turn bytes go flat, this **xpasses** → `strict` turns it into a hard CI failure → we retire the xfail. That is the falsifiable handle: the cliff is a red gate that the fix turns green.
- **`test_persistence_cost_regression_ceiling`** — passes today; guards against making the cliff *worse* (per-turn ≤ 160 KiB, total ≤ 4 MiB).
- **`test_cost_grows_with_accumulated_state_today`** — records the current O(n) signature on the record (so the fix is a visible delta).
- **`test_cost_metric_is_deterministic`** — the byte series is reproducible across runs.

## The fix this gate is waiting for

**Incremental / append-only persistence — algorithmic, in Python (Ring 2).** Persist only the turn's **delta** (new vault entries + the fixed-size field/anchor/scalar state) instead of re-serializing all history; periodic compaction; preserve bit-exact resume (Shape B+) and torn-write atomicity. The vault is append-mostly and the field is fixed-size, so O(Δ)/turn is natural, not a fight against the architecture. This is *not* a micro-optimization and *not* a language rewrite.

## Zig-codec follow-up (tagged — NOT authorized)

Once persistence is O(Δ) and this gate is green, **if** the bounded per-turn codec is still the device bottleneck, `core/array_codec.py` is the **locked reference contract** (ADR-0196 decision rule 1) for a Ring-1 Zig byte-exact codec component — gated through the G0–G8 ladder with a parity + determinism + mechanical-advantage proof, behind an explicit selector. A Zig rewrite of *today's* O(n) snapshot would only accelerate the wrong asymptotics, so it is **step 3**, after the algorithmic fix and after this gate proves it's needed. Tag lives in `core/array_codec.py`.

# Apple Silicon Engineering Support Brief (Draft)

This brief is factual and engineering-first. It does not claim Apple endorsement,
review, or sponsorship. All performance and memory-boundary claims are backed by
the reproducible benchmark report at
`evals/reports/apple_uma_mechanical_sympathy_latest.json`.

## What CORE is

CORE is a deterministic Cl(4,1) reasoning and safety engine. Its runtime path
preserves geometric field invariants, exact CGA recall, closed-world proof
surfaces, and replay-stable evidence — not stochastic token generation.

## What the benchmark measures

The **CORE Apple Silicon UMA Mechanical Sympathy Benchmark** measures:

- Exact CGA top-k recall throughput on contiguous `(N, 32)` float32 matrices
- Cl(4,1) scalar algebra hot paths (`geometric_product`, `versor_apply`,
  `cga_inner`, `versor_condition`)
- Off-serving closed-world FrameVerdict time-to-first-verifiable-verdict (TTFV)
- Deterministic `array_codec` persistence replay cost
- Honest Python/Rust copy and zero-copy input boundaries

It does **not** benchmark token generation, approximate recall, or transformer
throughput.

## Why Apple Silicon UMA is relevant

CORE workloads are dominated by contiguous-memory geometric operations and exact
recall scans. On Apple Silicon unified memory architecture, native bindings that
avoid Python marshalling tax on hot paths (for example Rust `vault_recall` and
`diffusion_step` input views) align with mechanical sympathy for UMA — when
measured, not assumed.

## Current hardware limits

On the machine that generated the latest report, larger validation lanes (for
example `N=65536` exact recall, large diffusion graphs, expanded replay buffers)
may be skipped or constrained by available memory and single-node throughput.
The benchmark records these limits explicitly.

## Requested engineering feedback

We are seeking Apple Silicon engineering feedback on:

1. Whether measured UMA-aligned workloads match expected memory behavior on M-series
2. Practical guidance for MLX/Metal kernel experiments under separate ADR/parity gates
3. Whether expanded hardware access would unlock larger reproducible validation runs

## Future-facing context (not benchmark claims)

Deterministic verification and replay throughput may be relevant to on-device
safety and audit surfaces in future R&D — but that relevance is **not** claimed
as a current product integration. MLX, Metal, CoreML, and Neural Engine paths
remain future work until implemented, parity-tested, and measured.

## How to reproduce

```bash
python -m benchmarks.apple_uma_mechanical_sympathy --write-report
# or
core bench --suite apple-uma --write-report
```

Reports land under `evals/reports/`. No network access is required.

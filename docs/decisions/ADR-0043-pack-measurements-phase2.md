# ADR-0043 — Phase-2 pack measurements: claims → numbers

Status: Accepted (2026-05-17)

## Context

The pack-layer chain (ADR-0027 → ADR-0042) ships three architectural
claims:

1. Identity is *load-bearing* — different identity packs produce
   different articulations on the same input.
2. Safety is the *universal floor* — refusal is invariant across
   identity choice.
3. Grounding refusal is *upstream of* articulation — identity packs do
   not change the gate.

Through ADR-0042 these claims are demonstrated by hand-curated tests
(`tests/test_identity_surface_divergence.py`,
`tests/test_pack_swap_*`) and the audit-tour demo. They are *asserted*.
They are not *published as numbers* across the three ratified packs.

The strategic frame from session 2026-05-17 is to "convert claim into
measurement without any pack growth" before doing anything that adds
new vocabulary, new packs, or new infrastructure.  This ADR is that
conversion.

## Decision

Ship two new pack-aware runners and a publisher that emit a single
combined report:

- `evals/identity_divergence/pack_runner.py` — drives the *real*
  `SentenceAssembler` + `SurfaceContext` across the three ratified
  identity packs (`default_general_v1`, `precision_first_v1`,
  `generosity_first_v1`) over the existing 10 dev+public cases at
  five alignment bands `{0.20, 0.45, 0.60, 0.80, 0.95}`.  No mocks.
  Reports per-pack `bare_rate` / `hedge_rate` / `qualifier_rate` and
  pairwise `distinct_rate`.

- `evals/refusal_calibration/pack_runner.py` — runs the existing
  grounding-refusal lane across all three identity packs via
  `RuntimeConfig(identity_pack=...)`.  Reports per-pack `refusal_rate`
  / `fabrication_rate` and a `pack_invariant_gate` flag that asserts
  the cold-start out-of-grounding surface is byte-identical across
  packs.

- `scripts/publish_pack_measurements.py` — orchestrator emitting
  `evals/results/phase2_pack_measurements.json` plus per-runner
  `results/packs_v1/measurements.json` artifacts.

The combined report carries a `claims_supported` block:

```json
{
  "identity_load_bearing": true,
  "grounding_gate_pack_invariant": true,
  "no_fabrication_under_any_pack": true
}
```

`tests/test_pack_measurements_phase2.py` gates these flags plus the
schema and the structural inequality
`precision_first.hedge_rate > generosity_first.hedge_rate`.  If any of
those flips the suite fails.

## Headline numbers (2026-05-17 baseline)

Identity-divergence (10 cases × 5 alignment bands):

| Pack | bare | hedge | qualifier |
|---|---|---|---|
| default_general_v1 | 0.60 | 0.40 | 0.00 |
| precision_first_v1 | 0.20 | 0.60 | 0.20 |
| generosity_first_v1 | 0.80 | 0.20 | 0.00 |

Pairwise pack divergence:

| Pair | distinct_rate |
|---|---|
| default ⇆ precision | 0.80 |
| default ⇆ generosity | 0.40 |
| precision ⇆ generosity | 0.80 |

Refusal-calibration (8 out-of-grounding probes × 3 packs):

| Pack | refusal_rate | fabrication_rate |
|---|---|---|
| default_general_v1 | 1.00 | 0.00 |
| precision_first_v1 | 1.00 | 0.00 |
| generosity_first_v1 | 1.00 | 0.00 |

`pack_invariant_gate=True` — every out-of-grounding probe produces a
byte-identical surface across the three packs, proving the gate is
upstream of pack articulation.

Note on `refusal_rate=1.00`: this lane uses an *extended* marker set
that recognizes CORE's cold-start unknown-domain surface ("I don't
have field coordinates for that yet.") as a refusal.  This is the
correct calibration for the *separation* claim being measured (gate
behavior vs articulation behavior).  The original v1 contract
in `evals/refusal_calibration/contract.md` deliberately uses a
narrower marker set and is expected to fail at v1 — that file
remains the source of truth for the canonical v1 refusal claim.

## Consequences

**Positive.**

- The two headline pack-layer claims are now CI-enforced numbers, not
  prose assertions.
- Adding a fourth identity pack auto-extends both reports; no glue
  code.
- The `pack_invariant_gate` flag turns the separation-of-concerns
  argument into a structural test — if anyone wires identity packs
  into the cognition gate the test flips immediately.

**Trade-offs.**

- The Phase-2 lane uses an extended marker set; reviewers must read
  the ADR to know why the number is 1.00.  This is documented above
  and in the runner module docstring.
- The pack-driven divergence runner uses simple humanization (`_`→space)
  on predicate tokens; case wording is awkward (e.g. "Bob is sibling
  of Carol") but this is irrelevant — the measurement is about *whether
  the pack's surface preferences fire*, not naturalness.  Naturalness
  is an articulation pipeline concern, not an identity-pack concern.
- Adding alignment bands or cases requires re-baselining the headline
  numbers in this ADR.  The test gates flags + structural inequality,
  not exact rates, so small case-set growth is safe.

## How to verify

```bash
PYTHONPATH=. python3 scripts/publish_pack_measurements.py
PYTHONPATH=. python3 -m pytest tests/test_pack_measurements_phase2.py -q
```

## Where it lives

- `evals/identity_divergence/pack_runner.py`
- `evals/refusal_calibration/pack_runner.py`
- `scripts/publish_pack_measurements.py`
- `tests/test_pack_measurements_phase2.py`
- `evals/results/phase2_pack_measurements.json` (artifact)
- `evals/identity_divergence/results/packs_v1/measurements.json`
- `evals/refusal_calibration/results/packs_v1/measurements.json`

## Related

- [ADR-0027](ADR-0027-identity-packs.md) — identity packs.
- [ADR-0028](ADR-0028-identity-surface-wiring.md) — surface preferences.
- [ADR-0042](ADR-0042-audit-tour-demo.md) — the qualitative tour these
  measurements now back with numbers.

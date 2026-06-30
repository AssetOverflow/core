# ADR-0112 — Runnable Expert-Demo Showcase

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0098, ADR-0099, ADR-0106, ADR-0109, ADR-0110, ADR-0111

---

## Context

ADR-0106 introduced the `expert-demo` ledger status as a contract-gated
promotion above `reasoning-capable`. ADR-0110 and ADR-0111 promoted
`mathematics_logic` and `physics` respectively under that contract.

The status name carries the word "demo." Until this ADR, the artifact
backing a promotion was a signed evidence-bundle digest in
`docs/reviewers.yaml` plus a set of on-disk lane result files —
*audit evidence*, not a runnable demonstration. An external reader
clone-and-run could verify the digest but had no per-domain HTML
artifact to open and see what the domain actually produces.

The asymmetry was real. `core demo audit-tour`,
`core demo register-tour`, `core demo learning-loop`,
`core demo showcase` all emit inspectable JSON + HTML walkthroughs.
The `expert-demo` *status* had no equivalent surface. The name implied
a demonstration that did not exist.

ADR-0112 closes the gap.

---

## Decision

Add a new demo target: `core demo expert --domain <id>`.

For a domain whose ledger row carries `expert_demo=true`, the composer
produces a per-domain runnable showcase:

1. Reads the signed `expert_demo_claims` entry from
   `docs/reviewers.yaml`.
2. Loads the latest on-disk result file for each attached lane on
   both `public` and `holdout` splits.
3. Re-derives the evidence-bundle digest from those files and asserts
   byte-for-byte equality with the signed `claim_digest`. This is the
   load-bearing audit step.
4. Runs each lane's metrics through the ADR-0109 lane-shape registry
   and surfaces the shape-check verdict.
5. Picks the first N cases (N = 3) from each split's `cases` array
   verbatim — same bytes the digest already covers, rendered for
   inspection.
6. Emits `expert_demo.json` (canonical-serialized, byte-deterministic
   via `core.demos.contract.canonical_json`) and `expert_demo.html`
   (presentation-only) under
   `evals/expert_demos/<domain>/latest/` by default.

The composer does **not** re-run the lanes. The lane result files are
the artifact the digest covers; replaying them would not strengthen
the claim and would introduce non-determinism (timestamp churn,
ordering). The "watch CORE answer X" experience is achieved by
surfacing the already-shipped case records — `surface`, `passed`,
`grounding_source`, `trace_hash` — directly from disk.

The composer is **read-only**. It writes only to its `output_dir`;
it does not mutate `docs/reviewers.yaml`, any lane result file, or
any pack manifest.

An unpromoted domain (no signed claim) raises `ValueError` with a
message naming the missing claim. The CLI surfaces a non-zero exit.

---

## Surface

```
core demo expert --domain mathematics_logic
core demo expert --domain physics

# default output dir: evals/expert_demos/<domain>/latest/
# override:           core demo expert --domain physics --output-dir <path>
```

Output structure:

```
evals/expert_demos/<domain>/latest/
  expert_demo.json    # canonical bytes; same on-disk inputs → same SHA
  expert_demo.html    # presentation surface; opens in a browser
```

JSON shape (excerpt):

```text
{
  "expert_demo_version": 1,
  "claim_contract_version": 1,
  "domain_id": "physics",
  "claim": {
    "signed_by": "shay-j",
    "evidence_revision": "adr-0111:reviewed:2026-05-22",
    "evidence_lanes": ["foundational_physics_ood", "inference_closure", "fabrication_control"],
    "claim_digest": "a104cad1..."
  },
  "digest_verification": {
    "signed":  "a104cad1...",
    "derived": "a104cad1...",
    "matches": true
  },
  "lanes": [
    {
      "lane_id": "foundational_physics_ood",
      "shape": "accuracy_shape",
      "splits": {
        "public":  { "metrics": {...}, "shape_check": {...}, "case_count": 117, "sample_cases": [...] },
        "holdout": { "metrics": {...}, "shape_check": {...}, "case_count":  39, "sample_cases": [...] }
      }
    },
    ...
  ],
  "all_lanes_pass": true,
  "all_digests_match": true,
  "all_claims_supported": true
}
```

---

## Invariants

### `adr_0112_promoted_domain_renders`

`build_expert_demo(domain_id)` for every domain whose ledger row
carries `expert_demo=true` returns a payload with
`all_claims_supported=True`. Tested by
`tests/test_expert_demo_runnable.py::TestPromotedDomainsBuildSuccessfully`.

### `adr_0112_digest_recompute_byte_equal`

The recomputed digest equals the signed `claim_digest`. This is the
load-bearing audit invariant: if any byte of any attached lane result
file changes, the digest changes and the showcase declares
`all_claims_supported=False`. Tested in the same module.

### `adr_0112_unpromoted_domain_refused`

A domain without a signed claim raises `ValueError`. There is no
silent fallback, no "preview" mode that would emit an unsigned
showcase.

### `adr_0112_byte_determinism`

Two consecutive `run_expert_demo` calls with identical on-disk inputs
produce byte-identical `expert_demo.json`. Tested by SHA-256 of the
output bytes.

### `adr_0112_read_only`

`run_expert_demo` does not mutate `docs/reviewers.yaml` or any
`evals/<lane>/results/v1_*.json` file. Tested by capturing the bytes
of the source files before and after a run.

---

## Acceptance evidence

Accepted when:

- `core/demos/expert_demo.py` exists with `build_expert_demo`,
  `run_expert_demo`, and `render_html` exported
- `core demo expert --domain <id>` works for `mathematics_logic` and
  `physics`; both produce `all_claims_supported=True` and digest match
- `tests/test_expert_demo_runnable.py` pins the five invariants
- README + docs/decisions/README.md updated to point readers at the
  new runnable surface

---

## Consequences

- The word "demo" in `expert-demo` now corresponds to something a
  reader can open. The name is no longer aspirational.
- Each future expert-demo promotion automatically gains a runnable
  surface — no per-domain composer work required. Adding a new
  promoted domain (e.g. `systems_software`) needs only its signed
  claim and on-disk lane results; the showcase composer handles the
  rest by following the lane-shape registry.
- The digest-recompute step is now exercised in two places: the
  ledger gate (`evaluate_expert_demo` at report time) and the
  runnable showcase (every time a reader runs it). Same load-bearing
  invariant, two independent enforcement points.
- An `expert_demo.html` is now a stable artifact a third party can
  ask for. Future PRs that touch any of the three attached lane
  result files for a promoted domain will, by definition, change
  that domain's showcase output — `expert_demo.json` SHA stability is
  a useful signal that the promotion claim still reproduces.

---

## Out of scope

- This ADR does not change the digest-derivation algorithm
  (`derive_evidence_digest`), the lane-shape registry (ADR-0109),
  or the contract gate (ADR-0106). The showcase is *consumer of*
  those contracts, not an amendment.
- This ADR does not commit the per-domain `expert_demo.{json,html}`
  artifacts to the repo. They are generated on demand. A future
  ADR may pin selected showcases under `evals/expert_demos/<domain>/`
  the way ADR-0099 pinned `evals/public_demo/results/latest/`; that
  is a separate decision involving review of the artifact churn
  cost.
- This ADR does not introduce live re-running of lane runners under
  the showcase. The lane result files are authoritative; the showcase
  is a renderer.
- Sample-case selection is the deterministic first-N. Replacing this
  with a stratified or quoted-claim sample (e.g. include one case
  per construction class) would be a future amendment.

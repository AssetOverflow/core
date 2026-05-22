# ADR-0113 — Rename `expert-demo` → `audit-passed`; Reserve `expert` for Future Capability Tier

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0106, ADR-0109, ADR-0110, ADR-0111, ADR-0112

---

## Context

ADR-0106 introduced the `expert-demo` ledger status as a contract-gated
promotion above `reasoning-capable`. ADR-0110 / ADR-0111 promoted
`mathematics_logic` and `physics` to that status. ADR-0112 added a
runnable per-domain showcase (`core demo expert --domain <id>`).

The word "expert" carried an unintended implication: that a domain at
`expert-demo` had been demonstrated at *expert-level capability* (i.e.
raw task performance comparable to a human domain expert). The gate
**does not** verify that. The gate verifies that a domain has cleared
the **CORE claim contract**:

1. Domain Pack Contract v1 — all nine ADR-0091 predicates pass.
2. A reviewer-signed evidence-bundle SHA-256 reproduces byte-for-byte
   from on-disk lane result files (ADR-0106 §1.5).
3. The lane outputs satisfy CORE-specific claim shapes:
   - **signed digest** — every claim reproduces from disk
   - **replay determinism** — same inputs → byte-equal trace_hash
   - **typed refusal** — fabrication is refused, not paraphrased
   - **exact recall** — no ANN, no cosine, no attention-bottleneck
   - **grounding-source provenance** — every surface tags its origin

These are claim shapes a transformer-based LLM **structurally cannot
produce**, regardless of how high its raw accuracy is on the same
benchmark. A frontier LLM might score higher on the raw answers but
cannot pass this contract because it cannot produce a digest that
re-derives, cannot guarantee typed refusal, cannot emit a trace hash
bound to a deterministic execution, cannot replay byte-equal.

That is the load-bearing claim. "Expert-demo" obscured it. "Audit-passed"
names it.

The framing is due to Codex's review (see PR #125 thread): *the real
story is not "this domain is expert-level" — it is "this domain's
results have been audited against the CORE claim contract, signed,
and are replay-reproducible."*

---

## Decision

### Rename (semantics-only scope)

The following **user-visible** identifiers are renamed:

| Surface | Before | After |
|---|---|---|
| Ledger status string | `"expert-demo"` | `"audit-passed"` |
| Predicate key on ledger row | `predicates.expert_demo` | `predicates.audit_passed` |
| Reason key on ledger row | `expert_demo_reason` | `audit_passed_reason` |
| `docs/reviewers.yaml` top-level key | `expert_demo_claims` | `audit_passed_claims` |
| CLI demo target | `core demo expert --domain X` | `core demo audit-passed --domain X` |
| Generated artifact JSON name | `expert_demo.json` | `audit_passed.json` |
| Generated artifact HTML name | `expert_demo.html` | `audit_passed.html` |
| Default output directory | `evals/expert_demos/<id>/` | `evals/audit_passed/<id>/` |
| HTML title | `CORE Expert-Demo: <id>` | `CORE Audit-Passed: <id>` |

### Kept (internal Python identifiers, not user-facing)

The following internal names are **deliberately unchanged** to minimize
churn under this ADR's "semantics-only" scope:

- Module names: `core/capability/expert_demo.py`,
  `core/demos/expert_demo.py`
- Function names: `evaluate_expert_demo`, `derive_evidence_digest`,
  `build_expert_demo`, `run_expert_demo`, `_load_registry_for_expert_demo`
- Class names: `ExpertDemoClaim`, `ExpertDemoVerdict`
- Method names on `ReviewerRegistry`: `expert_demo_claim_for`
- Dataclass field names: `ReviewerRegistry.expert_demo_claims`
- ADR file titles: ADR-0106 / ADR-0107 / ADR-0110 / ADR-0111 / ADR-0112
  retain their "expert-demo" titles as historical records
- Test class/method names that include "expert_demo": Python identifiers,
  retained

A future ADR may rename these internal identifiers if desired; that is
explicitly out of scope here.

### Future `expert` namespace reserved

The word `expert` (and any `"expert"` ledger status string above
`"audit-passed"`) is **reserved** for an actual raw-capability claim
backed by a domain-specific capability lane with a human-expert-calibrated
threshold. The current ADR establishes no such tier and no such gate.
ADR-0114+ may define it when there is evidence to gate on.

The status ordering remains a 5-tuple:

```text
blocked → seeded → grounded → reasoning-capable → audit-passed
```

A future `expert` tier would extend this to 6 entries; that extension
requires its own ADR and is out of scope here.

---

## Invariants

### `adr_0113_ledger_status_string_is_audit_passed`

`ledger_report()` reports `"audit-passed"` (not `"expert-demo"`) for
every domain whose contract gate passes. Pinned by every existing
ADR-0110 / ADR-0111 / capability-reports test that was updated to the
new vocabulary.

### `adr_0113_yaml_key_is_audit_passed_claims`

`load_reviewer_registry` reads from the `audit_passed_claims` YAML key.
The legacy `expert_demo_claims` key is **not** accepted (hard cut, no
backwards-compat read). Tested by `test_reviewer_registry.py`.

### `adr_0113_audit_passed_does_not_imply_capability`

The `audit-passed` status string carries no claim about raw task
performance vs. external benchmarks. It is a CORE-claim-contract
compliance status. This invariant is documentary (enforced by the
README + ADR text, not by code).

### `adr_0113_expert_namespace_reserved`

No ledger row carries `predicates.expert` and no `"expert"` status
string is emitted by `ledger_report()`. Tested by the existence of
exactly five statuses in `_EXPERT_DOMAIN_STATUSES`.

---

## Acceptance evidence

Accepted when:

- `_EXPERT_DOMAIN_STATUSES[-1] == "audit-passed"` in
  `core/capability/reporting.py`
- `predicates.audit_passed` (not `expert_demo`) is the key on every
  ledger row
- `docs/reviewers.yaml` top-level key is `audit_passed_claims`
- `core demo audit-passed --domain mathematics_logic` and
  `--domain physics` both produce `all_claims_supported=True` with
  digest match
- All test suites that previously asserted the old strings now assert
  the new strings (or accept both in transitional cases like the
  historical ratification tests)
- README, ADR-0091..0112 narrative refs, runtime_contracts,
  capability_roadmap updated to the new vocabulary (with explicit
  gloss on what `audit-passed` actually means)
- Generated artifacts are renamed (`audit_passed.{json,html}`); the
  default output directory is `evals/audit_passed/<id>/`

---

## Consequences

- The ledger now tells the honest story. `audit-passed` accurately
  names the load-bearing CORE-vs-LLM claim (audit-shape compliance) and
  reserves "expert" for an actual capability claim if/when one ever
  lands.
- External readers can no longer infer "this domain is expert-level"
  from the status string. They must read the gloss: audit-passed =
  signed digest + replay determinism + typed refusal + exact recall —
  claim shapes a transformer cannot structurally produce.
- The future `expert` tier has clean namespace. ADR-0114 may define it
  paired with a domain-specific capability lane (e.g. GSM8K for math).
- ADR-0106 + ADR-0109 contract bodies are unchanged. The gate's
  mechanics are identical; only the names move.
- Generated artifacts under `evals/audit_passed/<id>/` are still
  gitignored per ADR-0112.

---

## Out of scope

- Renaming internal Python identifiers (module / function / class
  names). A separate ADR may do that.
- Defining the `expert` tier above `audit-passed`. ADR-0114+.
- Backward-compatibility reading of the old `expert_demo_claims` YAML
  key. Hard cut. The repo is the single source of truth and ships with
  the new key.
- Re-rendering the ADR-0099 public showcase. That demo composes
  pre-existing scene adapters and is unaffected.
- The `core demo expert` CLI command. Replaced by `core demo
  audit-passed`. No alias.

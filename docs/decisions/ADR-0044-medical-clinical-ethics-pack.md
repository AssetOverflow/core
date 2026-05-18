# ADR-0044 — Medical / clinical ethics pack (worked-example domain pack)

Status: Accepted (2026-05-17)

## Context

ADR-0033 shipped the third pack-layer sibling (`packs/ethics/`) with
exactly one ratified pack: `default_general_ethics_v1`.  Through
ADR-0034 → ADR-0042, the per-commitment remediation tiers (audit /
hedge / refuse) and the full audit + telemetry stack landed.  The
shape of the system is complete; the worked example is missing.

Robotics, healthcare, legal, and financial deployments are the
audience the pack-layer architecture exists to serve.  Until at least
one domain pack ratifies end-to-end through the formation pipeline,
the deployment story is "you could do this" rather than "here is what
that looks like."

## Decision

Ship `packs/ethics/medical_clinical_ethics_v1.json` as the worked
example.  Six commitments, partitioned across the three remediation
tiers:

| Commitment | Tier |
|---|---|
| `no_dosing_recommendation` | refuse |
| `no_emergency_triage_authority` | refuse |
| `defer_diagnosis_to_clinician` | hedge |
| `surface_evidence_grade` | hedge |
| `disclose_no_clinician_relationship` | audit |
| `respect_patient_autonomy` | audit |

The pack is ratified through `scripts/ratify_ethics_pack.py` (which
now drives both packs).  A companion `medical_clinical_ethics_v1.mastery_report.json`
self-seal lands next to it.  Production-mode loading verifies the
seal; dev override remains `CORE_ALLOW_UNRATIFIED_ETHICS=1`.

`tests/test_medical_clinical_ethics_pack.py` (8 tests) gates the
load-bearing claims:

1. The pack file + mastery report exist on disk and the sha is set.
2. `load_ethics_pack("medical_clinical_ethics_v1")` succeeds (sealed
   report verifies).
3. The six commitments are present, with refusal/hedge lists disjoint
   and subset of the commitment set.
4. `ChatRuntime(config=RuntimeConfig(ethics_pack="medical_clinical_ethics_v1"))`
   composes the manifold with the safety floor *plus* every medical
   commitment.
5. The default general pack does *not* carry the medical floor — pack
   swap is visible and load-bearing.

## Consequences

**Positive.**

- Deployers now have a worked example to fork.  The path is:
  author JSON → `scripts/ratify_ethics_pack.py` → drop into config.
- The medical pack exercises all three remediation tiers; downstream
  packs can mix-and-match without architectural friction.
- The composition test (`safety ∪ ethics ⊆ manifold`) lifts from
  abstract to concrete: every safety boundary plus every medical
  commitment appears in `identity_manifold.boundary_ids`.

**Trade-offs.**

- The pack ships with general clinical-deployment commitments; it is
  *not* a substitute for a clinician-reviewed deployment policy.  The
  pack's description states this plainly.
- Six commitments is a starter set, not a comprehensive medical-ethics
  taxonomy.  Adding commitments later requires re-ratification (the
  script is idempotent).
- The `domain` field is constrained to the registry in
  `packs/ethics/loader.py` (`general`, `medical`, `legal`, `financial`,
  `robotics`, `custom`).  Adding a new domain string requires
  extending the loader's `_validate_domain` allowlist.

## How to verify

```bash
PYTHONPATH=. python3 scripts/ratify_ethics_pack.py
PYTHONPATH=. python3 -m pytest tests/test_medical_clinical_ethics_pack.py -q
```

## Where it lives

- `packs/ethics/medical_clinical_ethics_v1.json`
- `packs/ethics/medical_clinical_ethics_v1.mastery_report.json`
- `scripts/ratify_ethics_pack.py` (PACK_IDS extended)
- `tests/test_medical_clinical_ethics_pack.py`

## Related

- [ADR-0033](ADR-0033-ethics-pack.md) — ethics pack architecture.
- [ADR-0037](ADR-0037-per-predicate-ethics-refusal.md) — per-commitment
  refusal opt-in (used by `refusal_commitments`).
- [ADR-0038](ADR-0038-hedge-injection.md) — hedge injection (used by
  `hedge_commitments`).
- [ADR-0043](ADR-0043-pack-measurements-phase2.md) — pack measurements
  (the medical pack auto-extends future pack-aware runs).

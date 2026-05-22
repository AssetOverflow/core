# Capability Reports

Phase A-C adds read-only capability reports. These commands do not mutate packs,
execute dynamic validators, or flip dormant runtime flags.

Available commands:

- `core capability chains --json`
- `core capability flags --json`
- `core capability ledger --json`
- `core capability artifact --lane cognition --split public --version v1 --json`
- `core capability domain-contract --pack-id en_core_cognition_v1 --json`
- `core capability evidence-plan --json`

Day-1 output is expected to be low-status:

| Domain | Expected status | Primary blocker |
| --- | --- | --- |
| `systems_software` | `reasoning-capable` | audit-passed still gated by domain eval thresholds and replay/provenance evidence |
| `mathematics_logic` | `reasoning-capable` | audit-passed still gated by domain eval thresholds and replay/provenance evidence |
| `physics` | `reasoning-capable` | audit-passed still gated by domain eval thresholds and replay/provenance evidence |
| `hebrew_greek_textual_reasoning` | `reasoning-capable` | audit-passed still gated by eval thresholds and replay/provenance evidence |
| `philosophy_theology` | `reasoning-capable` | audit-passed still gated by eval thresholds and replay/provenance evidence |

Status is generated from predicates. A `blocked` row lifts only when the named
gap is closed and the next status predicate passes.

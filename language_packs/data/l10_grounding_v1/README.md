# l10_grounding_v1

Additive relational-predicate seed pack for the L10 stateless execution path.

## Scope

This pack contains only finite-entity grounding, range-restriction, vacuity, contradiction-barrier, and wrong=0 refusal primitives. It is not a general logic curriculum and does not introduce runtime behavior.

## L10 constraints

- Stateless: each row is self-contained and carries no external state dependency.
- Zero-dependency: no corpus, model, or online source is required to interpret the row.
- Finite-entity only: every positive relation is designed to require an explicit finite witness or guarded range.
- Fail closed: manifest OOV policy is `fail_closed`.
- Collision resistant: every lemma uses the `l10_` namespace to avoid collisions with existing packs.

## Checksums

- `lexicon.jsonl` sha256: `829efd10d7f5fa74f1189ec6d621f2a12bc5e7a022fd7a3de436655fc8fe5603`

## Review note

This pack is intentionally additive-only. Runtime loaders may ignore the additional L10 metadata fields until an explicit L10 loader is ratified.

# ADR-0148 — Wire VaultPromotionPolicy into turn boundary

**Status:** Accepted
**Date:** 2026-05-25
**Work item:** W-003

---

## Context

`VaultPromotionPolicy` (introduced in ADR-0014, implemented at
`core/physics/learning.py`) decides whether a stored vault entry should be
promoted from `SPECULATIVE` to `COHERENT` based on its energy profile.

Prior to this ADR, the policy had **zero callers**. Every vault entry written
by `session/context.py` remained `SPECULATIVE` indefinitely, regardless of how
settled or coherent the underlying field region was.

This blocked W-007 (DerivedRecognizer derivation), which requires `COHERENT`
vault entries to serve as valid recognition anchors.

---

## Decision

### 1. Flag in `RuntimeConfig` (`core/config.py`)

```python
vault_promotion_enabled: bool = False
```

Default `False` enforces the **null-drop invariant**: zero behavior change when
disabled. Operators opt in explicitly.

### 2. Energy metadata persisted at store time (`session/context.py`)

In `finalize_turn()`, after `_anchor_pull()` resolves `oriented_state`, the
energy fields are written into the vault payload before `vault.store()`:

```python
if oriented_state.energy is not None:
    payload["energy_raw"] = float(oriented_state.energy.raw)
    payload["energy_class"] = oriented_state.energy.energy_class.value
    payload["coherence_residual"] = float(oriented_state.energy.coherence_residual)
```

Storing raw scalars (not the `EnergyProfile` object) keeps the payload
JSON-serializable and avoids coupling the vault to the energy dataclass.

### 3. `VaultStore.promote_eligible_entries(policy)` (`vault/store.py`)

New method scans all SPECULATIVE entries. For each entry:

1. Parses the stored `epistemic_status` string.
2. If SPECULATIVE, reconstructs a minimal `EnergyProfile` from the stored
   `energy_raw`, `energy_class`, `coherence_residual` fields.
3. Calls `policy.decide(energy)`.
4. If `decision.promote`, updates `epistemic_status` to `COHERENT` in-place.

**Versors are not touched.** `_matrix_cache` is not invalidated because no
versor changes — only metadata mutates. Deterministic recall is unaffected.

### 4. Promotion fires post-finalize in `chat/runtime.py`

After each `finalize_turn()` call in `chat()`:

```python
if self.config.vault_promotion_enabled:
    self._context.vault.promote_eligible_entries(VaultPromotionPolicy())
```

**Why post-finalize, not at store time?**

A freshly stored entry is always `E2+` (new activation, high recency). The
`VaultPromotionPolicy` promotes only `E0`/`E1` entries
(`vault_candidate=True`). A just-written entry will not promote on the same
turn it was written — it needs to cool across subsequent turns. This is the
correct multi-turn crystallization behavior described in ADR-0014.

---

## Consequences

### Positive

- Vault entries can now crystallize: SPECULATIVE regions that settle over
  multiple turns become COHERENT, making them admissible as evidence under
  `min_status=EpistemicStatus.COHERENT` recall.
- W-007 (DerivedRecognizer derivation from promoted entries) is now unblocked.
- Zero coupling change when `vault_promotion_enabled=False` (default).

### Constraints preserved

- **versor_condition invariant**: no versor is modified during promotion.
  `promote_eligible_entries` mutates only `_metadata` dicts.
- **No normalization**: `vault/store.py` is a forbidden normalization site
  per `CLAUDE.md`. Promotion is a metadata-only operation — it does not
  repair, reproject, or normalize any field.
- **No approximate recall**: CGA inner-product scoring is unchanged.
- **Reviewed learning path**: promotion upgrades `epistemic_status` on
  already-stored entries; it does not inject new content or bypass the
  teaching review gate.

---

## Unlocks

- **W-007** — DerivedRecognizer can now query the vault at
  `min_status=EpistemicStatus.COHERENT` and receive crystallized entries as
  recognition anchors.

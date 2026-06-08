# Router-organ hygiene — standing invariant

**Rule:** *No organ may block another organ's legitimate proposal unless it has first positively
recognized the input as belonging to its own family.*

Operationally, in the multi-organ contemplation router (`route_setup` → contemplation pass):

> On any **other** organ's text, when an organ refuses, the refusal reason must map to the
> non-substantive `input_shape` family ("not my domain") — **never** a substantive boundary and
> **never** a growth surface.

## Why this exists

The contemplation pass classifies an `all_refused` problem **boundary-first**: a substantive
`must_remain_refused` family (anything but `input_shape`) blocks any proposal. That is correct
*within* an organ's domain — but if an organ emits a substantive boundary on text that is **not**
its domain, it silently **suppresses another organ's legitimate proposal**.

This exact hazard has now appeared three times:

| Where | Organ | Over-broad refusal | Fix |
|---|---|---|---|
| N6 | R2 | `category_pair_not_found` on any non-R2 text | → `input_shape`; `missing_category_pair` reserved |
| R3e | R3 | `temporal_state` (clock detector) on non-rate text | kept a boundary, **not** a growth surface |
| R3.1 | R3 | `missing_rate` on non-rate R2 text (blocked an R2 proposal) | claim only with a duration present; else `not_rate_shaped` → `input_shape` |

## The gate

`tests/test_router_organ_hygiene.py` enforces it for every organ × every other organ's gold. It is
**MUST-PASS before any new organ joins `route_setup`**: add the new organ's gold to `_GOLD` and its
classifier to `_ORGANS`, and the rule is enforced for free.

In plain terms — an organ's refusals on foreign text must say *"not my problem"*, never *"this is a
broken problem of my kind."* Only a refusal that follows **positive recognition** of the organ's own
structure (e.g. R3's `missing_time` requires a rate clause; `rate_unit_mismatch` requires a rate
clause + a duration) may be a substantive boundary.

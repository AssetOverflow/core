# language_relation_binding

Status: v1 foundation eval  
Scope: deterministic relation binding over `ParsedClaim` records

---

## Purpose

This eval is the first binding layer above `language_claim_parsing`.

Claim parsing identifies typed claim records with exact evidence spans. Relation binding converts those records into explicit relation structures only when the parsed claim carries enough operands.

---

## Non-goals

This eval does not implement:

- general natural-language parsing
- anaphora resolution
- quantity-ledger solving
- algebraic equation construction
- GSM8K solving
- inference of missing attributes
- inference of missing deltas in comparison claims

---

## v1 bindings

| Claim kind | Binding kind | Relation |
|---|---|---|
| `simple_action` | `action_relation` | surface verb |
| `quantity_possession` | `quantity_relation` | `quantity_of` |
| `ditransitive_transfer` | `transfer_relation` | surface transfer verb |
| `spatial_relation` | `spatial_relation` | surface spatial preposition |
| `conditional` | `conditional_relation` | `if_then` |
| `comparison` | `comparative_relation` | `compared_quantity` |
| `negated_possession` | `negated_relation` | `not_has` |
| `temporal_state` | `residual_state_relation` or `unbound` | `had_left_after` |

---

## Refusal / unbound discipline

The binder must not invent missing operands.

Example:

```text
After selling 5 tickets, he had 12 left.
```

The claim parser can extract subject `he`, quantity `12`, and temporal qualifier. But no residual attribute is present after `12`, so the binder returns:

```text
state = UNBOUND
refusal_reason = missing_residual_attribute
```

This is intentional. The quantity-ledger slice can later bind such cases when an antecedent or discourse context supplies the missing attribute.

---

## Fixture layout

```text
cases_public.jsonl
expected_public.jsonl
```

Both files are line-aligned by `case_id`.

---

## Test surface

`tests/test_language_relation_binding.py` verifies:

- all public cases have expectations;
- parser+binding output equals expected records;
- bound relations preserve exact input as `evidence_span`;
- unbound relations carry explicit refusal reasons;
- parser+binding is deterministic across repeated calls;
- direct `bind_claim()` preserves source claim kind and evidence.

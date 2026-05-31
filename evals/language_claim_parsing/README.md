# language_claim_parsing

Status: v1 foundation eval  
Scope: deterministic claim-record parsing over narrow English sentence shapes

---

## Purpose

This eval is the first executable layer above `en_core_syntax_v1`.

`en_core_syntax_v1` ratifies vocabulary for subject, predicate, object, modifier, conditional roles, comparison, negation, and evidence spans. This eval checks whether a narrow deterministic parser can bind those ideas into typed claim records with exact source evidence.

---

## Non-goals

This eval does not attempt full natural-language understanding.

It does not cover:

- arbitrary dependency parsing
- multi-sentence discourse
- anaphora resolution
- algebraic relation binding
- GSM8K solving
- quantity ledger construction
- semantic equivalence across paraphrases

Those are follow-on slices.

---

## v1 claim shapes

The v1 parser recognizes:

| Kind | Example |
|---|---|
| `simple_action` | `John bought apples.` |
| `quantity_possession` | `Mary has 3 books.` |
| `ditransitive_transfer` | `Sarah gave Tim 2 coins.` |
| `spatial_relation` | `The red ball is in the box.` |
| `conditional` | `If it rains, the ground gets wet.` |
| `comparison` | `John has more apples than Mary.` |
| `negated_possession` | `John does not have apples.` |
| `temporal_state` | `After selling 5 tickets, he had 12 left.` |
| `undetermined` | question or unmatched shape |

---

## Refusal discipline

The parser must not guess missing quantities or relations.

Example:

```text
John has fewer apples than Mary. How many apples does John have?
```

Expected:

```text
kind = undetermined
epistemic_state = UNDETERMINED
refusal_reason = insufficient_quantity_evidence
```

---

## Fixture layout

```text
cases_public.jsonl
expected_public.jsonl
```

Both files are line-aligned by `case_id`.

---

## Test surface

`tests/test_language_claim_parsing.py` verifies:

- all public cases have expectations;
- parser output equals expected records;
- every evidenced parse preserves the exact input as `evidence_span`;
- refusal/undetermined cases include a reason;
- parser output is deterministic across repeated calls.

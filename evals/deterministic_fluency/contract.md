# Deterministic Fluency Eval Lane — Contract

**Lane:** `deterministic_fluency`
**Version:** v1
**Created:** 2026-05-19

## What this lane measures

A small, deterministic, structural definition of "fluent" — no
subjective scoring, no embedding similarity, no LLM judge.  Each
case is a prompt + a list of structural predicates the runtime's
final surface must satisfy.

The 2026-05-19 design review observed that several existing eval
lanes (grammatical_coverage, english_fluency_ood) pass surfaces
like `"river flows valley"` and `"knowledge does not necessitates
force"`.  Those surfaces are token-ordered but not English.  This
lane closes that gap with checks that are testable as `bool`
predicates, not felt qualities.

## The six structural predicates

| Predicate | Definition | Implementation |
|---|---|---|
| `no_placeholder` | surface contains no `...`, `<pending>`, `<prior>`, `<empty>` | substring scan |
| `no_provenance_only` | surface is not bare structured disclosure like `"X — pack-grounded (pack_id): a; b; c. No session evidence yet."` | regex match: rejects surfaces matching `^[a-z_]+ — pack-grounded \(.*\): [^.]+\.\s*(No session evidence yet\|No prior turn in this session to correct yet)\.\s*$` |
| `complete_punctuation` | surface ends with `.`, `?`, `!`, or `;` after stripping whitespace | `rstrip().endswith(('.', '?', '!', ';'))` |
| `finite_predicate_shape` | surface contains at least one finite verb (is/are/was/were/has/have/does/do/did) OR an inflected verb form | regex scan for verb tokens |
| `no_dotted_domain_inventory` | surface does not contain three or more dotted-path tokens joined by `;` (e.g. `meta.x.y; meta.x; cognition.z`) | regex match |
| `surface_provenance_match` | actual `grounding_source` is consistent with the runtime's emitted surface tag | metadata cross-check |

Each predicate emits a binary signal per case.  Lane-level metrics
are rates across the predicate × case matrix.

## Scoring rubric

| Metric | Definition | v1 pass threshold |
|---|---|---|
| `no_placeholder_rate`         | fraction of cases passing `no_placeholder`         | 1.00 |
| `complete_punctuation_rate`   | fraction of cases ending with terminal punctuation | 1.00 |
| `finite_predicate_rate`       | fraction of cases with a finite-verb token         | >= 0.90 |
| `no_provenance_only_rate`     | fraction of cases NOT emitting a bare-disclosure surface | varies — see below |
| `no_dotted_inventory_rate`    | fraction of cases NOT emitting dotted-path inventory | varies — see below |

## The "varies" threshold note

Pre-gloss, `no_provenance_only_rate` and `no_dotted_inventory_rate`
will be at the floor (most pack-grounded surfaces today ARE bare
provenance disclosure with dotted paths).  This is expected and
documented — those two metrics are the lift target for the gloss
feature.  After the gloss feature wires through:

  pre-gloss:        no_provenance_only_rate ≈ 0.10, no_dotted_inventory_rate ≈ 0.10
  post-gloss:       no_provenance_only_rate >= 0.85, no_dotted_inventory_rate >= 0.85

## Why this lane is not "subjective fluency"

Every predicate above is decidable in code with no judgment.  A
surface either contains `...` or does not.  Either ends with a
terminal or not.  Either contains `meta.x.y; meta.x; ...` or not.
This is *structural completeness*, not aesthetic quality.

Subjective fluency (rhythm, idiom, register) is OUT OF SCOPE here.
It would require either an LLM judge (non-deterministic, doctrine
violation) or human review (not CI-pinnable).  Either belongs in a
different lane.

## Case schema

```jsonl
{
  "id": "fluency_truth_001",
  "prompt": "What is truth?",
  "category": "pack_definition",
  "expected_predicates": ["no_placeholder", "complete_punctuation",
                          "finite_predicate_shape"],
  "post_gloss_predicates": ["no_provenance_only", "no_dotted_inventory"]
}
```

`expected_predicates` is the set of predicates that must hold today.
`post_gloss_predicates` is the set that will be enforced after the
gloss feature lands — currently informational, not asserted in v1.

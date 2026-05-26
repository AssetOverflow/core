# Ratified Recognizer Registry (ADR-0163 Phase D)

The recognizer registry projects accepted exemplar-corpus proposals
from the append-only proposal log into a tuple the math
candidate-graph consults before refusing on an empty per-statement
choice list.  It is the connective tissue between Phase C's operator
review surface and Phase D/E's admission expansion.

## Projection rule

A proposal enters the registry iff **all** of:

- `source.kind == "exemplar_corpus"` (Phase C's source kind)
- `review_state == "accepted"` (operator ratification — never agent-side)
- `proposed_chain.recognizer_spec` parses as a
  `teaching.recognizer_synthesis.RecognizerSpec`

Pending, rejected, withdrawn, and non-exemplar proposals are
invisible.  Malformed accepted proposals raise `RegistryLoadError`
with the offending `proposal_id` — silent drops are forbidden.

Registry order is `(review_date, proposal_id)` ascending — stable
across runs.

## Match contract

`generate.recognizer_match.match(statement, registry)` returns at most
one `RecognizerMatch` per call (first-match-wins over registry order).
Each per-category matcher is rules-only — no LLM, no embedding, no
learned classifier.  A module-import test pins the no-ML constraint.

`parsed_anchors` carry numeric tokens extracted **from the statement
text**, not from the spec.  For `descriptive_setup_no_quantity`,
`parsed_anchors` is the empty tuple by design — the recognizer admits
the statement as setup context, contributing no math state.

## Narrowness invariant

Per ADR-0163 §Phase C The Synthesis Rule property (b), the
recognizer is the **narrowest** commitment that subsumes the seeds.
The matcher inherits that narrowness verbatim:

- A currency symbol outside the spec's `observed_currency_symbols`
  does not match `rate_with_currency`.
- A window unit outside `observed_window_units` does not match
  `temporal_aggregation`.
- A statement with any digit, number word, or indefinite quantifier
  does not match `descriptive_setup_no_quantity`.

Widening happens through the corridor — wider exemplar corpus →
Phase C synthesis on wider seeds → operator ratifies the wider
proposal — never by editing the matcher's permissiveness.

## Wiring point

`generate/math_candidate_graph.py:parse_and_solve` consults the
registry at the per-statement choice loop, **before** the existing
`no admissible candidate for statement` refusal.  When the registry
recognizes the statement, the statement is dropped from
`per_sentence_choices` and the loop continues.  Empty registry → the
guard is a no-op and the existing behavior is preserved
byte-identically.

Skipping a recognized statement contributes ZERO math state to the
solver, so the Cartesian product is identical to "this statement
was never there."  This preserves `wrong = 0` by construction; the
downstream solver still refuses if the remaining statements +
question cannot produce a consistent answer.

## Ratification boundary (ADR-0161 §5)

The agent does not ratify the live proposal log.  Phase D tests
build a synthetic in-memory `RatifiedRecognizer` tuple from the
Phase C pending proposals' content (`tests/_phase_d_fixture.py`).
The matcher and candidate-graph wiring exercise the same
RecognizerSpec bytes the operator will later ratify, with zero
modification to `teaching/proposals/proposals.jsonl`.

The operator's ratification path is the existing
`core teaching review <proposal_id> --accept --review-date <YYYY-MM-DD>`
— no new CLI surface lands with Phase D.

## Phase E follow-up

Phase D wires the registry into the admission boundary; downstream
consumption of `parsed_anchors` (turning recognized rate/temporal
surfaces into solver state that produces concrete answers) is
deferred to Phase E.  The wiring is in place; Phase E adds the
math_candidate_parser handler that consumes the typed anchors.

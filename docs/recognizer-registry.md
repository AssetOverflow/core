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

## Wiring point (current doctrine — post wrong=0 correction)

`generate/math_candidate_graph.py:parse_and_solve` consults the
registry at the per-statement choice loop, **before** the existing
`no admissible candidate for statement` refusal.

When the registry recognizes the statement:
- the per-category injector (`generate/recognizer_anchor_inject.inject_from_match`)
  is consulted;
- if the injector emits one or more `CandidateInitial` / `CandidateOperation`
  that survive admissibility, those candidates are added to the per-sentence
  choice space exactly as parser output would be;
- if the injector emits nothing (or all candidates are dropped by later
  pronoun/lookback guards), the graph **refuses explicitly** with the
  reason `"recognizer matched but produced no injection for statement: ... (category=...)"`.

**Never silently drop** a recognized math statement as "zero state".
The historical skip-only rule ("drop it, Cartesian product unchanged")
was retired because it admitted incomplete graphs at the problem level
(the solver could answer from the remaining statements and produce a
number that was not the answer to the full input).  The current code
and this document treat "recognized + no typed emission" as a refusal
case.  Old skip-only language appears only in historical notes below.

Empty registry → the guard is a no-op and the pre-registry refusal
behavior is preserved byte-identically.

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

## Phase E / D.2 follow-up (historical note)

Early Phase D wiring (the registry + skip-only guard) was intentionally
"skip-only by construction" so that adding recognizer categories could
not regress wrong=0.  That doctrine was corrected once the "recognized
but uninjected → incomplete graph" hazard was understood (see the
explicit refusal branch and comments in `math_candidate_graph.py` and
the ADR-0167 / Brief 11 lineage).

Current follow-up work (Workstream A Inc 2 and successors) adds the
per-category injectors that turn `parsed_anchors` for `rate_with_currency`
(and later categories) into grounded `CandidateOperation` / `Rate` /
`apply_rate` primitives that the existing solver already knows how to
execute.  When an injector is present and emits, the statement
contributes real solver state; when it cannot, refusal (not silent drop)
is the outcome.

Historical skip-only descriptions are preserved only as "rejected
behavior" markers in this document and in code comments.  Grep for the
old phrases on the active source surfaces should surface only such
markers.

# ADR-0178 GB-1 / GB-2 lookback report

Stream A findings-only report from `docs/handoff/CHATGPT-REMOTE-BRIEF.md`.

No code was changed. This was reviewed through the GitHub connector only; no local tests, CLI eval, or lane-SHA gate were run.

## Sources reviewed

- `docs/handoff/CHATGPT-REMOTE-BRIEF.md`
- `docs/decisions/ADR-0178-compositional-structure.md`
- `generate/derivation/clauses.py`
- `generate/derivation/compose.py`
- `generate/derivation/extract.py`
- `generate/derivation/model.py`
- `generate/derivation/multistep.py`
- `generate/derivation/search.py`
- `generate/derivation/verify.py`
- `generate/derivation/comparatives.py`
- `tests/test_adr_0178_gb1_clauses.py`
- `tests/test_adr_0178_gb2_compose.py`
- selected GSM8K train-sample cases: 0003, 0021, 0024, 0033

## Executive summary

GB-1 and GB-2 are conservative and deterministic. The reviewed paths are sealed under `generate/derivation`, and the visible ambiguous/no-candidate paths return `None` rather than manufacturing an answer.

Main finding: the documents describe GB-2 as a clause-by-clause sequential composer, but the current code is narrower. GB-1 produces `ClauseResult`; GB-2 does not consume it. GB-2 instead re-extracts quantities from the whole problem and implements a first same-unit-list composition slice.

This does not look like a revert-worthy problem. It should be pinned as scope drift before GB-3 so lookback/reevaluation is built on the actual current substrate, not a stronger assumed one.

## Solid findings

### S1 — GB-1 segmentation is deterministic

`segment_clauses()` is terminal-punctuation based and returns stripped non-empty strings in tuple order. The GB-1 tests cover sentence splitting, whitespace collapse, and deterministic replay.

### S2 — GB-1 has a clear hold convention

`ClauseResult.value is None` with `resolved is False` means unresolved/context/hold. Zero-quantity clauses become context, one-quantity clauses become leaves, and multi-quantity clauses only resolve through `search_chain(clause)`.

### S3 — GB-2 candidate construction is ordered

`compose_sequential()` builds candidates in fixed list order: additive list-sum first, multiplicative disagreement candidate second. Cue lists are tuples. `_same_unit()` uses a set only for a boolean cardinality check, not for output ordering.

### S4 — obvious refusal paths are covered

The GB-2 tests cover mixed units, too few quantities, and same-unit sum/product disagreement returning `None`.

### S5 — serving seal appears intact by connector search

Connector search found `compose_sequential` and `clause_local_results` only in derivation files, derivation exports, this handoff context, and tests. I did not find a `chat/**` import. This is only a connector-level observation; Claude still needs the lane-SHA gate.

## Gaps and drift

### G1 — GB-2 does not consume GB-1 output

ADR-0178 frames GB-2 as combining running clause-local results. Current GB-2 does not call `segment_clauses()` or `clause_local_results()`; it calls `extract_quantities(problem_text)` directly.

Recommendation: label the current implementation as a narrow GB-2a/list-structure substrate or amend ADR-0178 before GB-3.

### G2 — segmentation is sentence-level only

ADR-0178 discusses clause segmentation more broadly. Current GB-1 is sentence-level only. This is safe but narrower than the broader ADR language.

### G3 — unresolved local holds discard summary unit

When a multi-quantity clause does not locally resolve, `ClauseResult.unit` is `None` even if all extracted quantities share a unit. Safe, but future held-structure elimination may want that evidence.

### G4 — proof-obligation coverage is partial in the GB tests

The current GB tests do cover ambiguity/refusal and determinism. They only indirectly cover per-step verification and completeness through lower layers. They do not yet directly test locality/referent hazards in GB-2.

### D1 — GB-2 is narrower than the ADR's 0003/0024-class phrasing

Current GB-2 can express same-unit list-sum plus optional comparative scaling. It cannot express case 0003's cross-unit chain. Actual case 0024 also remains blocked until extraction richness handles list-unit inheritance and multi-word units.

### D2 — additive cue scope is whole-problem, not list-local

Any additive cue present in the token stream can license adding all extracted same-unit quantities. That is broader than a reading-licensed local list.

## Candidate hazards to pin before GB-3

These are practice-lane hazards, not serving-lane findings.

### H1 — unrelated same-unit quantities across sentences

Trigger candidate:

Alice has 6 apples and 4 apples. Tom has 2 apples. How many apples does Alice have?

Concern: all numbers have unit `apples`, and `and` is present. A whole-problem same-unit list composer can include Tom's apples in Alice's total unless clause/referent boundaries are enforced.

Expected safe outcome: `None` until referent-aware clause structure exists.

### H2 — comparative attached to the wrong referent

Trigger candidate:

Alice picked 6 apples and 4 apples. Tom picked twice as many apples. How many apples did Alice pick?

Concern: `twice` modifies Tom, not Alice. Current GB-2 applies comparative tails globally to the same-unit list candidate.

Expected safe outcome: `None` or no comparative application unless the comparative is bound to the target structure.

### H3 — later event quantity included in earlier asked scope

Trigger candidate:

Alice picked 6 apples and 4 apples. Later she gave 3 apples away. How many apples did she pick before giving any away?

Concern: the later depletion quantity is same-unit but outside the asked initial-pick scope. Whole-text extraction hides that boundary.

Expected safe outcome: `None` until temporal/depletion/read-scope semantics exist.

## Cross-PR consistency

The shapes are compatible: `ClauseResult` has text, quantities, value, unit, and resolved; `None` is the hold/refusal convention in both layers. But GB-2 does not currently compose GB-1 output, so the two PRs are compatible rather than truly integrated.

## Determinism audit

No replay-significant nondeterminism found in the reviewed code. Regex iteration is left-to-right, candidate lists are ordered, tuple cue order is stable, and set usage is cardinality-only.

## Bottom line

GB-1/GB-2 should stand. Before GB-3, amend/pin the phase language and add hazard tests for H1/H2/H3 so lookback work proceeds against the actual current implementation boundary.

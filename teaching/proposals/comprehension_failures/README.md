# Comprehension failure proposals (proposal-only)

This directory is the **write-only sink** for the contemplation pass (N5/N6). When the loop meets
a *growth-surface* failure family (`proposal_allowed = True` in the N4 registry), it may emit one
content-addressed artifact here:

```
<sha256(failure_family : sha256(problem_text))>.json
```

Every artifact is **deliberately toothless**:

```json
{
  "status": "proposal_only",
  "mounted": false,
  "requires_review": true,
  "suggested_next_fixture": null,
  ...
}
```

## Hard rules (enforced by tests)

- `status` is always `proposal_only`; `mounted` is always `false`; `requires_review` is always `true`.
- **Serving never reads these files.** No `generate/derivation`, `core/reliability_gate`,
  `generate/stream.py`, `field/propagate.py`, or `vault/store.py` references this path.
- The raw problem text is **hashed, never stored** (`problem_text_sha256`).
- The emitter never proposes against a correct wrong=0 boundary (`must_remain_refused` families
  produce no artifact).
- Filenames are content-addressed and deterministic — the same failure writes the same path.

## What happens next

A proposal is an *input to human review*, not a change. The aligned flow is

```
failure -> classification -> proposal -> review -> ratification
```

never `failure -> self-patch`. Ratification (authoring the gold fixture / reader rule) happens
only via a human-reviewed PR through the existing teaching flywheel (ADR-0055/0056/0057). The
engine cannot mount, ratify, or apply anything written here.

Generated artifacts are not committed; this README is the only tracked file in the directory.

# HITL review queue backpressure

To prevent reviewed proposal queues from growing beyond human attention limits, the queue enforces a pending count cap (ADR-0161 §4).

## Configuration

- **Default Cap**: 256 pending proposals.
- **Environment Override**: To temporarily raise the cap, set the `CORE_HITL_PENDING_CAP` environment variable:
  ```bash
  export CORE_HITL_PENDING_CAP=512
  ```

Accepted, rejected, and withdrawn proposals do not count toward the cap.

## Queue Full Reports

When the pending count is at or above the cap, `propose_from_candidate` will refuse to create a new proposal and instead emit a `queue_full` report to the contemplation runs directory:
`contemplation/runs/<ISO-8601-UTC>_queue_full.json`

Example `queue_full` report shape:
```json
{
  "report_kind": "queue_full",
  "emitted_at_revision": "9a738a16...",
  "pending_count": 256,
  "cap": 256,
  "candidates_skipped": [
    {
      "candidate_id": "8a9b2c3d...",
      "shape_category": "factual",
      "reason": "queue_full"
    }
  ]
}
```

The CLI exits with code `1` when capacity is refused, alerting CI runners and operators of the backpressure event.

## Operator Clearance Loop

When the queue is full and proposals are skipped:

1. **Review Pending Proposals**: Inspect the current queue using:
   ```bash
   core teaching hitl-queue list --state pending
   ```
2. **Clear Space**: Ratify or withdraw pending proposals:
   ```bash
   # Accept a proposal
   core teaching review <proposal_id> --accept --review-date 2026-05-26
   
   # Or withdraw a proposal
   core teaching review <proposal_id> --withdraw
   ```
3. **Re-run Propose**: Once pending count falls below the cap, re-run the propose command. Skipped candidates will land successfully as fresh proposals with the same deterministic `proposal_id`.

## Submission invariants

Before the replay gate runs, `propose_from_candidate` applies two additional
content-based checks (ADR-0161 §3, Step 3).  They fire in this order, after
the capacity check:

### Duplicate

A candidate whose deterministic `proposal_id` (SHA-256 over `candidate_id +
proposed_chain`, per ADR-0151) already exists in the log is refused with
`RefusedAsDuplicate`.  This covers all existing states — pending, accepted,
rejected, and withdrawn — because content-identical proposals carry the same
id regardless of their history.

CLI output:

```
duplicate: proposal_id=<id> existing_state=<state>
```

**No log entry is written.**  The refusal is operator-facing only.

### Dependent on pending

A candidate whose `proposed_chain.subject` or `.object` lemma (case-insensitive
exact-match) overlaps with any **pending** proposal's subject or object is
refused with `RefusedAsDependent`.  This prevents ratification-ordering
constraints from being silently baked into the queue.

CLI output:

```
dependent_on_pending: dependent_on=[<proposal_ids>]
overlapping_lemmas=[<lemmas>]
```

**No log entry is written.**  The operator should re-emit the candidate after
the dependency proposal is ratified.

**Conservatism trade-off**: the heuristic uses exact-match on the normalised
lemma string (`strip().lower()`).  A genuinely independent chain that happens
to share a common lemma word (e.g. "truth") will be refused.  This is
intentional: false positives are recoverable (re-emit after the blocking
proposal clears); false negatives silently couple ratification choices.  If
over-rejection becomes frequent, the operator should ratify or withdraw the
blocking pending proposals rather than loosening the heuristic.

### Check order summary

```
capacity check (Step 2)      ← queue_full report, no log entry
  ↓ (if under cap)
duplicate check (Step 3)     ← RefusedAsDuplicate, no log entry
  ↓ (if not duplicate)
dependent_on_pending (Step 3) ← RefusedAsDependent, no log entry
  ↓ (if no dependency)
replay gate                  ← runs; regression auto-rejects via transition
  ↓ (if replay-equivalent)
pending proposal created     ← created event appended to proposals.jsonl
```

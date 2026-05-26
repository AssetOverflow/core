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

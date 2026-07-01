# ADR-0057 — Teaching-Chain Proposal + Review + Replay-Equivalence Gate (Phase C2)

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Completes:** ADR-0055 §Decision Phase C (with [ADR-0056](./ADR-0056-contemplation-loop-c1.md))

---

## Context — how we got here

ADR-0055 introduced a four-tier inter-session memory architecture
and split corpus extension into a **proposal-only** path. ADR-0056
(Phase C1) implemented the cognitive surface: a contemplated
`DiscoveryCandidate` carries `polarity`, `claim_domain`, and
composed `evidence`. C1 explicitly does **not** mutate the active
teaching corpus — its output is structured evidence on disk.

C2 is the **only** path that turns reviewed evidence into a corpus
mutation. It is the riskiest piece in the chain and gets its own
ADR for that reason.

### Three load-bearing calls

#### Call 1 — Replay-equivalence as a *precondition*, not a permission

**Choice:** The replay-equivalence eval gate is a *necessary* but
**not sufficient** condition for corpus append. A proposal that
passes the gate becomes eligible for operator review; the operator
still has to accept it explicitly. The gate eliminates regressions;
the operator decides on the merits.

**Why:**

- CLAUDE.md doctrine: "Pack mutation is proposal-only until
  reviewed." Eval-passing is not review. A chain that doesn't
  regress metrics can still be wrong, harmful, or off-doctrine.
- The gate is mechanical (regress on any metric → auto-reject).
  Review is judgment. Conflating them would smuggle in an
  auto-apply path that bypasses human review.
- Auto-rollback on regression keeps the corpus byte-clean even
  when a proposal is mechanically rejected.

**Rejected alternative:** Replay-equivalent ⇒ auto-append. Same
shape as the smart-mistake C1 was extracted to prevent.

#### Call 2 — Eligibility = `polarity != "undetermined"` AND reviewed-evidence floor

**Choice:** A `DiscoveryCandidate` is *eligible* to become a
`TeachingChainProposal` iff:

1. `polarity ∈ {"affirms", "falsifies"}` (undetermined cannot
   propose — composing to undetermined means the system itself
   isn't sure).
2. `evidence` contains at least one `source="corpus"` pointer
   (reviewed-evidence floor — pack residency alone is shape
   evidence, not relation evidence).
3. `claim_domain != "evaluative"` UNLESS an operator has flagged
   the proposal with `--allow-evaluative` and a strong-tier hedge
   surface is attached (per ADR-0056 evaluative threshold).
4. `boundary_clean=True` (the source turn was not under refusal
   or hedge — boundary-clean is a guard against polluted
   provenance).
5. `proposed_chain` is *complete* — non-null `subject`, `intent`,
   `connective`, `object`.

**Why:** Each gate corresponds to a doctrinal commitment that
CLAUDE.md or an earlier ADR already pinned. Eligibility is a
mechanical check — no judgment. Failing any gate keeps the
candidate as evidence on disk; eligible ones move on for replay
+ review.

#### Call 3 — Append-only proposal log; corpus history append-only too

**Choice:** Every proposal — accepted, rejected (operator),
auto-rejected (replay regression), or withdrawn — is appended to
`teaching/proposals/proposals.jsonl` and never deleted. Accepted
proposals additionally append their `proposed_chain` to the active
corpus (`teaching/cognition_chains/cognition_chains_v1.jsonl`) with
typed `Provenance(source="discovery_promoted", adr_id="adr-0057",
review_date=...)` from ADR-0055 Phase A. The active corpus view
remains derived via the existing `superseded_by` mechanism — C2
adds entries, doesn't rewrite history.

**Why:**

- Append-only history is a CLAUDE.md commitment for replayability.
- The same `Provenance` schema Phase A introduced is the natural
  home for "where did this chain come from"; `discovery_promoted`
  is the canonical source tag.
- Future calibration / re-ratification ADRs (Phase D, E) need the
  full record of every proposal, not just the accepted ones.

---

## Decision — Phase C2 spec

### Data shape

```python
@dataclass(frozen=True, slots=True)
class TeachingChainProposal:
    proposal_id: str                       # sha256(source_candidate_id + chain payload)
    source_candidate_id: str
    proposed_chain: dict[str, Any]         # complete: subject, intent, connective, object
    polarity: Literal["affirms", "falsifies"]
    claim_domain: ClaimDomain
    evidence: tuple[EvidencePointer, ...]
    review_state: Literal["pending", "accepted", "rejected", "withdrawn"]
    operator_note: str = ""
    replay_evidence: ReplayEvidence | None = None
    provenance: Provenance | None = None   # populated on accept
```

```python
@dataclass(frozen=True, slots=True)
class ReplayEvidence:
    baseline: dict[str, float]             # metrics on the active corpus
    candidate: dict[str, float]            # metrics with proposed chain appended
    regressed_metrics: tuple[str, ...]
    replay_equivalent: bool
```

### Replay-equivalence gate

For every proposal that reaches the gate:

1. Snapshot the active corpus file bytes.
2. Run the cognition lane (public + dev + holdout splits) to
   produce the baseline metric set.
3. Append the proposed chain to a *temporary copy* of the corpus,
   invalidate the cached `_corpus_index()`, and re-run the lane
   on the same case sets.
4. Compare metric-for-metric. A metric *regresses* iff its
   candidate value is strictly less than the baseline value
   (no float tolerance — the lane is deterministic).
5. Restore the original corpus bytes (or never touch the active
   file in the first place — see implementation note below).
6. If any metric regressed ⇒ `replay_equivalent=False`,
   proposal auto-transitions to `review_state="rejected"`,
   `operator_note="auto_rollback_regression: <metric list>"`.
7. Otherwise ⇒ `replay_equivalent=True`, proposal stays
   `review_state="pending"` awaiting operator review.

**Implementation note (trust boundary):** the gate must never
write to the active corpus file even transiently. It writes to
an *isolated path* and patches `_corpus_index()` to load from
that path via dependency injection. Active-file bytes are
byte-identical pre/post regardless of outcome.

### Operator review surface

CLI commands (sibling of the existing `core teaching audit`):

```text
core teaching propose <candidate_id> [--from-sink <path>]
    Convert an eligible enriched DiscoveryCandidate into a
    TeachingChainProposal.  Runs the replay-equivalence gate
    immediately.  Idempotent on (candidate_id, chain payload).

core teaching proposals [--state <pending|accepted|rejected|withdrawn>] [--json]
    List proposals; default lists pending.

core teaching review <proposal_id> --accept [--note "..."]
core teaching review <proposal_id> --reject [--note "..."]
core teaching review <proposal_id> --withdraw [--note "..."]
    Operator decision.  --accept on a replay-equivalent proposal
    appends the chain to the active corpus with typed provenance.
    --accept on a non-equivalent proposal is rejected with an
    explicit error.  --reject and --withdraw transition state
    only; the corpus is untouched.
```

### Trust boundary

- **No automatic accept.** Replay-equivalence is a precondition,
  not a permission. Only operator `--accept` writes to the corpus.
- **No corpus rewrites.** Accept appends one new line; entries
  are retired only via the existing `superseded_by` mechanism in
  a separate operator action.
- **No proposal deletion.** All four review states are terminal
  in the append-only log; "delete" doesn't exist.
- **No identity / safety / ethics mutation.** Per ADR-0027 and
  ADR-0029, those packs are out of scope for C2.
- **No clock-time content read.** The `review_date` in
  `Provenance` is the only timestamp; sourced from the operator's
  command invocation, not from runtime hot path.

---

## Non-goals (explicit)

- No async or concurrency primitives — replay is synchronous.
- No cross-pack arbitration (deferred per ADR-0056 Call 2).
- No re-ratification of identity / safety / ethics packs.
- No automatic supersession of existing chains by a new accept;
  supersession is a separate, future operator action.
- No metric-tolerance bands; the lane is deterministic and any
  regression is real.

---

## Verification (acceptance criteria)

- Eligible enriched candidates produce a `TeachingChainProposal`;
  ineligible ones raise with the failing gate named.
- The replay-equivalence gate never mutates the active corpus
  file bytes regardless of outcome.
- A proposal whose chain causes any cognition metric to regress
  auto-transitions to `rejected` with `replay_equivalent=False`
  and an `auto_rollback_regression` note.
- A replay-equivalent proposal stays `pending` until operator
  decision.
- `core teaching review --accept` on a `pending` +
  replay-equivalent proposal appends one line to the active
  corpus with `Provenance(source="discovery_promoted",
  adr_id="adr-0057")` and re-runs the active corpus through
  `_corpus_index()` cleanly (no new drops).
- `core teaching review --accept` on a non-equivalent proposal
  raises and refuses to append.
- The proposals log is append-only; replaying it reconstructs
  the same review-state for every entry.
- `versor_condition(F) < 1e-6` invariant preserved (no algebra
  touched).
- `core eval cognition` numbers unchanged on splits that don't
  include accepted-proposal cases.

---

## Cross-References

- [ADR-0021](./ADR-0021-epistemic-status.md) — `EpistemicStatus`
  COHERENT promotion semantics; C2 is the mechanical surface.
- [ADR-0027](./ADR-0027-identity-packs.md) /
  [ADR-0029](./ADR-0029-safety-pack.md) /
  [ADR-0033](./ADR-0033-ethics-pack.md) — packs out of scope.
- [ADR-0052](./ADR-0052-teaching-grounded-surface.md) — the
  active corpus this loop appends to.
- [ADR-0055](./ADR-0055-inter-session-memory-discovery-promotion.md)
  — the parent design; Phase A's `Provenance` and `superseded_by`
  are the substrate this ADR builds on.
- [ADR-0056](./ADR-0056-contemplation-loop-c1.md) — the cognitive
  surface whose output feeds C2's eligibility gate.

## Governance Cross-Reference (ADR-0225)

This teaching chain proposal review ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: proposal review (`teaching/review.py`, `teaching/proposals.py`) is fail-closed and cannot mutate identity, safety, or ethics packs.
- Versor closure: accepted teaching chains must satisfy strict definitional and geometric invariants (`versor_condition(F) < 1e-6`).
- Reconstruction-over-storage: proposal review builds upon replay verification over exact trace reconstruction rather than approximate state snapshots.
- Replay-equivalence: the replay-equivalence gate (`teaching/replay.py`) guarantees that promoting a proposal introduces zero regressions across cognition evaluation splits.
- Mutation standing: proposals remain strictly `SPECULATIVE` / proposal-only until operator review (`--accept`) and replay verification pass.

# ADR-0055 — Inter-Session Memory: Reviewed Discovery Promotion

**Status:** Proposed
**Date:** 2026-05-18
**Author:** Shay

---

## Context

CORE already has a multi-tier memory story, but it is undocumented as
a single design and uneven in maturity.  This ADR proposes the shape
of inter-session memory **as a coherent surface**, sketches the
proposal-only path that lets the system contribute its own
reviewed-memory candidates, and names the doctrine guardrails so
later implementation ADRs have a contract to land against.

The north-star direction is explicit:

> CORE should eventually learn by self-thought-through and
> successful discoveries — knowledge-vs-truth confirmations
> stumbled on through reasoning, thinking, and responding to users —
> and these should become part of inter-session memory **in the way
> we do memory**, not in a database/embedding store.

"The way we do memory" means: pack-grounded atoms, reviewed
promotion, deterministic replay, append-only audit trail, no
parallel learning path.  This ADR defines what that looks like end
to end.

---

## Today — the four-tier inventory

```text
turn  ─►  session vault      (ephemeral, exact CGA recall)
                  │
                  └─►  TurnEvent / trace_hash / verdicts   (audit-only)
                                       │
                                       ▼
                          DiscoveryCandidate  (proposed; not built)
                                       │
                                       ▼
                          TeachingChainProposal  (reviewed → applied)
                                       │
                                       ▼
                          reviewed teaching corpus
                (teaching/cognition_chains/cognition_chains_v1.jsonl)
                                       │
                                       ▼
                          ratified packs
        (packs/identity/, packs/safety/, packs/ethics/, language_packs/)
```

### Tier 1 — Session vault (`vault/store.py`)

- Exact, deterministic CGA inner-product recall over a deque of
  stored versors.  Ephemeral, per `ChatRuntime` instance.
- ADR-0054 added matrix-cache indexing + batched recall.
- Holds **everything the session has seen** at the algebraic layer.
- Not promoted to inter-session memory automatically.

### Tier 2 — Turn-event audit trail

- Every turn emits a `TurnEvent` (`core/physics/identity.py`) with
  `trace_hash`, `grounding_source`, `safety_verdict`,
  `ethics_verdict`, `refusal_emitted`, `hedge_injected`.
- ADR-0040 added the JSONL telemetry sink; ADR-0041 the fan-out
  + operator readout; ADR-0042 the four-scene audit-tour demo.
- This is **evidence**, not memory — the record of what the system
  did, with enough state to replay it deterministically.
- It is the raw material from which discovery candidates can be
  mined.

### Tier 3 — Reviewed teaching corpus

- `teaching/cognition_chains/cognition_chains_v1.jsonl` (3 chains
  from ADR-0052, 10 after ADR-0053).
- Append-only JSONL.  Every entry carries a provenance tag
  (`adr-0052:reviewed:2026-05-17`,
  `adr-0053:reviewed:2026-05-18`).
- Pack-consistency check at load (ADR-0052): a chain whose subject
  or object is missing from the pack is silently dropped — the
  "every atom is pack-sourced" invariant is enforced at boundary,
  not at write time.
- `teaching/correction.py` is the canonical repair flow for
  per-session corrections; it does not write to the corpus
  automatically.

### Tier 4 — Ratified packs

- `packs/identity/`, `packs/safety/`, `packs/ethics/`,
  `language_packs/data/*`.
- Self-sealed via companion `.mastery_report.json`; verified at
  startup in production mode.
- `PackMutationProposal` (ADR-0051 lineage) is the only path that
  ever changes a pack; mutation is proposal-only until reviewed.
- These are the long-term substrate — what survives across all
  sessions and reboots.

---

## What is missing

1. **No automated promotion from Tier 1/2 to Tier 3.**  Today, a
   chain enters the reviewed corpus only when a human authors it in
   an ADR PR.  The system itself never proposes one, even when its
   own audit trail makes the candidate obvious (e.g., a turn that
   *would have grounded* if a specific chain existed).
2. **No supersession / forgetting semantics in Tier 3.**
   Append-only is correct for audit; it is not sufficient for an
   "active set" view.  A later chain that contradicts an earlier
   one has no way to mark the earlier one inactive.
3. **No audit lane for silent corpus drops.**  ADR-0052's
   pack-consistency check drops chains that reference missing
   lemmas without logging.  A pack swap can therefore silently
   shrink the active corpus.
4. **No discovery-candidate object at all.**  When a turn produces
   evidence that would extend the corpus (a successful comparison
   that grounded via the pack path; a hedge that fired and then
   was acknowledged in a follow-up turn; an OOV that resolved
   cleanly via decomposition), the evidence dies with the
   `TurnEvent`.

This ADR specifies the proposal-only objects and the doctrine
guardrails that close those gaps **without** introducing a
parallel learning path or an opaque LLM step.

---

## Decision — phased scope

### Phase A — make the current story load-bearing

**A1. Audit CLI lane.**  `core teaching audit` (sibling to
`core pack verify`) — diffs the on-disk corpus JSONL against the
loaded-and-pack-consistency-checked corpus and emits:

```json
{
  "corpus_path": "teaching/cognition_chains/cognition_chains_v1.jsonl",
  "lines_on_disk": 10,
  "lines_loaded": 10,
  "lines_dropped": [],
  "drop_reasons": {}
}
```

Lines dropped by the pack-consistency check are surfaced with the
exact reason (`"subject 'X' missing from en_core_cognition_v1"`).
Run as a non-mutating check; safe to wire into CI.

**A2. Active-set view.**  Add a `superseded_by: chain_id | null`
field to corpus entries (with default `null`).  The loader filters
out any chain whose `chain_id` appears as another's
`superseded_by`.  Append-only history is preserved on disk; the
active corpus is a derived view.  Existing 10 chains carry
`superseded_by: null` — no behaviour change.

**A3. Explicit provenance enum.**  Today `provenance` is a free
string (`adr-0052:reviewed:2026-05-17`).  Constrain it to a typed
shape: `{adr_id, source, review_date}` where `source ∈
{"hand_authored", "discovery_promoted", "imported"}`.  Existing
chains rewrite to `source="hand_authored"`.

Phase A introduces **no learning** and **no automation**.  It
makes the existing corpus inspectable, supersedable, and
provenance-typed so the later phases have something safe to write
into.

### Phase B — `DiscoveryCandidate` from the turn loop

A passive emitter on the `TurnEvent` pipeline that produces a
typed candidate object **whenever** a deterministic rule fires:

```python
@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    candidate_id: str                # deterministic hash of contents
    proposed_chain: dict             # subject / intent / connective / object
    trigger: Literal[
        "would_have_grounded",       # turn fell through to universal disclosure
                                     # but a single missing chain would have grounded it
        "successful_comparison",     # COMPARISON path produced a coherent surface
                                     # that the user did not correct
        "hedge_acknowledged",        # hedge_injected then a follow-up turn left it
                                     # unchallenged
        "oov_resolved_via_decomp",   # decomposition produced a deterministic surface
    ]
    source_turn_trace: str           # the originating TurnEvent.trace_hash
    pack_consistent: bool            # subject + object are pack lemmas
    boundary_clean: bool             # no safety/ethics verdict violation in the turn
    review_state: Literal["unreviewed"]  # ALWAYS unreviewed on emit
```

Emission rules are **deterministic and pack-derived** — no LLM
judgement, no stochastic sampling.  A candidate is just structured
evidence: "the audit trail says this turn meets condition X."

Candidates are written to a separate file
(`teaching/discovery_candidates/<YYYY>/<YYYY-MM>.jsonl`,
append-only, per-month rollover for inspection ergonomics).  They
**never** load into the active corpus.

### Phase C — `TeachingChainProposal` (the review surface)

Sibling to `PackMutationProposal`.  Reading a `DiscoveryCandidate`
and turning it into a proposed corpus addition is **proposal-only**:

```python
@dataclass(frozen=True, slots=True)
class TeachingChainProposal:
    proposal_id: str                 # deterministic
    candidate_id: str                # the DiscoveryCandidate it came from
    proposed_entry: dict             # the JSONL line that would be appended
    replay_equivalence_hash: str     # eval-lane trace hashes BEFORE the proposal
    rationale: str                   # template-formatted, not free text
    requires: tuple[str, ...]        # invariants the reviewer must confirm
```

`core teaching propose` CLI generates proposals from recent
candidates.  `core teaching review` lists proposals and accepts /
rejects them.  Acceptance:

1. Runs the cognition eval lane on dev + public splits **before**
   appending — captures `replay_equivalence_hash`.
2. Appends the entry to the corpus JSONL with
   `source="discovery_promoted"` and the originating
   `candidate_id` recorded in `provenance`.
3. Re-runs the eval lane.  If any metric regresses on either
   split, the append is rolled back (`git checkout --` the corpus
   file) and the proposal is marked `rejected_by_replay`.

This is the **only** path by which the system contributes to its
own inter-session memory.  Identity / safety / ethics packs are
**out of scope** for discovery promotion — they remain
hand-authored, hand-ratified.

### Phase D — knowledge-vs-truth: epistemic-tier-aware discovery

Tie discovery into ADR-0021's `EpistemicStatus`.  A candidate is
upgraded to a proposal only when the **source turn's vault entries
are admissible as evidence** (`EpistemicStatus.COHERENT`).
SPECULATIVE / CONTESTED / FALSIFIED turns produce candidates but
**not** proposals — they are kept as evidence-of-reasoning,
inspectable but inert.

This is the doctrine-aligned shape of "knowledge-vs-truth
confirmation":

- **Knowledge** = a chain present in the active corpus.
- **Coherence judgement** = the `EpistemicStatus` stamp on the
  evidence behind the candidate.
- **Truth** = survives review + replay-equivalence on the eval
  lanes.

The system does not assert truth.  It surfaces candidates whose
*own evidence* meets the coherence bar, and review decides.

### Phase E — curriculum integration

Once Phases A–D are deterministic and replay-stable, the
`evals.identity_divergence` and `formation/templates/`
curriculum-teaching path (see [[curriculum-platform]],
[[identity-doctrine]] memories) can consume discovery-promoted
chains as **curriculum candidates** — the same review gate, but
the artifact lives in formation rather than the teaching corpus.

This phase is explicitly **not** the place to ratify identity
shifts.  Identity packs stay hand-ratified per ADR-0027.

---

## Why this is doctrine-aligned

1. **No parallel learning path.**  Every promotion routes through
   `teaching/` review.  Identity / safety / ethics packs are
   off-limits to discovery promotion.
2. **No opaque LLM step.**  Candidate emission is deterministic
   rule-firing on the audit trail.  Replay-equivalence is a
   trace-hash comparison.
3. **Proposal-only by construction.**  `DiscoveryCandidate` and
   `TeachingChainProposal` are typed objects with explicit
   `review_state`.  Nothing applies without review + replay.
4. **Append-only with supersession, not mutation.**  History is
   preserved on disk; the loader derives the active view.
5. **Pack-consistency check stays the gate.**  A chain that
   refers to non-pack atoms is dropped at load — the same gate
   that protects today's 10 chains protects every future
   discovery-promoted entry.
6. **Deterministic replay is the safety net.**  An accepted
   proposal that regresses any eval-lane metric is rolled back.
7. **Identity informs doing.**  This ADR adds capability, not
   identity.  The system learns *how it grounds*, not *what it
   is*.

---

## Non-goals

- **Vector / embedding memory.**  CGA inner product remains the
  algebraic recall metric.  No HNSW, no ANN, no cosine.
- **Database storage.**  Inter-session memory is reviewed JSONL +
  ratified packs.  No SQL, no embedded KV store, no graph DB.
- **Automatic identity / safety / ethics pack mutation.**  Those
  remain hand-ratified.
- **Free-text reasoning logs as memory.**  Only typed,
  pack-grounded chains promote.
- **Removing the human reviewer.**  Review is part of the
  doctrine, not a placeholder for automation.

---

## Open questions

1. **Granularity of `DiscoveryCandidate` triggers.**  The four
   listed are the tightest; a fifth ("refusal averted by hedge")
   is tempting but needs a clean predicate before it can be
   deterministic.
2. **Storage of unreviewed candidates.**  Monthly JSONL rollover
   is one option; per-session is another.  Per-month was chosen
   for inspection ergonomics — revisit once volume is known.
3. **Replay-equivalence on holdouts.**  ADR-0054 wired
   `--split holdout`.  Acceptance currently runs dev + public; the
   call is whether the holdout split is also a regression gate.
   Probably yes once holdout numbers stabilise.
4. **Multilingual packs.**  Discovery promotion is currently
   English-only (`en_core_cognition_v1`).  The proposal mechanism
   generalises; the trigger rules may need per-pack tuning.
5. **What "successful comparison" means.**  Today the pack-grounded
   COMPARISON surface is emitted regardless of user follow-up.
   A trigger that conditions on *user did not correct in the next
   turn* is a stronger but session-spanning signal — needs care
   to stay deterministic.

---

## Cross-References

- [ADR-0021](./ADR-0021-epistemic-status.md) — `EpistemicStatus`
  tiers that Phase D depends on.
- [ADR-0027](./ADR-0027-identity-packs.md) — ratified-pack
  authority; out of scope for discovery promotion.
- [ADR-0040](./ADR-0040-structured-logging-sink.md) /
  [ADR-0041](./ADR-0041-fanout-sink-cli-verdicts.md) — turn-event
  telemetry that Phase B reads from.
- [ADR-0051](./ADR-0051-trust-boundary-hardening.md) — the
  `PackMutationProposal` lineage `TeachingChainProposal` mirrors.
- [ADR-0052](./ADR-0052-teaching-grounded-surface.md) —
  pack-consistency gate at load that Phase A makes inspectable
  and Phase C relies on.
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the existing
  hand-authored corpus this ADR proposes to extend in a
  reviewed-machine-contributed way.

---

## Verification (phase-by-phase)

This ADR is Proposed; no code yet.  Each phase lands as its own
ADR.  Acceptance criteria, expressed up front so later ADRs have
a contract:

- **Phase A**: `core teaching audit` is deterministic; corpus
  drops surface with reason; supersession field defaults `null`
  and changes nothing.  Eval lanes unchanged.
- **Phase B**: `DiscoveryCandidate` emission is replay-equivalent
  — same session, same prompts ⇒ same candidate file.  No
  candidate ever writes to the corpus.
- **Phase C**: A proposal that regresses any eval-lane metric on
  dev or public is rolled back automatically.  No proposal
  applies without review.
- **Phase D**: SPECULATIVE / CONTESTED / FALSIFIED candidates
  never become proposals.  Proven by case-level tests on each
  status.
- **Phase E**: Identity-divergence eval baseline unchanged after
  curriculum candidates are introduced (no identity drift).

The non-negotiable field invariant (`versor_condition(F) < 1e-6`)
is preserved by construction at every phase — none of this work
touches the algebra path.

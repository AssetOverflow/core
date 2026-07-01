# ADR-0056 — Contemplation Loop: Question Decomposition + Polarity + Domain Typing (Phase C1)

**Status:** Accepted (implemented at `4eecf73`, 2026-05-18)
**Date:** 2026-05-18
**Author:** Shay
**Supersedes part of:** ADR-0055 §Decision Phase C (split into C1 + C2)

---

## Context — how we got here

ADR-0055 originally proposed a single Phase C: "`TeachingChainProposal`,
a sibling to `PackMutationProposal`, sits between discovery and the
active corpus." Conversation while landing Phase B exposed that this
single-phase framing collapsed two distinct concerns:

1. **Cognitive work** — taking a posed question (a Phase B candidate)
   and *thinking through it*: decomposing into sub-questions,
   gathering both confirming and falsifying evidence, composing the
   result.
2. **Review surface** — taking a fully-composed proposal and
   gating it through human review + eval-lane replay-equivalence
   before any corpus mutation.

Conflating these into one phase had three concrete problems:

- The cognitive surface (the part where the system actually *thinks*)
  would be invisible — only the input (a Phase B candidate) and the
  output (an accepted corpus entry) would be auditable. The thinking
  in between would happen during review prep, not as a first-class,
  inspectable runtime artifact.
- The riskiest machinery (auto-apply on replay-equivalence pass)
  would ship at the same time as the most interesting, least-tested
  cognitive machinery. Both new at once.
- Three load-bearing distinctions the user surfaced ("contemplation
  starts with a question," "truths AND falsities both count,"
  "domain-relative humility") have no natural home in a pure review
  ADR — they belong to the cognitive surface.

The user's framing was: *"contemplation always starts with a question
… recursion … refining by finding truths and/or finding falsities …
remain humble and think and reason with humility."*

That language is precise enough to drive architecture. This ADR
extracts the cognitive half as Phase C1; the review-and-apply half
moves to a separate future ADR (Phase C2).

### Decision record — four load-bearing calls

These were debated in conversation; recording them here so future
sessions can re-derive the reasoning instead of re-arguing it.

#### Call 1 — Stopping condition for recursive sub-question decomposition

**Choice:** Epistemic rule = "stop when the sub-question cannot be
decomposed further." Engineering failsafe = bounded depth ceiling
whose hit emits a telemetry signal.

**Why:**

- A "success" rule alone ("stop when every sub-question grounded")
  cannot terminate on un-decomposable gaps — the loop spins forever
  on questions whose answers don't exist yet.
- A pure depth-ceiling rule pretends the limit is epistemically
  meaningful — it is not. Depth 5 may be productive; depth 3 may
  fully ground. Hardcoding a number is arbitrary.
- (c) "record the gap and stop" is doctrinally right: a recorded
  gap *is information* — the system has truthfully reported what it
  does not yet know, and that gap becomes a new Phase B candidate
  on its own merits. This composes with the rest of the loop.
- The depth ceiling stays in the design as a *failsafe* whose
  triggering is itself an audit event (`recursion_overflow`),
  never as the "real" stop. Silent truncation of the system's own
  thinking is exactly the opaque shortcut CLAUDE.md forbids.

**Rejected alternatives:**

- (a) bounded depth alone — discussed above.
- (b) "all sub-questions grounded" — success condition masquerading
  as stop condition.
- "stop on first sub-question failure" — too eager; throws away
  partial structure that may itself be promotable.

#### Call 2 — What counts as falsification evidence

**Choice:** Only **reviewed evidence** in the *same pack family* —
a corpus chain with opposite connective on the same `(subject,
object)`, or a ratified pack contradiction within the cognition-pack
family — falsifies a claim. Session-tier evidence contests but does
not falsify. Cross-pack falsification (ethics-pack vs cognition-pack)
is out of scope.

**Why:**

- CLAUDE.md: "session memory may be immediate; reviewed memory must
  go through `teaching/*`." Allowing session-tier corrections to
  falsify by themselves would smuggle in a parallel learning path.
- ADR-0021's `EpistemicStatus` already encodes this split:
  `COHERENT` promotes, `FALSIFIED` falsifies, `SPECULATIVE` and
  `CONTESTED` do neither. C1 doesn't add a new tier; it uses the
  existing one.
- Cross-pack arbitration is a real future problem (does an ethics
  commitment override a cognition claim?) but mixing it into C1
  would make the loop un-shippable. Same-pack falsification is the
  90% case; cross-pack is its own ADR.

**Rejected alternatives:**

- Pack-grounded surfaces as falsification evidence — pack
  `semantic_domains` don't actually express negation; they describe
  a subject's facets. Treating a pack-grounded surface as
  falsification would over-claim what the pack asserts.
- User corrections as direct falsification — corrections must go
  through `teaching/correction.py` review first. They become
  reviewed evidence only after that path completes.

#### Call 3 — Order: C1 (cognitive) before C2 (review-and-apply)

**Choice:** C1 lands first. C1's output is an *enriched*
`DiscoveryCandidate` with `proposed_chain.connective`,
`proposed_chain.object`, `polarity`, `claim_domain`, and accumulated
evidence pointers populated by the contemplation loop. Still
`review_state="unreviewed"`. **C1 never mutates the corpus.** C2
ships later as the review surface that finally permits append-on-
accept.

**Why:**

- The interesting work is the cognitive surface. Landing it first
  means the contemplation loop is exercised, inspected, and tested
  while it is *physically incapable* of touching the active corpus.
- The risky work is auto-apply on replay-equivalence pass. Landing
  it last means it ships with the maximum testing lead time and
  with an already-populated backlog of enriched candidates ready
  for review.
- Matches CLAUDE.md sequencing: "Expand curriculum teaching after
  replay/eval/calibration remain deterministic." C1 IS the
  curriculum-teaching surface; C2 is the bigger downstream commit.
- Reverses the earlier (instinctive) "land the small thing first"
  inclination. The "small" review surface is *useless* without
  enriched input; the cognitive surface is *useful* even without
  auto-apply (humans can review the JSONL pile directly).

**Rejected alternative:** C2 first (the original instinct). It
would ship as machinery with no real input — only Phase B's
partials with `connective=None, object=None`. A human reviewer
could hand-author the answer, but then C2 is a glorified discovery
log, not learning.

#### Call 4 — Sync vs async for the contemplation loop

**Choice:** Synchronous probe-list iteration. **No `asyncio.gather`,
no concurrency primitives, no thread pool.**

**Why:**

- CORE's hot path is deterministic by construction (exact CGA
  recall, no stochastic sampling, no clock-time reads). Async
  introduces nondeterministic completion order; tests that rely on
  trace-hash equivalence across runs would become flaky-by-design.
- Every grounding probe C1 runs is *fast and local*: vault recall
  is one matrix sweep (ADR-0054), pack lookup is a dict get,
  corpus lookup is a dict get. Concurrency overhead exceeds probe
  cost on a 32-component vault under a few thousand entries.
- Sync iteration preserves the canonical order
  (vault → pack → teaching corpus → gap) declared in
  `_maybe_pack_grounded_surface`. That order is itself
  audit-relevant — the first probe that grounds wins, and "which
  source grounded first" is part of the candidate's provenance.
- Async is a real architectural option *only* when a probe blocks
  on I/O (future remote pack fetch, network-backed knowledge
  source, etc.). None exist today. When one does, the right move
  is a separate ADR introducing async at that boundary, not
  retrofitting it everywhere.

**Rejected alternative:** `asyncio.gather` over sub-question probes.
Deferred to a future ADR if/when a blocking probe surface exists.

---

## Decision — Phase C1 spec

### Data shape

C1 enriches `DiscoveryCandidate` with four typed fields. The
existing Phase B fields stay; the new fields default to values
that make a Phase B candidate trivially valid as an unenriched
C1 candidate:

```python
@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    # Phase B fields (unchanged)
    candidate_id: str
    proposed_chain: dict[str, Any]   # subject, intent, connective?, object?
    trigger: DiscoveryTrigger
    source_turn_trace: str
    pack_consistent: bool
    boundary_clean: bool
    review_state: Literal["unreviewed"] = "unreviewed"

    # Phase C1 fields (NEW)
    polarity: Literal["affirms", "falsifies", "undetermined"] = "undetermined"
    claim_domain: ClaimDomain = "factual"
    evidence: tuple[EvidencePointer, ...] = ()
    sub_questions: tuple[SubQuestion, ...] = ()
    contemplation_depth: int = 0
    recursion_overflow: bool = False
```

#### `polarity`

Three values:
- `"affirms"` — composed evidence supports the proposed
  `(subject, connective, object)` relation.
- `"falsifies"` — composed evidence supports the *negation* of the
  proposed relation. Falsified candidates are first-class: the
  corpus learns what is NOT the case as much as what is.
- `"undetermined"` — the contemplation loop terminated without
  enough reviewed evidence on either side. The candidate records
  the gap but does not assert direction. Phase B candidates that
  have not yet been contemplated start here.

Placing polarity *on the chain itself* (not in a separate "anti-
chain" file) keeps the corpus single-source-of-truth and lets the
existing `superseded_by` mechanism work uniformly across affirming
and falsifying entries.

#### `claim_domain` taxonomy

```python
ClaimDomain = Literal["factual", "relational", "evaluative"]
```

- **`factual`** — claims whose truth-value is independent of
  context, observer, or value judgment. Example:
  `light reveals truth` is factual within the cognition pack:
  pack atoms compose; the relation either holds or it doesn't.
  Evidence threshold: **one consistent line of reviewed evidence.**
- **`relational`** — claims whose truth-value depends on the
  relation/context between the subject and the surrounding frame.
  Example: `wisdom orders judgment` is partly relational —
  whether wisdom *orders* judgment vs *informs* it vs *constrains*
  it depends on which other concepts are co-active in the frame.
  Evidence threshold: **multiple consistent reviewed lines AND no
  reviewed contradictions.**
- **`evaluative`** — claims that carry a value or aesthetic
  judgment, especially about people, style, intent, character.
  Example: `this user is direct` or `this argument is elegant`.
  Evidence threshold: **highest** — multiple reviewed lines, no
  reviewed contradictions, AND a strong-tier hedge surface MUST
  be attached. The doctrinal commitment is humility: in evaluative
  territory the system speaks hedged or not at all.

The thresholds are *guidance for the future C2 review gate* —
C1 does not enforce them. C1 only *classifies*. Classification
itself is deterministic:

- Default `"factual"` for pack-resident cognition lemmas where
  both subject and object are in `en_core_cognition_v1`.
- `"relational"` triggered by intent ∈ {COMPARISON, CAUSE} with
  a frame-dependent connective (e.g., `orders`, `grounds`,
  `informs`) — a small reviewed table in the cognition pack
  declares which connectives are frame-dependent.
- `"evaluative"` triggered by intent classification surfacing a
  person/style/intent referent (today: not classified — reserved
  for when intent classification grows that axis). Until then,
  `evaluative` is only assignable by an operator on review.

The classification table is itself versioned pack data, not code
constants, so refining the taxonomy doesn't require a code change.

#### `EvidencePointer`

```python
@dataclass(frozen=True, slots=True)
class EvidencePointer:
    source: Literal["corpus", "pack", "vault_coherent"]
    ref: str                       # chain_id, pack_lemma, or vault_index
    polarity: Literal["affirms", "falsifies"]
    epistemic_status: str          # mirrors ADR-0021 EpistemicStatus
```

Only `"corpus"` (reviewed teaching chains), `"pack"` (ratified pack
contradictions within the same family), and `"vault_coherent"`
(session vault entries stamped `EpistemicStatus.COHERENT`) are
admissible evidence pointers. SPECULATIVE / CONTESTED /
FALSIFIED vault entries are ignored — they contest but do not
contribute as evidence.

#### `SubQuestion`

```python
@dataclass(frozen=True, slots=True)
class SubQuestion:
    sub_id: str                    # deterministic hash; suffix on parent candidate_id
    proposed_subject: str
    proposed_intent: str
    outcome: Literal["grounded", "gap_recorded", "depth_failsafe"]
    evidence: tuple[EvidencePointer, ...] = ()
```

`outcome="gap_recorded"` is the load-bearing case from Call 1: the
sub-question couldn't be decomposed further, so the system records
the gap as its own first-class artifact. Gap-recorded sub-questions
spawn new top-level `DiscoveryCandidate` entries via the existing
Phase B sink — the recursion is reified into the same stream.

### Contemplation loop shape

```text
def contemplate(candidate: DiscoveryCandidate, *, max_depth: int = 8) -> DiscoveryCandidate:
    if candidate.contemplation_depth >= max_depth:
        return replace(candidate, recursion_overflow=True)   # failsafe, audited

    decomposition = decompose_question(candidate.proposed_chain)
    if decomposition.terminal:
        # Cannot decompose further — record gap, return undetermined.
        return replace(candidate, sub_questions=(_gap_subquestion(candidate),))

    sub_results: list[SubQuestion] = []
    for sub in decomposition.sub_questions:
        sub_candidate = _materialise_sub_candidate(sub, parent=candidate)
        # Synchronous probe: vault → pack → corpus → recurse if still ungrounded.
        ev = probe_for_evidence(sub_candidate)
        if ev.grounded:
            sub_results.append(_grounded(sub, ev))
        else:
            recursed = contemplate(sub_candidate, max_depth=max_depth)
            sub_results.append(_summarise(recursed))

    composed = compose(candidate, tuple(sub_results))
    return composed
```

Every step is a pure function over its inputs. `_materialise_sub_candidate`
derives a `sub_id` deterministically from `(parent.candidate_id, sub.index)`.
`probe_for_evidence` calls — in order — vault.recall (matrix-cached
ADR-0054 path), pack lookup, corpus lookup. The order is canonical;
the first grounding source wins and is recorded in the evidence
pointer.

### Composition rules

After all sub-questions return, `compose` reduces them to a single
polarity verdict on the parent:

- All sub-evidence affirms ⇒ parent polarity `affirms`.
- All sub-evidence falsifies (or one direct same-pack contradiction
  on the parent itself) ⇒ parent polarity `falsifies`.
- Mixed evidence with no clear majority of reviewed lines ⇒
  parent polarity `undetermined` and `claim_domain` upgraded one
  tier (factual → relational, relational → evaluative) so the
  later review gate demands more before accepting.

Composition is deterministic: no thresholds with floating-point
math, no scoring weights — every rule is a typed predicate over
the evidence tuple.

### What gets written

Enriched candidates emit through the **same** Phase B sink — the
JSONL line just has more fields populated. No new file, no new
path. The on-disk record stays append-only.

Gap-recorded sub-questions emit as **separate** Phase B candidates
on the same sink — each gap is its own first-class question the
system has identified. This is the recursion-into-the-stream
property.

---

## Trust boundary

- **No corpus mutation.** C1 reads `_pack_index()`,
  `_corpus_index()`, vault, and the most recent `TurnEvent`. It
  writes only to the discovery sink. The active corpus on disk is
  byte-identical before and after a contemplation pass.
- **No identity / safety / ethics pack mutation.** Ratified packs
  are read-only from this loop.
- **No clock-time reads.** Trace hashes and candidate ids are
  derived from content, not wall-clock.
- **No external I/O.** All probes hit in-process indices.

---

## Non-goals (explicit)

- No `TeachingChainProposal` typed object (that is C2).
- No `core teaching propose` / `core teaching review` CLI (C2).
- No replay-equivalence eval-lane gating (C2).
- No corpus append-on-accept (C2).
- No async or concurrency primitives — per Call 4, deferred to a
  future ADR only if a blocking probe surface emerges.
- No cross-pack falsification arbitration — per Call 2, deferred.
- No LLM judgement step, anywhere in the loop.

---

## Verification (acceptance criteria for the eventual C1 PR)

- `contemplate(candidate)` is deterministic: same inputs produce
  identical enriched-candidate JSONL bytes across runs.
- An empty corpus + empty pack still terminates (every probe
  fails, every sub-question gap-records, the parent returns
  `undetermined` with non-empty `sub_questions`).
- A factual candidate whose evidence is one reviewed corpus line
  composes to `polarity="affirms"`, `claim_domain="factual"`.
- A candidate whose direct same-pack contradiction exists composes
  to `polarity="falsifies"`.
- Mixed-evidence candidates upgrade `claim_domain` by exactly one
  tier and stay `polarity="undetermined"`.
- Recursion-overflow flips `recursion_overflow=True` and emits the
  telemetry signal — never silently truncates.
- Cognition eval lane unchanged on dev / public / holdout splits.
- `versor_condition(F) < 1e-6` invariant preserved (C1 touches no
  algebra path).

---

## Open questions (deferred, but named)

1. **Frame-dependent connective table.** `claim_domain="relational"`
   classification relies on a reviewed list of frame-dependent
   connectives (`orders`, `grounds`, `informs`, …). That list is
   pack data, not code — but who authors v1? Likely a small PR
   alongside the C1 implementation.
2. **Evaluative classifier without person-axis intent.** Today's
   intent classifier has no person/style axis. Until it does,
   `claim_domain="evaluative"` is operator-assigned only. That is
   the conservative default — the system never silently classifies
   a claim as evaluative.
3. **Telemetry signal shape for recursion overflow.** Likely a new
   `TurnEvent` flag or a sibling sink to the discovery sink. C2
   may need to consult overflow signals when scoring proposals.
4. **Sub-question deduplication.** Two parallel candidates may
   produce the same sub-question independently. The current design
   emits both — the receiving sink could dedupe by `sub_id`, but
   that conflicts with the per-trace audit story. Probably leave
   it: duplication IS information about which parent asked.

---

## Cross-References

- [ADR-0021](./ADR-0021-epistemic-status.md) — the
  `EpistemicStatus` substrate this loop reuses. `COHERENT` promotes,
  `FALSIFIED` falsifies, `SPECULATIVE`/`CONTESTED` contest.
- [ADR-0027](./ADR-0027-identity-packs.md) — ratified pack
  authority. C1 reads packs; never mutates them.
- [ADR-0038](./ADR-0038-hedge-injection.md) — the hedge surface
  C2 will plumb into for `claim_domain="evaluative"` humility
  enforcement.
- [ADR-0040](./ADR-0040-structured-logging-sink.md) /
  [ADR-0041](./ADR-0041-fanout-sink-cli-verdicts.md) — sink
  pattern this loop reuses.
- [ADR-0052](./ADR-0052-teaching-grounded-surface.md) — the
  reviewed teaching corpus this loop reads as evidence.
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the
  `teaching/correction.py` repair path that produces *reviewed*
  evidence after a session correction passes review.
- [ADR-0054](./ADR-0054-vault-recall-indexing-batching.md) — the
  cached-matrix vault recall the loop's per-probe vault lookup
  uses.
- [ADR-0055](./ADR-0055-inter-session-memory-discovery-promotion.md)
  — the parent design; this ADR extracts and refines its
  Phase C cognitive half.
- Future ADR (Phase C2) — `TeachingChainProposal` + review +
  replay-equivalence + corpus append-on-accept.

---

## Verification of provenance (for future re-derivation)

The four calls above were made in conversation on 2026-05-18 after
Phase B (`07d35c0`) landed. The user surfaced three load-bearing
distinctions:

> "contemplation always starts with a question"
> "refining by finding truths and/or finding falsities"
> "needing more evidence or proof before deciding on things as to
>  not be 'judgemental' or better put, to remain humble and think
>  and reason with humility"

Each maps directly onto a C1 design element:

- "question" → `DiscoveryCandidate` is the posing of the question;
  contemplation is the answering step.
- "truths and/or falsities" → `polarity ∈ {affirms, falsifies,
  undetermined}` on the chain itself.
- "humility" → `claim_domain` taxonomy with escalating evidence
  thresholds and mandatory hedge surfaces in evaluative territory.

The split of Phase C into C1 + C2, and the choice to land the
cognitive half before the auto-apply half, was an explicit
re-decision against my earlier instinct to land C2 first. Reasoning
recorded in Call 3 above. Future sessions that re-encounter the
question "should the review surface ship first?" can re-derive
the no-answer from that record without re-arguing.

## Governance Cross-Reference (ADR-0225)

This contemplation loop ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: contemplation probe execution (`teaching/contemplation.py`) is deterministic, read-only, and synchronous; off-limits to safety/identity mutation.
- Versor closure: sub-question decomposition and evidence composition preserve exact geometric field invariants (`versor_condition(F) < 1e-6`).
- Reconstruction-over-storage: contemplation probes derive evidence at runtime from pack manifests and exact recall indices.
- Replay-equivalence: synchronous contemplation loops execute deterministically and produce byte-identical candidate structures across identical traces.
- Mutation standing: contemplation loop outputs remain `SPECULATIVE` / unreviewed candidates until promoted via the reviewed teaching path.

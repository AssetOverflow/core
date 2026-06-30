# ADR-0150 — Autonomous Inter-Session Contemplation

Status: Accepted
Date: 2026-05-25

## Context
ADR-0056 Phase C1 shipped `contemplate()` as a pure function that enriches
DiscoveryCandidate with polarity, evidence, claim_domain, and sub_questions.
It ran inline (opt-in via attach_contemplation) or via CLI batch. Neither path
ran at session boundaries. Engine state (ADR-0146) persists discovery candidates
to disk, but stored candidates were unenriched (raw Phase B output).

## Decision
Run `contemplate()` on pending session candidates at `checkpoint_engine_state()`
before persisting to `engine_state/discovery_candidates.jsonl`. Enriched
candidates (polarity/evidence/claim_domain populated) are stored instead of
raw ones.

Flag: `RuntimeConfig.auto_contemplate = False` (null-drop default).

## Trust boundary
`contemplate()` is read-only w.r.t. corpus, pack, and vault per ADR-0056.
It enriches the in-memory candidate struct only. Nothing is written to any
shared store during enrichment.

## Why checkpoint, not inline
Fresh candidates are produced during the turn and accumulated in
`_pending_candidates`. Contemplation at checkpoint runs after the session
completes, not on the hot turn path. This avoids blocking turn latency.

## Unlocks
W-017: auto-proposal pipeline can filter enriched candidates (polarity,
evidence) to generate TeachingChainProposals.

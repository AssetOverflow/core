# Brief: W-017 — Auto-Proposal Pipeline at Load

**Status**: Ready to dispatch. W-007 (#274) and W-018 (#273) are both merged to main.  
**ADR**: ADR-0151 (create alongside implementation)  
**Dispatch to**: Gemini or Codex  
**Test suite**: `uv run pytest tests/test_adr_0151_auto_proposal.py tests/test_adr_0150_autonomous_contemplation.py tests/test_chat_runtime.py tests/test_architectural_invariants.py -q`

---

## What this wires up

W-018 (now merged) enriches `DiscoveryCandidate` objects via `contemplate()` at
`checkpoint_engine_state()`. W-017 completes the loop: on the **next session
load**, those enriched candidates are run through the ADR-0057 proposal gate
automatically, producing `TeachingChainProposal` entries with
`source.kind="contemplation"` in the standard `ProposalLog`.

The operator still ratifies via `core teaching review <id> --accept`. Nothing
auto-accepts. The only change is that the engine authors the proposal structure
(connective, object) from the contemplation enrichment rather than the operator
doing it manually.

---

## Prerequisite check

Before starting, confirm all of these exist on the current `main`:

- `RuntimeConfig.auto_contemplate: bool = False` in `core/config.py` ✓ (W-018)
- `chat/runtime.py`: `_load_engine_state()` loads `_pending_candidates` from disk ✓ (W-008)
- `chat/runtime.py`: `checkpoint_engine_state()` runs `contemplate()` when `auto_contemplate=True` ✓ (W-018)
- `teaching/proposals.py`: `propose_from_candidate(candidate, *, log, run_replay, allow_evaluative)` ✓
- `teaching/proposals.py`: `build_proposal(candidate, *, allow_evaluative, source)` accepts `source` ✓
- `teaching/source.py`: `ProposalSource(kind="contemplation", source_id=..., emitted_at_revision=...)` is valid ✓
- `ProposalKind` sealed literal includes `"contemplation"` ✓

---

## Changes required

### 1. `core/config.py` — add flag

Add to `RuntimeConfig` dataclass (after `auto_contemplate`):

```python
# ADR-0151 — generate TeachingChainProposals from enriched candidates on load.
# Requires auto_contemplate=True on the previous session to have enriched the
# candidates. Null-drop when False.
auto_proposal_enabled: bool = False
```

### 2. `teaching/proposals.py` — thread `source` through `propose_from_candidate`

`propose_from_candidate` currently calls `build_proposal(candidate, allow_evaluative=...)` 
without forwarding a `source`. Add the parameter:

```python
def propose_from_candidate(
    candidate: DiscoveryCandidate,
    *,
    log: ProposalLog,
    run_replay: Any = None,
    allow_evaluative: bool = False,
    source: "ProposalSource | None" = None,   # ADD THIS
) -> TeachingChainProposal:
    proposal = build_proposal(
        candidate,
        allow_evaluative=allow_evaluative,
        source=source,                          # AND PASS IT
    )
    ...  # rest unchanged
```

The default `source=None` preserves existing behaviour — `build_proposal`
defaults to `_default_operator_source()` when `source` is `None`.

### 3. `chat/runtime.py` — run proposal gate at load

In `_load_engine_state()`, after loading candidates, if
`self.config.auto_proposal_enabled` is True, run the proposal gate:

```python
def _load_engine_state(self) -> None:
    store = self._engine_state_store
    if store is None:
        return
    self._recognizer_registry = RecognizerRegistry.from_recognizers(
        store.load_recognizers()
    )
    self._pending_candidates = store.load_discovery_candidates()
    manifest = store.load_manifest() or {}
    self._turn_count = int(manifest.get("turn_count", 0))

    # ADR-0151 — auto-generate proposals from enriched candidates.
    if self.config.auto_proposal_enabled and self._pending_candidates:
        _auto_propose_from_candidates(self._pending_candidates)
```

Implement `_auto_propose_from_candidates` as a module-level helper (not a
method, keeps `ChatRuntime` surface clean):

```python
def _auto_propose_from_candidates(
    candidates: list[DiscoveryCandidate],
) -> None:
    """Run ADR-0057 proposal gate on enriched candidates.

    Uses the standard ProposalLog (DEFAULT_PROPOSAL_LOG_PATH) so
    proposals are visible to 'core teaching proposals --state pending'.
    ProposalError on eligibility failure → skip silently.
    propose_from_candidate is idempotent, so re-loading the same state
    does not duplicate proposals.
    """
    from teaching.proposals import ProposalError, ProposalLog, propose_from_candidate
    from teaching.source import ProposalSource

    log = ProposalLog()   # uses DEFAULT_PROPOSAL_LOG_PATH

    for candidate in candidates:
        source = ProposalSource(
            kind="contemplation",
            source_id=candidate.candidate_id,
            emitted_at_revision=_current_revision(),
        )
        try:
            propose_from_candidate(candidate, log=log, source=source)
        except ProposalError:
            pass   # eligibility gate failed — unenriched or evaluative candidate
```

Add `_current_revision()` import from `teaching.proposals` (it's already used
there) or from `teaching.source` — check where it lives and import from the
same place rather than duplicating it.

---

## Eligibility gate (already enforced by existing code)

`check_eligibility()` in `teaching/proposals.py` (called inside `build_proposal`)
enforces these three conditions — no new gate logic needed in W-017:

1. `any(e.source == "corpus" for e in candidate.evidence)` — corpus evidence floor
2. `candidate.polarity in ("affirms", "falsifies")` — polarity resolved
3. `not allow_evaluative` AND `candidate.claim_domain != "evaluative"` — domain gate

Candidates that fail any condition raise `ProposalError` → caught and skipped.
Unenriched candidates (those produced without `auto_contemplate=True`) will
have `polarity=None` and empty evidence, so they fail at gate 1 or 2 and are
silently dropped. This is correct — auto-proposals only fire on contemplated
candidates.

---

## Determinism contract

Same engine state directory + same corpus state = same set of proposals
generated on load. `propose_from_candidate` is already idempotent via the
`(source_candidate_id, proposed_chain)` key check — re-loading the same
state never duplicates an existing proposal. The `emitted_at_revision` in
`ProposalSource` is pinned at the git SHA at load time, not at contemplation
time; this is intentional — it records when the proposal was surfaced, not
when the candidate was enriched.

---

## ADR-0151 to create

Minimal decision record covering:
- What the auto-proposal pipeline does and why it differs from operator-authored proposals
- The eligibility gate (existing `check_eligibility` — no new gate logic)
- `source.kind="contemplation"` provenance and what it means for audit
- Determinism contract (idempotent re-loads, same corpus = same proposals)
- Trust boundary: `_auto_propose_from_candidates` reads corpus and pack via `check_eligibility` → `contemplate()`'s evidence; never writes to corpus
- Flag: `auto_proposal_enabled=False` default; null-drop when False

---

## Tests — `tests/test_adr_0151_auto_proposal.py`

8 tests, module-scoped fixture not needed — each test creates its own tmpdir
engine state.

### Test 1: `test_auto_proposal_off_does_not_generate_proposals`

With `auto_proposal_enabled=False`:
- Save an enriched candidate to a tmpdir engine state store
- Load a `ChatRuntime` with `engine_state_dir=tmpdir`, `auto_proposal_enabled=False`
- Assert `ProposalLog().pending()` does NOT contain the candidate's proposal

### Test 2: `test_auto_proposal_generates_pending_proposal_from_enriched_candidate`

With `auto_proposal_enabled=True`:
- Build a `DiscoveryCandidate` with `polarity="affirms"`, `claim_domain="factual"`,
  `evidence=(EvidencePointer(source="corpus", ...),)`, valid `proposed_chain`
- Save it to a tmpdir engine state store
- Load a `ChatRuntime` with `auto_proposal_enabled=True`
- Assert at least one proposal in `ProposalLog().pending()` with
  `record["proposal"]["source"]["kind"] == "contemplation"`

For the replay gate: pass `run_replay` stub to `propose_from_candidate` that
returns a `ReplayEvidence(replay_equivalent=True, regressed_metrics=[])` —
same pattern as `test_learning_loop_demo.py`. The runtime calls
`_auto_propose_from_candidates` which calls `propose_from_candidate`; to inject
the stub you may need to monkeypatch `teaching.replay.run_replay_equivalence`
via `monkeypatch.setattr`.

### Test 3: `test_unenriched_candidate_skipped_silently`

With `auto_proposal_enabled=True`:
- Build a raw `DiscoveryCandidate` with `polarity=None`, empty `evidence`
- Save to tmpdir engine state
- Load `ChatRuntime` with `auto_proposal_enabled=True`
- Assert no proposals generated, no exception raised

### Test 4: `test_evaluative_candidate_skipped`

With `auto_proposal_enabled=True`:
- Build an enriched candidate with `claim_domain="evaluative"`, `polarity="affirms"`,
  `evidence=(EvidencePointer(source="corpus", ...),)`
- Save to tmpdir engine state
- Assert no proposal generated (evaluative domain fails gate)

### Test 5: `test_proposal_source_kind_is_contemplation`

Verify the generated proposal's `source.kind == "contemplation"` and
`source.source_id == candidate.candidate_id`.

### Test 6: `test_propose_from_candidate_accepts_source_kwarg`

Unit test: call `propose_from_candidate(candidate, log=log, source=ProposalSource(kind="contemplation", source_id="test_id", emitted_at_revision="abc123"))` directly.
Assert proposal record has `source.kind == "contemplation"`.

### Test 7: `test_idempotent_reload_does_not_duplicate`

Load `ChatRuntime` twice from the same tmpdir (with `auto_proposal_enabled=True`
and an enriched candidate). Assert `len(ProposalLog().pending()) == 1` after
both loads.

### Test 8: `test_auto_proposal_does_not_write_corpus`

Assert that the active corpus (teaching corpus path) is byte-identical before
and after loading a `ChatRuntime` with `auto_proposal_enabled=True` and an
enriched candidate. Proposals land in `ProposalLog` only — never in the corpus.

---

## What NOT to do

- Do not auto-accept proposals — everything lands in `state="pending"`
- Do not add a new `ProposalKind` — `"contemplation"` is already sealed
- Do not add corpus evidence floor logic — `check_eligibility()` already enforces it
- Do not run `_auto_propose_from_candidates` at `checkpoint_engine_state()` — it runs at **load**, not at checkpoint
- Do not skip the replay gate — `propose_from_candidate` runs it; keep it
- Do not write to `vault/store.py`, `generate/stream.py`, `field/propagate.py`
- Do not weaken `versor_condition(F) < 1e-6`

---

## Verification

```bash
uv run pytest tests/test_adr_0151_auto_proposal.py tests/test_adr_0150_autonomous_contemplation.py tests/test_chat_runtime.py tests/test_architectural_invariants.py -q
uv run python -m core.cli test --suite smoke -q
```

Expected: all tests pass.

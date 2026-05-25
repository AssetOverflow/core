# Brief: W-019 — `core demo learning-arc`

**Status**: Ready to dispatch. Requires W-007, W-018, W-017 merged to main first.  
**ADR**: ADR-0151 (create alongside implementation)  
**Dispatch to**: Gemini or Codex  
**Test suite to run**: `uv run pytest tests/test_learning_arc_demo.py tests/test_learning_loop_demo.py tests/test_chat_runtime.py -q`

---

## Headline claim

> CORE, encountering a gap it cannot ground, enriches the discovery candidate
> autonomously through contemplation, then **proposes its own teaching chain**
> without a human crafting the connective or object. An operator ratifies with
> a single acceptance call. The same prompt now produces a deterministic
> teaching-grounded surface — and the engine authored the proposal.

This is categorically different from `core demo learning-loop` (ADR-0055..0057),
where the human operator authors the proposal structure (connective, object,
evidence pointer). Here the operator only reviews and ratifies.

---

## Prerequisites (confirm before starting)

- `RuntimeConfig.auto_contemplate: bool = False` exists in `core/config.py`
- `RuntimeConfig.auto_proposal_enabled: bool = False` exists in `core/config.py` (W-017)
- `checkpoint_engine_state()` in `chat/runtime.py` runs `contemplate()` when `auto_contemplate=True` (W-018)
- `_load_engine_state()` in `chat/runtime.py` generates proposals from enriched candidates when `auto_proposal_enabled=True` (W-017)
- `ProposalSource(kind="contemplation", ...)` is a valid source (already sealed in `teaching/source.py`)
- `accept_proposal(proposal_id, log, review_date)` exists in `teaching/proposals.py`

If any prerequisite is missing, stop and report which W is incomplete.

---

## Scene structure (5 scenes)

### S1 — Cold Session 1

```python
import tempfile
from pathlib import Path
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig

tmpdir = Path(tempfile.mkdtemp())
cfg = RuntimeConfig(auto_contemplate=True, auto_proposal_enabled=False)
rt = ChatRuntime(config=cfg, engine_state_dir=tmpdir)
response = rt.chat(_DEMO_PROMPT)
rt.checkpoint_engine_state()
```

**Assert**:
- `response.grounding_source` is NOT `"teaching"` (cold — ungrounded or OOV)
- `(tmpdir / "discovery_candidates.jsonl").exists()` is True
- The JSONL file contains at least one line

### S2 — Contemplation enrichment visible in persisted state

Read `(tmpdir / "discovery_candidates.jsonl")`. Parse the first line as a `DiscoveryCandidate`.

**Assert**:
- `candidate.polarity` is not None and not `"undetermined"` (contemplation ran and resolved)
- `candidate.domains` is not empty
- `candidate.evidence` is not empty
- `candidate.sub_questions` is not empty

This is **Jaw 1**: the engine deepened its understanding of the gap without human input.

> **Choosing the cold subject**: Before finalising `_DEMO_PROMPT`, run
> `contemplate(candidate)` interactively on candidate subjects to find one
> that produces at least one `EvidencePointer` with `source == "corpus"`.
> The W-017 gate requires `any(e.source == "corpus" for e in evidence)`.
> `"narrative"` is a strong candidate — `cause_creation_reveals_meaning`
> and cognition-saturation chains are related enough that sub-question
> traversal finds corpus hits. Verify empirically and document the chosen
> subject with a comment in the demo file.

### S3 — Auto-proposal surfaces on load

```python
cfg2 = RuntimeConfig(auto_contemplate=True, auto_proposal_enabled=True)
rt2 = ChatRuntime(config=cfg2, engine_state_dir=tmpdir)
# Loading triggers _load_engine_state() → W-017 proposal gate runs
```

Retrieve proposals via `ProposalLog` (same log path W-017 writes to).

**Assert**:
- At least one proposal in `log.pending()`
- `proposal.source.kind == "contemplation"`
- `proposal.subject` matches the cold subject from S1
- `proposal.state == "pending"`
- `proposal.connective` and `proposal.object` are non-empty strings (engine filled these, not the operator)

This is **Jaw 2**: the engine generated a complete, reviewable proposal from its own contemplation.

If no proposal is found (corpus evidence condition not met), **do not fail silently**. Report:
```
S3 PARTIAL: enriched candidate present but auto-proposal gate did not fire.
Reason: no corpus-evidenced EvidencePointer in candidate.evidence.
Choose a different _DEMO_SUBJECT with corpus-evidenced contemplation output.
```
Then halt — fix the subject choice before proceeding to S4/S5.

### S4 — Operator ratifies against transient corpus

```python
from teaching.proposals import accept_proposal, ProposalLog
from teaching import replay as _replay

# Accept against transient corpus (same swap pattern as learning-loop demo)
transient_corpus = tmpdir / "transient_corpus.jsonl"
with _replay._swap_corpus_path(transient_corpus):
    chain_id = accept_proposal(
        proposal.proposal_id,
        log=log,
        review_date="2026-05-25",
    )
```

**Assert**:
- `chain_id` is a non-empty string
- `transient_corpus.exists()` is True
- Active corpus on disk is byte-identical to before S4 (demo does not mutate production corpus)

### S5 — Session 2 grounded response

```python
from chat import teaching_grounding as _tg

original_path = _tg._CORPUS_PATH
_tg._CORPUS_PATH = transient_corpus
try:
    cfg3 = RuntimeConfig(auto_contemplate=False, auto_proposal_enabled=False)
    rt3 = ChatRuntime(config=cfg3, engine_state_dir=tmpdir)
    response2 = rt3.chat(_DEMO_PROMPT)
finally:
    _tg._CORPUS_PATH = original_path
```

**Assert**:
- `response2.grounding_source == "teaching"`
- `response2.surface != response.surface` (measurably different from S1)
- Subject word from the ratified chain appears in `response2.surface.lower()`

---

## Demo file location

```
evals/learning_arc/
    __init__.py       (empty)
    run_demo.py       (implements run_demo(emit_json=True) -> dict)
```

`run_demo()` returns a dict matching this shape:
```python
{
    "learning_arc_closed": bool,         # True iff all 5 scenes pass
    "active_corpus_byte_identical": bool, # S4 safety check
    "prompt": str,
    "cold_subject": str,
    "before": {"grounding_source": str, "surface": str},
    "after": {"grounding_source": str, "surface": str},
    "scenes": [
        {"scene": "S1_cold_session", "passed": bool, "detail": dict},
        {"scene": "S2_contemplation_enrichment", "passed": bool, "detail": dict},
        {"scene": "S3_auto_proposal", "passed": bool, "detail": dict},
        {"scene": "S4_operator_ratifies", "passed": bool, "detail": dict},
        {"scene": "S5_grounded_session", "passed": bool, "detail": dict},
    ],
}
```

---

## CLI registration

In `core/cli.py`:

1. Add `core demo learning-arc` to `EPILOG` examples string (after `learning-loop`)
2. In `cmd_demo()`, add handling for `target == "learning-arc"`:
   ```python
   if target == "learning-arc":
       from evals.learning_arc.run_demo import run_demo as run_arc_demo
       report = run_arc_demo(emit_json=emit_json)
       return 0 if report.get("learning_arc_closed") else 1
   ```
3. In `core demo all`: add `learning-arc` as scene 9 (after `learning-loop`)
4. In the tabular summary string, add entry:
   `"learning-arc: ADR-0151 — two-session contemplation → autonomous proposal → grounded"`
5. Add `"learning-arc"` to the `core demo list-results` entries

---

## Tests

File: `tests/test_learning_arc_demo.py`

Use a module-scoped fixture for `run_demo()` (same pattern as `test_learning_loop_demo.py` — one execution shared across all tests in the file).

```python
@pytest.fixture(scope="module")
def demo_report() -> dict:
    return run_demo(emit_json=True)
```

**8 tests**:

1. `test_learning_arc_closes` — `demo_report["learning_arc_closed"] is True`
2. `test_active_corpus_untouched` — `demo_report["active_corpus_byte_identical"] is True`
3. `test_before_is_ungrounded` — `before["grounding_source"] != "teaching"`
4. `test_after_is_teaching_grounded` — `after["grounding_source"] == "teaching"`
5. `test_s2_enrichment_has_polarity_domains_evidence` — S2 detail has non-empty polarity, domains, evidence, sub_questions
6. `test_s3_proposal_source_is_contemplation` — S3 detail has `source_kind == "contemplation"` and non-empty connective + object
7. `test_s4_corpus_byte_identical_after_accept` — S4 detail confirms production corpus unchanged
8. `test_before_and_after_surfaces_differ` — `before["surface"] != after["surface"]`

---

## ADR-0151 (create alongside)

Minimal ADR covering:
- What `core demo learning-arc` demonstrates and why it differs from `learning-loop`
- The two "jaws": checkpoint contemplation enrichment (W-018) + autonomous proposal generation (W-017)
- Trust boundary: demo writes only to `tmpdir` and `transient_corpus`; active corpus is read-only
- Which flags enable it: `auto_contemplate=True`, `auto_proposal_enabled=True`
- Determinism contract: same engine state + same corpus = same scenes, same surfaces

---

## What NOT to do

- Do not mutate the active teaching corpus on disk — use the transient swap pattern from `learning-loop`
- Do not add any stochastic sampling, LLM calls, or approximate recall
- Do not weaken `versor_condition(F) < 1e-6`
- Do not write to `vault/store.py`, `generate/stream.py`, `field/propagate.py`
- Do not auto-accept proposals — S4 must call `accept_proposal()` explicitly (simulates operator ratification)
- Do not skip the corpus-evidence check in S3 — if it doesn't fire, report and stop rather than faking success

---

## Verification

After implementation, run:
```bash
uv run python -m core.cli demo learning-arc
uv run pytest tests/test_learning_arc_demo.py tests/test_learning_loop_demo.py -q
uv run python -m core.cli test --suite smoke -q
```

Expected: all tests pass, `learning_arc_closed: true` in JSON output.

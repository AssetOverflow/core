# ADR-0167-W2C: Cross-Domain Partition Audit

This document surveys the usage of `DiscoveryCandidate` across the codebase to analyze how it partitions between the **cognition** and **math** domains, identifying construction sites, consumption patterns, test coverage, and downstream risks.

## 1. Inventory

The following files import, construct, or reference `DiscoveryCandidate`:

### Implementation Files
1. **[teaching/discovery.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/teaching/discovery.py)**
   - Line 47: `from typing import Any, Literal`
   - Line 146: Class definition `class DiscoveryCandidate`
   - Line 203: Deserialization `from_dict(cls, payload)`
   - Line 274: Function `extract_discovery_candidates` returning `tuple[DiscoveryCandidate, ...]`
   - Line 344: Instantiates `DiscoveryCandidate`
   - Line 356: Serialisation `format_candidate_jsonl(candidate)`
2. **[teaching/contemplation.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/teaching/contemplation.py)**
   - Line 43: Imports `DiscoveryCandidate`
   - Line 192: Parameter type annotation in `_decompose`
   - Line 332: Parameter/return type annotation in `_materialise_sub_candidate`
   - Line 403: Parameter type annotation in `contemplate`
   - Line 525: Return type annotation in `contemplate_exemplar_corpus`
   - Line 590: Instantiates `DiscoveryCandidate`
3. **[teaching/proposals.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/teaching/proposals.py)**
   - Line 38: Imports `DiscoveryCandidate`
   - Line 165: Parameter type annotation in `check_eligibility`
   - Line 212: Parameter type annotation in `propose_from_candidate`
   - Line 478: Parameter type annotation in `_write_contemplation_report`
4. **[teaching/discovery_sink.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/teaching/discovery_sink.py)**
   - Line 29: Type annotation for `DiscoveryCandidateSink(Protocol)`
5. **[chat/runtime.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/chat/runtime.py)**
   - Line 49: Imports `DiscoveryCandidate`
   - Line 111: Parameter type annotation in `_auto_propose_from_candidates`
   - Line 661: Property `self._pending_candidates: list[DiscoveryCandidate]`
   - Line 857: Parameter type annotation in `attach_discovery_sink`
6. **[core/cli.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/core/cli.py)**
   - Line 1306: Imports `DiscoveryCandidate` in `_load_candidate_jsonl`
   - Line 1333: Instantiates `DiscoveryCandidate`
7. **[engine_state/__init__.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/engine_state/__init__.py)**
   - Line 26: Imports `DiscoveryCandidate`
   - Line 132: Parameter type annotation in `save_discovery_candidates`
   - Line 143: Return type annotation in `load_discovery_candidates`
   - Line 148: Deserialization `DiscoveryCandidate.from_dict`
8. **[benchmarks/teaching_loop.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/benchmarks/teaching_loop.py)**
   - Line 33: Imports `DiscoveryCandidate`
   - Line 44: Return type annotation in `_canonical_candidate`
   - Line 45: Instantiates `DiscoveryCandidate`

### Test Files
1. **[tests/test_contemplation.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_contemplation.py)** (Lines 26, 39, 117, 146, 194, 244, 283, 341)
2. **[tests/test_discovery_candidates.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_discovery_candidates.py)** (Lines 28, 230)
3. **[tests/test_teaching_proposals.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_teaching_proposals.py)** (Lines 24, 55)
4. **[tests/test_teaching_queue.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_teaching_queue.py)** (Lines 13, 19)
5. **[tests/test_hitl_queue_backpressure.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_hitl_queue_backpressure.py)** (Lines 13, 27)
6. **[tests/test_hitl_queue_submission_invariants.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_hitl_queue_submission_invariants.py)** (Lines 11, 36)
7. **[tests/test_contemplation_pipeline_convergence.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_contemplation_pipeline_convergence.py)** (Lines 39, 129)
8. **[tests/test_adr_0146_engine_state.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_adr_0146_engine_state.py)** (Lines 9, 44, 137)
9. **[tests/test_adr_0150_autonomous_contemplation.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_adr_0150_autonomous_contemplation.py)** (Lines 8, 14)
10. **[tests/test_adr_0151_auto_proposal.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_adr_0151_auto_proposal.py)** (Lines 10, 45, 64)
11. **[tests/test_adr_0153_trace_hash_backstamp.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_adr_0153_trace_hash_backstamp.py)** (Lines 2, 7, 104)
12. **[tests/test_adr_0158_reboot_event.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/audit-cross-domain-partition/tests/test_adr_0158_reboot_event.py)** (Lines 24, 62)

---

## 2. Construction Sites

There are **5 main construction sites** of `DiscoveryCandidate` in implementation code:

1. **`teaching/discovery.py::extract_discovery_candidates`** (Shared/Cognition)
   - *Nature*: Cognition-specific turn-loop discovery predicate. Fires when safety/ethics boundaries are clean and a (subject, intent) falls through to the universal disclosure.
2. **`teaching/contemplation.py::contemplate_exemplar_corpus`** (Math/Admissibility)
   - *Nature*: Math-specific synthesis pathway. Turns an admissibility exemplar corpus into a candidate that proposes a recognizer.
3. **`teaching/contemplation.py::_materialise_sub_candidate`** (Shared/Cognition)
   - *Nature*: Cognition-specific sub-candidate decomposition helper. Used during recursive search in inline contemplation.
4. **`core/cli.py::_load_candidate_jsonl`** (Shared)
   - *Nature*: Deserializer helper in the proposal CLI commands. Used for constructing candidate objects from JSONL inputs.
5. **`benchmarks/teaching_loop.py::_canonical_candidate`** (Cognition)
   - *Nature*: Cognition-specific benchmark helper. Constructs a static candidate to benchmark proposal and review throughput.

---

## 3. Consumption Sites

There are **8 main consumption sites**:

1. **`chat/runtime.py`** (Domain-Agnostic)
   - Manages lists of `_pending_candidates` and handles checkpointing.
2. **`engine_state/__init__.py`** (Domain-Agnostic)
   - Writes `discovery_candidates.jsonl` files to the local checkpoint directory.
3. **`teaching/contemplation.py::contemplate`** (Cognition-Specific)
   - Resolves claims using `_pack_index()` and `_corpus_index()`. Currently hardcoded to the cognition pack and cognition teaching corpus.
4. **`teaching/proposals.py::propose_from_candidate`** (Cognition/Math)
   - Inspects candidate validity, checks capacity/duplicates, and executes a replay gate.
5. **`teaching/gaps.py::aggregate_gaps`** (Domain-Agnostic)
   - Reads files written by the discovery sinks to report on-disk gaps.
6. **`teaching/promotion.py`** (Domain-Agnostic)
   - Promotes gaps to mutation proposals.
7. **`core/cli.py`** (Shared)
   - Converts candidates into proposal entries using the CLI lanes.
8. **`tests/`** (Domain-Agnostic / Cognition)
   - Unit tests validating serialization, contemplation convergence, and auto-proposals.

---

## 4. Test Coverage

- **`tests/test_discovery_candidates.py`**: Verifies candidate extraction rules (verdicts, intents, safety/ethics interaction).
- **`tests/test_contemplation.py`**: Verifies contemplation loop determinism, direct affirmations, direct contradictions, mixed evidence, and recursion limits.
- **`tests/test_teaching_proposals.py`**: Validates the proposal creation lifecycle.
- **`tests/test_contemplation_pipeline_convergence.py`**: Validates the `DiscoveryCandidateSink` integration.
- **`tests/test_adr_0146_engine_state.py`**: Verifies deserialization/serialization round-trips from dictionary payloads.
- **`tests/test_adr_0153_trace_hash_backstamp.py`**: Verifies trace hash back-stamping.

---

## 5. Recommendation

### Files to Modify:
1. **`teaching/discovery.py`**: Add the `domain: Literal["cognition", "math"]` field with `"cognition"` default. Update `as_dict()` conditionally and `from_dict()` unconditionally.
2. **`core/cli.py`**: Ensure `_load_candidate_jsonl` reads and populates the `domain` field.

### Files to NOT Modify:
- Do **not** modify any file under `tests/` except the new test file `tests/test_candidate_domain_partition.py`.
- Do **not** modify `teaching/contemplation.py` or `teaching/proposals.py` as part of this PR.

---

## 6. Risks

### Downstream Risks:
1. **Contemplation Indexing**: `teaching/contemplation.py`'s `_pack_index()` and `_corpus_index()` are cognition-hardcoded. If a math candidate is passed to `contemplate()`, it will probe the cognition pack instead of the math pack, leading to false negatives or incorrect polarity results. Follow-up work must redirect index lookups based on the `candidate.domain`.
2. **Replay Gate**: The replay gate in `teaching/proposals.py` defaults to `run_cognition_replay_gate`. Math candidates must use `run_admissibility_replay_gate` to prevent false rejections.
3. **Workbench Display**: The workbench display will need to filter and color-code candidates by their domain discriminator so operators can review them separately.

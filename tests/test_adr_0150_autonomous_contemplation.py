from __future__ import annotations

import json
from pathlib import Path
from core.config import RuntimeConfig
from chat.runtime import ChatRuntime
from engine_state import EngineStateStore
from teaching.discovery import DiscoveryCandidate, EvidencePointer, SubQuestion
from chat.pack_grounding import _pack_index
from chat.teaching_grounding import _corpus_index
from teaching.contemplation import contemplate

def _raw_candidate() -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id="cand-1",
        proposed_chain={"subject": "light", "intent": "verification", "connective": None, "object": None},
        trigger="would_have_grounded",
        source_turn_trace="trace-1",
        pack_consistent=True,
        boundary_clean=True,
    )

def test_auto_contemplate_off_stores_raw_candidates(tmp_path: Path) -> None:
    config = RuntimeConfig(auto_contemplate=False)
    runtime = ChatRuntime(config=config, engine_state_path=tmp_path)
    
    cand = _raw_candidate()
    runtime._pending_candidates.append(cand)
    runtime.checkpoint_engine_state()
    
    store = EngineStateStore(tmp_path)
    loaded = store.load_discovery_candidates()
    assert len(loaded) == 1
    assert loaded[0].polarity == "undetermined"
    assert len(loaded[0].evidence) == 0

def test_auto_contemplate_enriches_at_checkpoint(tmp_path: Path) -> None:
    config = RuntimeConfig(auto_contemplate=True)
    runtime = ChatRuntime(config=config, engine_state_path=tmp_path)
    
    cand = _raw_candidate()
    runtime._pending_candidates.append(cand)
    runtime.checkpoint_engine_state()
    
    # Clear pending candidates and load from disk
    runtime._pending_candidates = []
    runtime._load_engine_state()
    
    assert len(runtime._pending_candidates) == 1
    loaded_cand = runtime._pending_candidates[0]
    
    # Verify loaded candidate has claim_domain and evidence populated (not defaults)
    assert loaded_cand.claim_domain == "factual"
    assert len(loaded_cand.evidence) > 0
    # The default polarity is undetermined, but evidence is populated
    assert any(e.source == "pack" and e.ref == "light" for e in loaded_cand.evidence)

def test_enriched_candidates_survive_jsonl_round_trip(tmp_path: Path) -> None:
    cand = _raw_candidate()
    enriched = contemplate(cand)
    
    store = EngineStateStore(tmp_path)
    store.save_discovery_candidates([enriched])
    
    loaded = store.load_discovery_candidates()
    assert len(loaded) == 1
    loaded_cand = loaded[0]
    
    assert loaded_cand.polarity == enriched.polarity
    assert loaded_cand.claim_domain == enriched.claim_domain
    assert loaded_cand.evidence == enriched.evidence
    assert loaded_cand.sub_questions == enriched.sub_questions
    assert loaded_cand.contemplation_depth == enriched.contemplation_depth
    assert loaded_cand.recursion_overflow == enriched.recursion_overflow

def test_contemplate_does_not_write_corpus_or_pack() -> None:
    corpus_before = dict(_corpus_index())
    pack_before = dict(_pack_index())
    
    cand = _raw_candidate()
    _ = contemplate(cand)
    
    corpus_after = dict(_corpus_index())
    pack_after = dict(_pack_index())
    
    assert corpus_before == corpus_after
    assert pack_before == pack_after

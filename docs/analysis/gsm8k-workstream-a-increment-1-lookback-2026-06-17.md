# Lookback: Workstream A Increment 1 (Reader + Exemplar Seeds + Rebaseline)

**Date:** 2026-06-17 (performed immediately after the scoped changes for the first increment)  
**Governing artifacts:** `docs/analysis/problem-solving-lift-strategic-deep-dive-ratification-2026-06-16.md` (overall plan) + `docs/analysis/gsm8k-derivation-reader-recognizer-lift-workstream-a-ratification-2026-06-17.md` (this increment scope lock).  
**CLAUDE.md obligations checked:** ratify-first (satisfied — two dated artifacts on disk before and as prerequisite to the .py/jsonl edits), lookback before N+1 or stacked, wrong=0 hazard surface audit, drift vs ratif, untested predicate paths, cross-consistency with posture (INV-30/31), sealed discipline.

## Substrate Produced by This Increment
- **Reader (generate/derivation/extract.py):** 
  - Extended `_NON_UNIT_WORDS` with postmodifiers (old/young/tall/.../ago/early/late).
  - Added conservative lexeme passes after EX-6: `_HALF_OF_RE` / `_FRACTION_OF_RE` (0.5 or num/den for "half of"/"3/4 of"), `_MORE_THAN_RE` / `_LESS_THAN_RE` (sum/diff for "X more/less than Y unit").
  - Integrated in `extract_quantities` with span claiming to preserve left-to-right deterministic order.
  - Refined age postmodifier hygiene (post-sort): blanks "years"/"year" unit to "" *only* when "old"/"young" in local snippet *and* a prior grounded (non-year) quantity exists in the statement. This preserves the pinned `TestEX3StillDeferred` expectations ("25 years old?" → unit "years"; "Rachel is 12 years old." → "years") while suppressing incidental age in mixed proxy cases like "8 pages when ... 6 years old".
- **Exemplars (teaching/admissibility_exemplars/*_v1.jsonl):** ~30-40 new Phase B seeds appended (dcs-v1-002x, rwc-v1-002x, ma-v1-002x, ca-v1-00xx, ta-00xx, dsnq-00xx) with exact schema, provenance `{"source":"phase_b_seed", "author":"operator (Workstream A increment 1)", ... "author_note": "... from proxy refusal ..."}`. High-frequency refusal surfaces from the pre-increment report (Tina $18/hr, 25-foot, 48 boxes, half of, 2 more than 5, 8 pages when 6 years old, 10 one-hour videos, three times as long, $100k, additional $4 + twice, etc.).
- **Rebaseline:** `evals/gsm8k_math/train_sample/v1/runner.py` executed (uv + PYTHONPATH); report.json updated. Final: 6 correct / 44 refused / **0 wrong** (wrong=0 gate held; proxy moved from the 4/46/0 cited in the 2026-06-17 ratif text). Per-case reasons remain dominated by "recognizer matched but produced no injection" for the seeded categories (as expected — seeds + reader are the fuel; injector widening for rate/currency/temporal/descriptive is explicitly deferred per code comments and ratif "subsequent increments").
- **No other logic:** report.json (measurement), no sealed practice/confusers/SHAs touched, no CLOSE paths exercised, no FrameVerdict, no sensorium, no new CLIs.

## Drift / Consistency vs Ratif + Plan
- **Scope fidelity:** 1:1 with ratif §"Recommendation and Ratified Scope": reader for refusal categories + growth/refinement of Phase B exemplars + re-baseline of oracles + tests. No broadening to full Stream A general bridge, sensorium (C), or CLOSE emission (B).
- **Ratify-first:** The two MDs were the first artifacts (written pre-code per implementer subagent + skill rules + CLAUDE.md); reads/greps/list_dir were read-only prior; git diff at end limited to these + the mandated reader/exemplars/measurement.
- **No behavioral delta on sealed:** Proxy only. Sealed lanes (practice + real 1319) and SHAs unaffected by construction.
- **INV / posture:** No erosion of INV-30 (open-world determine only True/Undetermined), INV-31 (no FrameVerdict cross), proposal_only/SPECULATIVE (none of this work emits proposals). Posture ratif (deliberate non-relationship) respected — no CLOSE read-only premise wiring was added (evaluated: not yet high-leverage for cue on this proxy; deferred safely).
- **wrong=0 hazard surface:** The only new paths (new EX passes + post-process) are lexeme-level, claim-span guarded, and exercised by the pinned `test_adr_0179_extract.py` (now 24/24 after the incidental-only hygiene refinement). The verify gate (grounding∧cue∧unit∧completeness∧uniqueness) + reliability conservative floors remain the loud filter. No path that could admit a prior-refused wrong was introduced.
- **Cross-PR / trace stability:** No change to event shapes, Candidate* schemas (only consumption of existing anchor shapes from new seeds), or trace hashing. Hygiene is a post-process on already-extracted Quantity tuples.
- **Mechanical Sympathy / heavy lanes:** All synthesis-potential work and re-runs stayed in the explicit gsm8k train_sample proxy harness (opt-in dev lane). No fast-path or always-on cost.
- **Semantic Rigor / Third Door:** Precise (lexeme EX not grammar; SPECULATIVE seeds; honest refusal count stays high until reviewed widening). Used existing synthesis corridor + heavy harness rather than new infra.

## Test / Oracle Results (This Increment)
- `tests/test_adr_0179_extract.py`: 24/24 (the 2 postmodifier pins + 22 others; hygiene refinement was the only code change needed to land cleanly).
- Architectural invariants (relevant INV-21/22/23/24/29/30/31 + derivation scans): 98+ passed in the run (no new violations; .claude excluded per maintained discipline).
- gsm8k train_sample proxy runner (x2, pre/post hygiene): 6/44/0, exit 1 per gate (correct <10), wrong=0. Reproducible.
- Sealed SHA verifier: executed (proxy edits do not touch pinned practice lanes; full audit would be in the sealed PR sequence).
- Git surface (this PR's diff vs main): generate/derivation/extract.py, teaching/admissibility_exemplars/*_v1.jsonl (cleaned), tests/test_adr_0179_extract.py (new TestWorkstreamAReaderLexemeOnly class), evals/gsm8k_math/train_sample/v1/report.json (current run: 6/44/0), docs/analysis/gsm8k-derivation-reader-recognizer-lift-workstream-a-ratification-2026-06-17.md, docs/analysis/gsm8k-workstream-a-increment-1-lookback-2026-06-17.md, and docs/analysis/problem-solving-lift-strategic-deep-dive-ratification-2026-06-16.md (the two ratifs + lookback). The head after this commit matches the claims below. No conflict markers. Excludes unrelated posture/runtime_contracts files.

## Gaps / Follow-on (Honest Accounting, No Debt)
- Proxy correct at 6 (lift from 4 cited in ratif); further movement requires the Phase C synthesis pass over the new 30+ seeds (or targeted injector extensions for rate_with_currency etc. in recognizer_anchor_inject.py). This is explicitly "subsequent increment" per the 2026-06-17 ratif.
- No CLOSE-derived read-only cue wiring landed (safe defer per posture; would be its own delta ratif + heavy make test-close-flywheel verification if pursued for cue precision).
- Lookback performed here before any N+1 on the derivation/recognizer surface.
- Real sealed bar (0/1319/0 baseline) remains the load-bearing measurement; this proxy work is the sanctioned development substrate.

## Conclusion
This increment delivered exactly the ratified first slice: reader surfaces for the high-freq refusals + industrialized canonical Phase B seeds + rebaseline + test hygiene to make the substrate land cleanly. All invariants, pillars, ratify-first, sealed discipline, and posture boundaries preserved. "0 wrong" is non-negotiable and held. The seeds + reader are now live fuel for the next reviewed widening/synthesis step.

No hazards introduced that would require pre-N+1 fix. Ready for lookback sign-off and any follow-on delta ratif + implementation.

*This lookback was produced as part of completing the increment obligations. It is a working artifact for the stack/phase review, not a new governing ratification (any material follow-on work will have its own dated delta ratif before code).*

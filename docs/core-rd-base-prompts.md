# CORE R&D Base Prompts

These prompts are grounded directly in CORE’s actual architecture — the runtime contracts, invariants, ADR chain, and epistemic model. They are designed to be dropped into Grok Build, Claude Code, or any agentic loop as standing prefixes.

They work **in addition to** `GROK.md` and `AGENTS.md`, not as replacements.

## Recommended Usage Pattern

The cleanest loop for CORE R&D:

1. Start every session with the **Session Entry / Context Load** prompt.
2. Add the appropriate phase-specific prompt (#2–#6) for the work at hand.
3. End every session by running the **Standing Loop Axiom Check** (#7) as a final self-audit before committing.

For Grok Build’s parallel subagent (Arena) mode, assign one subagent per major module boundary and give each its own copy of the relevant phase prompt. The contracts are precise enough that agents rarely drift when anchored to the same ADR references and invariants.

---

## 1. Session Entry / Context Load

Paste this at the start of any coding session:

```text
You are working inside AssetOverflow/core. Before touching anything:

1. Read CLAUDE.md and AGENTS.md fully. Do not infer the project structure — derive it.
2. The field invariant is load-bearing: versor_condition(F) < 1e-6. Any path you write that propagates field state must preserve closure or fail loudly. Never silently downgrade.
3. Teaching claim status uses the four-position reviewed revision graph: SPECULATIVE, COHERENT, CONTESTED, FALSIFIED.

   Do not confuse this with runtime EpistemicState / DisclosureClaim surfaces, which are richer (PERCEIVED, EVIDENCED, VERIFIED, DECODED, INFERRED, UNDETERMINED, SCOPE_BOUNDARY, etc.) and governed separately.
4. Durable standing mutations (corpus/pack/policy/identity) are proposal-only, reviewed via teaching/*. Do not route around this.
5. wrong == 0 is not a metric target — it is an architectural obligation. If a path you produce can emit a wrong (non-refused) answer that isn't disclosed as [approximate], treat that as a structural defect, not a test failure. Do not proceed until you have internalized the above.
```

## 2. New Feature / ADR-Driven Work

```text
You are implementing a new capability slice for CORE under the ADR discipline.

Rules:
- Every non-trivial decision must be traceable to an existing ADR or require a new one. If you are making an architectural choice with no ADR anchor, name it explicitly and propose the ADR before writing code.
- Placement is load-bearing. generate/* owns generation/propagation semantics. algebra/versor.py owns closure invariants only — no admissibility logic there. field/propagate.py is a forbidden normalization/repair site.
- Fail loudly, not silently. No silent catch-and-continue on versor violations, refusal exhaustion, or epistemic transitions.
- New test gates follow the taxonomy in docs/runtime_contracts.md: algebra/ physics/ runtime/ cognition/ teaching/ packs/. Do not mix concerns across test directories.
- Every new invariant must be enforced by a failing test, not by convention.
```

## 3. Refactor / Cleanup Pass

```text
You are doing a refactor pass on CORE.

Constraints:
- Do not reorganize tests as standalone churn. Only move files if it directly reduces contract ambiguity or unlocks a cognitive subsystem.
- Protect load-bearing behavior: versor closure, deterministic replay, runtime response/telemetry contracts, memory correctness, identity protection, teaching/correction safety, and the articulation contract.
- Do not preserve stale constructors, private helper shapes, or exact formatting that is not part of a documented contract. These are not worth protecting.
- Backward compatibility is a real constraint: InnerLoopExhaustion is a ValueError; every existing except ValueError handler must continue to work.
- Trace hash determinism is a hard invariant: compute_trace_hash must produce byte-identical output for identical inputs. Any change that touches hashed payloads must be verified against this.
```

## 4. Eval / Testing Lane Work

```text
You are writing or extending an eval lane for CORE.

Invariants for all eval work:
- wrong == 0 is the gate, not a stretch goal. A lane that permits any non-refused wrong answer does not pass.
- refused is the safe failure mode. A lane that refuses everything (0 correct, 0 wrong, N refused) is a passing gate; whether it qualifies for expert promotion is a separate ADR question.
- Seal discipline: plaintext holdout data never touches disk. CORE_HOLDOUT_KEY is required to decrypt; tests without the key skip, never fail.
- No cross-domain bleed: evidence lanes must attach only to their domain's ratified packs.
- Adversarial suites must include at least one family that proves the gate isn't trivially satisfied by refusing everything.
- Lane shapes are registered, not inferred. Adding a new lane to the audit-passed surface requires an explicit registry entry and an ADR amendment.
```

## 5. Determinism / Replay Audit

```text
You are auditing or restoring deterministic replay in CORE.

The replay contract:
- No clock, no LLM sampling, no external randomness in any replayable path.
- compute_trace_hash folds refusal_reason only when non-empty, preserving byte-identical hashes for non-refused turns.
- Divergence in a persisted CognitivePipelineRecord is evidence against equivalence, not wall-clock noise. Treat it as a falsification signal, not a flake.
- No pickle. Pickle defeats replay determinism and is a code-execution surface.
- All hashed payloads: canonical JSON (sorted keys, tight separators, UTF-8, no NaN/Infinity). Floats forbidden in hashed payloads.
- A live turn with a trace hash but no status="recorded" CognitivePipelineRecord fails before journal append.
```

## 6. Architectural Boundary / Separation Guard

```text
You are working near a trust boundary or architectural separation in CORE.

The most critical active separation: open-world CLOSE derivation vs. closed-world FrameVerdict. These have zero data flow in either direction. This is enforced by INV-30 and INV-31.

Do not create import paths, type sharing, or semantic composition across this boundary. Any controlled interaction — however narrow — is a material architectural change requiring a new ADR, updates to INV-30/INV-31, re-verification that wrong_total == 0, and fresh ratification.

Formation Pipeline boundary discipline: every trust boundary has a content-addressed input and output. Every rejection produces an audit record. No silent failures anywhere in the pipeline.

When in doubt about whether a change crosses a boundary: it does. Prove it doesn't before proceeding.
```

## 7. The Standing Loop Axiom Check

Use this as a closing self-audit after any session before committing:

```text
Before committing, answer each question:

1. Does any new propagation path preserve versor_condition(F) < 1e-6? If no: do not commit.
2. Does any new path produce a wrong (non-refused, undisclosed) answer? If yes: structural defect, not a test to patch.
3. Does any new code touch corpus/pack/policy/identity mutation outside the reviewed teaching path? If yes: route through proposal-only.
4. Does any new invariant have a failing test that would catch violation? If no: write the test first.
5. Does the change cross the CLOSE/FrameVerdict boundary? If yes: stop and open an ADR.
6. Are all hashed payloads in canonical JSON with no floats? If no: fix before committing.

All six must be clean. If any is uncertain, surface it explicitly — do not silently assume it's fine.
```

---

## 8. PR Merge-Readiness Audit

You are auditing a CORE PR for merge readiness.

Do not approve based on intent. Verify:
1. Exact branch head SHA
2. Diff scope vs PR claim
3. Touched invariants
4. Relevant tests/evals and exact outputs
5. wrong_total == 0 where applicable
6. No open-world/closed-world boundary leak
7. No unreviewed corpus/pack/policy/identity mutation
8. No hidden normalization, approximate recall, stochastic fallback, or dynamic execution surface

Return:
- Verdict: MERGE / BLOCK / NEEDS PATCH
- Blockers
- Non-blocking concerns
- Exact commands run
- Files inspected
- Residual risk
```

## 9. Grok Build Implementation Session

You are working inside AssetOverflow/core.

First:
- Read GROK.md, AGENTS.md, docs/runtime_contracts.md
- Read the most recent HANDOFF-* if dated within 3 days
- Run `core test --suite smoke -q`
- State the exact scope and invariant you will preserve

Then:
- Do not edit until you have traced all imports/callers for the target path
- Keep the PR small
- Write failing tests before behavior changes
- Prefer refusal over wrong
- Never add hidden normalization, approximate recall, stochastic fallback, or direct mutation of claim/pack/policy/identity state

End with:
- Exact files changed
- Tests run with outputs
- Invariants verified
- Handoff doc content

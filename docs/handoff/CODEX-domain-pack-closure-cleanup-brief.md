# Codex Brief - Domain-Pack Closure Cleanup (PR #97 follow-up)

**Audience:** Same agent that landed PR #97 (chain-first capability ledger + 5 domain seeds + ADR-0091 domain-pack contract).

**Mission:** The three new English domain seed packs landed with `manifest.json` carrying `"definitional_layer": true`, which opted them into the ADR-0084 definitional-closure verifier - but they were not authored against ADR-0084 closure discipline (atoms must equal `content_tokens(gloss)` exactly; every atom must resolve as a `lemma` somewhere). The verifier is currently red on main solely because of these three packs.

Flip the flag on each of the three packs to remove them from the ADR-0084 closure lane. They remain governed by their own `domain_contract_version: 1` contract (ADR-0091), which is a different and intentional layer.

**Estimated effort:** Trivial - three one-character JSON edits + checksum refresh + verification.

---

## Background - why this happened

PR #97 introduced ADR-0091 (`domain_contract_version`) as a new pack-layer contract for domain seeds. These packs carry axioms, rules, teaching chains, and capability evidence - they are not the closed-under-atoms definitional packs that ADR-0084 governs.

ADR-0084's closure verifier requires for every gloss:

1. `definitional_atoms == content_tokens(gloss)` exactly (token equality, after stripping stopwords/prepositions).
2. Every atom in `definitional_atoms` resolves as a `lemma` field in some pack's `lexicon.jsonl`, `glosses.jsonl`, or in `packs/primitives/en_semantic_primitives_v1/primitives.jsonl`.

Domain seed packs don't satisfy either rule, by design - they list domain-specific tokens (`mapping`, `input`, `output`, `transition`, `inertia`, ...) that are not lemmas in the lexicon layer, and their glosses are written for human/contract readability, not as atom-graph closure proofs.

Both the script `scripts/verify_definitional_closure.py` and the integration test `tests/test_adr_0084_integration_closure.py` filter by `definitional_layer: true`. The integration test additionally hard-codes an `OPTED_IN_PACKS` allowlist that does not include the three domain packs - which is why the test is green even though the script is red. Flipping the manifest flag aligns the script with the test's clearly-intended scope.

## Phase 0 - Baseline

```bash
PYTHONPATH=. python3 scripts/verify_definitional_closure.py 2>&1 | head -5
# Expected: 3 packs in unresolved_by_pack and 3 packs in mismatched_atoms_by_pack
# (en_mathematics_logic_v1 / en_physics_v1 / en_systems_software_v1)

PYTHONPATH=. python3 -m pytest tests/test_adr_0084_integration_closure.py -q
# Expected: 30 passed

PYTHONPATH=. python3 -m core.cli eval cognition > /tmp/eval_baseline.json
# Capture baseline for byte-identity check.
```

## Phase 1 - Flip the flag

For each of these three manifest files, change exactly one line:

```
language_packs/data/en_mathematics_logic_v1/manifest.json
language_packs/data/en_physics_v1/manifest.json
language_packs/data/en_systems_software_v1/manifest.json
```

Before:

```json
"definitional_layer": true,
```

After:

```json
"definitional_layer": false,
```

Do not touch any other field. Do not touch `glosses.jsonl`, `lexicon.jsonl`, `axioms.json`, `rules.json`, the chains file, or the `domain_contract_version`. The ADR-0091 domain-pack contract is unchanged.

## Phase 2 - Refresh manifest checksum

The `checksum` field on each manifest hashes the bytes of the lexicon file (see `language_packs/loader.py`'s checksum policy). Since we are not touching the lexicon, the lexicon-hash component is unchanged. But some loaders also hash the manifest itself in their own provenance - confirm by running the standard checksum-refresh shell snippet from [ADR-0085-content-style-pass-brief.md](./ADR-0085-content-style-pass-brief.md) Phase 3, applied only to these three packs.

If the `glosses_checksum` field exists and the loader does not require it to change when only the manifest flag changes, leave it. If you are unsure, run:

```bash
PYTHONPATH=. python3 -m core.cli pack validate en_mathematics_logic_v1
PYTHONPATH=. python3 -m core.cli pack validate en_physics_v1
PYTHONPATH=. python3 -m core.cli pack validate en_systems_software_v1
```

 - and let those tell you whether checksum refresh is needed. If the loader rejects a manifest as stale, refresh `checksum` for that pack only.

## Phase 3 - Verify

All five must pass:

```bash
# 1. Closure verifier green
PYTHONPATH=. python3 scripts/verify_definitional_closure.py
# Expected: 0 unresolved, 0 mismatches.

# 2. ADR-0084 integration test still green (scope unchanged)
PYTHONPATH=. python3 -m pytest tests/test_adr_0084_integration_closure.py -q
# Expected: 30 passed.

# 3. Domain pack contract test still green
PYTHONPATH=. python3 -m pytest tests/ -k domain_contract -q
# Expected: same pass count as before the change.

# 4. Cognition eval byte-identical
PYTHONPATH=. python3 -m core.cli eval cognition > /tmp/eval_post.json
diff /tmp/eval_post.json /tmp/eval_baseline.json
# Expected: empty diff (closure-layer flag does not affect chat/eval lanes).

# 5. Packs lane
PYTHONPATH=. python3 -m core.cli test --suite packs -q
# Expected: pass.

# 6. Smoke lane
PYTHONPATH=. python3 -m core.cli test --suite smoke -q
# Expected: pass.
```

If `core eval cognition` drifts byte-from-byte from baseline, stop and report - the flag should be inert for runtime, but if it isn't there's an unexpected coupling worth investigating before merge.

## What this brief does not do

- Does not modify any pack content (glosses, lexicon, atoms, rules, axioms).
- Does not modify the ADR-0091 `domain_contract_version` or any field under it.
- Does not modify the closure verifier code or the integration test allowlist.
- Does not alter `chat/`, `generate/`, `core/cognition/`, or any other runtime module.

If verification surfaces something the manifest-flag flip alone cannot fix, stop and report - do not start patching atoms in the domain packs as a workaround.

## Deliverables

1. Edits on branch `feat/codex/domain-pack-closure-cleanup`.
2. Draft PR titled `fix(packs): flip domain-seed packs out of ADR-0084 closure layer (PR #97 follow-up)` with this report:

```
## Summary

Three domain seed packs from PR #97 (`en_mathematics_logic_v1`,
`en_physics_v1`, `en_systems_software_v1`) shipped with
`definitional_layer: true` but are governed by ADR-0091
`domain_contract_version: 1` - a different and intentional layer.
The ADR-0084 closure verifier was red on main solely because of this
mis-labeling. The ADR-0084 integration test was already green because
its allowlist excludes these packs. This PR flips the three manifest
flags to align the script with the test's intended scope.

## Verification

- closure verifier: 0 unresolved, 0 mismatches
- ADR-0084 integration test: 30/30
- domain contract test: <N>/<N>
- cognition eval: byte-identical to baseline
- packs lane: pass
- smoke lane: pass
```

3. Mark Draft. Human reviews before merge.

## Hard rules

- Do not touch glosses, lexicons, atoms, rules, axioms, or the chains file.
- Do not touch any code.
- Do not widen the ADR-0084 integration test's allowlist.
- Closure verifier must exit 0 after the flip.
- Cognition eval must be byte-identical to baseline.
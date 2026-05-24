# L3 brief — (Opus#2 or Gemini, small lane) — ADR-0131.1 Sealed Holdout for B1

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-1-sealed-holdout -b feat/adr-0131-1-sealed-holdout origin/main
cd ../core-adr-0131-1-sealed-holdout
```

**Scope.** Add a pyrage-X25519 sealed-holdout split to Benchmark 1 (symbolic equivalence v1, merged in #167). Mirror the methodology already proven on ADR-0119.7 for GSM8K — same crypto, same exit-criterion shape, different content. This makes the B1 lane's claim externally credible (operator cannot have peeked at the holdout cases).

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0119.7-sealed-gsm8k-test.md` — your methodological blueprint. Copy the sealed-holdout structure exactly.
2. `evals/math_symbolic_equivalence/v1/` (on main, post-#167) — the lane you're hardening. Do not modify `cases.jsonl`; you are *adding* a sealed split, not replacing.

**What to ship:**
- `evals/math_symbolic_equivalence/v1/sealed_holdout.age` — pyrage-X25519-encrypted JSONL of ~10–15 hand-curated cases. **Categories must match the curated 30 cases** (no novel categories — the sealed set is a held-out *sample* of the same distribution, not a different benchmark).
- `evals/math_symbolic_equivalence/v1/sealed_holdout.pubkey` — X25519 public key (private key stays off-repo per ADR-0119.7).
- `evals/math_symbolic_equivalence/v1/sealed_runner.py` — CLI that decrypts (env var `CORE_SEALED_KEY`) and runs the lane; refuses cleanly with typed error when key absent. Writes `sealed_report.json`.
- `tests/test_adr_0131_1_sealed_holdout.py` — 4–6 tests: encrypted file exists, decryption refuses without key, decrypted contents parse as valid case JSON, sealed-runner exit criterion matches public-runner (gate: `wrong == 0`, `correct_rate ≥ 0.95`).
- `docs/decisions/ADR-0131.1.S-sealed-holdout.md` — short ADR; cite ADR-0131 parent, ADR-0119.7 as methodology source, and #167 as the lane being hardened.

**Hard constraints:**
- **No peek.** The cases.jsonl on main is the public corpus; the sealed corpus must not duplicate any case_id or expression-pair from it. Lane test asserts disjointness post-decryption.
- **Same engine, no scope expansion.** The sealed runner calls the same `check_equivalence` API as the public runner. **Do not depend on PR #169** (the v1.B refactor) — that branch is in draft and may not land first. Stay within v1's univariate-integer-polynomial scope.
- **Refusal-first holds.** Out-of-scope sealed cases must refuse, not coerce.
- **Determinism.** `sealed_report.json` byte-equal across runs when `CORE_SEALED_KEY` set.
- **Trust boundary.** Decryption is the only filesystem-write you do; no logging of decrypted contents, no echo of raw cases to stdout. Cite the trust-boundary section of CLAUDE.md in the ADR.

**Out of scope (do not touch):**
- B2 / B3 lanes.
- Binding-graph implementation.
- #169 v1.B hardening — work strictly within v1's contract.
- Promotion-gate wiring.

**Coordinate with #169.** If #169 reconciles and merges *before* you open, rebase your branch onto the resulting main; the sealed cases must still pass under the v1.B engine (which is a strict superset of v1, so they should). If they don't, refuse to widen scope — flag it and stop.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.1.S): sealed holdout for symbolic equivalence v1`. Body must include lane result on sealed split + scope-discipline section.

**Exit criterion.** PR opens with CI green, sealed runner exits 0 (`wrong == 0`, gate passed) under a CI-provided key, ADR-0131.1.S included.

**Do not stack on another agent's branch.** Target main directly.

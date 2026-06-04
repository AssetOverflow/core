# Claims Ledger — Single Source of Truth

**Purpose.** Every public or material claim CORE makes — in `README.md`,
`CLAIMS.md`, ADRs, eval summaries, and any outward-facing brief or site copy —
maps here to its exact in-repo evidence and its *honest* framing. When a number
or status appears in any external material, it must reconcile against this file.
If a claim cannot be substantiated from the repo, it is softened or cut, not
defended.

> **Discipline:** Honesty is the product. CORE refuses rather than guesses; that
> discipline applies to how we describe ourselves, not only to what the engine
> outputs. Overclaiming to hit a deadline is failure, not success.

- **Base commit:** `c058d96` (origin/main).
- **Verification date:** 2026-06-02.
- **Reproduce the machine-derived rows:**
  ```bash
  uv run core capability ledger          # Tier-1 status (audit-passed ×3; NO expert)
  uv run python scripts/verify_lane_shas.py   # Tier-2 pinned lane SHAs
  uv run python scripts/generate_claims.py --check   # CLAIMS.md is current
  ```

---

## 1. The Four GSM8K Numbers — never conflate these

CORE has **four** distinct GSM8K-related measurements. They measure different
things on different data, and only **one** is the real external benchmark. Any
material that blurs them is a credibility risk.

| Tag | What it is | Result | Real GSM8K? | Gates expert? | Evidence |
|---|---|---|---|---|---|
| **A** | **Sealed real GSM8K test** (1,319 cases, HuggingFace `openai/gsm8k` test split) | **0 correct / 0 wrong / 1,319 refused** | **Yes** | No | `ADR-0119.7`; ciphertext `evals/gsm8k_math/holdouts/v1/cases.jsonl.age` |
| **B** | **CORE-authored synthetic "public" split** (150 cases, rule-based, written to exercise the grammar) | **150 correct / 0 wrong / 0 refused** (rate 1.0) | **No** | No | `evals/gsm8k_math/baselines/comparison_v1.json`, `frontier.json` |
| **C** | **Real `train_sample`** (50-case dev sample of real GSM8K) | **6 correct / 44 refused / 0 wrong** | Yes (sample) | No | `evals/gsm8k_math/train_sample/v1/report.json` |
| **D** | **Expert-promotion composite gate** (CORE-authored lanes B1/B2/B3) | **185/185 + 14/14 + 40/40 + 50/50, wrong=0** | **No** | Yes (but reverted — §2) | `ADR-0131.4`; `core/capability/composite_math_gate.py` |

**Per-number honest framing:**

- **(A) The honest external number.** `0/0/1319` — CORE's grammar covers **zero**
  real GSM8K test problems today. This is the truthful gap. The load-bearing
  property is **`wrong == 0` against the external corpus**: CORE *refuses* what it
  cannot grammar-handle; it does not confabulate. The seal is one-way
  (encrypted to an off-repo key); the number is a **recorded measurement**, not
  CI-reproducible without the holdout key. Never present A as an accuracy
  achievement — present it as zero-confabulation discipline plus an honest
  coverage gap.

  > **⚠ 2026-06-04 — `wrong=0` breach found and remediated.** The first re-run of
  > this sealed lane since the original record measured **`0 / 5 / 1314`** — the
  > `product_bridge` serving promotion (ADR-0195) had been silently committing **5
  > wrong** on held-out, invisible because the working metric was the 50-case train
  > sample it was tuned to. Bisection isolated it; both serving promotion bridges
  > (`product_bridge`, `goal_residual`/ADR-0207 §5 step 2) were **disabled**
  > (`generate/math_candidate_graph.py`), restoring `0/0/1319`. **The bridges must
  > not be re-enabled without a gate proven `wrong=0` on this sealed set, not the
  > train sample.** Lesson: the train_sample number had **zero predictive validity**
  > for the exam; never treat it as the score again.
- **(B) A frontier *comparison*, not a benchmark result.** 150/150 is on a split
  **CORE wrote**, designed to exercise its own grammar without data
  contamination. `frontier.json` itself flags the "apples-vs-oranges" caveat:
  frontier LLMs (Claude 3.5 Sonnet 96.4%, GPT-4 92.0%, Gemini 1.5 Pro 90.8%) are
  scored on *real* GSM8K. **Never cite B as "CORE scores 100% on GSM8K."** The
  qualitative differentiator is `wrong=0`, not the rate.
- **(C) The dev-sample reality.** 6/44/0 on 50 real cases — the lane's
  `exit_criterion` (`correct_min: 10`) is **NOT met**. A stricter candidate-graph
  coverage probe reports **4/46/0** on the same 50 cases
  (`train_sample_coverage_report.json`); both preserve `wrong=0`. The two readers
  differ on 2 fast-path cases. The probe's movement (`3→4`) is precisely what
  reverted the expert claim (§2).
- **(D) CORE-authored, and currently NOT conferring expert.** All four B-lanes are
  written and scored by CORE; none is external GSM8K. ADR-0131.4 replaced the
  original real-GSM8K gate (`correct_rate ≥ 0.60`) with this composite; ADR-0131.5
  retired the GSM8K probe from per-iteration gating. **Expert status therefore
  rests on CORE-authored evals, not external GSM8K — and must always be stated
  that way.** It is also *currently reverted* (§2).

---

## 2. Capability ledger status — and the expert fail-closed revert

**No domain is at `expert`.** The live ledger (`core capability ledger`) reports:

| Domain | Status | Note |
|---|---|---|
| `mathematics_logic` | **audit-passed** | expert promotion **fail-closed-reverted** — see below |
| `physics` | audit-passed | no expert composer wired |
| `systems_software` | audit-passed | no expert composer wired |
| `hebrew_greek_textual_reasoning` | reasoning-capable | — |
| `philosophy_theology` | reasoning-capable | — |

**What `audit-passed` means (and does NOT).** Per `ADR-0113`, `audit-passed`
verifies *CORE claim-shape compliance* — signed digest, replay determinism, typed
refusal, exact recall, grounding provenance. These are shapes a transformer LLM
cannot structurally produce regardless of raw accuracy. **It is explicitly NOT a
raw-capability claim.** A frontier LLM might score higher on the same benchmark
and still fail this contract.

**The expert revert (the honesty story).** On 2026-05-23 `mathematics_logic` was
signed and promoted to `expert` (the first-ever flip). It **auto-reverted to
`audit-passed`** when its evidence bundle later drifted. The live composer refuses:

> `reviewer claim_digest mismatch — registry has '4c46f530…', evidence-derived
> digest is '02f6d3c8…'; the evidence bundle has changed since the signature was
> added.`

Root cause (proven 2026-06-02, Week-1a): **genuine single-source evidence-drift,
not a determinism defect.** The digest is byte-stable across processes and
`PYTHONHASHSEED`; all digest/obligation modules are unchanged since signing; the
signature was valid at its commit; the **only** moved input is the GSM8K coverage
probe (`train_sample_coverage_report.json`, `3/47 → 4/46` via PRs #310/#488), and
restoring those bytes in-place reproduces `4c46f530` exactly. This is the
ADR-0120 fail-closed property working as designed — **CORE revoked its own expert
claim when its evidence moved.** Full record: `ADR-0200`.

> **Known safe-direction wrinkle (documented, not yet fixed):** a *non-gating*
> GSM8K disclosure value is committed into the *gating* digest, so improving
> coverage invalidates the signature. It fails toward `audit-passed`, never toward
> a false `expert` — so it is not a `wrong=0` hazard. Digest-scoping refinement is
> deferred to a future ADR (`ADR-0200` §Consequences).

---

## 3. Verified invariants (safe to assert)

| Claim | Evidence | Reproduce |
|---|---|---|
| Versor closure `‖F·reverse(F) − 1‖_F < 1e-6` at all times | `algebra/`, `tests/test_versor_closure.py` | `uv run pytest tests/test_versor_closure.py` |
| **Byte-identical replay / determinism** (same inputs → same trace hash) | `core/cognition/trace.py`; lane reports byte-equal across runs | digest determinism proven Week-1a (stable across processes/seeds) |
| **Refuse-rather-than-guess / `wrong = 0`** | typed refusal across all four GSM8K numbers; `verify.py` gate | A/B/C/D all `wrong=0` |
| Exact CGA recall (no ANN / HNSW / cosine) | `vault/store.py`; `docs/Yellowpaper.md` recall section | `uv run core test --suite algebra` |
| Safety pack: add-but-never-remove, fail-closed on load | `packs/safety/core_safety_axes_v1.json`; `ADR-0029` | `uv run core test --suite smoke` |
| On-device, non-LLM, no sampling/gradient/tokenizer | architecture; `README.md` "Third Door" | — |

---

## 4. Multimodal status — text only is *capability*; the rest is substrate or proposal

The patent application's "multimodal" title is broader than what is demonstrated
in-repo. **External materials must not imply working vision or motor.**

| Modality | Status | Evidence |
|---|---|---|
| **Text** (English, Hebrew, Koine Greek) | **Active capability** | `sensorium/adapters/text.py`; language packs |
| **Audio** | **Substrate landed, gate CLOSED (no capability claim)** | `sensorium/audio/*`; `make_audio_pack(gate_engaged=False)`; determinism + order-invariant CRDT merge + no-PCM-in-trace all gate-tested |
| **Vision** (`ADR-0197`) | **Proposed only** — no code, no pack, no eval | `Modality.VISION` enum exists; no `sensorium/vision/` |
| **Motor** (`ADR-0198`) | **Proposed only** — "design spike, no implementation" | registry has no `decode()` path; `persona/motor.py` is an *internal CGA screw motion*, not an actuator |

Honest line: *text is a working modality; audio is a determinism-proven substrate
with its capability gate deliberately closed; vision and motor are design
proposals with no implementation.*

---

## 5. Attestation — single-signer (a known boundary)

The reviewer registry has exactly **one** signer: `shay-j`, `domains: ["*"]`,
`role: primary` (`docs/reviewers.yaml`; `reviewer_count: 1`). Every
`audit_passed_claims` and the (now-quarantined) `math_expert_claims` entry is
signed by the same identity. This is a real single-point-of-capture a partner may
probe. The migration toward a multi-reviewer / threshold-signing registry is
scoped as a Week-4 deliverable (`ADR-02xx`, design-only — no fake signers).

---

## 6. Claims we explicitly do NOT make

- ❌ "A domain is at `expert`." → No domain is; `mathematics_logic` is
  `audit-passed` (expert reverted).
- ❌ "CORE is externally validated on GSM8K." → The expert gate rests on
  **CORE-authored** lanes; the real external number is A = `0/0/1319`.
- ❌ "CORE scores ~100% on GSM8K." → That is B, a CORE-authored synthetic split.
- ❌ "CORE has vision / motor / working multimodal perception." → Audio is
  substrate-only (gate closed); vision/motor are proposals.
- ❌ "`audit-passed` means expert-level capability." → It is claim-shape
  compliance, not raw capability (`ADR-0113`).

---

## 7. Reconciliation log (proposed — pending operator ratification)

These reconcile stale artifacts to the truth above. **History-describing**
artifacts keep their content with a dated "valid-at … auto-reverted … current =
audit-passed" note (keep the receipt; keep the mismatch-refusal firing).
**Current-machine-state** artifacts reconcile to the truth. Tracked in `ADR-0200`.

| Artifact | Type | Action |
|---|---|---|
| `docs/reviewers.yaml` `math_expert_claims` | history (receipt) | keep entry; add quarantine note; do not re-sign |
| `docs/decisions/ADR-0120-math-expert-ledger-flip.md` | history | header note: valid-at 2026-05-23, auto-reverted, current = audit-passed |
| `evals/math_expert_claims/v1/expert_claims_math_v1_signed.json` | current state | regenerate → `promote_admitted: false` |
| `README.md` §"Path to expert" + ledger lines | current state | reconcile narrative to built-attempted-reverted; verify test count |
| `tests/test_mathlogic_expert_ledger_flip.py`, `tests/test_adr_0120_math_expert_promotion.py` | current state | flip 3 red "is-expert" assertions into fail-closed-revert assertions |

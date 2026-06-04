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

- **Base commit:** `3a72d69` (origin/main before this reconciliation branch).
- **Verification date:** 2026-06-03 / 2026-06-04 UTC merge window.
- **Reproduce the machine-derived rows:**
  ```bash
  uv run core capability ledger                  # Tier-1 status (audit-passed ×3; NO expert)
  uv run python scripts/verify_lane_shas.py      # Tier-2 pinned lane SHAs
  uv run python scripts/generate_claims.py --check   # CLAIMS.md is current, when regenerated from this ledger
  uv run python -m pytest tests/test_vision_eval_gates.py -q
  uv run python -m pytest tests/test_audio_compiler.py tests/test_audio_crdt_merge.py tests/test_audio_sensorium_mount.py -q
  uv run python -m pytest tests/test_observation_frame_contract.py tests/test_sensorimotor_contract.py -q
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
| **C** | **Real `train_sample`** (50-case dev sample of real GSM8K) | **7 correct / 43 refused / 0 wrong** | Yes (sample) | No | `evals/gsm8k_math/train_sample/v1/report.json` |
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
- **(B) A frontier *comparison*, not a benchmark result.** 150/150 is on a split
  **CORE wrote**, designed to exercise its own grammar without data
  contamination. `frontier.json` itself flags the "apples-vs-oranges" caveat:
  frontier LLMs (Claude 3.5 Sonnet 96.4%, GPT-4 92.0%, Gemini 1.5 Pro 90.8%) are
  scored on *real* GSM8K. **Never cite B as "CORE scores 100% on GSM8K."** The
  qualitative differentiator is `wrong=0`, not the rate.
- **(C) The dev-sample reality.** `7/43/0` on 50 real cases — the lane's
  `exit_criterion` (`correct_min: 10`) is **NOT met**. The latest lift is the
  ADR-0207 §5 R4 goal-residual production (`generate/derivation/goal_residual.py`),
  which moves train-sample case `0037` while preserving `wrong=0`. A stricter
  candidate-graph coverage probe is a separate diagnostic lane and must not be
  conflated with the serving train-sample report.
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
| Sensorium compiler law: compiled afferent units are content-addressed, replayable, and merge by deterministic key | `sensorium/compiler/*`; audio/vision/sensorimotor tests | see §4 reproduce commands |
| On-device, non-LLM, no sampling/gradient/tokenizer in the CORE runtime path | architecture; `README.md` "Third Door" | — |

---

## 4. Multimodal status — distinguish capability from substrate

The patent application's "multimodal" title is broader than what is demonstrated
as end-user capability in-repo. **External materials must not imply working
open-domain vision, audio understanding, robotics, or autonomous action.** The
current truth is: text is capability; audio/vision/sensorimotor are deterministic
afferent substrates with gates and synthetic evals; motor/efferent output is
fail-closed governance scaffolding only.

| Surface | Status | Evidence | Honest claim boundary |
|---|---|---|---|
| **Text** (English, Hebrew, Koine Greek) | **Active capability** | `sensorium/adapters/text.py`; language packs | Working textual modality. |
| **Audio** (`audio_core_v1`) | **Substrate landed, gate CLOSED by default** | `sensorium/audio/*`, `sensorium/adapters/audio.py`, `packs/audio/audio_core_v1/`, `tests/test_audio_*` | Deterministic compiler substrate; no broad audio-understanding capability claim. |
| **Vision** (`vision_core_v1`) | **Substrate landed, gate CLOSED by default** | `sensorium/vision/*`, `sensorium/adapters/vision.py`, `packs/vision/vision_core_v1/`, `evals/vision_sensorium/`, `tests/test_vision_eval_gates.py` | Tile-first deterministic visual compiler over synthetic fixtures; no open-domain vision claim. |
| **Environmental loop** (`ADR-0208`) | **Afferent observation-frame contract landed** | `sensorium/environment/frame.py`, `sensorium/environment/harness.py`, `tests/test_observation_frame_*` | Bundles already-compiled afferent units; not late fusion, not a mutable world model. |
| **Sensorimotor feedback** (`ADR-0209`) | **Afferent substrate landed** | `sensorium/sensorimotor/*`, `sensorium/adapters/sensorimotor.py`, `tests/test_sensorimotor_*` | Proprioception/contact/action-result evidence only; no decoder, actuator driver, trajectory executor, or skill invocation. |
| **Motor / efferent output** (`ADR-0198`) | **Partially implemented governance spike; action emission still refused unless verdict-governed** | `ModalityRegistry.decode*`, `AuthorityToken`, `DefaultEfferentGate`, `EfferentRefusal` | Registry path exists, but no motor decoder or real actuation capability is claimed. |

Honest line: *text is a working modality; audio/vision/sensorimotor are
replayable afferent compiler substrates with gates and eval fixtures; motor is a
fail-closed efferent governance surface, not an actuator.*

---

## 5. Attestation — single-signer (a known boundary)

The reviewer registry has exactly **one** signer: `shay-j`, `domains: ["*"]`,
`role: primary` (`docs/reviewers.yaml`; `reviewer_count: 1`). Every
`audit_passed_claims` and the (now-quarantined) `math_expert_claims` entry is
signed by the same identity. This is a real single-point-of-capture a partner may
probe. The migration toward a multi-reviewer / threshold-signing registry is
scoped as a future design deliverable — no fake signers.

---

## 6. Claims we explicitly do NOT make

- ❌ "A domain is at `expert`." → No domain is; `mathematics_logic` is
  `audit-passed` (expert reverted).
- ❌ "CORE is externally validated on GSM8K." → The expert gate rests on
  **CORE-authored** lanes; the real external number is A = `0/0/1319`.
- ❌ "CORE scores ~100% on GSM8K." → That is B, a CORE-authored synthetic split.
- ❌ "CORE has broad working multimodal perception." → Audio, vision, and
  sensorimotor are afferent substrates/eval lanes, not demonstrated open-domain
  capability.
- ❌ "CORE can perform motor actions / robotics / vehicle control." → Efferent
  output is fail-closed governance scaffolding only; no motor decoder/actuator
  path is ratified.
- ❌ "`audit-passed` means expert-level capability." → It is claim-shape
  compliance, not raw capability (`ADR-0113`).

---

## 7. Reconciliation log

These reconcile stale artifacts to the truth above. **History-describing**
artifacts keep their content with dated context. **Current-machine-state**
artifacts reconcile to the truth.

| Artifact | Type | Action |
|---|---|---|
| `docs/claims_ledger.md` | current state | reconciled to `7/43/0`, afferent sensorium substrate landed, and fail-closed efferent governance scaffold |
| `CLAUDE.md` GSM8K substrate header | current operator instruction | reconcile serving metric to `7/43/0`; keep wrong=0 governor |
| `evals/gsm8k_math/train_sample/v1/README.md` | current eval summary | reconcile current report and note R4 goal-residual lift |
| `docs/decisions/ADR-0207-gsm8k-substrate-ratification.md` | ratified decision with evolving execution status | keep ratification baseline; add current-state note after R4 lift |
| `docs/reviewers.yaml` `math_expert_claims` | history (receipt) | keep entry; add quarantine note separately; do not re-sign |
| `docs/decisions/ADR-0120-math-expert-ledger-flip.md` | history | header note: valid-at 2026-05-23, auto-reverted, current = audit-passed |
| `evals/math_expert_claims/v1/expert_claims_math_v1_signed.json` | current state | future regeneration should preserve `promote_admitted: false` until a ratified expert path exists |

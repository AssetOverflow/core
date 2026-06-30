<!--
Source of truth: docs/claims_ledger.md (merged main). Every number and status in
this brief reconciles to that file. Nothing here is sourced from memory; claims
that cannot be substantiated from the repository are omitted, not defended.
Prepared for an internal technical conversation. Not for distribution.
-->

# CORE — Technical Brief
### A replayable, refusable, audit-grade decision substrate — *beneath* an autonomy stack, not a perception system

> **Read this boundary first.** CORE is **not** a perception, navigation, SLAM, or
> motor-control system, and it does not overlap with or compete against BrainOS.
> It is a deterministic decision-and-accountability **substrate** that can sit
> underneath an autonomy stack and make *bounded* decisions it can prove. Wherever
> this brief touches robotics, it is describing that substrate role — never
> perception. If a claim below cannot be reproduced from the repository, it does
> not belong here.

---

## Executive summary (one page)

CORE is a deterministic, non-LLM cognitive engine built on Cl(4,1) conformal
geometric algebra. It has no transformer backbone, no sampling temperature, no
gradient descent, no approximate-nearest-neighbour index, and no standard
tokenizer. Three properties are load-bearing and **reproducible from the repo
today**:

1. **Byte-identical replay.** The same inputs produce the same decision trace and
   the same trace hash, across processes and runs.
2. **Exact recall and typed refusal.** Memory recall is exact (no ANN / cosine
   approximation). When input is under-determined or out-of-distribution, the
   engine emits a **typed refusal** rather than a guess. Across every external
   measurement we have, the *wrong* count is **zero** — it refuses instead of
   confabulating.
3. **Add-but-never-remove safety + single-mutation-path learning.** Safety
   boundaries load fail-closed and cannot be removed by content; knowledge enters
   the runtime through exactly one reviewed path.

**The sharpest evidence of this discipline came from CORE turning it on itself.**
On 2026-05-23 CORE signed an internal **"expert"** capability claim for its
mathematics domain against its own evidence bundle. Weeks later it **automatically
revoked that claim** — dropping the domain back to `audit-passed` — the moment a
*non-gating* coverage metric drifted and the signature no longer re-derived. No
human intervened; the engine refused to keep carrying a claim its evidence no
longer supported. That is *refuse-rather-than-guess applied to CORE's own status*,
and it is the same mechanism that, beneath an autonomy stack, produces a decision
record a safety reviewer can **replay byte-for-byte and trust** — because the
system will not assert what it cannot currently re-derive.

**What this is worth to a robotics autonomy stack.** Not perception — that is
solved above CORE, in BrainOS. The value is the layer *beneath* a bounded
decision:

- **Replayable decision provenance** — every bounded decision (proceed / stop /
  hand off) carries a deterministic, re-derivable trace for incident review.
- **Refusal on ambiguity / OOD** — under-determined or out-of-distribution inputs
  produce a typed *refusal* (escalate to human / safe-state), never a fabricated
  answer.
- **Audit-grade accountability** — the record is exact, content-addressed, and
  reproducible offline on-device, so "why did it decide that?" has a byte-exact
  answer.

**What this is NOT (stated plainly, because it is where credibility is won or
lost).** No domain is at `expert`. CORE is **not** externally validated on a
public benchmark as a capable solver — on the real GSM8K test set it solves
**0 of 1,319** problems and gets **0 wrong** (it refuses all of them; see §4).
Its `audit-passed` domains are a **claim-shape** compliance result, *not* a
raw-capability claim. Audio is a determinism-proven substrate with its capability
gate deliberately **closed**; vision and motor are **design proposals with no
implementation**. Attestation currently has a **single signer**. These boundaries
are detailed below and are the point: the differentiator is not capability scores,
it is that every claim is exact, reproducible, and refusable — including the
claims CORE makes about itself.

**How a skeptic should check this brief:** don't trust it — run it. These three
run green on a fresh clone of `main` with no native backend built:

```bash
uv run core capability ledger                       # status: audit-passed x3, NO expert (prints the revert reason live)
uv run pytest tests/test_versor_closure.py          # the core algebraic invariant (9 tests, <1s)
uv run python demos/amr_decision_substrate/run_demo.py   # bounded decision + byte-identical replay + real refusal
```

The pinned eval-lane SHAs (`scripts/verify_lane_shas.py`) are a separate,
CI-enforced gate — the `lane-shas` workflow is green on every `main` merge. Run
it locally only with the native Rust backend built (`core rust build`): it
re-runs the demos under the ADR-0099 30-second budget, which the Python fallback
can exceed on a fresh clone.

---

## Backing detail

### 1. The fail-closed revert, in full (the honesty story, with receipts)

On 2026-05-23 `mathematics_logic` was signed and promoted to the `expert` ledger
tier — the first such promotion. As of today the live ledger reports it as
**`audit-passed`**, and the promotion composer refuses with a typed reason:

> `reviewer claim_digest mismatch — registry has '4c46f530…', evidence-derived
> digest is '02f6d3c8…'; the evidence bundle has changed since the signature was
> added.`

This was investigated to ground (record: **ADR-0200**). The finding:

- **It is genuine evidence-drift, not a determinism defect.** The digest is
  byte-stable across processes and hash seeds; every digest/obligation module is
  unchanged since signing; the signature was valid *at its commit*; and the
  **only** input that moved is one GSM8K coverage probe (`3/47 → 4/46`). Restoring
  those exact bytes in place reproduces the original signed digest `4c46f530…`.
- **It failed in the safe direction.** The drift dropped the status *toward*
  `audit-passed`, never *toward* a false `expert`. This is the documented
  fail-closed property of the promotion contract working as designed.

Why a CTO should care: the property that revoked CORE's self-claim is the same
property that prevents a stale or unsupported *decision* from being asserted
downstream. The engine's honesty is structural, not aspirational.

### 2. Verified invariants (each reproducible from the repo)

| Invariant | Evidence | Reproduce |
|---|---|---|
| Versor closure `‖F·reverse(F) − 1‖_F < 1e-6` at all times | `algebra/`, `tests/test_versor_closure.py` | `uv run pytest tests/test_versor_closure.py` |
| Byte-identical replay / determinism | `core/cognition/trace.py`; lane reports byte-equal across runs; digest stability proven in ADR-0200; lane-SHA pins enforced by CI | `uv run python demos/amr_decision_substrate/run_demo.py` → `trace_a == trace_b` |
| Refuse-rather-than-guess / `wrong = 0` | typed refusal; the four GSM8K `wrong=0` numbers are itemized in §4, sourced to the ledger | `uv run python demos/amr_decision_substrate/run_demo.py` (under-determined case → typed `recognition_refused`) |
| Exact CGA recall (no ANN / HNSW / cosine) | `vault/store.py`; `docs/Yellowpaper.md` recall section | `uv run core test --suite algebra` |
| Safety pack: add-but-never-remove, fail-closed on load | `packs/safety/core_safety_axes_v1.json`; ADR-0029 | `uv run core test --suite smoke` |
| Single reviewed mutation path for learning | architectural-invariant test; `docs/truth_seeking_schema.md` | `uv run pytest tests/test_architectural_invariants.py` |

### 3. Honest status — demonstrated vs roadmap

| Capability / property | Status | Evidence |
|---|---|---|
| Deterministic decision + provenance + typed refusal (text) | **Demonstrated** | invariants in §2 |
| Exact, offline, on-device recall | **Demonstrated** | `vault/store.py` |
| Text modality (English, Hebrew, Koine Greek) | **Demonstrated** (capability) | `sensorium/adapters/text.py` |
| Audio modality | **Substrate landed, capability gate CLOSED** — no capability claim | `sensorium/audio/*`; `make_audio_pack(gate_engaged=False)`; determinism + order-invariant CRDT merge + no-raw-PCM-in-trace are gate-tested |
| Vision modality | **Proposed only** (no code) | ADR-0197; `Modality.VISION` enum exists, no `sensorium/vision/` |
| Motor modality | **Proposed only** ("design spike — no implementation") | ADR-0198; registry has no efferent `decode()` path |
| Domain capability tier `expert` | **None** (math signed then auto-reverted) | §1; ADR-0200 |
| Domains at `audit-passed` (claim-shape compliance) | `mathematics_logic`, `physics`, `systems_software` | `core capability ledger`; ADR-0113 |
| Domains at `reasoning-capable` | `hebrew_greek_textual_reasoning`, `philosophy_theology` | `core capability ledger` |
| Bounded AMR decision demo (proceed/stop/refuse, replayable) | **In review, not merged** (companion, not evidence) | PR #520 (draft) — *cited only as roadmap; nothing in this brief depends on it* |

> **What `audit-passed` means — and does not.** It verifies CORE *claim-shape
> compliance*: a signed digest that re-derives, replay determinism, typed refusal,
> exact recall, and grounding provenance. These are shapes a transformer LLM
> cannot structurally produce regardless of raw accuracy. **It is explicitly not a
> raw-capability claim.** A frontier LLM might score higher on the same benchmark
> and still fail this contract (ADR-0113).

### 4. The four GSM8K numbers — separated so they are never conflated

CORE has four distinct GSM8K-related measurements. Only **A** is the real external
benchmark. Conflating them would be the fastest way to lose a technical reviewer's
trust, so they are kept explicitly apart.

| Tag | What it measures | Result | Real GSM8K? | Gates `expert`? |
|---|---|---|---|---|
| **A** | Sealed **real** GSM8K test (1,319 cases) | **0 correct / 0 wrong / 1,319 refused** | **Yes** | No |
| **B** | CORE-authored **synthetic** "public" split (150 cases) | **150 / 0 / 0** | No | No |
| **C** | Real `train_sample` dev sample (50 cases) | **6 correct / 44 refused / 0 wrong** | Yes (sample) | No |
| **D** | Expert-promotion composite gate (CORE-authored lanes) | **185/185 + 14/14 + 40/40 + 50/50, wrong=0** | No | Yes (currently reverted) |

- **A is the honest external number.** CORE's grammar covers **zero** real GSM8K
  test problems today — a truthful coverage gap. The load-bearing property is
  `wrong = 0` against the external corpus: it refuses what it cannot handle rather
  than confabulating. (Sealed, key-gated; a recorded measurement — `ADR-0119.7`.)
- **B is a frontier *comparison*, not a benchmark result** on a CORE-authored
  split, with the apples-vs-oranges caveat flagged in-repo. For reference, frontier
  LLMs on *real* GSM8K report ~90–96% (Claude 3.5 Sonnet 96.4%, GPT-4 92.0%,
  Gemini 1.5 Pro 90.8%). **CORE does not claim a comparable score.** The
  differentiator is `wrong = 0`, not the rate.
- **C** is the dev-sample reality; its `correct_min: 10` exit criterion is **not
  met**.
- **D's** four lanes are all **CORE-authored** — none is external GSM8K. The
  original real-GSM8K gate (`correct_rate ≥ 0.60`) was replaced by this composite
  (ADR-0131.4) and the GSM8K probe was retired from gating (ADR-0131.5).
  **Therefore the `expert` contract rests on CORE-authored evals, not external
  validation — and it is currently reverted regardless** (§1).

### 5. Specific value beneath an autonomy stack (substrate, not perception)

Perception, navigation, and motor control are above CORE and out of scope. The
substrate value is the accountable decision layer underneath a *bounded* decision:

- **Decision provenance that replays.** A bounded proceed / stop / hand-off
  decision emits a deterministic, content-addressed trace. Incident review gets a
  byte-exact answer to "why did it decide that?", reproducible offline on-device.
- **Refusal as a first-class output.** Under-determined or out-of-distribution
  inputs route to a typed refusal (escalate / safe-state), never a fabricated
  decision. This is the property a deterministic-safety posture actually needs at
  the decision boundary.
- **Accountability that cannot be quietly edited.** Safety boundaries are
  add-but-never-remove and fail-closed; learning flows through one reviewed path;
  identity/policy cannot be rewritten by input. The audit trail is structural.

This is complementary to BrainOS, not competitive with it: BrainOS owns
perception and navigation; CORE offers an auditable, refusable decision/record
substrate beneath bounded decisions for partners who need deterministic
accountability they can replay.

### 6. Known boundaries we name before a reviewer finds them

- **No `expert` domain.** The only promotion fail-closed-reverted; the gate is
  CORE-authored, not externally validated (§1, §4).
- **`audit-passed` ≠ capability.** Claim-shape compliance only (ADR-0113).
- **External benchmark coverage is currently zero** (A = 0/0/1,319). We present
  this as zero-confabulation discipline plus an honest coverage gap, never as an
  achievement.
- **Multimodal is mostly roadmap.** Audio = substrate, gate closed; vision/motor =
  proposals with no implementation. No working perception of any kind.
- **Single-signer attestation.** The reviewer registry has exactly one signer
  (`shay-j`, `domains: ["*"]`, `reviewer_count: 1`). This is a real
  single-point-of-capture; the migration to multi-reviewer / threshold signing is
  scoped as a design ADR (no fabricated signers).
- **A documented, safe-direction digest wrinkle.** A non-gating coverage value is
  committed into the gating digest, which is why coverage improvement can revoke
  the signature. It only ever fails toward `audit-passed`; the scoping refinement
  is deferred to a future ADR (ADR-0200).

### 7. Reproduce everything

```bash
# Local — green on a fresh clone, no native backend required:
uv run core capability ledger                       # Tier-1 domain status (audit-passed x3, no expert)
uv run pytest tests/test_versor_closure.py          # the core invariant
uv run python demos/amr_decision_substrate/run_demo.py   # bounded decision + byte-identical replay
uv run python scripts/generate_claims.py --check    # CLAIMS.md reproduces from in-tree state (static pins + ledger)
```

> The four GSM8K numbers (A/B/C/D — all `wrong=0`) are itemized in §4 and sourced
> to the ledger; **read** them there rather than run a command, because
> `core eval gsm8k_math` defaults to the CORE-authored synthetic split (B) and its
> `100%` is *not* a real-GSM8K result.

The Tier-2 pinned eval-lane SHAs (`scripts/verify_lane_shas.py`) are verified by
the `lane-shas` CI workflow — green on every `main` merge. Run it locally only
with the native Rust backend built (`core rust build`), since it re-runs the
demos under the ADR-0099 30-second budget.

Single source of truth for every figure above: [`docs/claims_ledger.md`](../claims_ledger.md).

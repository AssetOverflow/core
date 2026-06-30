# Scope: wiring proof-carrying coherence promotion (the decision)

**Date:** 2026-06-14
**Status:** decision scope — **no code; nothing wired without your call.**
**Context:** the epistemic-coherence finding
(`docs/analysis/epistemic-coherence-architecture-2026-06-14.md`) established that
the speculative ceiling does **not** blunt learning. The *only* genuine epistemic
lever is wiring the proof-carrying promotion path. This doc scopes that decision.
Builds on the existing design doc `docs/issues/proof-carrying-coherence-promotion.md`
(ADR-0218) — read it first; this adds the bootstrapping analysis and frames the call.

## What the path actually is (precise)

`teaching/proof_promotion.certify_promotion` + `vault/store.py::apply_certified_promotion`
promote a SPECULATIVE vault claim to **COHERENT** iff a `PromotionCertificate`
fail-closes through **all** of:
1. the certificate **replays/verifies** under the pinned deductive engine
   (`DEDUCTIVE_ENGINE_PIN`) — independent re-verification, not trust;
2. the **claim** is SPECULATIVE, `reading_certified`, and its `propositional_form`
   matches the certificate;
3. **every premise** is `reading_certified`, form-matched, and **already COHERENT**
   (`vault/store.py:475-507`).

It is built, sound, and proven (`tests/test_adr_0218_proof_promotion.py`,
INV-29). **It has zero runtime callers** — only tests + the demo invoke it.

## The bootstrapping reality (the load-bearing subtlety)

The path is the **inductive step only**: *coherent premises + verified proof →
coherent conclusion*. But every realized fact is born SPECULATIVE
(`realize.py:217`), and **promotion fail-closes on any non-coherent premise.** So
the path can lift **nothing** until a **coherent base case** exists — and nothing
in the runtime mints one. In the tests the coherent premises are hand-injected
(`_coherent_premises` stores entries directly as `COHERENT`).

Therefore wiring is **two halves**, and half (a) is the real decision:
- **(a) A curator-certified coherent base.** A small, deliberate set of base
  facts/readings a curator declares COHERENT (axioms / ground readings). The
  design doc is explicit that the base + reading-certification **stay
  curator-mediated initially** — "entailment automated, reading human, the honest
  first cut" (proof-carrying-coherence-promotion.md:214-216). Without this, half
  (b) is inert.
- **(b) The runtime trigger.** Call `certify_promotion` → `apply_certified_promotion`
  when the determine/derive path produces a SPECULATIVE propositional claim that is
  deductively entailed by coherent premises in the vault. Narrow surface: it only
  fires for **certified propositional forms** (the deductive-logic flagship), not
  arbitrary cognition facts.

## What wiring buys (honest framing)

**This is an honesty/disclosure upgrade, not a learning fix.** Per the finding,
learning already works at the speculative ceiling. What changes:
- `determine._basis` could return `"verified"` (vs `"as_told"`) for a deductively
  **proven** propositional conclusion — the engine would honestly distinguish
  *"I proved this"* from *"I was told this"* (`render.py:31`).
- The COHERENT-gated recall probe (`chat/runtime.py:195`, `min_status=COHERENT`)
  would have content to return.

Scope of `"verified"` stays **narrow and defensible**: only propositional-entailment
conclusions from curator-certified coherent premises. That is exactly the verified
flagship (sound+complete propositional logic) — surfacing it honestly is
pitch-relevant ("watch it refuse to say *verified* unless it actually proved it").

## wrong=0 analysis

The promotion path itself **cannot false-promote**: it fail-closes on a failed
replay, a non-SPECULATIVE claim, an uncertified reading, a form mismatch, or any
non-coherent premise — and it never *vacuously* entails (refuses inconsistent
premise sets; `test_inconsistent_coherent_premises_refuse_never_vacuously_entail`).
**The entire risk shifts to half (a):** the soundness of `"verified"` reduces to
the soundness of the **curator-certified coherent base**. Garbage in the base →
sound proofs over garbage → false `"verified"`. So the base set must be small,
auditable, and genuinely curator-reviewed. The runtime trigger adds no risk the
fail-closed gate doesn't already cover.

## Work required (if you decide to wire)

1. **Base set (curated, reviewed):** a small certified-coherent axiom/reading set
   in the vault/seed — the deliberate ground for entailment. This is the real
   review work; keep it minimal.
2. **Runtime trigger (small):** invoke `certify_promotion`/`apply_certified_promotion`
   from the determine/derive path for certified propositional claims; fold the
   promotion digest into the turn `trace_hash` (the code notes this is the missing
   D4 step). Default-off flag first (mirror `vault_promotion_enabled`).
3. **Disclosure + tests:** `verified` now reachable → update `docs/runtime_contracts.md`,
   a non-vacuous test that a proof-backed claim becomes `verified` AND a
   non-proof-backed one stays `as_told`, and confirm no path emits `verified`
   without a replayed certificate.

## The decision (yours)

Three honest options:
1. **Wire it (narrow, deliberate):** stand up a minimal curator-certified base +
   the runtime trigger, default-off → on after review. Buys: honest `"verified"`
   for proven propositional conclusions. Cost: the base-curation + a ratified-ADR
   commitment to runtime coherence promotion. **My lean if you value the honesty
   capability for the pitch** — it's the one real, wrong=0-safe epistemic upgrade.
2. **Record "curator-mediated by design" (cheapest honest):** the design doc's own
   fallback (proof-carrying-coherence-promotion.md:232-234) — decide the logical arm
   isn't worth wiring now, amend the paper §3.4 to stop forward-referencing it, and
   leave promotion curator-mediated. Zero risk, zero capability gain.
3. **Defer:** keep it designed-but-unwired (status quo), revisit when a concrete
   use case (a demo, a pitch beat) needs runtime `"verified"`.

Recommendation: this is **not** urgent (it doesn't unblock learning), but it **is**
the single honest "the engine earns *verified*" capability. If the pitch wants that
beat, do (1) narrowly; otherwise (2) is the honest, cheap close. Either way, the
current "all speculative" state is **not** a defect to rush-fix.

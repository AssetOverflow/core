# CORE Boundary Lock — Reuse-vs-Build Plan

*Operationalizes `CORE_boundary_lock_spec.md`. Audited against `main`. Tags: **HAVE** (exists, reuse directly) · **PARTIAL** (exists but concentrated/incomplete) · **NET-NEW** (must build).*

The headline from the audit: this is **not greenfield.** ~80% of both halves already exists. Part 1 is "point existing admissibility + safety machinery at a new (hard) target." Part 2 is "harden existing single-signer attestation into multi-party." The genuinely new work is small and specific.

---

## Part 1 — `affirm_human_life` as constitutive inadmissibility

| Component | Status | Reuses |
|---|---|---|
| Refuse-preferring decision core ("evil not in the admissible set") | **HAVE** | `generate/derivation/*` — refuse on disagreement/ambiguity; wrong=0 preserved by refusal |
| Typed refusal verdicts + traces | **HAVE** | `EquivalenceVerdict` (REFUSED), `InnerLoopExhaustion`; replayable |
| Generic frame-based admissibility | **HAVE** | ADR-0022–0026: `AdmissibilityRegion`(`allowed_indices`,`relation_blade`,`frame_versor`), inner-loop `cga_inner`, `generate/rotor_admissibility.py`, margin gate |
| Unremovable boundary pattern | **HAVE** | `packs/safety/core_safety_axes_v1.json` — fail-closed, unioned, add-but-never-remove |
| Adversarial mastery gate pattern | **HAVE** | mastery report `G3_adversarial_rejection_rate=1.0`; `identity_anchor` ratification (ADR-0029) |
| Identity-axis duality (motor bias + trajectory scoring + lock) | **HAVE** | `PersonaMotor`, `IdentityManifold`, `no_identity_override` |
| Trilingual manifold + cross-language resonance | **HAVE** | `alignment/` (`AlignmentGraph`, `AlignmentEdge`, `alignment.jsonl`), `language_packs/` |
| **Harm-purpose region + telos test (the conscience's actual content)** | **NET-NEW** | §1.3 below — the real work |

Everything the conscience *runs on* is built. What's missing is the conscience's content: the harm-purpose region itself.

### §1.3 (rewritten) — the harm-purpose region, anchored trilingually

**Telos, not content.** A keyword ban on "harm/wound/kill" is a removable gate *and* wrong — casualty care must reason about wounds *to heal*. The boundary is about purpose/foreseeable effect: "reason about a hemorrhage to stop it" passes; "select a target to kill a person" is inadmissible. Content-matching can't separate those; purpose-orientation can.

**NET-NEW core:** ratify a *harm-to-persons relation region* through the existing teaching DAG, anchored as a `relation_blade`/frame, so admissibility rejects candidates whose **destination frame** lies in the harm-purpose region while preserving the heal/protect region.

**Anchor it in the trilingual convergence, not English surface forms (reuse the depth-language foundation).** This is the concrete lever for the hard part:
- English flattens purpose; Hebrew and Greek *lexicalize* it. Binyanim encode causation/agency morphologically (a hiphil causative is a distinct form, not a synonym); Greek encodes aspect and voice (middle/passive agency).
- The lexica distinguish what English collapses: רצח *ratzach* (murder) vs הרג *harag* (kill/slay broadly); φόνος *phonos* (murder) vs lawful killing; נפש *nephesh* as *living being*, not flat "life."
- **Triangulation = redundancy against euphemism.** An adversary laundering harm-intent in clean English ("neutralize the asset," "service the target") drifts the English token — but if the concept still resonates with the Hebrew/Greek roots for destroying a person, the geometry still localizes near the harm-region. They must evade *all three* resonances at once → the false-negative (euphemism) surface shrinks.
- It protects the **inverse heal-gate** too: a restore-telos resonates differently than a destroy-telos, which is exactly what keeps legitimate trauma/triage reasoning from being wrongly blocked.

**Honest bounds (so the claim stays calibrated):**
1. *Raises the bar; not impossible.* Triangulation makes laundering much harder, not unreachable; genuinely ambiguous cases still land in the boundary region — which is what the review-gated revisability is for.
2. *Domain-dependent strength.* Strongest at the moral/theological/textual core where the trilingual corpus is dense (murder of a person localizes beautifully); **thinner** for novel operational-harm framings far from that lexicon (drone targeting, cyber, logistics-of-harm). Supplement there — don't assume the root-systems cover it.
3. *Enriches coordinates, not the rule.* The languages give a sharper space to place the region in; someone still must define and ratify the region and its telos test. Representation help, significant — but not the whole of §1.3.

**Instrumented both directions; revisable only via the review-gated path** (never hot-path, never user-teachable). Mastery gates: `G_harm_rejection_rate=1.0`, `G_lifesaving_acceptance_rate=1.0`, `G_replay_determinism=1.0`, `G_provenance_nonempty=1.0`.

---

## Part 2 — uncoercible authenticity

| Component | Status | Reuses / Notes |
|---|---|---|
| Content-addressing & digests | **HAVE** | `*_sha256` everywhere; `core pack verify` |
| Signed claim digest that re-derives byte-for-byte | **HAVE** | `docs/reviewers.yaml` (`signed_by`+`claim_digest`); ADR-0106/0109 |
| Reviewer registry | **HAVE** | ADR-0092 |
| Provenance auditing | **HAVE** | pack-provenance auditor, ADR-0114a.10 |
| **Single-signer concentration** | **PARTIAL / RISK** | registry has **one** reviewer — `shay-j`, role `primary`, domains `["*"]`, all scopes; every claim `signed_by: shay-j`. *This is the single point of capture the whole governance arc set out to remove. It exists in the repo today.* |
| **Threshold (M-of-N) signing** | **NET-NEW** | no signing threshold exists (the `threshold` flags in `cli.py` are admissibility/OOV thresholds, unrelated) |
| **Reproducible binary builds** | **NET-NEW** | you have reproducible *results/digests*, not a reproducible *build* pipeline (pin toolchains; Nix/Reproducible-Builds) |
| **Public append-only transparency log** | **NET-NEW** | Merkle/transparency-log model (Sigstore rekor, TUF) |

The attestation *primitive* is already real and arguably ahead of most projects. What's missing is **distribution** — turning one trusted signer into M-of-N so no single party (including you) can ship a boundary-stripped official build, and making the build itself publicly reproducible and logged.

---

## Sequencing (smallest, highest-leverage first)

1. **§1.3 harm-purpose region prototype, trilingually anchored.** *Highest research risk; also the exact capability the casualty-care mission needs* — so this build pays twice. Start at the moral core where the trilingual corpus is densest.
2. **Expand the reviewer registry toward multi-party / threshold signing.** *Removes a risk that exists right now* — the single `shay-j` signer. Lowest technical cost, immediate governance payoff, and it operationalizes Charter §5 + Constraints §3.
3. **Reproducible builds + transparency log.** Supply-chain hardening; do once 1–2 land.

## The guarantee (unchanged, still truthful)

> Canonical CORE cannot be used, taught, or coerced into deliberate harm to persons — that refusal is constitutive of how it decides anything, verifiable by replay, and anchored across three independent root-systems so euphemism can't launder past it. It can only be defeated by forking and re-architecting the core — a loud, deliberate, publicly detectable act. No single party, including its makers, can ship an official build that weakens this, and there is no secret anyone can be pressured to surrender, because the conscience lives in the architecture, not a vault.

## Open questions
1. §1.3 telos-vs-content region — the genuine research problem; trilingual anchoring helps most at the moral core, needs supplementing toward technical-domain harm.
2. M, N, and signer selection (jurisdictional diversity); migration path off single-signer.
3. Reproducible builds across Python/Rust(/Zig).
4. Offline/austere attestation UX (verify-once-cache) so it doesn't break the on-device, no-network property.

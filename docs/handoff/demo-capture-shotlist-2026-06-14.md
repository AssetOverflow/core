# CORE Demo Capture Shot-List & Script (2026-06-14)

A ready-to-shoot plan for the first public-facing demo assets (flagship video,
short clips, screenshots). Every route, on-screen line, and honesty card below
is sourced from the live workbench — nothing here overclaims past what the
engine actually proves.

**Cardinal rule:** never open on the Chat box. The moat is *refuse / replay /
show-its-work*, not "type → get text." The target reaction is the workbench's
own guiding question (`docs/workbench/README.md`):

> "Wait… I can actually inspect and replay the cognition." — not "Cool chatbot."

---

## 0. Setup

```bash
core workbench api          # read-only backend on http://127.0.0.1:8765
# in a second terminal, from workbench-ui/:
pnpm dev                    # React UI
```

Capture settings:

- 1920×1080, or 2× retina downscaled for crisper text.
- Dark theme. Hide OS chrome / notifications. Full-screen the browser.
- Slow the cursor. **Pause 1–2s on every honesty card and every hash** — they
  are the payload; let viewers read them.
- Keep the **Evidence Chain Rail** visible where possible (reinforces
  "URL = subject; everything is addressable evidence").

The verbatim thesis (from `workbench/tour.py`) — use as tagline / cold-open VO,
do **not** re-author:

> "CORE is the deterministic engine the opaque transformer defines itself
> against. Bring a claim — from any model, including your own — and watch the
> engine decide it, refuse it, or replay it to the same hash. The proposing
> model's authority is ignored; only verified evidence promotes."

---

## 1. Flagship video — film the Tour (target 60–90s)

`/tour` is purpose-built for this: a 5-step narrative bound to the live demos,
where honesty cards are pulled from each demo spec and cannot claim more than
the demo proves. Film it in order.

| # | Route | Hold the camera on (real on-screen text) | Voiceover | Dur |
|---|---|---|---|---|
| 1 | `/tour` (intro) | "These are not screenshots or animations. Each step runs a real demo over pinned fixtures, end to end." | Read the thesis line above. | ~12s |
| 2 | `/demos/deductive_entailment_authority` | "served … only when the pinned ROBDD engine and an independent oracle **agree**" | "Two independent engines. They must agree, or it refuses." | ~12s |
| 3 | `/demos/epistemic_truth_state` | "You are watching a wrong answer get **refused** rather than served" | "This is what wrong=0 looks like — a wrong proposer gets rejected." | ~12s |
| 4 | `/demos/proof_carrying_promotion` | "authority lives in the **evidence**, not the model" | "Nothing enters memory without a verified certificate." | ~12s |
| 5 | `/replay` | "Replay to the same hash… Determinism isn't a claim here; it's a deliverable." | Re-run the turn; let both hashes sit side by side. | ~15s |

**Money shot:** step 5 — two identical trace hashes after a re-run. Freeze-frame
+ highlight box in post. This is the thumbnail and the pinned-tweet image; no
transformer demo can show it.

---

## 2. Short clips (15–40s each) — one capability per clip, numbered series

Post as a thread/reel series. Each is a self-contained "they can't do this."

| # | Route | What to show | Caption |
|---|---|---|---|
| 1 | `/demos/epistemic_truth_state` | Proposer smuggles an unsupported truth-state; engine rejects. | "We measure intelligence by what it refuses to say." |
| 2 | `/replay` | Run, re-run, hashes match. | "Same input, same cognition, same hash. Every time." |
| 3 | `/demos/{any}` | Slow zoom on the paired `what_this_proves` / `what_this_does_not_prove` cards. | "Every claim ships with what it does NOT prove." |
| 4 | `/evals` | The wrong=0 ledger; the **wrong** column at 0. | "0 wrong answers. Not 'low' — zero, by construction." |
| 5 | `/calibration` | Gold-tether arena: Wilson floor vs θ ceiling. | "It has to earn the right to guess — with a one-sided confidence floor." |
| 6 | `/trace` → Field tab | `versor_condition < 1e-6`, `field_valid`, field digest. | "Cognition runs on a geometric field — proven coherent to 1e-6." |
| 7 | `/lived-life` | Always-on heartbeat holding identity across reboot. | "Not a stateless chatbot. One continuous life." |
| 8 | `/trace` | Scrub Pipeline / Grounding / Verdicts / Surfaces tabs. | "Every turn, fully inspectable: intent → graph → realizer → verdict." |

---

## 3. Screenshot set (stills for README, site hero, social cards)

High-res, dark theme, Evidence Chain Rail visible.

1. **Hero:** the two matching trace hashes (`/replay`).
2. Honesty-card pair (`/demos/{any}`).
3. `/evals` wrong=0 ledger (the 0 column).
4. `/calibration` Wilson-floor-vs-θ arena.
5. `/trace` Field tab with `versor_condition`.
6. LeftNav fully expanded — all 7 sections (Converse / Cognition / Determinism /
   Evidence / Discipline / Substrate / Settings) — "instrument, not chat box" at
   a glance.
7. Command palette open (⌘K) over a route — operator-grade tooling signal.

---

## 4. Caption / VO bank (all from real on-screen text — nothing overclaims)

- "Bring a claim — from any model, including your own. The engine decides it,
  refuses it, or replays it to the same hash."
- "The proposing model's authority is ignored. Only verified evidence promotes."
- "These aren't screenshots or animations — each step runs a real demo over
  pinned fixtures, end to end."
- "Two independent engines have to agree, or it refuses to answer."
- "Determinism isn't a claim here. It's a deliverable."
- "Every claim ships with what it does *not* prove."

---

## 5. Docs walkthrough order (for the written launch post / deep dive)

- `docs/Whitepaper.md` / `docs/position_paper.md` — the "why" (decoding, not
  generating). Lead here.
- `docs/workbench/README.md` — the "cognition observatory, NOT a chatbot shell"
  framing; the guiding-question quote is a strong pull-quote.
- `docs/workbench/UI-UX-GUIDE.md` — operator/evaluator route map + evidence
  grammar; the proof the UX is *designed*. Cite for the UI/UX-value argument.
- `docs/runtime_contracts.md` — surface/walk/articulation contract (determinism
  is contractual, not aspirational).
- `CLAIMS.md` + `docs/claims_ledger.md` — the receipts. Linking these publicly
  is itself a credibility move.

Technical-reader combo: Whitepaper (idea) → Tour video (demo) → CLAIMS.md
(receipts).

---

## 6. Honesty guardrails — stay inside these (the whole pitch is honesty)

- **Do not** headline Chat answering a hard open-domain question. Verified
  capability is **formal/propositional decision**, not broad NL reasoning — the
  demos' own `what_this_does_not_prove` cards say so; let them. If Chat appears,
  it's "the conversational surface," not "look how smart it is."
- **GSM8K is a diagnostic, not a flagship.** Never headline a math score. If math
  appears, it's "watch it *refuse* what it can't ground."
- **Lived Life is real; the frontier is honest.** Resume-as-same-life and
  idle-tick learning are built; the *indefinite* always-on process is the active
  edge. "One continuous life" (true), not "alive for months" (not yet).
- **Lean on the honesty cards harder than on any capability.** A system that
  volunteers its own limits on screen is what makes serious people trust the
  rest.

---

## 7. Post-production cues

- Freeze-frame + highlight box on the matching hashes (flagship step 5, clip 2).
- 1–2s holds on every honesty card and every hash.
- Lower-thirds from the caption bank only — no invented claims.
- Brand voice: humble + confident, geometric. Donations/credit: ACB Content;
  site core.acbcontent.org.

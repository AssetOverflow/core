# VERIFIED serving-wiring — `verified_serving_enabled` — scoping brief

**Date:** 2026-06-08 · **Status:** scoping (NO CODE) · **HOLD for review** ·
**Branch:** `docs/serving-integration-scoping`

**What this brief is.** The scope for the served-surface decision the VERIFIED lane
deferred. The off-serving VERIFIED lane is complete and on main:

```text
P1-A  the VERIFIED contract        (verified_contract.py — two independent reads converge)
P1-B  gold-setup-backed producer   (evals/constraint_oracle/verified_producer.py — OFF-SERVING)
P1-C  bound_slots_digest           (a separable, load-bearing proof obligation)
```

P1-B verifies 7/13 real R2 problems with wrong=0 — but it is **gold-setup-backed**, so
it is structurally off-serving: the independent read is the INV-25 hand-authored gold
SETUP, which is not available at serving time. This brief scopes what a *serving-time*
VERIFIED would require — and why it cannot reuse P1-B. **No code here.**

> Companions: [[ask-serving-integration-scoping-2026-06-08]] (the ASK half of the same
> "where off-serving stops" line), [[VERIFIED-canonical-comparison-scoping-2026-06-06]]
> (the validate-first probe that already KILLED the naive fold-reader producer),
> [[stage2-epistemic-disclosure-bus-verified-v1-scoping-2026-06-08]] (Doc 1).

---

## 1. The seam (grounded) — and why it is still inert by design

`generate/derivation/verify.py::_canonically_verified(verified, problem_text, policy)`
is the ADR-0206 §5 VERIFIED gate — *the only thing that may license a math answer past
gold* (resolve a disagreement STRICT refuses). It **returns `None` today**, so the
widening is structurally inert: disagreement refuses regardless of `policy`, preserving
absolute `wrong == 0`. Its own docstring states the bright line this brief must honour:

> "A reliability *license* (statistical) must NEVER substitute here: math serving is
> absolute-wrong=0, not disclosed like the cognition path."

So VERIFIED serving = replacing that `return None` with a producer that returns a
derivation **only when it is canonically VERIFIED** (proven correct, not merely sound),
behind a kill switch, proven on a holdout. Everything below is the eligibility bar for
that producer.

---

## 2. The five things this decision must pin

```text
1. the gold-free independent-reader requirement   — the crux
2. verified_serving_enabled                        — the kill switch
3. holdout gates                                    — validate-first, no quiet widening
4. proof-producer eligibility                       — what may plug into _canonically_verified
5. the explicit ban on eval-gold-backed serving     — why P1-B cannot serve
```

---

## 3. The gold-free independent-reader requirement (the crux)

VERIFIED means **two independent reads that converge on one canonical structure**
(P1-A): a faithful solve of a *wrong read* is caught because the independent read
disagrees. P1-B's two reads are `read_constraint_problem` (the engine reader) vs the
**gold-authored setup**. At serving time there is no gold. So serving-time VERIFIED
needs a **second, gold-free reader** whose disagreement is the safety mechanism.

The hard constraints, from the killed-probe doc and CLAUDE.md:

- **Independence must be in the READING, not the solving.** Back-substitution catches
  solve-errors, never read-errors. Two solvers over one reading is *fake* independence.
  The second reader must parse the problem into the same `ConstraintProblem` structure
  by a **genuinely different route** (different lineage, asserted by the
  `SAME_READER_LINEAGE` firewall / INV-27 reader-disjointness), and converge on the
  same canonical signature.
- **No eval gold in the read** (§7). The second reader may not consult, hash, or be
  derived from any gold artifact — not the answer, not the setup. If it needs gold to
  read, it is P1-B, and P1-B does not serve.
- **Conservative refuse-on-doubt carries wrong=0.** The second reader, like the first,
  refuses when uncertain. VERIFIED fires only on *agreement of two confident,
  independent reads*; any refusal or disagreement → STRICT refuses (today's behaviour).

**Eligibility, stated as a gate:** a serving-time VERIFIED producer is eligible **only
if** it exhibits two reads with (a) distinct, firewall-asserted lineages, (b) neither
read derived from gold, (c) convergence on one canonical `ConstraintProblem` signature,
(d) back-substitution + boundary-clear + bound-slots (the P1-A/P1-C obligations), and
(e) refuse-preferring failure. Absent any one, it stays `None`.

Whether such a second R2 reader *exists yet* is the open empirical question — the killed
fold-reader probe is the cautionary precedent: complementary readers were ~98% wrong on
the refused set. **This brief does not assume one exists; it sets the bar a candidate
must clear, validate-first, before any wiring.**

---

## 4. `verified_serving_enabled` — the kill switch

Add `verified_serving_enabled: bool = False` to `core/config.py` (sibling of
`estimation_enabled`). Default **off**. When off, `_canonically_verified` returns `None`
unconditionally (today's inert state) regardless of any producer being present. The
switch is the single audited place that lights the seam, and it stays off until §5.

---

## 5. Holdout gates — validate-first, no quiet widening

VERIFIED may not widen live until proven on a **held-out** set it never trained or
tuned on (INV-25 discipline; the killed-probe doc's validate-first rule). The gate, in
order:

1. **Holdout probe (off-serving):** run the candidate producer over a held-out R2 set
   with gold answers withheld; require **wrong == 0** on everything it marks VERIFIED,
   and that everything it cannot independently verify it *refuses* (over-refusal is
   acceptable; one wrong is disqualifying).
2. **Seal byte-identity:** the GSM8K candidate-graph serving seal (pinned SHAs) stays
   byte-identical — VERIFIED widens a *different* surface (R2 constraint answers), it
   must not perturb the sealed lane.
3. **Disagreement-still-refuses:** a test proving that with the producer wired and the
   switch ON, a faithful solve of a deliberately wrong read still refuses (the P1-A
   poison test, now on the served path).
4. Only then does `verified_serving_enabled` go on, **one surface at a time** (R2
   first; R4 second), each with its own holdout pass.

---

## 6. The served surface — a distinct `[verified]` disclosure

When wired and enabled, a VERIFIED R2 answer is served under its **own** disclosure
claim/marker — the locked decision from Doc 1's review: *VERIFIED gets a distinct
served disclosure mode + `[verified]` prefix, NEVER reused from `[approximate]`*.
VERIFIED is a *license* claim (more licensed than gold-strict), not a *speculation*
claim. The route to it is the only sanctioned one: `disclosure_for_verification(result)`
→ `(EpistemicState.VERIFIED, DisclosureClaim.VERIFIED)` → `ServedDisposition.DISCLOSE`
under the P0-3 guard (which already degrades an unbacked VERIFIED claim to COMMIT).

---

## 7. The explicit ban on eval-gold-backed serving (the load-bearing non-claim)

**P1-B must never become a serving producer.** It is gold-setup-backed: its independent
read is the hand-authored gold SETUP. Wiring it into `_canonically_verified` would mean
the engine "verifies" by consulting the answer key's structure — circular, and a
wrong=0 fiction (it would serve VERIFIED on exactly the problems it was handed the setup
for). The ban, stated so a test can enforce it:

- `_canonically_verified` (and any serving producer behind it) may import **nothing**
  from `evals/` — no gold loader, no `gold_to_problem`, no `r2_gold`. An AST/import test
  asserts the serving path is gold-free, the mirror of the off-serving AST tests.
- P1-B stays in `evals/` precisely so this boundary is structural: `evals → core` is the
  allowed direction; `core/generate serving → evals` is forbidden.
- "Verified on a holdout" (§5) is **not** the same as "verified by gold at serving" —
  the holdout *measures* a gold-free producer; it never *feeds* gold into one.

This is the VERIFIED analogue of the GSM8K "candidate-graph owns the metric; no bridge
re-enables without sealed/independent wrong=0" discipline.

---

## 8. What this is NOT

- **Not** a claim that a serving-time VERIFIED producer exists — §3 sets the eligibility
  bar; whether an R2 second reader clears it is an open, validate-first question.
- **Not** a reliability/statistical license at the math seam — that path is the
  cognition `[approximate]` disclosure; math serving is absolute wrong=0 (§1 bright line).
- **Not** a GSM8K-seal move — VERIFIED widens R2 constraint answers, seal stays
  byte-identical (§5.2).
- **Not** P1-B promoted to serving — explicitly banned (§7); P1-B stays off-serving.

---

## 9. The questions for the ruling

1. **Eligibility bar:** adopt §3 (a)–(e) as the gate any serving VERIFIED producer must
   clear — gold-free second reader, independence-in-the-reading, refuse-preferring? (rec: yes)
2. **Gate:** add `verified_serving_enabled = False` (sibling of `estimation_enabled`),
   `_canonically_verified` stays `None` while off? (rec: yes)
3. **Holdout:** require the §5 validate-first sequence (wrong=0 on holdout + seal
   byte-identity + disagreement-still-refuses) before the switch, R2-first? (rec: yes)
4. **Gold ban:** enforce the §7 import ban (serving path imports nothing from `evals/`)
   with a test, keeping P1-B off-serving forever? (rec: yes)
5. **Surface:** serve VERIFIED under its distinct `[verified]` marker via
   `disclosure_for_verification` only? (rec: yes — the locked Doc 1 decision)

No served-surface code until this brief is reviewed. Pairs with
[[ask-serving-integration-scoping-2026-06-08]] — together they draw the full line where
off-serving stops.

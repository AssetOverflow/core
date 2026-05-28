# CORE Research Portfolio

This document is the public-facing portfolio entry point for funders, research collaborators, and hiring teams evaluating CORE as independent AI research.

CORE is not presented here as a finished general-purpose replacement for frontier systems. It is a reproducible research program around a deterministic cognitive architecture whose current value is strongest in bounded-domain reasoning, traceability, refusal-first behavior, audited learning paths, and mechanically checkable invariants.

## One-page research summary

**Project:** CORE — Continuous Orthogonal Resonance Engine

**Research thesis:** intelligence systems should be able to expose the path by which a claim was admitted, revised, refused, or rejected. CORE explores that thesis through a deterministic architecture with explicit epistemic state, audited mutation surfaces, and invariant-preserving runtime checks.

**Current proof corridor:** bounded-domain verified reasoning with deterministic replay, traced rejection, coherent refusal, and safety/identity boundaries that fail closed.

**Primary audiences:**

- AI alignment and safety funders evaluating non-sampling architectures, refusal discipline, and audited learning.
- Research labs or small teams seeking independent architecture work outside the transformer-default path.
- Open-source collaborators who want reproducible experiments rather than opaque model claims.
- Employers evaluating research taste, systems discipline, and scientific execution from public artifacts.

## What to inspect first

| Question | Artifact |
|---|---|
| What is the architecture? | [`README.md`](../README.md), [`docs/Whitepaper.md`](Whitepaper.md), [`docs/Yellowpaper.md`](Yellowpaper.md) |
| What claims are currently measured? | [`CLAIMS.md`](../CLAIMS.md) |
| What are the truth-seeking guarantees and gaps? | [`docs/truth_seeking_schema.md`](truth_seeking_schema.md) |
| What demos are reproducible? | `core demo flywheel`, `core demo phase6`, `core demo anti-regression`, `core demo learning-loop` |
| What is the decision history? | [`docs/decisions/`](decisions/) |
| How do I verify the invariant? | `pytest tests/test_versor_closure.py` and `core test --suite algebra` |

## Reproducibility commands

Run the smallest invariant lane first:

```bash
pip install -e ".[dev]"
pytest tests/test_versor_closure.py
```

Run the public proof corridor:

```bash
core demo flywheel
core demo phase6
core demo anti-regression
core eval gsm8k_math
```

Inspect generated and committed measurements:

```bash
core demo list-results
cat CLAIMS.md
```

## Evidence framing

Use precise language when discussing CORE publicly:

- Say **deterministic bounded-domain proof corridor**, not generic AGI.
- Say **zero confabulations in the cited eval/report only when backed by the current report**, not as a universal property.
- Say **refusal-first behavior under measured lanes**, not universal safety.
- Say **commercially licensable open research artifact**, not a finished product.
- Say **independent research portfolio**, not PhD-equivalent unless the audience uses that analogy first.

## Funding path

CORE is now public and dual-licensed, which supports two compatible funding channels:

1. **Open research support:** GitHub Sponsors, Open Collective, small OSS grants, alignment grants, and research fellowships.
2. **Commercial licensing:** private evaluation, applied pilots, and dual-license commercial use that does not require closing the open research record.

Suggested sponsor/funder positioning:

> CORE is an independent research program exploring deterministic, traceable AI reasoning with audited learning and refusal-first safety behavior. Funding supports reproducible benchmarks, public demos, documentation, and the next proof corridors for broader domains.

Suggested near-term grant proposal title:

> Deterministic Refusal-First Reasoning with Audited Learning and Reproducible Trace Evidence

Suggested grant abstract:

> CORE investigates an alternative cognitive architecture for AI systems whose reasoning paths are deterministic, inspectable, and governed by explicit epistemic state. The current public proof corridor demonstrates invariant preservation, replay determinism, traced rejection, coherent refusal, and review-gated learning in bounded domains. Grant support will extend evaluation breadth, improve reproducibility, publish public demos, and produce clear negative results where the architecture does not yet generalize.

## Hiring / collaborator framing

For research roles, lead with research output rather than conventional credentials:

> Independent AI researcher and systems architect building CORE, a deterministic cognitive architecture focused on traceable reasoning, refusal-first safety, audited learning, and reproducible evaluation. Public artifacts include architecture papers, ADRs, test suites, CLI demos, and measured claim reports.

Recommended resume bullets:

- Designed and implemented a deterministic cognitive runtime with explicit epistemic states, audited mutation paths, and invariant-preserving transitions.
- Built reproducible CLI demos and evaluation lanes for replay determinism, traced rejection, coherent refusal, anti-regression, and reviewed learning.
- Maintained a public research repository with architecture papers, decision records, test suites, measured claims, and dual-license commercialization path.
- Developed multi-language implementation surfaces across Python, Rust, and MLX-oriented acceleration paths.

## Outreach assets to add next

These are not required for correctness, but they make the repo easier to fund and evaluate:

- A five-minute demo video showing `core demo flywheel` and `core demo phase6` from clone to output.
- A short `docs/demo_script.md` for recording the demo reproducibly.
- GitHub Sponsors metadata via `.github/FUNDING.yml` after Sponsors is enabled for the account.
- A public-safe preprint derived from the whitepaper/yellowpaper with measured claims limited to `CLAIMS.md`.
- A one-page PDF summary generated from this file for grant applications and recruiter packets.

## Non-goals and honesty boundaries

CORE should not be marketed as fully general, production-safe, medically safe, legally safe, or frontier-model equivalent. The strongest public posture is stricter and more credible: a novel, independently built research system with reproducible evidence in narrow corridors, a disciplined roadmap, and clear gaps documented before they are solved.

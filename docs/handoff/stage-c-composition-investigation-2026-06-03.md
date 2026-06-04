<!-- handoff | stage-c-composition-investigation | 2026-06-03 | execution-lane dispatch task | read-only investigation, no code | input: composition-wall-execution-plan-2026-06-03.md -->

# Stage-C Composition Investigation — dispatch task (execution lane)

**Type:** Read-only, in-tree investigation. **No code changes.** Output is a per-case fix-spec.
**Dispatch:** execution lane (this is the fine-grained runtime tracing the spec-and-review lane
deliberately does *not* do from a sandbox — it must run the real code paths in-tree).
**Input:** [composition-wall-execution-plan-2026-06-03.md](../analysis/composition-wall-execution-plan-2026-06-03.md).
**Base:** current `origin/main` (`git fetch && git reset --hard origin/main` first — the tree
moves constantly; verify the SHA you run against and record it).

## Why this is an execution-lane task, not a sandbox one

The execution plan's stage taxonomy is a verified **symptom-map** (what's blocked, by candidate
count). It is **not** a fix-spec. Pinning *why* a Stage-C production builds the wrong chain needs
instrumenting the real production internals — the kind of fine-grained trace that has been
unreliable from the spec lane's sandbox. Run the actual functions, in-tree, faithfully.

## The targets (Stage C — production-wrong)

The composer builds chains but only **wrong** ones (none equals gold); the disagreement rule then
correctly refuses. Five cases, from the plan's §2 table:

| case | comp | gold | acc/mul/chn | what it builds instead (plan) |
|---|---|---|---|---|
| cv-0002 | R1 | 400 | 0/0/4 | wrong chains only |
| cv-0004 | R1 | 3840 | 0/1/4 | wrong chains only |
| cv-0006 | R5 | 14 | 3/0/4 | wrong (e.g. accumulation + chain rivals) |
| cv-0022 | R5 | 38 | 0/1/4 | (plan: builds 80/160/18/36, none = 38) |
| cv-0018 | compare_mult | 28 | 0/0/2 | wrong chains only |

## What to produce, per case

For each of the five, using the **serving-faithful inputs** (`extract_target` gets the *question
clause*; the composers get the *full problem* — the §9 methodology fix):

1. **Enumerate every candidate** each composer builds (`accumulation_candidates`,
   `multiplicative_candidates`, `candidate_chains`): the exact step list (op, operand, unit) and
   answer of each, not just the count.
2. **Locate the gold chain.** Is the correct grouping/op-order *expressible* by the current
   composer primitives at all? If a sequence of existing ops yields gold, the gap is **search/
   ranking** (the production can build it but doesn't, or builds it and a wrong rival outvotes it).
   If no sequence of existing ops yields gold, the gap is a **missing primitive/production**.
3. **Pin the divergence.** Where does the built (wrong) chain diverge from the gold reading — wrong
   clause segmentation, wrong referent binding, wrong op for a relational cue, wrong grouping order?
   Name the exact function and the exact decision (cite `file:line`).
4. **Minimal production fix.** State the smallest change that would make the gold chain *buildable
   and uniquely certifiable*, and the **co-designed structural gate** that admits it without
   admitting the wrong rivals (per plan §5 — `extract_target` + `target_units`, never disagreement
   alone).

## Hard constraints (non-negotiable — from ADR-0207 §6 / plan §6)

- **Read-only.** No edits to `generate/` in this task. The output is a spec; building is a later,
  separately-gated task.
- **`wrong=0` is the governor.** Any proposed fix must be argued to preserve: train_sample
  `wrong=0` (6/44/0+), the no-reference `<N> times` refusal, and the 0016 firewall (a lone wrong
  chain with no rival must still refuse — the gate, not disagreement, is the defense).
- **Sealed set is the real bar.** Note explicitly that building gold on a corpus case proves
  nothing about transfer; the fix-spec must say what would be measured on the sealed 1,319.
- **Serving-faithful reproduction.** `extract_target(question_clause)`; composers get full text.
  Record the `origin/main` SHA you ran against.

## Output

A markdown report, one section per case, with the four items above, ending in a ranked list:
which Stage-C case has the **smallest buildable gap** (search/ranking) vs which needs a **new
primitive** — so the build lane starts with the cheapest real lift. This report becomes the
fix-spec; it does not authorize a build.

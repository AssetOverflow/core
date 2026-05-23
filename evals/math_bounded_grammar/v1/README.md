# Bounded-Grammar Word Problems Benchmark (v1)

This evaluation lane (ADR-0131.3 Benchmark 3) measures the CORE engine's deterministic end-to-end correctness on word problems that fall strictly within a closed, bounded grammar specification.

## Scope & Philosophy

Rather than paraphrase-chasing a benchmark designed to reward natural language flexibility (like GSM8K), this benchmark focuses on CORE's structural strengths: **infallible correctness and deterministic verification within a strict, reviewable grammar contract.**

The grammar's boundedness is the contract. Problems within scope must solve perfectly, and problems out of scope must refuse cleanly. The correctness of the engine within this boundary is the primary claim, while grammar coverage remains an honest, separately measurable capability.

---

## Dataset Categorization

The dataset (`cases.jsonl`) contains 50 hand-curated word problems, split across three expected outcome classes:

1. **`solved_correct`** (35 cases): Grammar-conformant problems with a single correct numeric answer. These span all 8 valid operation kinds in the math expert domain:
   - `add`
   - `subtract`
   - `transfer`
   - `multiply`
   - `divide`
   - `apply_rate`
   - `compare_additive`
   - `compare_multiplicative`

2. **`solved_wrong`** (5 cases): Grammar-conformant problems whose expected answer is **deliberately wrong**. These exercise the verifier's ability to catch solver errors, confirming that the `wrong == 0` gate is load-bearing.

3. **`refused`** (10 cases): Out-of-grammar problems that must refuse cleanly. Categories of refusal:
   - Paraphrase outside the templates (e.g. unknown verbs).
   - Unit not present in `en_units_v1` and not in the allowed generic count nouns set.
   - Ambiguous or undefined entity references.
   - Operations that would violate basic arithmetic rules (e.g. division by zero).

---

## Shape Categories

Every problem carries a `shape_category` tag belonging to the following closed set:
- `canonical_has_buys`
- `there_are_count`
- `substance_qualifier`
- `compare_additive`
- `compare_multiplicative`
- `transfer`
- `multiply`
- `divide`
- `apply_rate`
- `refused_paraphrase`
- `refused_unit`
- `refused_ambiguous`
- `refused_multistep`

---

## Grammar Specification

The detailed templates and mapping to `MathProblemGraph` are specified in:
- [grammar.md](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/implement-bounded-grammar-problems/evals/math_bounded_grammar/v1/grammar.md)

---

## Exit Criteria

To pass this lane, the execution of the runner must satisfy:
1. `wrong == 0` across all three classes (no unexpected correct, wrong, or refused classifications).
2. `correct_rate >= 0.95` (at least 95% of cases match their expected outcome).
3. The generated `report.json` must be deterministic and byte-equal across consecutive runs.

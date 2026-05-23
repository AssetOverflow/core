# GSM8K Math Evaluation Lane Contract

## What it measures

This lane measures the mathematical reasoning capability of the CORE cognitive engine over grade-school word problems, specifically evaluating the integration of:
1. Natural language problem parsing (`generate/math_parser.py` -> `MathProblemGraph`).
2. Graph-based deterministic solution generation (`generate/math_solver.py` -> `SolutionTrace`).
3. Solution trace verification (`generate/math_verifier.py`).

## Why it matters

Mathematical reasoning requires chaining logical and state-mutating operations deterministically. This lane enforces that the cognitive engine can parse, represent, solve, and verify arithmetic problems without relying on stochastic generation or approximation.

By using an original, curated set of 200 problems matching our own vocabulary and grammar, we can safely benchmark development without contaminating the sealed GSM8K holdout test set.

## Splits and ID Schema

- **Dev Set**: 50 cases (`gma-001` ... `gma-050`)
- **Public Set**: 150 cases (`gma-101` ... `gma-250`)
- **Holdout Set**: Sealed, loaded dynamically in future phases.

## Metrics

The lane runner enforces three gate checks per case:
- **`M1. Parse Correctness`**: `parse_problem(problem_text)` yields a graph whose canonical bytes are identical to the ground-truth graph.
- **`M2. Solve Correctness`**: `solve(graph)` yields a trace with `answer_value` and `answer_unit` exactly matching the expected answer and unit.
- **`M3. Verification Correctness`**: The trace successfully replays via the verifier to reproduce the answer value and unit.

## Pass Thresholds

- **Total Success Rate**: 100% of authored dev and public cases (200/200) must satisfy M1, M2, and M3.
- **Replay Determinism**: 100% trace determinism.

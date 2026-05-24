# Branch Reconciliation Warning

This branch was created from `a53ce93` and is currently behind `main` by a large number of commits.

## Current risk

The initial `TargetBinding` substrate commit modified `generate/math_problem_graph.py` by replacing a large portion of the file instead of applying a minimal surgical patch. That is risky because `main` has advanced materially since the branch point.

Do not merge this branch as-is without reconciliation.

## Safe path forward

1. Rebase or recreate the branch from current `main`.
2. Cherry-pick only the docs corridor files first.
3. Re-apply the G.5 code changes surgically:
   - add `TargetBinding` dataclass;
   - add optional `target_binding` field to `MathProblemGraph`;
   - preserve all current `main` comments, type shapes, and helper functions;
   - add `_target_binding_from_dict` without touching existing operand reconstruction logic.
4. Then wire `generate/math_target_binding.py` into `math_candidate_graph.py` with a minimal import and a single call in `_build_graph`.
5. Run at minimum:

```bash
uv run python -m pytest tests/test_adr_0131_G4_multi_clause.py tests/test_adr_0131_G_gsm8k_coverage_probe.py -q
uv run python -m pytest tests -q
```

## Intended graph integration patch

The desired future patch to `math_candidate_graph.py` is conceptually:

```python
from generate.math_target_binding import target_binding_from_question

...
branch_entities = tuple(entities)
target_binding = target_binding_from_question(
    question_choice,
    branch_entities=branch_entities,
)
return MathProblemGraph(
    entities=branch_entities,
    initial_state=tuple(initials_list),
    operations=tuple(operations_list),
    unknown=question_choice.unknown,
    target_binding=target_binding,
)
```

This must remain read-only metadata until a dedicated solver/verifier phase consumes it.

## Merge policy

- Docs corridor is safe to keep.
- `generate/math_target_binding.py` is safe if imports resolve against current `main`.
- `generate/math_problem_graph.py` must be reconciled before merge.
- Do not add solver semantics on this stale branch.

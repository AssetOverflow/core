# ScalarEquivalence Facade PR-1 Handoff (2026-06-18)

This handoff is the execution brief for the first runtime slice after the Kernel Knowledge Layer PR-0 (#828).

It is intentionally narrow: implement a `ScalarEquivalence` facade over the existing ADR-0128 `en_numerics_v1` pack. Do not change serving behavior in this PR.

## Current anchor

- PR #827 is merged.
- PR #828 is merged.
- Current expected `train_sample`: `30 correct / 20 refused / 0 wrong`.
- Current observed `holdout_dev`: `5 correct / 495 refused / 0 wrong`.

## Existing repo foothold

The implementation should reuse existing pack machinery rather than create a duplicate scalar pack.

`language_packs/numerics_loader.py` already exposes:

- `lookup_cardinal(token)`
- `lookup_ordinal(token)`
- `lookup_fraction(token)`
- `lookup_quantifier(token)`
- `lookup_multiplier(token)`
- `lookup_comparison_anchor(token)`
- `lookup_comparison_anchors(token)`
- `match_number_format(token)`
- `parse_compound_cardinal(text)`

Important existing behavior:

- `lookup_fraction()` supports article-bound forms such as `a half` and `a quarter`.
- `lookup_fraction()` supports compound forms such as `two-thirds`, `three quarters`, and `one half` through `_parse_compound_fraction()`.
- `match_number_format()` supports ratified exact-format parsing for decimals, slash fractions, mixed numbers, percentages, signed integers, and thousands-separated integers.
- The existing ADR-0128 numeric-format tests deliberately refuse ambiguous/malformed formats such as spaced slash fractions (`1 / 2`) and percent forms without the exact ratified shape.

The facade should respect those invariants unless a later ADR explicitly extends ADR-0128.

## Mission

Create:

```text
language_packs/scalar_equivalence.py
```

The facade should expose source-grounded scalar candidates with canonical rational values and ambiguity hazards.

It must not solve problems, bind bases, choose operations, or admit serving answers.

## Required public type

```python
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

@dataclass(frozen=True)
class ScalarLexeme:
    canonical: Fraction
    source_surface: str
    source_span: tuple[int, int]
    surface_kind: Literal[
        "digit_fraction",
        "decimal",
        "percent",
        "word_fraction",
        "unicode_fraction",
    ]
    provenance: Literal["problem_text"]
    hazards: tuple[str, ...]
```

## Required public API

```python
def extract_scalar_lexemes(text: str) -> tuple[ScalarLexeme, ...]: ...

def canonicalize_scalar_surface(surface: str) -> Fraction | None: ...

def hazards_for_scalar_surface(
    surface: str,
    *,
    context: str | None = None,
) -> tuple[str, ...]: ...
```

Optional helpers are allowed only if they remain facade-local and are directly tested.

## Hard non-goals

Do not touch:

- `generate/math_candidate_graph.py`
- any `generate/derivation/*` organ
- `evals/gsm8k_math/**/report.json`
- sealed artifacts
- train or holdout data
- scoring logic

Do not implement:

- a new duplicate scalar data pack
- a broad parser
- a generic fraction solver
- serving integration
- case-id logic
- hardcoded benchmark answers
- direct final-answer extraction

## Canonical values for v1

At minimum:

- `1/2`
- `1/3`
- `2/3`
- `1/4`
- `3/4`
- `1/10`
- `1/100`

Represent canonical values as `fractions.Fraction`, not float.

## Required surface families

### Word fractions

Examples:

- `half`
- `one half`
- `one-half`
- `third`
- `one third`
- `two thirds`
- `quarter`
- `one quarter`
- `three quarters`

Use `lookup_fraction()` where possible.

### Digit fractions

Examples:

- `1/2`
- `3/4`

Use `match_number_format()` where possible.

Do not silently broaden ADR-0128. If `1 / 2` is unsupported by `match_number_format()`, either leave it unsupported in PR-1 or document why a later ADR should extend the numerics pack.

### Decimals

Examples:

- `0.5`
- `0.25`
- `0.75`

Use `match_number_format()` where possible.

Do not silently add `.5` if ADR-0128 currently refuses it. If `.5` is desired, document it as a future numerics-pack extension unless the PR intentionally includes a reviewed ADR-0128 extension.

### Percentages

Examples:

- `50%`
- `25%`
- `75%`
- `100%`

Use `match_number_format()` where possible.

For phrase forms such as `50 percent`, implement conservatively and test exact span/provenance. Do not let `50 percentage points` become an unhazarded scalar-of-base.

### Unicode fractions

Examples:

- `½`
- `⅓`
- `⅔`
- `¼`
- `¾`

Use `lookup_fraction()` where possible.

## Hazard policy

The facade may emit scalar candidates with hazards, but it must not emit ambiguous surfaces as silently safe.

Required hazard labels:

- `unbound_base_quantity`
- `half_duration`
- `quarter_coin`
- `quarter_calendar_period`
- `quarter_school_term`
- `third_ordinal`
- `ordinal_context`
- `currency_context`
- `temporal_context`
- `percent_change_vs_percent_of`
- `multiple_scalar_ambiguity`

Examples:

- `half` by itself should carry `unbound_base_quantity` unless a caller-supplied context explicitly narrows it.
- `half an hour` should carry `temporal_context` and `half_duration`, or the facade may refuse to emit it as a usable scalar candidate.
- `third place` should carry `ordinal_context` and `third_ordinal`, or be refused as scalar.
- `quarter dollar` should carry `currency_context` and `quarter_coin`, or be refused as scalar.
- `50 percentage points` should carry `percent_change_vs_percent_of`, or be refused as scalar-of-base.

A downstream derivation organ or future `ProblemFrame` must still license the base quantity, actor, object, unit, relation, and question target.

## Provenance policy

Every emitted `ScalarLexeme` must have:

- exact `source_surface`
- exact `source_span`
- `provenance == "problem_text"`
- no derived or synthesized values

A scalar value produced by arithmetic is not a `ScalarLexeme` and must not be represented as problem-text provenance.

## Determinism requirements

- Extraction order must be deterministic by source span.
- Duplicate/overlapping scalar candidates must be handled deterministically.
- If two candidates occupy the same span, prefer the more specific surface family only if the rule is explicitly tested.
- If ambiguous, refuse or emit hazards; do not guess.

## Tests

Create:

```text
tests/test_language_packs_scalar_equivalence.py
```

Required tests:

1. `half` maps to `Fraction(1, 2)` with `problem_text` provenance.
2. `one half` maps to `Fraction(1, 2)` with exact span.
3. `one-half` maps to `Fraction(1, 2)` with exact span if supported by `lookup_fraction()`; otherwise document unsupported.
4. `1/2` maps to `Fraction(1, 2)`.
5. `3/4` maps to `Fraction(3, 4)`.
6. `0.5` maps to `Fraction(1, 2)`.
7. `0.25` maps to `Fraction(1, 4)`.
8. `50%` maps to `Fraction(1, 2)`.
9. `50 percent` maps to `Fraction(1, 2)` if phrase support is implemented.
10. `three quarters` maps to `Fraction(3, 4)`.
11. Unicode `½` maps to `Fraction(1, 2)` if supported.
12. `source_surface` preserves exact text.
13. `source_span` slices the original text to exactly `source_surface`.
14. extraction order is by source span.
15. multiple scalar surfaces emit multiple deterministic lexemes.
16. `third place` is hazardous or refused; it must not be silently safe.
17. `quarter dollar` is hazardous or refused; it must not be silently safe.
18. `half an hour` is hazardous or refused; it must not be silently safe.
19. `50 percentage points` is hazardous or refused; it must not be silently safe.
20. unsupported forms from ADR-0128 remain unsupported unless explicitly extended.

Do not weaken existing ADR-0128 tests.

## Documentation

Create:

```text
docs/analysis/scalar-equivalence-facade-pr1-2026-06-18.md
```

Required sections:

1. Purpose
2. Relationship to #828
3. Relationship to ADR-0128/en_numerics_v1
4. Why this is a facade, not a new pack
5. Supported canonical scalars
6. Supported surfaces
7. Explicit unsupported surfaces
8. Hazard policy
9. Provenance policy
10. Determinism policy
11. Non-goals
12. Tests
13. Next PR recommendation

## Validation

Run:

```bash
git diff --check origin/main...HEAD
pytest tests/test_language_packs_scalar_equivalence.py -q
pytest tests/test_adr_0128_numeric_formats.py -q
pytest tests/test_math_candidate_graph_xhigh_sprint13_lift.py -q
pytest tests/test_math_candidate_graph_sprint12_singleton_contract_lift.py -q
pytest tests/test_math_candidate_graph_sprint11_cluster_contract_lift.py -q
```

Confirm no score change:

```bash
uv run python - <<'PY'
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases, build_report

r = build_report(_load_cases(_CASES_PATH))
c = r["counts"]
print("train_sample:", c["correct"], c["refused"], c["wrong"])
print("wrong_ids:", sorted(x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"))
PY
```

Expected:

```text
train_sample: 30 20 0
wrong_ids: []
```

Holdout safety:

```bash
uv run python - <<'PY'
from evals.gsm8k_math.holdout_dev.v1.runner import build_report

r = build_report()
c = r["counts"]
print("holdout_dev:", c, "n=", r["n"])
print("wrong_ids:", [x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"])
PY
```

Expected:

```text
wrong_ids: []
```

If practical:

```bash
uv run python -m core.cli test --suite smoke -q
```

## Commit / PR

Suggested commit:

```text
feat(language-packs): add scalar equivalence facade
```

Suggested PR title:

```text
feat(language-packs): add scalar equivalence facade
```

PR body must include:

- Implements `ScalarEquivalence` facade over ADR-0128/en_numerics_v1.
- No serving integration.
- No `generate/math_candidate_graph.py` change.
- No A2 organ changes.
- No report.json change.
- No sealed artifact change.
- Preserves `train_sample` 30/20/0.
- Preserves `holdout_dev` wrong=0.
- Includes provenance and ambiguity hazards.
- Validation outputs.

Do not merge without review.

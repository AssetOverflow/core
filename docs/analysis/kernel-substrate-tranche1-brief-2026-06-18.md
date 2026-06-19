# Kernel Substrate Tranche 1 — Broad Implementation Brief (2026-06-18)

This brief supersedes any interpretation that the next Kernel Knowledge implementation should be a narrow `half`/fraction-only patch.

The scalar equivalence examples are the first concrete foothold, not the final design. Tranche 1 must implement a broad base-level substrate slice that establishes the reusable knowledge organs CORE needs before solving should scale.

## Why this exists

CORE should not keep adding isolated A2 organs that each rediscover the same base facts. The recent GSM8K sprints improved the benchmark but exposed the architectural gap: fundamental knowledge is still too often local to specific derivations.

Tranche 1 shifts from local patching to seeded substrate construction.

The objective is to create a reusable, deterministic base layer for:

- scalar equivalence
- unit/dimension knowledge
- provenance and source grounding
- ambiguity hazards
- process frame schemas
- part/whole and container relation schemas
- a minimal ProblemFrame-compatible fact model
- morphology atlas labels that identify missing substrate rather than only missed cases

This is not a request for a broad solver. It is a request for a broad substrate.

## Current anchor

- PR #827 established the current GSM8K capability baseline.
- PR #828 merged Kernel Knowledge Layer doctrine and inventory.
- Expected `train_sample`: `30 correct / 20 refused / 0 wrong`.
- Observed `holdout_dev`: `5 correct / 495 refused / 0 wrong`.

Tranche 1 should preserve `wrong == 0` and should not alter serving unless explicitly called out as a final, separately gated step.

## Design correction

Do not interpret `half / 1/2 / 0.5 / 50%` as the whole project.

Those examples are symptoms of the broader problem:

```text
raw surface variants
→ canonical substrate facts
→ provenance + hazards
→ typed ProblemFrame-ready facts
→ derivation organs consume facts instead of scraping prose
```

The Tranche 1 branch should build multiple base substrate surfaces together, while still separating runtime serving from substrate construction.

## Implementation target

Create a single implementation branch for a coherent Tranche 1 substrate:

```text
feat/kernel-substrate-tranche1
```

The branch may produce multiple commits, but it should aim for one reviewable PR with clear internal sections instead of several tiny PRs that each wait on full CI.

If the branch becomes too large to review, split only at natural substrate boundaries, not at individual examples.

## Required modules

### 1. Scalar equivalence facade

Create:

```text
language_packs/scalar_equivalence.py
```

Purpose:

- expose canonical rational scalar facts from ADR-0128/en_numerics_v1
- preserve source spans
- attach ambiguity hazards
- distinguish problem-text facts from derived values

Required examples include but are not limited to:

- `half`, `one half`, `one-half`
- `1/2`, `3/4`
- `0.5`, `0.25`, `0.75`
- `50%`, `25%`, `75%`, `100%`
- `third`, `two thirds`, `quarter`, `three quarters`
- unicode fractions supported by the existing pack

Respect ADR-0128. If ADR-0128 refuses a surface such as `.5` or `1 / 2`, do not silently broaden it. Either leave it unsupported or add an explicit reviewed numerics-pack extension with tests.

### 2. Unit and dimension facade

Create or extend a facade around ADR-0127/en_units_v1:

```text
language_packs/unit_dimensions.py
```

Purpose:

- expose exact unit and dimension facts
- classify compatible/incompatible dimensions
- provide exact conversions only where ratified
- preserve whether a value came from problem text, unit pack, calendar pack, or derivation

Required families:

- count/items
- money: dollars/cents if ratified
- time: seconds/minutes/hours/days/weeks if ratified
- length: inches/feet/yards/miles if ratified
- rate dimensions: `distance/time`, `money/time`, `items/container`, `items/time`

Non-goals:

- fuzzy months/years
- unsupported real-world conversions
- unit guessing
- using unit conversion to solve a problem by itself

### 3. Kernel fact / provenance primitives

Create:

```text
generate/kernel_facts.py
```

or an equivalent low-level module if existing structure suggests a better path.

Purpose:

Define reusable, immutable dataclasses for substrate facts. These should be lightweight and not tied to GSM8K.

Required concepts:

- `SourceSpan`
- `KernelProvenance`
- `KernelHazard`
- `GroundedScalar`
- `GroundedUnit`
- `CandidateRelation`
- `RelationRole`
- `SubstrateFact`

Provenance classes should include:

- `problem_text`
- `derived`
- `kernel_unit`
- `kernel_calendar`
- `kernel_math`
- `kernel_world_fact`
- `reviewed_pack`
- `speculative`

Rules:

- problem-text facts require exact source spans
- pack/world facts must not masquerade as problem text
- derived facts must name their derivation inputs
- speculative facts cannot be consumed by serving

### 4. Ambiguity hazard registry

Create:

```text
language_packs/ambiguity_hazards.py
```

Purpose:

Centralize known ambiguous base-level surfaces and their safe/refusal contexts.

Required surfaces:

- `half`
- `quarter`
- `third`
- `percent`
- `percentage points`
- `times`
- `more than`
- `less than`
- `of`
- `per`
- `each`
- `some`
- `remaining`
- `left`
- `total`
- `altogether`

The registry should not solve; it should annotate hazards and context requirements.

### 5. Process frame schema layer

Create:

```text
generate/process_frames.py
```

or a similarly named substrate module.

Purpose:

Expose candidate process schemas without executing arithmetic.

Required frames:

- transfer/give/receive
- gain/loss/use/spend/eat
- buy/sell/cost
- earn/work/rate
- travel/route/segment/round-trip
- container/full-box/loose-items
- partition/part/whole/remainder
- comparison/more-than/less-than/times-as-many

Each frame must declare:

- trigger surfaces
- required roles
- optional roles
- candidate relation emitted
- hazards
- what is not licensed

A process frame may say “this looks like a transfer candidate.”
It may not calculate the final answer.

### 6. ProblemFrame skeleton

Create:

```text
generate/problem_frame.py
```

Purpose:

Define the target IR shape that future organs will consume.

This PR does not need to fully wire all parsers into ProblemFrame, but it must define enough structure that the substrate modules are not floating utilities.

Required fields:

- quantities
- scalars
- units
- actors
- objects
- candidate relations
- process frames
- question target, if identified
- hazards
- provenance

This can be a construction target for later PRs. It should not replace the current candidate graph in Tranche 1 unless the implementation proves it safely.

### 7. Morphology atlas missing-substrate labels

Extend the morphology/flywheel/atlas code if present:

```text
scripts/gsm8k_experience_flywheel.py
```

or the current morphology atlas script if it exists.

Purpose:

Failures should be categorized by missing substrate, not only by missed benchmark case.

Required labels:

- `missing_scalar_equivalence`
- `missing_unit_dimension`
- `missing_process_frame`
- `missing_part_whole_frame`
- `missing_container_frame`
- `missing_temporal_frame`
- `missing_route_frame`
- `missing_question_target`
- `blocked_ambiguity_hazard`
- `blocked_provenance_gap`

Non-goal:

- no automatic pack mutation
- no sealed artifact analysis
- no benchmark answer mining

## Serving integration policy

Default: no serving integration in Tranche 1.

Allowed integration, only if kept separately gated:

- add read-only construction of substrate facts for debug/inspection
- no answer admission based only on new substrate facts
- no new `correct` expected unless a separate organ refactor is explicitly included

If a serving lift is attempted in the same branch, it must be isolated behind a separate test section and must preserve:

- train wrong ids empty
- holdout_dev wrong ids empty
- no `report.json` rebaseline
- no sealed artifact mutation

## Tests required

This tranche should test breadth, not a single example.

Required test files may include:

```text
tests/test_language_packs_scalar_equivalence.py
tests/test_language_packs_unit_dimensions.py
tests/test_kernel_facts.py
tests/test_ambiguity_hazards.py
tests/test_process_frames.py
tests/test_problem_frame_skeleton.py
tests/test_gsm8k_morphology_missing_kernel_labels.py
```

At minimum, tests must prove:

- scalar surfaces canonicalize to exact `Fraction` where supported
- unit compatibility rejects mismatches
- exact source spans are preserved
- pack/world facts do not claim `problem_text` provenance
- ambiguous surfaces are hazardous or refused, not silently safe
- process frames emit schemas/roles, not answers
- ProblemFrame can hold substrate facts without executing solving
- morphology labels identify missing substrate categories deterministically

## Validation

Use grouped validation rather than running full expensive suites after every tiny edit.

Recommended local sequence:

```bash
git diff --check origin/main...HEAD
pytest tests/test_language_packs_scalar_equivalence.py -q
pytest tests/test_language_packs_unit_dimensions.py -q
pytest tests/test_kernel_facts.py -q
pytest tests/test_ambiguity_hazards.py -q
pytest tests/test_process_frames.py -q
pytest tests/test_problem_frame_skeleton.py -q
pytest tests/test_gsm8k_morphology_missing_kernel_labels.py -q
```

Then run current capability safety checks once before PR:

```bash
pytest tests/test_adr_0128_numeric_formats.py -q
pytest tests/test_math_candidate_graph_xhigh_sprint13_lift.py -q
pytest tests/test_math_candidate_graph_sprint12_singleton_contract_lift.py -q
pytest tests/test_math_candidate_graph_sprint11_cluster_contract_lift.py -q
```

Confirm no score regression:

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

Confirm holdout safety:

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

If practical, run smoke once near the end:

```bash
uv run python -m core.cli test --suite smoke -q
```

## PR expectations

Suggested branch:

```text
feat/kernel-substrate-tranche1
```

Suggested PR title:

```text
feat(kernel): add substrate tranche 1 foundations
```

PR body must include:

- broad substrate scope, not scalar-only
- modules added
- serving integration status
- explicit no report/sealed changes
- expected baseline before/after
- train wrong ids
- holdout wrong ids
- validation output
- known unsupported surfaces
- follow-up path to first ProblemFrame-consuming organ

## Review stance

Do not let review collapse this back into a tiny `half` implementation.

A successful Tranche 1 PR is not measured by immediate GSM8K score gain. It is measured by whether CORE now has reusable substrate facts that future organs can consume without repeatedly hand-parsing fundamentals.

The system must stop paying the same implementation tax case-by-case.

# GSM8K Sealed Attempt Scout S1 — Lookback (2026-06-17)

## Purpose

First practical bridge from ADR-0175 practice/contemplation design into the
Capability Strike lift workflow. Dual-scores **train_sample** cases with:

1. **Serving** — conservative `_score_one_candidate_graph` (wrong=0 path)
2. **Sealed** — aggressive `resolve_pooled_scorer` (may be wrong; practice-only)

## Boundaries (enforced)

- **No serving mutation** — scout imports scorers read-only; no runtime edits.
- **No `report.json` rebaseline** — default CLI prints to stdout only.
- **No sealed-lane movement** — does not call `regenerate_practice_artifacts()`.
- **No autonomous promotion** — recommendations are diagnostic/SPECULATIVE only.

## Runner

```bash
uv run python scripts/gsm8k_sealed_attempt_scout.py
uv run python scripts/gsm8k_sealed_attempt_scout.py --out /tmp/scout.jsonl
```

Core logic: `evals/gsm8k_math/train_sample/v1/scout.py`

## Schema (`SealedAttemptScoutRow`)

| Field | Description |
|-------|-------------|
| `case_id` | Train-sample case id |
| `served_status` | correct / wrong / refused |
| `aggressive_status` | correct / wrong / refused |
| `aggressive_answer` | Sealed numeric answer if any |
| `gold_answer` | Dataset gold |
| `refusal_reason` | Serving refusal when refused |
| `failure_family` | Conservative taxonomy |
| `candidate_lift_family` | Primitive hint when lift candidate |
| `first_failed_step` | question_parse / injection / completeness / … |
| `trace_key` | Deterministic SHA-256 prefix |

## Baseline observed (full train_sample, #811 main)

Ephemeral serving (live code): **8 correct / 42 refused / 0 wrong**.

Scout full pass (serving arm matches live): `serving_counts.wrong == 0`.

Typical cross-regime pattern on refused cases:

- `lift_refused_to_correct` — sealed commits, serving refuses (primary lift map)
- `joint_refusal` — both arms refuse (substrate gap)
- `elimination_refused_to_wrong` — sealed wrong (not a lift target)

## Top recommended lift families (scout ranking)

On full 50-case pass, top groups cluster on:

1. `recognized_no_injection` + `discrete_count_statement` → `relation_hypothesis`
2. `recognized_no_injection` + `multiplicative_aggregation` → `multiplicative_aggregate`
3. `no_admissible_question` → `question_binding` families (peer/conditional/yield)

**Note:** Track A Batch 3 landed `peer_partition_question` independently; scout
would have surfaced 0025-style `no_admissible_question` refusals on the #811
baseline.

## Usage alongside Capability Strike

1. Run scout after a merge to rank refused cases where sealed already commits.
2. Pick the highest-count **family** with confuser review (not case-id chasing).
3. Implement narrow injector lift; re-run ephemeral `build_report()` for proof.
4. Never wire `resolve_pooled` wholesale to serving.

## Limitations (S1)

- Failure taxonomy is conservative; unknown → `unclassified`.
- No per-step operation-chain extraction beyond `first_failed_step` heuristic.
- Train_sample only (50 cases); practice lane (150) is a future `--cases` extension.
- No timestamps in golden outputs; order fixed by `case_id`.

## Non-goals

- No serving guesses.
- No pack/policy/identity mutation.
- No accepted runtime proposal emission.
- No `determine()` / `FrameVerdict` / `CLOSE`.
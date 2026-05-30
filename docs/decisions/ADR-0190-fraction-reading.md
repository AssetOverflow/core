# ADR-0190 — Fraction reading via a `partition` operation (the first fraction flip)

**Status:** Accepted (implemented). Serving-path capability; landed because
**wrong=0 is proven across every lane**. Builds on the ADR-0123 candidate-graph
solver and the #488 (ADR-0189) "land in serving when wrong=0 proven" method.

> **One line.** The official GSM8K `train_sample` metric moves a second time:
> **4/46/0 → 5/45/0** (case 0046, answer 15). Fraction problems need a new core
> **`partition`** operation — a unit-*changing* scaled subset (`base[unit A, V] →
> subset[unit B] = factor·V`) — because `compare_multiplicative` is unit-*preserving*
> by construction and cannot model "half of the **students** are **girls**."

---

## 1. The build-discovered finding (why not `compare_multiplicative`)

The scoping spec assumed fraction-of would reuse `compare_multiplicative`.
Building it refuted that empirically:

- `compare_multiplicative` **does** handle fractional factors
  (`"3/4 times as many as Bob"`, Bob=80 → 60 ✓) — but only for the
  **distinct-actor, same-unit, no-overwrite, entity-reference** shape.
- **No** train_sample fraction case fits it: 0046/0004/0041 are **partitions**
  (unit changes `students→girls`); 0005 is a **temporal self-overwrite**
  (`temp → ¾·temp`, refused by the overwrite guard); 0010 is multi-step.

So fraction reading needs a genuinely new operation, not a surface alias.

## 2. The `partition` operation

`generate/math_problem_graph.py` — `Partition(base_unit, subset_unit, factor)`,
a new isolated `Operation.kind="partition"` (existing kinds untouched).

`generate/math_solver.py::_apply_partition` — the base is bound **by unit**
(distinct from `compare_multiplicative`, which binds its reference by entity);
`state[(actor, subset_unit)] = base_value · factor`. **Refuses** (→ refusal,
never a wrong number) on: no state holds `base_unit`; >1 entity holds it
(ambiguous); the target slot already exists (overwrite). Reuses the `multiply`
pack lemma (a partition is a scaled multiply).

**Entity/unit rule** (the extractor, `_partition_candidates`):
`<frac> of [the] <BASE> <verb> <SUBSET>` →
- `are <X>` (relabel) → `actor=X, subset_unit=X`
- `have/own <Y>` (predicate) → `actor=BASE, subset_unit=Y`

So 0046 reads as a chain `students(100) → girls(50)/boys(50) → girls·dogs(10) +
boys·dogs(5)`, and the question `"How many students own dogs?"` aggregates unit
`dogs` = **15** — the intermediate populations keep distinct units so the
aggregate never over-counts. Factors: word (`half`/`third`/`quarter` via
`_ANCHOR_TO_FACTOR`), percentage (`N%`), slash (`N/M`).

## 3. Multi-partition-per-sentence → clause splitting

The candidate-graph picks one choice per sentence (Cartesian product), so two
partitions in one sentence would compete. `split_partition_clauses` splits on
`,`/`and` **iff every resulting clause is partition-shaped** (ordinary
conjunctions untouched), and rewrites an elliptical `"the other half are boys"`
into `"half of the <base> are boys"` using the sibling clause's base (the base
noun is real — it appears in the same sentence, so grounding stays honest).

## 4. wrong=0 obligations — every layer learns partition

The wrong=0 firewall is multi-layer; a partition that only solved would have
slipped a wrong answer past three of them. All updated + pinned:

1. **Round-trip filter** (`roundtrip_admissible`): dedicated partition branch —
   both population units + the factor (word/`%`/`N/M`) must ground; an
   ungrounded subset unit refuses (`test_partition_refuses_when_subset_unit_ungrounded`).
2. **Verifier** (`_verify_partition_step`): independent replay rebinds the base
   by unit and re-derives `factor·base`; mismatch/ambiguity/overwrite refuse.
3. **Realizer** (`_step_sentence`): articulates the partition step (a realizer
   gap was silently downgrading 0046 to `decoded_unarticulated`).

## 5. Evidence

- **`train_sample` 4/46/0 → 5/45/0, wrong=0** (full parse→solve→verify→realize
  pipeline; correct set `{0014, 0018, 0024, 0042, 0046}`).
- Synthetic-registry wrong=0 guard green; **1100+ tests pass**;
  `tests/test_adr_0190_partition.py` adds failing-under-violation guards
  (no-base / ambiguous-base / overwrite / ungrounded-unit / same-unit refuse).
- `verify_lane_shas` / `generate_claims --check` consistent after re-baseline.
- 0021 enters the sealed audit's pre_frame_filler set (benign — its serving is
  unaffected; the partition extractor does not fire on it).

## 6. Principles

Decode-not-guess (reads the partition structure, composes the existing solver);
general-not-overfit (partition is a fundamental construction recurring across
0046/0004/0041 + most percentage problems in real GSM8K); wrong=0 supreme
(refusal-preferring at every layer); no contradiction with in-use ADRs (extends
the ADR-0123 solver, isolated new kind).

## 7. What this opens

The partition operation unblocks the `fraction_operand` cluster. Next: temporal
self-overwrite (0005-class `decrease to ¾ of`) and the multi-step fraction
chains (0010), each landed the same way — general, wrong=0-proven, re-baselined.

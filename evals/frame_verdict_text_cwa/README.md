# frame_verdict_text_cwa — text closed-world evaluation lane (B4 PR-2)

A measure-only lane over the closed-world `FrameVerdict` text evaluator
(`generate/frame_verdict/evaluate.py`, ADR-0222). It proves the sealed type can evaluate
text/propositional closed frames safely — including a sound negative conclusion
(`entailed_false`) — **without** touching the open-world `determine()` path or runtime serving.

## What it checks

For each `v1/cases.jsonl` case (a `ClosedFrame` + `query` + hand-authored `gold`):

- the production `evaluate_frame_verdict` verdict == gold (**wrong = 0**);
- the gold is **independent** — `oracle.py::oracle_frame_verdict` re-derives it by its OWN
  recursive-descent parser + brute-force truth-table enumeration, **disjoint from the ROBDD**
  (imports no engine module; never calls `evaluate_frame_verdict` / `determine` /
  `response_governance`). Engine and oracle must agree on every case (INV-25/27 discipline);
- every `entailed_false` carries an admissible proof (`proof_chain.entail` / `REFUTED` /
  `ROBDD_REFUTATION`, non-empty `proof_sha256`); a generic FALSIFIED is impossible (the type's
  `__post_init__` invariant);
- **absence / OPEN / undeclared-closure are never `entailed_false`** — they refuse
  (`UNDETERMINED` / `SCOPE_BOUNDARY`).

## Input contract (PR-2)

`propositions` and `query` are **propositional-formula strings** in the `proof_chain.entail`
grammar (atoms, `~`, `&`, `->`, parens; `~` > `&` > `->`, `->` right-assoc). There is **no
prose lowering** — a prose front-end is out of scope. Malformed / out-of-regime input refuses
with `SCOPE_BOUNDARY`.

## Gold categories

`ENTAILED_TRUE` · `ENTAILED_FALSE` · `UNDETERMINED` · `CONTRADICTION` · `SCOPE_BOUNDARY`.

## Independence (honest scope note)

The disjoint solver is the wrong=0-critical part: the truth-table oracle decides entailment
independently of the ROBDD. The **frame-gating contract** (OPEN / undeclared / non-TEXT =>
`SCOPE_BOUNDARY`) is shared by both — it is the frame contract, not a solver, so both apply it;
independence is in the solving.

## Capability-index: deliberately NOT registered

This lane is **not** added to `evals/capability_index` and does **not** change the capability
baseline/digest. The whole closed-world feature is off-serving (sealed type + INV-31 firewall;
default-dark even after the governance slice), so registering a closed-world *serving*
capability domain would be premature. ADR-0222 §9 anticipates a future ProofWriter-CWA
capability lane registering once closed-world becomes a ratified serving capability; until then
this stays a measure-only correctness lane (the posture of the #779 ProofWriter-OWA floor).

## Run

```
python -m pytest tests/test_frame_verdict_text_cwa_lane.py
python -m evals.frame_verdict_text_cwa.score   # prints the report; exit 1 on wrong>0
```

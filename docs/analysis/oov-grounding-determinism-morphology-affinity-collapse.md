# OOV Grounding Determinism: Morphology-Affinity Collapse

## Map

Three candidate explanations were checked in the OOV grounding path:

- Unseeded random synthesis: not found. `ingest/gate.py` did not call `random` or
  `np.random` for unknown-token construction.
- Python hash / hash-seed ordering: not found on the active construction path.
  The compiler feature rotors and the new fix use SHA-256, not `hash()`.
- Transient index or vocabulary process state: not the failing source. Transient
  insertion happens after construction; it did not feed the failing field bytes.

The exact failing source was `_best_decomposition()` in `ingest/gate.py`. When a
token had no exact prefix/root/suffix decomposition, the function fell back to a
root-affinity scan over mounted morphology. `_ground_unknown_token()` then used
that selected root as the whole OOV point whenever no prefix/suffix operators
were applied. The OOV token's byte content did not enter the versor at all in
that generic path.

Observed RED repro:

- `probe_ingest(["<oov>"]).F.tobytes()` was already stable across fresh contexts.
- `probe_ingest(["xyzzy_unknown_token_12345"]).F.tobytes()` and
  `probe_ingest(["zzq-no-morph-019"]).F.tobytes()` were byte-identical because
  both were assigned the same affinity root, `ἀποκρίνομαι`, with no operators.

## Build

The fix lives only at the sanctioned ingest boundary, `ingest/gate.py`.

- Exact morphology still uses the known root when the OOV token has a real
  prefix or suffix decomposition.
- Empty-prefix/empty-suffix affinity fallback is no longer treated as structural
  grounding. Generic OOV starts from the identity versor instead of inheriting an
  arbitrary morphology root.
- Every OOV transient receives a token-byte delta:
  `sha256("oov:token:v1" || token_utf8)` selects three small negative-bivector
  Spin rotors and records a `token:sha256:<prefix>` audit operator.
- Morphology prefix/suffix deltas in the OOV path now also use negative-bivector
  Spin rotors rather than the compiler's feature rotors.

No realization code and no vault code were touched.

## Justify

The corrected intrinsic space is the token's stable byte identity composed with
any real morphology decomposition. The previous fallback projected unknown
tokens into a borrowed root space; that collapsed unrelated symbols and made the
generic OOV point a function of mounted vocabulary shape rather than token
content.

Closure is preserved by construction: each new delta is `cos(theta) + B
sin(theta)` where `B` is one of `(6, 7, 8, 10, 11, 13)`, the negative
bivectors in `Cl(4,1)`. These are Spin factors, so composing them with a closed
root or with the identity remains on the versor manifold. The OOV constructor
checks `versor_condition(versor) < 1e-6` and raises if construction violates the
contract; it does not normalize, unitize, grade-project, or repair the transient
after the fact.

The field-level `inject()` holonomy boundary remains unchanged and continues to
own prompt-field closure.

## Verification

Initial RED:

```bash
uv run python -m pytest tests/test_oov_grounding_cache.py::test_generic_oov_probe_is_byte_stable_across_contexts_and_restore -q
# FAILED: two distinct generic OOV tokens produced identical field bytes
```

Targeted GREEN after the fix:

```bash
uv run python -m pytest tests/test_unknown_token_ingest.py tests/test_oov_grounding_cache.py -q
# 8 passed
```

Final verification:

```bash
uv run python -m pytest tests/test_unknown_token_ingest.py tests/test_oov_grounding_cache.py -q
# 8 passed in 3.26s

uv run python -m pytest tests/test_unknown_token_ingest.py tests/test_oov_grounding_cache.py tests/test_oov_pipeline.py tests/test_oov_surface.py tests/test_pack_grounded_unknown.py tests/test_partial_surface.py tests/test_cold_start_grounding_lane.py tests/test_language_pack_runtime.py tests/test_language_pack_cache.py tests/test_language_pack_load_safety.py -q
# 142 passed in 75.09s

uv run python -m core.cli test --suite smoke -q
# 90 passed in 114.00s

uv run python -m core.cli test --suite cognition -q
# 121 passed, 1 skipped in 55.84s

uv run python -m core.cli eval cognition
# intent_accuracy: 100.0%
# term_capture_rate: 100.0%
# surface_groundedness: 100.0%
# versor_closure_rate: 100.0%

uv run python -m core.cli eval cognition --json
# all 13 case records had intent_correct=true, surface_contains_pass=true,
# and versor_closure=true; this lane does not emit a separate wrong counter.
```

Wrinkle: the repository declares a `core` console script in `pyproject.toml`, but
`uv sync` reports that entry points are skipped because the project is not
packaged in this checkout. The exact `uv run core ...` form therefore fails to
spawn `core`; the verified equivalent is `uv run python -m core.cli ...`.

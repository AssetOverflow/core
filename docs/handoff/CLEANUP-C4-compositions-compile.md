# C4 — Compile and commit `compositions.jsonl` for the math pack

**Classification**: Half-built producer/consumer loop (audit finding C4)  
**Risk**: Low — purely additive, wrong == 0 guaranteed by registry design  
**Scope**: `language_packs/data/en_core_math_v1/`, `language_packs/compile_compositions.py`

---

## Problem

`language_packs/data/en_core_math_v1/compositions/multiplicative_composition.jsonl`
was ratified via ADR-0169 and is present on disk. But
`language_packs/data/en_core_math_v1/compositions.jsonl` (the compiled
artifact that the runtime reads) **does not exist**.

The consumer chain is:

```
compositions/multiplicative_composition.jsonl   ← ratified source (EXISTS)
    ↓  compile_compositions.py
compositions.jsonl                              ← compiled registry (MISSING)
    ↓  comprehension/composition_registry.py::load_composition_registry()
    ↓  recognizer_anchor_inject.py (line 157–159)
InjectorEmission[]                              ← runtime output (always empty)
```

`load_composition_registry()` handles the missing file gracefully — it
returns an empty registry when `compositions.jsonl` is absent and
`manifest.json` does not declare `composition_checksum`. So the system is
stable; the ratified claims simply have no effect on runtime decisions.

---

## What to do

### Step 1 — Run the compile step

```bash
uv run python -c "
from pathlib import Path
from language_packs.compile_compositions import compile_pack_compositions

pack = Path('language_packs/data/en_core_math_v1')
result = compile_pack_compositions(pack)
print('written to:', result.output_path)
print('sha256:', result.sha256)
print('entries:', result.entry_count)
"
```

Verify `entry_count > 0` (at least the multiplicative_composition entries).

### Step 2 — Update manifest.json with composition_checksum

The manifest checksum enforces that the committed compiled artifact matches
what `compile_compositions.py` would produce from the source files. Once the
compiled artifact is committed, `manifest.json` should be updated to declare
`composition_checksum` so any future drift raises
`CompositionRegistryLoadError` at load time (defense in depth).

```bash
sha=$(sha256sum language_packs/data/en_core_math_v1/compositions.jsonl | cut -d' ' -f1)
# or on macOS:
sha=$(shasum -a 256 language_packs/data/en_core_math_v1/compositions.jsonl | cut -d' ' -f1)
```

Then add `"composition_checksum": "<sha>"` to `manifest.json`.

### Step 3 — Verify the registry is non-empty at runtime

```bash
uv run python -c "
from generate.comprehension.composition_registry import load_composition_registry
r = load_composition_registry()
print('empty:', r.is_empty())
print('categories:', list(r.by_category.keys()))
"
```

Expected: `empty: False`, at least `multiplicative_composition` in categories.

### Step 4 — Run packs + smoke suites

```bash
uv run core test --suite packs -q
uv run core test --suite smoke -q
```

### Step 5 — Commit

```
language_packs/data/en_core_math_v1/compositions.jsonl   (new)
language_packs/data/en_core_math_v1/manifest.json        (updated: composition_checksum)
```

Commit message:
```
feat(packs): compile multiplicative_composition registry for math pack

Runs compile_compositions.py to produce compositions.jsonl from the
ratified multiplicative_composition.jsonl source. Updates manifest.json
with composition_checksum. load_composition_registry() now returns a
non-empty registry; recognizer_anchor_inject.py can emit InjectorEmission
for composition-shape matches. Closes the producer/consumer gap from
ADR-0169.
```

---

## Invariant gates

- `wrong == 0` is preserved by the registry's refusal-preferring discipline:
  `is_falsified` returns `()` immediately; `is_affirmed` gates every emission.
- The `WrongCompositionCategory` check at load time prevents any unsafe
  category from being accepted even if the source file is mutated.
- The manifest checksum (after Step 2) provides ongoing compile-drift
  detection.

---

## Relation to other findings

- **C2** (run_lane migration): C4 should land at the same time or before C2
  so the candidate-graph path immediately sees a non-empty composition
  registry.
- **C5** (reader zero-delta): the reader's zero-delta is unrelated to
  compositions — it is a statement-level injector gap. C4 does not fix C5.

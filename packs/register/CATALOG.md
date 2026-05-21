# Register pack catalog — production guide

`packs/register/_catalog.json` is the canonical, machine-readable spec for the
**100-register catalog**. Each entry is a complete production input — an author
or content pipeline materializes `packs/register/<register_id>.json` from it
mechanically and re-runs ratification.

| Group | Count | Voice |
| --- | --- | --- |
| A — Depth ladder | 6 | Varies disclosure_domain_count + structural booleans. No markers. |
| B — Tone | 16 | Affective marker palettes. Default knobs. |
| C — Stance | 12 | Epistemic posture — assertive, hedged, exploratory, etc. |
| D — Posture | 10 | Social role — peer, mentor, scholar, etc. |
| E — Domain | 12 | Academic, technical, legal, scientific, philosophical, etc. |
| F — Cultural | 12 | Plainspoken, cosmopolitan, classic, lyrical, etc. |
| G — Affective | 10 | Cheerful, somber, wry, gentle, etc. |
| H — Functional | 10 | Documentary, instructional, persuasive, etc. |
| I — Composite | 12 | Combine knobs from multiple groups. |
| **Total** | **100** | 7 ratified + 93 drafted |

## Production loop

For each entry whose `status == "drafted"`:

1. **Materialize** `packs/register/<register_id>.json` from the catalog entry.
   Required fields: `register_id`, `version` (set to `"1.0.0"`),
   `description`, `schema_version` (`"1.0.0"`), `mastery_report_sha256`
   (leave `""` — the ratify script will fill it),
   `display_name`, `depth_preference`, `realizer_overrides`,
   `discourse_markers`.
2. **Widen** `scripts/ratify_register_packs.py::REGISTER_IDS` to include
   the new `register_id`.
3. **Ratify**: `python scripts/ratify_register_packs.py`. Idempotent;
   re-runs produce byte-identical files.
4. **Test**: the ratification script writes the `.mastery_report.json`
   companion and updates `mastery_report_sha256` in the pack file.
   Run `python -m pytest tests/test_register_loader.py -q` to confirm
   the loader self-seal check passes.
5. **Smoke**: `core chat "Test prompt" --register <register_id>` should
   produce a surface whose `grounding_source` and `trace_hash` are
   byte-identical to the same prompt under `default_neutral_v1`
   (ADR-0072 register invariant). Only the surface text varies.

## Trust boundaries

- `realizer_overrides` is restricted to the allow-list in
  `scripts/ratify_register_packs.py::_KNOWN_OVERRIDE_KEYS`:
  `disclosure_domain_count` (1, 2, or 3), `compress_gloss`,
  `drop_articles`, `drop_provenance_tag`, `append_semantic_domain_clause`,
  plus `per_intent` nested block keyed by `IntentTag` names. Any other
  key fails ratification.
- `discourse_markers` has exactly three buckets: `openings`,
  `transitions`, `closings`. Each is a list of strings. An empty string
  `""` inside a bucket is a legal entry — the seeded selector (ADR-0071)
  treats it as "no marker this turn", enabling natural variation.

## Author guidance

- Keep each marker palette small (3–5 entries per non-empty bucket).
  Larger palettes are not better — the seeded selector wants a tight
  bounded space so per-turn variation is felt without being noisy.
- Include `""` in `openings` and `closings` for ~20–30% of registers
  so the system has a "land plainly" option per turn.
- Markers may contain Unicode em-dash (—), ASCII punctuation, and
  standard English contractions. Avoid emoji and non-English script
  unless the register's purpose is explicitly multilingual.
- For composite registers (group I), the `description` field should
  name the two constituent voices it combines.

## Invariants pinned by ADR-0072 / ADR-0071

Every register in this catalog must satisfy, on every prompt:

- `grounding_source` is byte-identical to `default_neutral_v1`.
- `trace_hash` is byte-identical to `default_neutral_v1`.
- `aggregate metrics` (cognition eval lane) are byte-identical.
- Only the surface text varies.

The `core demo register-tour` runner exists to assert this. New registers
should be added to its sweep once authored.

## Next steps after authoring

- Update the cognition eval's register-invariance test fixtures to
  include the new register ids (sweep, no per-register code change).
- Optional follow-up: add a `register_distribution_lift` benchmark
  (ADR-0072 variant) that measures surface-variance across the full
  100-register sweep for a fixed prompt corpus.

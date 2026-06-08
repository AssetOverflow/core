# R3.2 — explicit time-unit conversion (single-rate)

**As of:** R3.2, on `main` + `feat/r3-2-conversion`.

R3.2 adds exactly one capability to the single-rate organ: a duration whose unit **converts** to the
rate's denominator (`minute` ↔ `hour`) is now **solved** instead of refused. It closes the most
common rate gap — `60 miles per hour for 30 minutes → 30 miles` — which the R3.1 loop surfaced as a
proposal.

## Lane state
- R3 gold **13 / 13 valid** (7 solved / 2 solver_refuses / 4 reader_refuses)
- R3 reader **9 setup_correct / 0 setup_wrong / 4 refused** → answers **7 / 0 / 6**
- R1 **7/0/3** · R2 **10/0/0** · serving unchanged · router-hygiene invariant green · off-serving

## Design — Option A (text-faithful model, Fraction in the solver)
- **Model** (`RateProblem`) gains `time_unit` — the duration's **original** unit from the text; `time`
  stays the original `int`. `rate_unit.denominator` is the target unit for composition. The setup
  remembers what the text said ("30 minutes"), not a normalized internal.
- **Conversion** (`conversion.py`): `convert_time(value, from, to) -> Fraction` — exact rational
  (`fractions.Fraction`), identity for the same unit (incl. non-time like `box`), `minute ↔ hour`
  otherwise, refuse else. **No floats.**
- **Solver** confines `Fraction`: `rate × convert(time)` (or the inverses), then exact-int-or-refuse
  (`non_integer_solution`). A non-convertible duration raises `ConversionError` → `rate_unit_mismatch`.
- **Reader** accepts a convertible mismatch (keeps the original `time_unit`; the solver converts);
  a non-convertible mismatch still refuses `rate_unit_mismatch`.
- **Signature** includes `time_unit` — "30 minutes" and "30 hours" are different setups at the same rate.

## Gold change
- `r3-09` flips **reader_refuses → solved**: "60 mph for 30 minutes" → 30 minute = `Fraction(1,2)` hour
  → `60 × 1/2 = 30` mile (the never-convert distractor `1800` is rejected).
- New `r3-13` (non-convertible): "…per hour for 3 gallons" → `rate_unit_mismatch` (gallon is not a
  time unit). Stays a proposal surface.

## Failure-family / hygiene (confirmed, no code change)
- `rate_unit_mismatch` now fires **only for non-convertible** durations → still maps to the
  `unsupported_rate_duration` growth surface (propose adding *that* unit pair). Convertible mismatches
  now **solve** (no longer a failure). `temporal_state` / `not_rate_shaped` unchanged.
- The **router-organ-hygiene invariant** stays green — R3 still refuses foreign R1/R2 text as
  `input_shape`, never a substantive boundary.

## Acceptance (met)
R3 `setup_correct` **8 → 9** · `answer_wrong = 0` · `r3-09` refused/proposal → solved ·
non-convertible mismatch still refused/proposal · R1/R2 unchanged · **no float path** (Fraction →
int-or-refuse).

## Deferred (named for later)
length (`mile ↔ km`), currency (`dollar ↔ cent`), compound conversions, combined/multi-rate,
clock-time intervals. The dimensional substrate is now proven for exact rational time conversion.

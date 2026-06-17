# Test lanes — see docs/testing-lanes.md.
#
# Slow tests are classified in conftest.py (SLOW_FILES / SLOW_TESTS), not via
# in-file decorators.  Classification adds the `slow` marker only; it never
# skips, so the lanes below are selected explicitly by marker expression.
#
# These run serially.  Parallel (`-n auto`) is intentionally NOT the default
# until the suite is xdist-hermetic (shared repo engine_state/ + report.json +
# teaching/proposals writers race under parallel workers).  See
# docs/testing-lanes.md "Follow-up: xdist".
#
# CLOSE flywheel Claim-B determinism (post-#791 hardening): after any
# CLOSE/idle_tick/realize_derived/consolidate/vault/determine change, also run
#   uv run python -m evals.close_derived_climb
#   uv run python -m pytest tests/test_derived_close_proposals.py tests/test_architectural_invariants.py -q
# See docs/testing-lanes.md "Recommended determinism / teaching regression invocation".

.PHONY: test-fast test-slow test-full

# Fast dev lane — excludes the slow soak/bench/proof/eval-matrix registry.
test-fast:
	uv run pytest -m "not quarantine and not slow" -q

# Slow lane — only the heavyweight registry tests.
test-slow:
	uv run pytest -m "slow and not quarantine" -q

# Full lane — everything except known-failing quarantine (what CI runs).
test-full:
	uv run pytest -m "not quarantine" -q

"""On-demand entrypoint for the L10 continuity soak panel.

Run:  PYTHONPATH=. .venv/bin/python -m evals.l10_continuity [n_turns] [reboot_turn]

Prints the structured report as JSON and exits non-zero if any gate fails. This
lane is a soak — it is NOT in the default smoke suite; run it on demand or
nightly. The ``deterministic_digest`` in the output is the freeze handle: pin it
once the lane is trusted so a regression flips it.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from evals.l10_continuity.report import build_report


def main(argv: list[str]) -> int:
    n_turns = int(argv[0]) if len(argv) > 0 else 12
    reboot_turn = int(argv[1]) if len(argv) > 1 else 3
    with tempfile.TemporaryDirectory(prefix="l10_continuity_") as tmp:
        report = build_report(
            n_turns=n_turns,
            reboot_turn=reboot_turn,
            engine_state_root=Path(tmp),
        )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.all_gates_pass() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

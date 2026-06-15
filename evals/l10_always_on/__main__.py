"""On-demand entrypoint for the L10 always-on heartbeat soak panel.

Run:  PYTHONPATH=. .venv/bin/python -m evals.l10_always_on [n_beats] [reboot_beat]

Drives the IDLE heartbeat over a seeded continuous life for ``n_beats`` beats (default 24;
pass a large N — e.g. 100000 — for a true long-horizon soak), prints the structured report
as JSON, and exits non-zero if any gate fails. NOT in the default smoke suite — a soak, run
on demand / nightly. ``deterministic_digest`` is the freeze handle.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from evals.l10_always_on.report import build_report


def main(argv: list[str]) -> int:
    n_beats = int(argv[0]) if len(argv) > 0 else 24
    reboot_beat = int(argv[1]) if len(argv) > 1 else max(1, n_beats // 2)
    with tempfile.TemporaryDirectory(prefix="l10_always_on_") as tmp:
        report = build_report(
            n_beats=n_beats, reboot_beat=reboot_beat, engine_state_root=Path(tmp)
        )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.all_gates_pass() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

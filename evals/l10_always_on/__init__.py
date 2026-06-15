"""L10 always-on heartbeat soak — the falsifiable long-horizon gate for the IDLE path.

The continuity lane (``evals/l10_continuity``) soaks the TURN loop. This lane soaks the
IDLE heartbeat (``chat/always_on.run_continuous``): it seeds a real continuous life, then
drives the engine over many beats with NO user turn and evaluates falsifiable predicates
over the per-beat evidence — closure holds over indefinite idle uptime (read, never
repaired), idle resources stay bounded, the saturated life converges to rest, and a reboot
mid-soak resumes the SAME life.

Not in default smoke (it is a soak; run on demand / nightly):
``PYTHONPATH=. .venv/bin/python -m evals.l10_always_on [n_beats] [reboot_beat]``
"""

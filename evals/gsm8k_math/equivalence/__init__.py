"""ADR-0184 S4b — the replay/provenance equivalence harness.

Canonical candidate traces for the full GSM8K/derivation corpus, pinned as a
committed artifact (``v1/expected_traces.jsonl`` + ``v1/manifest.json``) so the
semantic-ledger candidate source cannot silently drift from the behavior that was
proven byte-equal to the pre-ledger legacy path (the #684/#685 cross-tree
differentials).  See ``trace.py`` and
``docs/analysis/adr-0184-replay-provenance-equivalence-harness-2026-06-10.md``.
"""

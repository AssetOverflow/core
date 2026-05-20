"""Rhetorical-style pack layer (ADR-0087, substrate phase).

A *rhetorical style* is the substantive-frame axis: it constrains
which rhetorical-mode frames the realizer may emit and which
rhetorical-move requirements the composer applies.  It is **not** a
motor on the field — see ADR-0087 §Forbidden alternatives.

Sister to:

* :mod:`packs.anchor_lens` — substantive-vocabulary axis
  (semantic content / tradition).  Rhetorical style is the third
  selection axis: rhetorical-genre constraint, sibling to anchor lens,
  orthogonal to register.
* :mod:`packs.safety` and :mod:`packs.identity` — pack-layer
  composition discipline (mastery-report self-seal, fail-closed
  loader).

This is the substrate-only layer.  No composer or realizer yet
consumes the pack — that wiring is the consumer ADR's job.  Today the
substrate exists so the consumer ADR has something to be wired
against.
"""

from packs.rhetorical_style.loader import (
    DEFAULT_RHETORICAL_STYLE_PACK,
    RhetoricalStylePack,
    RhetoricalStylePackError,
    load_rhetorical_style_pack,
)

__all__ = (
    "DEFAULT_RHETORICAL_STYLE_PACK",
    "RhetoricalStylePack",
    "RhetoricalStylePackError",
    "load_rhetorical_style_pack",
)

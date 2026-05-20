"""Primitives-pack layer (ADR-0084).

A *primitive* is a lemma whose meaning is taken as terminal at the system
level — every other gloss's :attr:`definitional_atoms` bottoms out on
primitives, same-pack lemmas, or other mounted-pack lemmas (no infinite
regress).

The primitives pack is sister to :mod:`packs.safety` and :mod:`packs.identity`:

* swappable like :mod:`packs.identity` (operators may fork the floor)
* never auto-mutable like :mod:`packs.safety`
* ratified through a manifest checksum (same discipline as
  ``language_packs/`` glosses_checksum)

This package exposes :func:`load_primitives_pack` and the immutable
:class:`PrimitivesPack` dataclass.  It is NEVER mountable as a teaching
corpus — primitives have no chains, no propositions, and no surface
realization path.
"""

from packs.primitives.loader import (
    DEFAULT_PRIMITIVES_PACK,
    PrimitivesPack,
    PrimitivesPackError,
    load_primitives_pack,
)

__all__ = (
    "DEFAULT_PRIMITIVES_PACK",
    "PrimitivesPack",
    "PrimitivesPackError",
    "load_primitives_pack",
)

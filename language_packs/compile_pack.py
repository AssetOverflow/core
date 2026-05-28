"""RAT-1 — unified pack compile step.

Single entry point that regenerates compiled-artifact bytes for every
optional ratification surface (frames + compositions) AND updates the
pack manifest's checksum fields atomically.

This is the missing link between operator ratification (which writes
source files under ``{pack}/frames/`` or ``{pack}/compositions/``) and
runtime visibility (which loads from compiled artifacts +
manifest-declared checksums).

Doctrine:

- The compile step is **read-only over reviewed source files**.
- Manifest mutation is the only side effect besides the compiled
  artifacts. The lexicon checksum (``checksum`` field) is preserved
  byte-equal — only ``frame_checksum`` and ``composition_checksum``
  fields are added/updated.
- Empty source directory produces a zero-byte compiled artifact AND
  ``manifest_checksum_field = sha256("")`` — the loader treats this
  as an empty-registry no-op.
- Idempotent: running compile twice in a row is a no-op.

Trust boundary identical to the per-surface handlers (ADR-0168 §"Mutation
boundary", ADR-0169 §"Mutation boundary"): the compile step does NOT
touch solver, parser, decomposer, arithmetic operators, runtime graph
execution, or refusal logic. It writes ``compositions.jsonl`` +
``frames.jsonl`` + ``manifest.json``. Nothing else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from language_packs.compile_compositions import compile_compositions
from language_packs.compile_frames import compile_frames


@dataclass(frozen=True, slots=True)
class CompilePackReceipt:
    pack_path: Path
    frame_checksum: str
    composition_checksum: str
    frame_bytes_written: int
    composition_bytes_written: int
    manifest_updated: bool


def compile_pack(pack_path: Path) -> CompilePackReceipt:
    """Compile all ratification surfaces for *pack_path* + update manifest.

    Returns the receipt with computed checksums + I/O counts.
    """
    pack_path = Path(pack_path).resolve()
    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Pack manifest missing: {manifest_path}")

    frame_bytes, frame_sha = compile_frames(pack_path)
    comp_bytes, comp_sha = compile_compositions(pack_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    before = dict(manifest)
    manifest["frame_checksum"] = frame_sha
    manifest["composition_checksum"] = comp_sha
    updated = manifest != before
    if updated:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return CompilePackReceipt(
        pack_path=pack_path,
        frame_checksum=frame_sha,
        composition_checksum=comp_sha,
        frame_bytes_written=len(frame_bytes),
        composition_bytes_written=len(comp_bytes),
        manifest_updated=updated,
    )


__all__ = ["compile_pack", "CompilePackReceipt"]

"""CW-1 — compile frames/*.jsonl into a deterministic frames.jsonl artifact.

Mirrors the lexicon compile pattern (see ``language_packs/compiler.py``).
Reads per-category source files under ``{pack}/frames/*.jsonl``, normalizes
ordering, and writes the compiled artifact ``{pack}/frames.jsonl`` with
entries sorted by ``(frame_category, surface_form)``.

Returns the sha256 of the compiled bytes so callers (typically the
manifest writer) can pin ``frame_checksum`` per CLAUDE.md
"Semantic Pack Discipline".

Trust boundary: read-only over the reviewed pack; no engine_state writes,
no corpus mutation. Empty source directory produces an empty (zero-byte)
compiled artifact — the loader treats this as a no-op.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_entry(rec: dict[str, Any]) -> dict[str, Any]:
    """Project the entry to its canonical-bytes shape.

    Drops unknown keys to keep the compiled artifact byte-stable across
    upstream schema additions. Required keys: surface_form, frame_category,
    polarity, provenance, evidence_hashes.
    """
    return {
        "surface_form": str(rec["surface_form"]),
        "frame_category": str(rec["frame_category"]),
        "polarity": str(rec["polarity"]),
        "provenance": str(rec.get("provenance", "")),
        "evidence_hashes": [str(h) for h in rec.get("evidence_hashes", [])],
    }


def compile_frames(pack_path: Path) -> tuple[bytes, str]:
    """Compile ``{pack_path}/frames/*.jsonl`` → bytes + sha256.

    The compiled bytes are written to ``{pack_path}/frames.jsonl`` if
    they differ from the existing file (or it does not exist). The
    sha256 is returned so the caller may update the pack manifest.

    Deterministic ordering: source files iterated alphabetically; entries
    within each file are re-sorted globally by
    ``(frame_category, surface_form)`` before write.

    Empty source directory (or missing) → zero-byte artifact.
    """
    source_dir = pack_path / "frames"
    entries: list[dict[str, Any]] = []
    if source_dir.is_dir():
        for src in sorted(source_dir.glob("*.jsonl")):
            for line in src.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entries.append(_canonical_entry(json.loads(line)))

    entries.sort(key=lambda e: (e["frame_category"], e["surface_form"]))

    if not entries:
        compiled_bytes = b""
    else:
        compiled_bytes = (
            "\n".join(
                json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for e in entries
            )
            + "\n"
        ).encode("utf-8")

    out_path = pack_path / "frames.jsonl"
    existing = out_path.read_bytes() if out_path.exists() else None
    if existing != compiled_bytes:
        out_path.write_bytes(compiled_bytes)

    sha256 = hashlib.sha256(compiled_bytes).hexdigest()
    return compiled_bytes, sha256


__all__ = ["compile_frames"]

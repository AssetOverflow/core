"""CW-2 — compile compositions/*.jsonl into a deterministic compositions.jsonl artifact.

Mirrors :mod:`language_packs.compile_frames` for the composition surface.
Reads per-category source files under ``{pack}/compositions/*.jsonl`` and
writes ``{pack}/compositions.jsonl`` with entries sorted by
``(composition_category, surface_pattern)``.

Trust boundary: read-only over the reviewed pack. The compile step does
**not** enforce the SAFE_COMPOSITION_CATEGORIES allowlist — that lives
at write time (handler) and re-fires at load time (registry). Compile
is byte-deterministic projection only.

Empty source directory produces an empty (zero-byte) compiled artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_entry(rec: dict[str, Any]) -> dict[str, Any]:
    """Project an entry to its canonical-bytes shape.

    Required keys: surface_pattern, composition_category, polarity,
    provenance, evidence_hashes.
    """
    return {
        "surface_pattern": str(rec["surface_pattern"]),
        "composition_category": str(rec["composition_category"]),
        "polarity": str(rec["polarity"]),
        "provenance": str(rec.get("provenance", "")),
        "evidence_hashes": [str(h) for h in rec.get("evidence_hashes", [])],
    }


def compile_compositions(pack_path: Path) -> tuple[bytes, str]:
    """Compile ``{pack_path}/compositions/*.jsonl`` → bytes + sha256.

    Writes ``{pack_path}/compositions.jsonl`` if the bytes differ.
    Returns ``(compiled_bytes, sha256)`` so the caller may update the
    pack manifest's ``composition_checksum``.
    """
    source_dir = pack_path / "compositions"
    entries: list[dict[str, Any]] = []
    if source_dir.is_dir():
        for src in sorted(source_dir.glob("*.jsonl")):
            for line in src.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entries.append(_canonical_entry(json.loads(line)))

    entries.sort(key=lambda e: (e["composition_category"], e["surface_pattern"]))

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

    out_path = pack_path / "compositions.jsonl"
    existing = out_path.read_bytes() if out_path.exists() else None
    if existing != compiled_bytes:
        out_path.write_bytes(compiled_bytes)

    sha256 = hashlib.sha256(compiled_bytes).hexdigest()
    return compiled_bytes, sha256


__all__ = ["compile_compositions"]

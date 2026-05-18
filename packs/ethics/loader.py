"""Ethics-pack loader.

ADR-0033.  Ethics packs sit alongside identity (ADR-0027) and safety
(ADR-0029) but occupy a distinct architectural niche:

* **Identity packs** carry *who* CORE is — value axes, directions, weights.
* **Safety packs** carry *what CORE will never do* — universal red lines.
* **Ethics packs** carry *what this deployment commits to in its domain* —
  propositional pledges scoped to a deployment context (general, medical,
  legal, financial, robotics, ...).

Like identity packs, ethics packs are **swappable** per deployment.  Unlike
safety packs, missing ratification is not fail-closed: an absent or
unratified ethics pack falls back to ``DEFAULT_ETHICS_PACK`` with a typed
``EthicsPackError`` raised only when the requested pack is missing
*and* the default cannot be loaded.

At composition time, ``commitment_ids`` from the ethics pack are unioned
into the runtime manifold's ``boundary_ids`` alongside identity and
safety contributions.  The composition is monotone: ethics can add
constraints, never remove them.

See ``docs/decisions/ADR-0033-ethics-packs.md``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterable

from formation.hashing import verify_seal


class EthicsPackError(ValueError):
    """Raised when an ethics pack is missing, malformed, or unverified.

    Inherits from ``ValueError`` (like ``IdentityPackError``, not
    ``SafetyPackError``) — ethics packs are swappable, and a missing
    one is recoverable by falling back to the default.  Only when *both*
    the requested pack and the default are unloadable does this
    surface.
    """


DEFAULT_ETHICS_PACK: str = "default_general_ethics_v1"
_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)
_ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {"general", "medical", "legal", "financial", "robotics", "custom"}
)


@dataclass(frozen=True, slots=True)
class EthicsPack:
    """Loaded ethics pack.

    ``commitment_ids`` is the set of propositional pledges contributed
    to the runtime manifold's ``boundary_ids``.  ``domain`` declares the
    deployment context (audit-only at v1; no behavior change yet).
    """

    pack_id: str
    version: str
    description: str
    domain: str
    commitment_ids: FrozenSet[str]
    commitment_descriptions: dict[str, str]
    mastery_report_sha256: str
    ratified: bool


def load_ethics_pack(
    pack_id: str = DEFAULT_ETHICS_PACK,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> EthicsPack:
    """Load an ethics pack.

    Args:
        pack_id: Pack identifier.  Defaults to ``DEFAULT_ETHICS_PACK``.
        search_paths: Directories to search.  Defaults to
            ``packs/ethics/``.
        require_ratified: When ``True``, require the companion
            ``<pack_id>.mastery_report.json`` and verify its self-seal.
            ``None`` (default) → production mode unless
            ``CORE_ALLOW_UNRATIFIED_ETHICS=1``.

    Raises:
        EthicsPackError: On malformed pack, bounds violation, or — in
            production mode — unverified seal.  Missing-file errors
            surface here so callers can decide whether to fall back to
            the default.
    """
    paths = _resolve_search_paths(search_paths)
    pack_path = _find_pack(pack_id, paths)
    raw = _read_json(pack_path)
    _validate_envelope(raw, pack_id)
    _validate_ratification(raw, pack_id, require_ratified, pack_path)
    commitments = _validate_commitments(raw["commitment_ids"], pack_id)
    descriptions = _validate_descriptions(
        raw.get("commitment_descriptions", {}), pack_id, commitments,
    )
    domain = _validate_domain(raw.get("domain", "general"), pack_id)
    return EthicsPack(
        pack_id=str(raw["pack_id"]),
        version=str(raw["version"]),
        description=str(raw["description"]),
        domain=domain,
        commitment_ids=frozenset(commitments),
        commitment_descriptions=descriptions,
        mastery_report_sha256=str(raw.get("mastery_report_sha256", "")),
        ratified=bool(raw.get("mastery_report_sha256")),
    )


def available_packs(
    search_paths: Iterable[Path | str] | None = None,
) -> list[dict[str, object]]:
    """List discoverable ethics packs as
    ``{"pack_id", "version", "description", "domain", "ratified", "path"}``
    dicts in lex order.
    """
    paths = _resolve_search_paths(search_paths)
    seen: dict[str, dict[str, object]] = {}
    for d in paths:
        if not d.is_dir():
            continue
        for entry in sorted(d.glob("*.json")):
            if entry.name.endswith(".mastery_report.json"):
                continue
            try:
                raw = _read_json(entry)
            except EthicsPackError:
                continue
            if not isinstance(raw, dict):
                continue
            if "schema_version" not in raw or "commitment_ids" not in raw:
                continue
            pack_id = str(raw.get("pack_id", entry.stem))
            if pack_id in seen:
                continue
            seen[pack_id] = {
                "pack_id": pack_id,
                "version": str(raw.get("version", "")),
                "description": str(raw.get("description", "")),
                "domain": str(raw.get("domain", "general")),
                "ratified": bool(raw.get("mastery_report_sha256")),
                "path": str(entry),
            }
    return sorted(seen.values(), key=lambda d: str(d["pack_id"]))


# ---------- internals ----------


def _resolve_search_paths(
    search_paths: Iterable[Path | str] | None,
) -> tuple[Path, ...]:
    if search_paths is None:
        return _DEFAULT_SEARCH_PATHS
    return tuple(Path(p) for p in search_paths)


def _find_pack(pack_id: str, paths: tuple[Path, ...]) -> Path:
    if not pack_id or "/" in pack_id or ".." in pack_id:
        raise EthicsPackError(f"invalid ethics pack_id: {pack_id!r}")
    for d in paths:
        candidate = d / f"{pack_id}.json"
        if candidate.is_file():
            return candidate
    raise EthicsPackError(
        f"ethics pack {pack_id!r} not found in {[str(p) for p in paths]}"
    )


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise EthicsPackError(
            f"failed to read ethics pack {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise EthicsPackError(
            f"ethics pack {path} did not deserialize to a dict"
        )
    return data


def _validate_envelope(raw: dict, pack_id: str) -> None:
    required = (
        "pack_id",
        "version",
        "description",
        "schema_version",
        "domain",
        "commitment_ids",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise EthicsPackError(
            f"ethics pack {pack_id!r} missing required fields: {missing}"
        )
    if raw.get("schema_version") != "1.0.0":
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: unsupported schema_version "
            f"{raw.get('schema_version')!r}"
        )
    if raw.get("pack_id") != pack_id:
        raise EthicsPackError(
            f"ethics pack file declares pack_id={raw.get('pack_id')!r} "
            f"but was requested as {pack_id!r}"
        )


def _validate_ratification(
    raw: dict, pack_id: str, require_ratified: bool | None, pack_path: Path,
) -> None:
    if require_ratified is False:
        return
    if require_ratified is None:
        require_ratified = (
            os.environ.get("CORE_ALLOW_UNRATIFIED_ETHICS") != "1"
        )
    if not require_ratified:
        return
    declared_sha = raw.get("mastery_report_sha256", "")
    if not declared_sha:
        raise EthicsPackError(
            f"ethics pack {pack_id!r} is not ratified "
            "(mastery_report_sha256 empty); set "
            "CORE_ALLOW_UNRATIFIED_ETHICS=1 for development, or ratify "
            "via scripts/ratify_ethics_pack.py."
        )
    report_path = pack_path.parent / f"{pack_id}.mastery_report.json"
    if not report_path.is_file():
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: companion report "
            f"{report_path.name!r} is missing"
        )
    try:
        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: failed to read companion report: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: companion report is not a JSON object"
        )
    if report.get("report_sha256") != declared_sha:
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: companion report SHA "
            f"{str(report.get('report_sha256'))[:12]}... does not match "
            f"pack's declared {declared_sha[:12]}..."
        )
    if not verify_seal(report, sha_field="report_sha256"):
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: companion report failed self-seal "
            "verification"
        )
    if not report.get("ratified", False):
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: companion report has ratified=False"
        )


def _validate_commitments(value: object, pack_id: str) -> list[str]:
    if not isinstance(value, list) or len(value) < 1:
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: commitment_ids must be a non-empty list"
        )
    seen: set[str] = set()
    out: list[str] = []
    for i, c in enumerate(value):
        if not isinstance(c, str) or not c:
            raise EthicsPackError(
                f"ethics pack {pack_id!r}: commitment_ids[{i}] must be a "
                "non-empty string"
            )
        if c in seen:
            raise EthicsPackError(
                f"ethics pack {pack_id!r}: duplicate commitment_id {c!r}"
            )
        seen.add(c)
        out.append(c)
    return out


def _validate_descriptions(
    value: object, pack_id: str, commitments: list[str],
) -> dict[str, str]:
    if not isinstance(value, dict):
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: commitment_descriptions must be a dict"
        )
    out: dict[str, str] = {}
    for c in commitments:
        desc = value.get(c, "")
        if not isinstance(desc, str):
            raise EthicsPackError(
                f"ethics pack {pack_id!r}: commitment_descriptions[{c!r}] "
                "must be a string"
            )
        out[c] = desc
    return out


def _validate_domain(value: object, pack_id: str) -> str:
    if not isinstance(value, str) or not value:
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: domain must be a non-empty string"
        )
    if value not in _ALLOWED_DOMAINS:
        raise EthicsPackError(
            f"ethics pack {pack_id!r}: domain={value!r} not in "
            f"{sorted(_ALLOWED_DOMAINS)}"
        )
    return value


__all__ = [
    "DEFAULT_ETHICS_PACK",
    "EthicsPack",
    "EthicsPackError",
    "available_packs",
    "load_ethics_pack",
]

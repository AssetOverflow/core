"""Read-only CORE-Logos Workbench projections.

The engine owns pack truth.  This module projects committed language-pack
artifacts into stable Workbench read models; it never mutates packs, compiles
new state, or repairs broken links.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from language_packs.schema import AlignmentEdge, LexicalEntry, MorphologyEntry
from workbench.schemas import (
    LogosAlignmentRow,
    LogosAlignmentTargetIssue,
    LogosGlossRow,
    LogosLexiconRow,
    LogosMorphologyLinkIssue,
    LogosMorphologyRow,
    LogosPackContents,
    LogosPackOverview,
    LogosPackSummary,
    LogosSafetyReport,
    SafetyVerdict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_PACK_ROOT = REPO_ROOT / "language_packs" / "data"
READ_CHUNK_BYTES = 64 * 1024
SAFE_LOGOS_PACK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

_LOGOS_DEPTH_ROLES = frozenset({"depth_root", "depth_relation"})
_LOGOS_DOMAIN_ID = "hebrew_greek_textual_reasoning"
_OOV_POLICIES = frozenset(
    {"fail_closed", "tagged_fallback", "propose_vocab_expansion"}
)


def list_logos_packs(
    *, data_root: Path | None = None
) -> list[LogosPackSummary]:
    """Return the deterministic CORE-Logos pack universe."""

    root = _data_root(data_root)
    summaries: list[LogosPackSummary] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        manifest = _read_json_object(manifest_path)
        pack_dir = manifest_path.parent
        if not _is_logos_pack(manifest, pack_dir):
            continue
        overview = logos_pack_overview(pack_dir.name, data_root=root)
        summaries.append(
            LogosPackSummary(
                pack_id=overview.pack_id,
                language=overview.language,
                role=overview.role,
                script=overview.script,
                version=overview.version,
                determinism_class=overview.determinism_class,
                gate_engaged=overview.gate_engaged,
                oov_policy=overview.oov_policy,
                lexicon_count=overview.lexicon_count,
                gloss_count=overview.gloss_count,
                morphology_count=overview.morphology_count,
                frame_count=overview.frame_count,
                composition_count=overview.composition_count,
                alignment_edge_count=overview.alignment_edge_count,
                holonomy_case_count=overview.holonomy_case_count,
                safety_status=overview.safety_status,
                manifest_digest=overview.manifest_digest,
                manifest_path=overview.manifest_path,
            )
        )
    return sorted(summaries, key=lambda item: item.pack_id)


def logos_pack_overview(
    pack_id: str, *, data_root: Path | None = None
) -> LogosPackOverview:
    root = _data_root(data_root)
    pack_dir = _require_logos_pack_dir(pack_id, root)
    manifest_path = pack_dir / "manifest.json"
    manifest = _read_json_object(manifest_path)
    lexicon = _load_lexicon(pack_dir)
    morphology = _load_morphology(pack_id, root)
    alignment = _load_alignment(pack_id, root)
    safety = logos_pack_safety(pack_id, data_root=root)
    return LogosPackOverview(
        pack_id=str(manifest.get("pack_id") or pack_id),
        language=_optional_str(manifest.get("language")),
        role=_optional_str(manifest.get("role")),
        script=_optional_str(manifest.get("script")),
        version=_optional_str(manifest.get("version")),
        determinism_class=_optional_str(manifest.get("determinism_class")),
        gate_engaged=bool(manifest.get("gate_engaged", False)),
        oov_policy=_optional_str(manifest.get("oov_policy")),
        lexicon_count=len(lexicon),
        gloss_count=len(_read_jsonl_objects(pack_dir / "glosses.jsonl")),
        morphology_count=len(morphology),
        frame_count=len(_read_jsonl_objects(pack_dir / "frames.jsonl")),
        composition_count=len(_read_jsonl_objects(pack_dir / "compositions.jsonl")),
        alignment_edge_count=len(alignment),
        holonomy_case_count=0,
        safety_status=safety.verdict,
        manifest_digest=_sha256_file(manifest_path),
        manifest_path=_display_path(manifest_path),
        normalization_policy=_optional_str(manifest.get("normalization_policy")),
        source_manifest=_optional_str(manifest.get("source_manifest")),
        known_gaps=_string_list(manifest.get("known_gaps")),
    )


def logos_pack_contents(
    pack_id: str, *, data_root: Path | None = None
) -> LogosPackContents:
    root = _data_root(data_root)
    pack_dir = _require_logos_pack_dir(pack_id, root)
    manifest = _read_json_object(pack_dir / "manifest.json")
    lexicon = _load_lexicon(pack_dir)
    lexicon_rows = [_lexicon_row(entry) for entry in lexicon]
    entry_ids_by_lemma = _entry_ids_by_lemma(lexicon_rows)
    return LogosPackContents(
        schema_version="logos_pack_contents_v1",
        pack_id=str(manifest.get("pack_id") or pack_id),
        manifest=manifest,
        lexicon=lexicon_rows,
        glosses=_gloss_rows(pack_dir, entry_ids_by_lemma),
        morphology=[
            _morphology_row(entry)
            for entry in _load_morphology(pack_id, root)
        ],
        frames=_read_jsonl_objects(pack_dir / "frames.jsonl"),
        compositions=_read_jsonl_objects(pack_dir / "compositions.jsonl"),
        alignment_edges=logos_pack_alignment(pack_id, data_root=root),
        holonomy_cases=[],
    )


def logos_pack_alignment(
    pack_id: str, *, data_root: Path | None = None
) -> list[LogosAlignmentRow]:
    root = _data_root(data_root)
    _require_logos_pack_dir(pack_id, root)  # validate id / logos membership
    target_index = _entry_id_index(root)
    return [
        _alignment_row(edge, target_index)
        for edge in _load_alignment(pack_id, root)
    ]


def logos_pack_safety(
    pack_id: str, *, data_root: Path | None = None
) -> LogosSafetyReport:
    root = _data_root(data_root)
    pack_dir = _require_logos_pack_dir(pack_id, root)
    manifest = _read_json_object(pack_dir / "manifest.json")
    lexicon = _load_lexicon(pack_dir)
    morphology = _load_morphology(pack_id, root)
    alignment_rows = logos_pack_alignment(pack_id, data_root=root)

    checksum_status, checksum_errors = _checksum_status(pack_id, pack_dir, root)
    domain_contract = _domain_contract_status(pack_id, root)
    domain_status = (
        SafetyVerdict.CLEAR
        if bool(domain_contract.get("valid", False))
        else SafetyVerdict.FAILED
    )
    morphology_ids = {entry.morphology_id for entry in morphology}
    dangling = [
        LogosMorphologyLinkIssue(
            entry_id=entry.entry_id,
            morphology_id=entry.morphology_id or "",
        )
        for entry in lexicon
        if entry.morphology_id and entry.morphology_id not in morphology_ids
    ]
    invalid_targets = [
        LogosAlignmentTargetIssue(
            edge_id=row.edge_id,
            source_id=row.source_id,
            target_id=row.target_id,
            relation=row.relation,
            target_pack_id=row.target_pack_id,
        )
        for row in alignment_rows
        if row.invalid_target
    ]
    epistemic_counts: dict[str, int] = {}
    speculative: list[str] = []
    contested: list[str] = []
    falsified: list[str] = []
    for entry in lexicon:
        status = entry.epistemic_status or "speculative"
        epistemic_counts[status] = epistemic_counts.get(status, 0) + 1
        if status == "speculative":
            speculative.append(entry.entry_id)
        elif status == "contested":
            contested.append(entry.entry_id)
        elif status == "falsified":
            falsified.append(entry.entry_id)

    oov_policy = _optional_str(manifest.get("oov_policy"))
    role = _optional_str(manifest.get("role"))
    oov_policy_ok = oov_policy in _OOV_POLICIES
    gate_policy_ok = not (
        role in _LOGOS_DEPTH_ROLES
        and bool(manifest.get("gate_engaged", False))
        and oov_policy != "fail_closed"
    )
    warning_present = bool(dangling or invalid_targets or contested or falsified)
    known_gaps = _string_list(manifest.get("known_gaps"))
    if checksum_status is SafetyVerdict.FAILED or domain_status is SafetyVerdict.FAILED:
        verdict = SafetyVerdict.FAILED
    elif not (oov_policy_ok and gate_policy_ok):
        verdict = SafetyVerdict.FAILED
    elif warning_present or known_gaps:
        verdict = SafetyVerdict.WARNING
    else:
        verdict = SafetyVerdict.UNKNOWN

    return LogosSafetyReport(
        schema_version="logos_safety_report_v1",
        pack_id=str(manifest.get("pack_id") or pack_id),
        checksum_status=checksum_status,
        checksum_errors=checksum_errors,
        domain_contract=domain_contract,
        domain_contract_status=domain_status,
        oov_policy_ok=oov_policy_ok,
        gate_policy_ok=gate_policy_ok,
        path_safety_ok=True,
        dangling_morphology_links=dangling,
        invalid_alignment_targets=invalid_targets,
        missing_holonomy_refs=SafetyVerdict.UNKNOWN,
        epistemic_status_counts=dict(sorted(epistemic_counts.items())),
        speculative_entries=sorted(speculative),
        contested_entries=sorted(contested),
        falsified_entries=sorted(falsified),
        known_gaps=known_gaps,
        verdict=verdict,
    )


def _data_root(data_root: Path | None) -> Path:
    return (data_root or LANGUAGE_PACK_ROOT).resolve()


def _validate_pack_id(pack_id: str) -> str:
    if not SAFE_LOGOS_PACK_ID_RE.fullmatch(pack_id) or ".." in pack_id:
        raise ValueError("pack id contains unsafe characters")
    return pack_id


def _require_logos_pack_dir(pack_id: str, root: Path) -> Path:
    safe_id = _validate_pack_id(pack_id)
    candidate = (root / safe_id).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("pack id resolves outside language pack root")
    manifest_path = candidate / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(pack_id)
    manifest = _read_json_object(manifest_path)
    if not _is_logos_pack(manifest, candidate):
        raise FileNotFoundError(pack_id)
    return candidate


def _is_logos_pack(manifest: dict[str, Any], pack_dir: Path) -> bool:
    if (pack_dir / "alignment.jsonl").is_file():
        return True
    role = _optional_str(manifest.get("role"))
    if role not in _LOGOS_DEPTH_ROLES:
        return False
    pack_id = str(manifest.get("pack_id") or pack_dir.name)
    # The committed tree also contains a generic English relation seed with
    # role=depth_relation.  Role-only admission is constrained to the Logos
    # substrate so the Studio universe stays the four-pack wave contract.
    return (
        manifest.get("domain_id") == _LOGOS_DOMAIN_ID
        or "logos" in pack_id
        or pack_id.startswith(("he_", "grc_"))
    )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (str(v) for v in value) if item]


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(READ_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _sha256_hex(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(READ_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {_display_path(path)}")
    return payload


def _read_jsonl_records(path: Path) -> list[tuple[int, dict[str, Any]]]:
    if not path.exists():
        return []
    records: list[tuple[int, dict[str, Any]]] = []
    for line_no, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {_display_path(path)}:{line_no}")
        records.append((line_no, payload))
    return records


def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    return [payload for _, payload in _read_jsonl_records(path)]


def _load_lexicon(pack_dir: Path) -> list[LexicalEntry]:
    from language_packs.compiler import _parse_entry

    return [
        _parse_entry(payload)
        for _, payload in _read_jsonl_records(pack_dir / "lexicon.jsonl")
    ]


def _load_morphology(pack_id: str, root: Path) -> tuple[MorphologyEntry, ...]:
    from morphology.registry import load_morphology

    return tuple(load_morphology(pack_id, data_root=root).entries)


def _load_alignment(pack_id: str, root: Path) -> tuple[AlignmentEdge, ...]:
    from alignment.graph import load_alignment

    return tuple(load_alignment(pack_id, data_root=root).edges)


def _lexicon_row(entry: LexicalEntry) -> LogosLexiconRow:
    return LogosLexiconRow(
        entry_id=entry.entry_id,
        surface=entry.surface,
        lemma=entry.lemma,
        language=entry.language,
        part_of_speech=entry.part_of_speech,
        pos=entry.pos,
        morphology_id=entry.morphology_id,
        morphology_tags=list(entry.morphology_tags),
        semantic_domains=list(entry.semantic_domains),
        provenance_ids=list(entry.provenance_ids),
        epistemic_status=entry.epistemic_status,
    )


def _entry_ids_by_lemma(rows: list[LogosLexiconRow]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in rows:
        out.setdefault(row.lemma, []).append(row.entry_id)
    return {lemma: sorted(ids) for lemma, ids in sorted(out.items())}


def _gloss_rows(
    pack_dir: Path, entry_ids_by_lemma: dict[str, list[str]]
) -> list[LogosGlossRow]:
    rows: list[LogosGlossRow] = []
    for line_no, payload in _read_jsonl_records(pack_dir / "glosses.jsonl"):
        lemma = str(payload.get("lemma") or "")
        gloss = str(payload.get("gloss") or "")
        pos = _optional_str(payload.get("pos"))
        gloss_id = hashlib.sha256(
            f"{pack_dir.name}|{line_no}|{lemma}|{pos or ''}|{gloss}".encode("utf-8")
        ).hexdigest()[:16]
        rows.append(
            LogosGlossRow(
                gloss_id=gloss_id,
                lemma=lemma,
                gloss=gloss,
                pos=pos,
                entry_ids=entry_ids_by_lemma.get(lemma, []),
                provenance_ids=_string_list(payload.get("provenance_ids")),
                epistemic_status=_optional_str(
                    payload.get("epistemic_status", payload.get("status"))
                ),
                raw=dict(payload),
            )
        )
    return rows


def _morphology_row(entry: MorphologyEntry) -> LogosMorphologyRow:
    return LogosMorphologyRow(
        morphology_id=entry.morphology_id,
        surface=entry.surface,
        lemma=entry.lemma,
        language=entry.language,
        root=entry.root,
        prefix_chain=list(entry.prefix_chain),
        stem=entry.stem,
        inflection={str(k): str(v) for k, v in entry.inflection.items()},
        suffix_chain=list(entry.suffix_chain),
    )


def _edge_id(edge: AlignmentEdge) -> str:
    return hashlib.sha256(
        f"{edge.source_id}|{edge.target_id}|{edge.relation}".encode("utf-8")
    ).hexdigest()[:16]


def _entry_id_index(root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for lexicon_path in sorted(root.glob("*/lexicon.jsonl")):
        for _, payload in _read_jsonl_records(lexicon_path):
            entry_id = payload.get("entry_id")
            if isinstance(entry_id, str) and entry_id:
                index[entry_id] = lexicon_path.parent.name
    return index


def _alignment_row(
    edge: AlignmentEdge, target_index: dict[str, str]
) -> LogosAlignmentRow:
    target_pack_id = target_index.get(edge.target_id)
    target_resolved = target_pack_id is not None
    # A target is valid iff it resolves to a real declared lexicon entry in some
    # pack (collapse anchors like ``en-collapse-love`` are declared entries in
    # ``en_collapse_anchors_v1``).  An ``en-collapse-*`` target that is declared
    # nowhere is a genuine dangling reference and is reported as such — no
    # relation/prefix carve-out, so the safety reader cannot silently pass an
    # undeclared anchor.
    return LogosAlignmentRow(
        edge_id=_edge_id(edge),
        source_id=edge.source_id,
        target_id=edge.target_id,
        relation=edge.relation,
        weight=edge.weight,
        evidence_ids=list(edge.evidence_ids),
        target_pack_id=target_pack_id,
        target_resolved=target_resolved,
        invalid_target=not target_resolved,
    )


def _checksum_status(
    pack_id: str, pack_dir: Path, root: Path
) -> tuple[SafetyVerdict, list[str]]:
    manifest = _read_json_object(pack_dir / "manifest.json")
    errors: list[str] = []
    lexicon_path = pack_dir / "lexicon.jsonl"
    declared = manifest.get("checksum")
    if not isinstance(declared, str) or not declared:
        errors.append("manifest.checksum:missing")
    elif not lexicon_path.is_file():
        errors.append("lexicon.jsonl:missing")
    else:
        actual = _sha256_hex(lexicon_path)
        if actual != declared:
            errors.append(f"lexicon_checksum:mismatch:{actual}!={declared}")

    for filename, key in (
        ("glosses.jsonl", "glosses_checksum"),
        ("frames.jsonl", "frame_checksum"),
        ("compositions.jsonl", "composition_checksum"),
    ):
        expected = manifest.get(key)
        if expected is None:
            continue
        path = pack_dir / filename
        if not path.is_file():
            errors.append(f"{filename}:missing_for:{key}")
            continue
        actual = _sha256_hex(path)
        if actual != expected:
            errors.append(f"{key}:mismatch:{actual}!={expected}")

    if not errors and root == LANGUAGE_PACK_ROOT.resolve():
        try:
            from language_packs.compiler import load_pack

            load_pack(pack_id)
        except ValueError as exc:
            errors.append(f"compiler:{exc}")
    return (SafetyVerdict.FAILED, errors) if errors else (SafetyVerdict.CLEAR, [])


def _domain_contract_status(pack_id: str, root: Path) -> dict[str, Any]:
    from language_packs.domain_contract import validate_domain_contract_pack

    return validate_domain_contract_pack(pack_id, data_root=root).as_dict()

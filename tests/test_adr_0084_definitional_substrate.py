"""ADR-0084 — substrate tests.

Covers the schema parser, primitives-pack loader, and closure-rule
verifier introduced as the code-side substrate for ADR-0084.  The
content (primitives.jsonl + extended glosses.jsonl) lives on a parallel
PR and is exercised by ``scripts/verify_definitional_closure.py``;
this file pins the *substrate* contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from language_packs.definitions import (
    ClosureViolation,
    DefinitionalSchemaError,
    GlossEntry,
    clear_definitions_cache,
    load_pack_glosses,
    parse_gloss_entry,
    verify_definitional_closure,
)
from packs.primitives.loader import (
    PrimitivesPackError,
    clear_primitives_cache,
    load_primitives_pack,
)


# --------------------------------------------------------------------------- #
# Strict-mode gloss parser
# --------------------------------------------------------------------------- #


def _valid_strict_payload() -> dict:
    return {
        "lemma": "analogy",
        "gloss": "a mapping of relations shared between distinct domains",
        "pos": "NOUN",
        "definitional_atoms": ["mapping", "relation", "shared", "distinct", "domain"],
        "predicates_invited": ["reveals", "illustrates", "maps"],
        "definition_version": 1,
        "provenance_ids": ["seed:glosses_v1", "adr-0084:reviewed:2026-05-20"],
    }


class TestStrictParser:
    def test_valid_payload_parses(self) -> None:
        entry = parse_gloss_entry(_valid_strict_payload(), strict=True)
        assert isinstance(entry, GlossEntry)
        assert entry.lemma == "analogy"
        assert entry.definition_version == 1
        assert entry.predicates_invited == ("reveals", "illustrates", "maps")
        assert entry.provenance_ids[-1] == "adr-0084:reviewed:2026-05-20"

    @pytest.mark.parametrize(
        "missing_key",
        [
            "lemma",
            "gloss",
            "definitional_atoms",
            "predicates_invited",
            "definition_version",
            "provenance_ids",
        ],
    )
    def test_missing_required_key_rejected(self, missing_key: str) -> None:
        payload = _valid_strict_payload()
        del payload[missing_key]
        with pytest.raises(DefinitionalSchemaError, match=r"missing required key"):
            parse_gloss_entry(payload, strict=True)

    def test_unknown_key_rejected(self) -> None:
        payload = _valid_strict_payload()
        payload["unexpected"] = True
        with pytest.raises(DefinitionalSchemaError, match=r"unrecognised key"):
            parse_gloss_entry(payload, strict=True)

    def test_empty_predicates_invited_accepted(self) -> None:
        # Migration aid — ADR-0084 explicitly permits empty
        # predicates_invited so packs can adopt the schema before
        # committing to predicate constraints (ADR-0086 territory).
        payload = _valid_strict_payload()
        payload["predicates_invited"] = []
        entry = parse_gloss_entry(payload, strict=True)
        assert entry.predicates_invited == ()

    def test_empty_definitional_atoms_rejected(self) -> None:
        payload = _valid_strict_payload()
        payload["definitional_atoms"] = []
        with pytest.raises(DefinitionalSchemaError, match=r"non-empty 'definitional_atoms'"):
            parse_gloss_entry(payload, strict=True)

    @pytest.mark.parametrize("bad_version", [0, -1, "1", 1.0, True])
    def test_invalid_definition_version_rejected(self, bad_version: object) -> None:
        payload = _valid_strict_payload()
        payload["definition_version"] = bad_version
        with pytest.raises(DefinitionalSchemaError, match=r"definition_version"):
            parse_gloss_entry(payload, strict=True)

    def test_non_string_definitional_atom_rejected(self) -> None:
        payload = _valid_strict_payload()
        payload["definitional_atoms"] = ["mapping", 42]
        with pytest.raises(DefinitionalSchemaError):
            parse_gloss_entry(payload, strict=True)


# --------------------------------------------------------------------------- #
# Lax / back-compat parser
# --------------------------------------------------------------------------- #


class TestLaxParser:
    def test_legacy_two_field_entry_parses(self) -> None:
        entry = parse_gloss_entry(
            {"lemma": "analogy", "gloss": "a mapping of relations"},
            strict=False,
        )
        assert entry.lemma == "analogy"
        assert entry.definitional_atoms == ()
        assert entry.predicates_invited == ()
        assert entry.definition_version == 0

    def test_lax_silently_drops_malformed_extras(self) -> None:
        entry = parse_gloss_entry(
            {
                "lemma": "analogy",
                "gloss": "a mapping",
                "definitional_atoms": "not-a-list",
                "definition_version": "not-an-int",
            },
            strict=False,
        )
        assert entry.definitional_atoms == ()
        assert entry.definition_version == 0


# --------------------------------------------------------------------------- #
# load_pack_glosses on a fixture pack written to a temp dir
# --------------------------------------------------------------------------- #


def _write_temp_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    glosses_lines: list[str],
    pack_id: str = "fixture_pack_v1",
) -> str:
    """Create a fake pack in tmp_path and point _PACK_ROOT at it."""
    from language_packs import definitions as _def

    pack_dir = tmp_path / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "glosses.jsonl").write_text("\n".join(glosses_lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(_def, "_PACK_ROOT", tmp_path)
    clear_definitions_cache()
    return pack_id


class TestLoadPackGlosses:
    def test_missing_glosses_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from language_packs import definitions as _def

        monkeypatch.setattr(_def, "_PACK_ROOT", tmp_path)
        clear_definitions_cache()
        assert load_pack_glosses("nonexistent_pack", strict=True) == ()

    def test_strict_load_raises_on_bad_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = json.dumps({"lemma": "x", "gloss": "y"})
        pack_id = _write_temp_pack(tmp_path, monkeypatch, glosses_lines=[bad])
        with pytest.raises(DefinitionalSchemaError):
            load_pack_glosses(pack_id, strict=True)

    def test_lax_load_skips_bad_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        good = json.dumps({"lemma": "x", "gloss": "y"})
        bad = "{ not json"
        pack_id = _write_temp_pack(tmp_path, monkeypatch, glosses_lines=[good, bad])
        entries = load_pack_glosses(pack_id, strict=False)
        assert len(entries) == 1
        assert entries[0].lemma == "x"

    def test_strict_load_raises_on_malformed_json_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(tmp_path, monkeypatch, glosses_lines=["{ not json"])
        with pytest.raises(DefinitionalSchemaError, match=r"malformed JSON"):
            load_pack_glosses(pack_id, strict=True)


# --------------------------------------------------------------------------- #
# Closure-rule verifier
# --------------------------------------------------------------------------- #


def _strict_line(lemma: str, atoms: list[str]) -> str:
    return json.dumps(
        {
            "lemma": lemma,
            "gloss": "fixture gloss for " + lemma,
            "definitional_atoms": atoms,
            "predicates_invited": [],
            "definition_version": 1,
            "provenance_ids": ["test:fixture"],
        }
    )


class TestClosureVerifier:
    def test_same_pack_reference_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(
            tmp_path,
            monkeypatch,
            glosses_lines=[
                _strict_line("alpha", ["beta"]),
                _strict_line("beta", ["alpha"]),
            ],
        )
        violations = verify_definitional_closure(
            pack_id, mounted_pack_lemmas=(), primitive_lemmas=(), strict=True
        )
        assert violations == ()

    def test_primitive_reference_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(
            tmp_path, monkeypatch, glosses_lines=[_strict_line("alpha", ["exist", "be"])]
        )
        violations = verify_definitional_closure(
            pack_id,
            mounted_pack_lemmas=(),
            primitive_lemmas=("exist", "be"),
            strict=True,
        )
        assert violations == ()

    def test_mounted_pack_reference_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(
            tmp_path, monkeypatch, glosses_lines=[_strict_line("alpha", ["foreign_lemma"])]
        )
        violations = verify_definitional_closure(
            pack_id,
            mounted_pack_lemmas=("foreign_lemma",),
            primitive_lemmas=(),
            strict=True,
        )
        assert violations == ()

    def test_unresolved_token_surfaces_violation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(
            tmp_path, monkeypatch, glosses_lines=[_strict_line("alpha", ["unknown_word"])]
        )
        violations = verify_definitional_closure(
            pack_id, mounted_pack_lemmas=(), primitive_lemmas=(), strict=True
        )
        assert len(violations) == 1
        assert violations[0] == ClosureViolation(
            pack_id=pack_id, lemma="alpha", unresolved_token="unknown_word"
        )

    def test_case_insensitive_resolution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_temp_pack(
            tmp_path, monkeypatch, glosses_lines=[_strict_line("alpha", ["EXIST"])]
        )
        violations = verify_definitional_closure(
            pack_id, mounted_pack_lemmas=(), primitive_lemmas=("exist",), strict=True
        )
        assert violations == ()


# --------------------------------------------------------------------------- #
# Primitives-pack loader
# --------------------------------------------------------------------------- #


def _write_primitives_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    manifest_overrides: dict | None = None,
    primitives_lines: list[str] | None = None,
    pack_id: str = "fixture_primitives_v1",
) -> str:
    from packs.primitives import loader as _loader

    pack_dir = tmp_path / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    if primitives_lines is None:
        primitives_lines = [
            json.dumps(
                {
                    "lemma": "exist",
                    "category": "existence",
                    "pos": "VERB",
                    "primitive_version": 1,
                    "provenance_ids": ["test:fixture"],
                }
            ),
            json.dumps(
                {
                    "lemma": "be",
                    "category": "existence",
                    "pos": "VERB",
                    "primitive_version": 1,
                    "provenance_ids": ["test:fixture"],
                }
            ),
        ]
    primitives_path = pack_dir / "primitives.jsonl"
    body = ("\n".join(primitives_lines) + "\n").encode("utf-8")
    primitives_path.write_bytes(body)
    checksum = hashlib.sha256(body).hexdigest()

    manifest = {
        "pack_id": pack_id,
        "language": "en",
        "kind": "primitives",
        "definitional_layer": True,
        "version": 1,
        "issued_at": "2026-05-20T00:00:00Z",
        "checksum": checksum,
        "primitive_count": len(primitives_lines),
        "never_auto_mutable": True,
        "provenance": "test:fixture",
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (pack_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(_loader, "_PACK_ROOT", tmp_path)
    clear_primitives_cache()
    return pack_id


class TestPrimitivesLoader:
    def test_valid_pack_loads(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(tmp_path, monkeypatch)
        pack = load_primitives_pack(pack_id)
        assert pack.pack_id == pack_id
        assert pack.lemmas == frozenset({"exist", "be"})

    def test_checksum_mismatch_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, manifest_overrides={"checksum": "0" * 64}
        )
        with pytest.raises(PrimitivesPackError, match=r"checksum mismatch"):
            load_primitives_pack(pack_id)

    def test_wrong_kind_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, manifest_overrides={"kind": "lexicon"}
        )
        with pytest.raises(PrimitivesPackError, match=r"kind must be 'primitives'"):
            load_primitives_pack(pack_id)

    def test_definitional_layer_must_be_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, manifest_overrides={"definitional_layer": False}
        )
        with pytest.raises(PrimitivesPackError, match=r"definitional_layer: true"):
            load_primitives_pack(pack_id)

    def test_never_auto_mutable_must_be_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, manifest_overrides={"never_auto_mutable": False}
        )
        with pytest.raises(PrimitivesPackError, match=r"never_auto_mutable: true"):
            load_primitives_pack(pack_id)

    def test_primitive_count_mismatch_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, manifest_overrides={"primitive_count": 99}
        )
        with pytest.raises(PrimitivesPackError, match=r"primitive_count"):
            load_primitives_pack(pack_id)

    def test_duplicate_lemma_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dup_line = json.dumps(
            {
                "lemma": "exist",
                "category": "existence",
                "primitive_version": 1,
                "provenance_ids": ["test:fixture"],
            }
        )
        pack_id = _write_primitives_pack(
            tmp_path, monkeypatch, primitives_lines=[dup_line, dup_line]
        )
        with pytest.raises(PrimitivesPackError, match=r"more than once"):
            load_primitives_pack(pack_id)

    def test_path_traversal_pack_id_rejected(self) -> None:
        with pytest.raises(PrimitivesPackError, match=r"forbidden path token"):
            load_primitives_pack("../escape")

    def test_unknown_key_in_primitive_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad_line = json.dumps(
            {
                "lemma": "exist",
                "category": "existence",
                "primitive_version": 1,
                "provenance_ids": ["test:fixture"],
                "rogue_field": True,
            }
        )
        pack_id = _write_primitives_pack(tmp_path, monkeypatch, primitives_lines=[bad_line])
        with pytest.raises(PrimitivesPackError, match=r"unrecognised key"):
            load_primitives_pack(pack_id)


# --------------------------------------------------------------------------- #
# Manifest field — definitional_layer propagates from manifest.json
# --------------------------------------------------------------------------- #


class TestManifestField:
    def test_default_is_false(self) -> None:
        from language_packs.schema import LanguagePackManifest, LanguageRole

        manifest = LanguagePackManifest(
            pack_id="x",
            language="en",
            role=LanguageRole.OPERATIONAL_BASE,
            script="Latin",
            normalization_policy="unitize_versor",
            source_manifest="x.jsonl",
            determinism_class="D0",
            checksum="0" * 64,
        )
        assert manifest.definitional_layer is False

    def test_non_opted_packs_default_false(self) -> None:
        # Packs that haven't flipped the ADR-0084 flag in their manifest
        # MUST still ratify with definitional_layer=False — the substrate
        # is opt-in per pack and must not silently flip any pack on.
        # The 9 core packs + 4 relations packs + collapse-anchors opted
        # in via PR #65; the non-English cognition packs and en_minimal
        # remain non-opted at the time of writing.
        from language_packs.compiler import load_pack

        for pack_id in (
            "en_minimal_v1",
            "he_core_cognition_v1",
            "grc_logos_cognition_v1",
        ):
            manifest, _ = load_pack(pack_id)
            assert manifest.definitional_layer is False, (
                f"{pack_id} unexpectedly opted into definitional_layer"
            )

    def test_opted_packs_carry_flag(self) -> None:
        # Conversely: packs that DID flip the flag (via PR #65) must
        # surface it through the manifest loader.  This proves the
        # substrate's loader propagation works against real ratified
        # content, not just fixture packs.
        from language_packs.compiler import load_pack

        for pack_id in ("en_core_cognition_v1", "en_core_relations_v1"):
            manifest, _ = load_pack(pack_id)
            assert manifest.definitional_layer is True, (
                f"{pack_id} declares definitional_layer:true in its manifest "
                f"but loader did not propagate it"
            )

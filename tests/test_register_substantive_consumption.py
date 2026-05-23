"""ADR-0077 (R6) — per-knob unit + end-to-end coverage of
``chat/register_substantive.py``.

Two test families:

* Pure-unit tests against synthetic canonical surfaces — assert each
  knob is the deterministic string transform documented in the ADR,
  with no dependency on the runtime.
* End-to-end tests run a real ChatRuntime under each ratified
  register and assert the user-facing surface matches the post-
  substantive expectation.

C1 (ADR-0075) preservation: every R6 knob combination must produce a
surface that the realizer guard accepts.  This module pins that
contract by running the guard against every produced surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import pytest

from chat.register_substantive import apply_substantive_register
from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from generate.realizer_guard import check_surface
from packs.register.loader import RegisterPack, load_register_pack


# ---------- Fake register for synthetic unit coverage ----------


@dataclass(frozen=True)
class _FakeMarkers:
    openings: tuple[str, ...] = ()
    transitions: tuple[str, ...] = ()
    closings: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return True


@dataclass(frozen=True)
class _FakeRegister:
    """Minimal duck-type that ``apply_substantive_register`` accepts.

    Only ``realizer_overrides`` is read in the substantive path.
    """

    realizer_overrides: Mapping[str, object] = field(default_factory=dict)
    discourse_markers: _FakeMarkers = field(default_factory=_FakeMarkers)


def _r(overrides: Mapping[str, object]) -> _FakeRegister:
    return _FakeRegister(realizer_overrides=dict(overrides))


_DEF_CANONICAL = (
    "Light is a visible medium that reveals truth. "
    "pack-grounded (en_core_cognition_v1)."
)
_DEF_CANONICAL_LENS = (
    "Light is a visible medium that reveals truth. "
    "pack-grounded (en_core_cognition_v1) [lens(grc_logos_v1):systematic]."
)
_CMP_CANONICAL = (
    "light (cognition.illumination; logos.core) contrasts with "
    "truth (cognition.truth; logos.core) — pack-grounded "
    "(en_core_cognition_v1). No session evidence yet."
)
_DOT_CANONICAL = (
    "light — pack-grounded (en_core_cognition_v1): "
    "cognition.illumination; logos.core; cognition.knowledge. "
    "No session evidence yet."
)


# ---------- No-op contract ----------


def test_empty_overrides_is_byte_identical():
    """The default register (empty overrides) must be a no-op."""
    out = apply_substantive_register(_DEF_CANONICAL, _r({}))
    assert out == _DEF_CANONICAL


def test_all_knobs_false_is_byte_identical():
    """Explicit False values must also be a no-op — the ``.get(key)``
    lookup returns ``False`` which is falsy."""
    out = apply_substantive_register(
        _DEF_CANONICAL,
        _r({
            "drop_provenance_tag": False,
            "compress_gloss": False,
            "drop_articles": False,
            "append_semantic_domain_clause": False,
        }),
    )
    assert out == _DEF_CANONICAL


def test_empty_canonical_is_byte_identical():
    out = apply_substantive_register("", _r({"drop_provenance_tag": True}))
    assert out == ""


# ---------- drop_provenance_tag ----------


def test_drop_provenance_strips_trailing_gloss_clause():
    out = apply_substantive_register(
        _DEF_CANONICAL, _r({"drop_provenance_tag": True}),
    )
    assert "pack-grounded" not in out
    assert out.endswith("reveals truth.")
    assert "..," not in out and ".." not in out  # no double-period bug


def test_drop_provenance_preserves_lens_annotation():
    out = apply_substantive_register(
        _DEF_CANONICAL_LENS, _r({"drop_provenance_tag": True}),
    )
    assert "pack-grounded" not in out
    assert "[lens(grc_logos_v1):systematic]" in out


def test_drop_provenance_strips_infix_em_dash_form():
    out = apply_substantive_register(
        _CMP_CANONICAL, _r({"drop_provenance_tag": True}),
    )
    assert "pack-grounded" not in out
    # Em-dash before the provenance is consumed by the infix regex.
    assert " — pack-grounded" not in out
    assert "contrasts with truth" in out
    assert "No session evidence yet" in out


def test_drop_provenance_strips_dotted_disclosure_form():
    out = apply_substantive_register(
        _DOT_CANONICAL, _r({"drop_provenance_tag": True}),
    )
    assert "pack-grounded" not in out
    assert out.startswith("light:")  # em-dash + provenance gone; colon kept


# ---------- compress_gloss ----------


def test_compress_gloss_replaces_is_a():
    out = apply_substantive_register(
        "Light is a source of revelation.", _r({"compress_gloss": True}),
    )
    assert out == "Light: source of revelation."


def test_compress_gloss_replaces_is_an():
    out = apply_substantive_register(
        "Answer is an example of speech.", _r({"compress_gloss": True}),
    )
    assert out == "Answer: example of speech."


def test_compress_gloss_replaces_is_the():
    out = apply_substantive_register(
        "Beginning is the origin point.", _r({"compress_gloss": True}),
    )
    assert out == "Beginning: origin point."


def test_compress_gloss_replaces_bare_is():
    out = apply_substantive_register(
        "Cause is that which produces effect.",
        _r({"compress_gloss": True}),
    )
    assert out == "Cause: that which produces effect."


def test_compress_gloss_only_first_occurrence():
    """Multiple ``is`` tokens must not all collapse — only the gloss
    opener.  Mangling a subordinate clause's ``is`` would be a bug."""
    out = apply_substantive_register(
        "X is a Y. The reason is clear.", _r({"compress_gloss": True}),
    )
    assert out == "X: Y. The reason is clear."


def test_compress_gloss_noop_on_comparison():
    """COMPARISON form has no ``is`` — must be byte-identical."""
    out = apply_substantive_register(
        _CMP_CANONICAL, _r({"compress_gloss": True}),
    )
    assert out == _CMP_CANONICAL


# ---------- drop_articles ----------


def test_drop_articles_strips_mid_sentence_a():
    out = apply_substantive_register(
        "Light reveals a truth in this case.", _r({"drop_articles": True}),
    )
    assert out == "Light reveals truth in this case."


def test_drop_articles_strips_mid_sentence_the():
    out = apply_substantive_register(
        "Light reveals the truth.", _r({"drop_articles": True}),
    )
    assert out == "Light reveals truth."


def test_drop_articles_preserves_article_after_not():
    """C1 R3 safety: must not collapse ``is not a claim`` to ``is not
    claim`` because R3 fires when a be-negation is followed by a VERB.
    ``claim`` is a NOUN so R3 wouldn't fire anyway, but the lookbehind
    guards us against a more dangerous case in the future."""
    out = apply_substantive_register(
        "Light is not a claim.", _r({"drop_articles": True}),
    )
    assert out == "Light is not a claim."


def test_drop_articles_collapses_double_space_artifact():
    """Adjacent removals must not leave a double space in the output."""
    out = apply_substantive_register(
        "Walks the path of a sage.", _r({"drop_articles": True}),
    )
    assert "  " not in out
    assert out == "Walks path of sage."


# ---------- append_semantic_domain_clause ----------


def test_append_picks_lex_first_unused_atom():
    out = apply_substantive_register(
        "Light is the source.",
        _r({"append_semantic_domain_clause": True}),
        semantic_domains=("logos.core", "cognition.illumination"),
    )
    # Sorted atoms: ("cognition.illumination", "logos.core").
    # Both are absent from canonical, so the first lex-sorted wins.
    assert out.endswith(" Related: cognition.illumination.")


def test_append_skips_atom_already_in_canonical():
    out = apply_substantive_register(
        "Light is a source in cognition.illumination.",
        _r({"append_semantic_domain_clause": True}),
        semantic_domains=("cognition.illumination", "logos.core"),
    )
    assert out.endswith(" Related: logos.core.")


def test_append_noop_when_all_atoms_already_used():
    canonical = "Light: covers logos.core cognition.illumination."
    out = apply_substantive_register(
        canonical,
        _r({"append_semantic_domain_clause": True}),
        semantic_domains=("cognition.illumination", "logos.core"),
    )
    assert out == canonical


def test_append_noop_when_no_atoms_supplied():
    out = apply_substantive_register(
        _DEF_CANONICAL,
        _r({"append_semantic_domain_clause": True}),
        semantic_domains=(),
    )
    assert out == _DEF_CANONICAL


# ---------- Knob composition (terse_v1 combined) ----------


def test_terse_full_combo_def_form():
    """compress_gloss + drop_provenance_tag + drop_articles together
    on the canonical DEFINITION form."""
    out = apply_substantive_register(
        _DEF_CANONICAL,
        _r({
            "compress_gloss": True,
            "drop_provenance_tag": True,
            "drop_articles": True,
        }),
    )
    # compress: "Light is a visible medium ... truth." -> "Light: visible medium ... truth."
    # drop_articles: removes leftover "a/the" articles.
    # drop_provenance_tag: trailing pack-grounded clause removed.
    assert out == "Light: visible medium that reveals truth."


def test_terse_full_combo_with_lens():
    """Lens annotation must survive the terse combo."""
    out = apply_substantive_register(
        _DEF_CANONICAL_LENS,
        _r({
            "compress_gloss": True,
            "drop_provenance_tag": True,
            "drop_articles": True,
        }),
    )
    assert "[lens(grc_logos_v1):systematic]" in out
    assert "pack-grounded" not in out


# ---------- Guard safety (C1 preservation) ----------


def _trivial_pos_lookup(_token: str) -> None:
    """Pack-less POS lookup — returns None for every token.  The C1
    guard then fails-open on every unknown token, which is what we
    want for synthetic unit assertions.
    """
    return None


@pytest.mark.parametrize("knobs", [
    {"compress_gloss": True},
    {"drop_provenance_tag": True},
    {"drop_articles": True},
    {"append_semantic_domain_clause": True},
    {
        "compress_gloss": True,
        "drop_provenance_tag": True,
        "drop_articles": True,
    },
])
def test_every_knob_combination_passes_guard(knobs):
    """invariant_realizer_no_illegal_articulation preservation —
    no R6 knob combination produces a surface that trips R2/R3."""
    domains = ("cognition.illumination", "logos.core")
    for canonical in (_DEF_CANONICAL, _DEF_CANONICAL_LENS, _CMP_CANONICAL, _DOT_CANONICAL):
        out = apply_substantive_register(
            canonical, _r(knobs), semantic_domains=domains,
        )
        v = check_surface(out, pos_lookup=_trivial_pos_lookup)
        assert v.status == "ok", (
            f"knobs={knobs} produced guard-rejected surface "
            f"{out!r} from canonical {canonical!r}: {v}"
        )


# ---------- End-to-end against real packs + runtime ----------


@pytest.fixture(scope="module")
def neutral_def_surface() -> str:
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id="default_neutral_v1"))
    pipe = CognitiveTurnPipeline(runtime=rt)
    pipe.run("What is light?")
    return rt.turn_log[-1].surface


def test_e2e_terse_drops_provenance_tag():
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id="terse_v1"))
    pipe = CognitiveTurnPipeline(runtime=rt)
    pipe.run("What is light?")
    te = rt.turn_log[-1]
    assert "pack-grounded" not in te.surface
    assert te.register_canonical_surface != ""
    assert "pack-grounded" in te.register_canonical_surface


def test_e2e_terse_compresses_gloss():
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id="terse_v1"))
    pipe = CognitiveTurnPipeline(runtime=rt)
    pipe.run("What is light?")
    te = rt.turn_log[-1]
    assert "Light: " in te.surface
    # Gloss compression strips " is a "; raw " is a " must NOT survive
    # in the user-facing surface under terse.
    assert " is a " not in te.surface


def test_e2e_terse_drops_articles():
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id="terse_v1"))
    pipe = CognitiveTurnPipeline(runtime=rt)
    pipe.run("What is light?")
    te = rt.turn_log[-1]
    # Should not contain standalone mid-sentence articles in the
    # compressed surface.  ``" a "`` and ``" the "`` are mid-sentence
    # markers we expect to be absent in the compressed gloss.
    assert " a " not in te.surface
    assert " the " not in te.surface


def test_e2e_convivial_appends_related_clause(neutral_def_surface: str):
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id="convivial_v1"))
    pipe = CognitiveTurnPipeline(runtime=rt)
    pipe.run("What is light?")
    te = rt.turn_log[-1]
    assert "Related: " in te.surface
    # The Related clause must be derived from a pack atom — atoms in
    # the cognition pack are dotted ``domain.subdomain`` form (e.g.
    # ``cognition.illumination``, ``logos.core``).  Match a dotted
    # atom inside the Related clause specifically.
    import re
    m = re.search(r"Related: ([\w]+\.[\w.]+)\.", te.surface)
    assert m is not None, f"no dotted atom in Related clause: {te.surface!r}"
    assert "." in m.group(1)


def test_e2e_neutral_unchanged_by_r6(neutral_def_surface: str):
    """default_neutral_v1 has no R6 knobs → surface must be identical
    to the pre-R6 byte-for-byte expected gloss."""
    expected = (
        "Light is a visible medium that reveals truth. "
        "pack-grounded (en_core_cognition_v1)."
    )
    assert neutral_def_surface == expected


# ---------- Pack-loaded knob schema ----------


@pytest.mark.parametrize("register_id,expected_keys", [
    ("default_neutral_v1", set()),
    (
        "terse_v1",
        {"compress_gloss", "disclosure_domain_count", "drop_articles",
         "drop_provenance_tag"},
    ),
    ("convivial_v1", {"append_semantic_domain_clause"}),
])
def test_register_pack_carries_expected_r6_keys(
    register_id: str, expected_keys: set[str],
):
    """Pin the on-disk pack contents so future re-ratification can't
    silently drop the R6 knobs."""
    pack = load_register_pack(register_id)
    actual_keys = set(pack.realizer_overrides.keys())
    assert actual_keys == expected_keys

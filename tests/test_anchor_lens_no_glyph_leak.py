"""anchor_lens_no_glyph_leak — hard substrate-glyph gate (ADR-0073c).

ADR-0073's substrate commitment: anchor lens renders English compound
phrasing at the user surface, never raw non-English **substrate
glyphs** (Greek / Hebrew / Coptic / Aramaic letters).  This test pins
that as a falsifiable invariant — a single substrate-block character
in ``ChatResponse.surface`` under any lens fails the lane.

Stylistic punctuation such as em-dash (U+2014) is permitted; it
pre-dates L1.3 and is unrelated to the substrate-leak risk this
invariant protects against.  The forbidden zones are:

  - U+0370..U+03FF  Greek and Coptic
  - U+1F00..U+1FFF  Greek Extended
  - U+0590..U+05FF  Hebrew
  - U+0700..U+074F  Syriac (forward-looking)
  - U+0600..U+06FF  Arabic (forward-looking)

Scope: every cognition lane case × {unanchored, default_unanchored_v1,
grc_logos_v1, he_logos_v1}.  Forbidden block leaks fail immediately.
"""

from __future__ import annotations

import pytest

from core.config import RuntimeConfig
from evals.run_cognition_eval import load_cases, run_eval


_LENS_IDS_TO_TEST = (
    None,
    "default_unanchored_v1",
    "grc_logos_v1",
    "he_logos_v1",
)

#: Forbidden Unicode blocks: substrate letter scripts that anchor lens
#: must not leak.  Each tuple is ``(start_codepoint, end_codepoint,
#: block_label)``.  Inclusive on both ends.
_FORBIDDEN_BLOCKS: tuple[tuple[int, int, str], ...] = (
    (0x0370, 0x03FF, "Greek and Coptic"),
    (0x1F00, 0x1FFF, "Greek Extended"),
    (0x0590, 0x05FF, "Hebrew"),
    (0x0700, 0x074F, "Syriac"),
    (0x0600, 0x06FF, "Arabic"),
)


def _substrate_glyph_violations(surface: str) -> list[tuple[int, str, str]]:
    """Return ``[(pos, char, block_label), ...]`` for every substrate
    glyph in *surface*.  Empty list means clean."""
    out: list[tuple[int, str, str]] = []
    for i, ch in enumerate(surface):
        cp = ord(ch)
        for start, end, label in _FORBIDDEN_BLOCKS:
            if start <= cp <= end:
                out.append((i, ch, label))
                break
    return out


@pytest.fixture(scope="module")
def cases():
    return load_cases()


@pytest.mark.parametrize("lens_id", _LENS_IDS_TO_TEST)
def test_cognition_lane_surfaces_free_of_substrate_glyphs(cases, lens_id):
    report = run_eval(cases, config=RuntimeConfig(anchor_lens_id=lens_id))
    leaks: list[str] = []
    for case in report.cases:
        if not case.surface:
            continue
        violations = _substrate_glyph_violations(case.surface)
        if violations:
            for pos, ch, block in violations:
                leaks.append(
                    f"  case={case.case_id} "
                    f"substrate_glyph={ch!r} (block={block}) at pos {pos} "
                    f"surface={case.surface!r}"
                )
    assert not leaks, (
        f"anchor_lens_no_glyph_leak violated under lens={lens_id!r}.\n"
        "ChatResponse.surface MUST NOT contain substrate-script glyphs "
        "(Greek / Hebrew / etc.) regardless of loaded lens "
        "(ADR-0073 surface contract).  Offending cases:\n"
        + "\n".join(leaks)
    )


def test_lens_annotation_is_ascii_directly():
    """Independent of the cognition lane: the lens metadata itself
    (lens_id, cognitive_mode_label) must be pure ASCII so the
    annotation can never carry non-ASCII even if a future composer
    forgets to ASCII-check before emit."""
    from packs.anchor_lens import load_anchor_lens

    for lens_id in ("default_unanchored_v1", "grc_logos_v1", "he_logos_v1"):
        lens = load_anchor_lens(lens_id)
        lens.lens_id.encode("ascii")
        lens.cognitive_mode_label.encode("ascii")
        for atom in lens.semantic_domain_preferences:
            atom.encode("ascii")

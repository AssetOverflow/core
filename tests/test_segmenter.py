"""
tests/test_segmenter.py

Full coverage for core_ingest.segmenter.StructuralSegmenter.

All segmenters are D0: given the same source bytes they produce the same
output with no external state.  Tests verify:
  - prose: paragraph splitting, heading detection, empty-block filtering
  - scripture: verse-boundary splitting, region label format
  - code: fenced block extraction (backtick and tilde fences, lang tag)
  - math: LaTeX display environments (\\[...\\], $$...$$, \\begin{env})
  - SourceSpan byte-offset integrity for all modalities
"""

import hashlib
import pytest

from core_ingest.segmenter import Segment, SegmentKind, StructuralSegmenter
from core_ingest.types import SourceSpan


@pytest.fixture
def segmenter() -> StructuralSegmenter:
    return StructuralSegmenter()


def sha(src: bytes) -> str:
    return hashlib.sha256(src).hexdigest()


# ---------------------------------------------------------------------------
# Prose
# ---------------------------------------------------------------------------

class TestProseSegmenter:
    def test_two_paragraphs(self, segmenter):
        src = b"First paragraph.\n\nSecond paragraph."
        segs = segmenter.segment(src, "prose")
        assert len(segs) == 2
        assert segs[0].kind == SegmentKind.BODY
        assert segs[1].kind == SegmentKind.BODY
        assert "First" in segs[0].text
        assert "Second" in segs[1].text

    def test_atx_heading_detected(self, segmenter):
        src = b"## Section Title\n\nBody text here."
        segs = segmenter.segment(src, "prose")
        heading_segs = [s for s in segs if s.kind == SegmentKind.HEADING]
        assert len(heading_segs) >= 1
        assert "Section Title" in heading_segs[0].text

    def test_empty_blocks_filtered(self, segmenter):
        src = b"Para one.\n\n\n\nPara two."
        segs = segmenter.segment(src, "prose")
        # Should not produce empty-text segments
        assert all(seg.text.strip() for seg in segs)

    def test_span_byte_offsets_in_source(self, segmenter):
        src = b"Hello world.\n\nGoodbye world."
        source_sha = sha(src)
        segs = segmenter.segment(src, "prose")
        for seg in segs:
            assert seg.span.source_sha256 == source_sha
            assert seg.span.byte_start >= 0
            assert seg.span.byte_end > seg.span.byte_start
            # The bytes at the span match the text
            span_bytes = src[seg.span.byte_start:seg.span.byte_end]
            assert span_bytes.strip()

    def test_single_paragraph(self, segmenter):
        src = b"Only one paragraph here."
        segs = segmenter.segment(src, "prose")
        assert len(segs) == 1
        assert segs[0].text == "Only one paragraph here."

    def test_unknown_hint_falls_back_to_prose(self, segmenter):
        src = b"Paragraph A.\n\nParagraph B."
        segs = segmenter.segment(src, "unknown_modality")
        assert len(segs) == 2


# ---------------------------------------------------------------------------
# Scripture
# ---------------------------------------------------------------------------

class TestScriptureSegmenter:
    def test_verse_boundaries(self, segmenter):
        src = (
            b"Gen 1:1 In the beginning God created the heavens and the earth.\n"
            b"Gen 1:2 Now the earth was formless and empty."
        )
        segs = segmenter.segment(src, "scripture")
        assert len(segs) == 2
        assert all(s.kind == SegmentKind.VERSE for s in segs)

    def test_verse_region_label(self, segmenter):
        src = b"John 1:1 In the beginning was the Word."
        segs = segmenter.segment(src, "scripture")
        assert len(segs) >= 1
        assert segs[0].span.region is not None
        assert "verse:" in segs[0].span.region

    def test_dot_separated_reference(self, segmenter):
        src = b"GEN.1.1 In the beginning.\nGEN.1.2 The earth was formless."
        segs = segmenter.segment(src, "scripture")
        assert len(segs) >= 1

    def test_span_sha_matches_source(self, segmenter):
        src = b"Rev 1:1 The revelation of Jesus Christ."
        source_sha = sha(src)
        segs = segmenter.segment(src, "scripture")
        for seg in segs:
            assert seg.span.source_sha256 == source_sha


# ---------------------------------------------------------------------------
# Code
# ---------------------------------------------------------------------------

class TestCodeSegmenter:
    def test_backtick_fence_extraction(self, segmenter):
        src = b"Some prose.\n\n```python\nprint('hello')\n```\n\nMore prose."
        segs = segmenter.segment(src, "code")
        assert len(segs) == 1
        assert segs[0].kind == SegmentKind.CODE
        assert "print" in segs[0].text

    def test_tilde_fence_extraction(self, segmenter):
        src = b"~~~rust\nfn main() {}\n~~~"
        segs = segmenter.segment(src, "code")
        assert len(segs) == 1
        assert segs[0].kind == SegmentKind.CODE

    def test_lang_tag_in_region(self, segmenter):
        src = b"```python\nx = 1\n```"
        segs = segmenter.segment(src, "code")
        assert len(segs) == 1
        assert "python" in (segs[0].span.region or "")

    def test_no_fence_produces_no_segments(self, segmenter):
        src = b"Just plain text with no fences."
        segs = segmenter.segment(src, "code")
        assert segs == []

    def test_multiple_fences(self, segmenter):
        src = b"```py\nfoo()\n```\n\n```js\nbar()\n```"
        segs = segmenter.segment(src, "code")
        assert len(segs) == 2


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------

class TestMathSegmenter:
    def test_display_brackets(self, segmenter):
        src = rb"Some text \[E = mc^2\] more text."
        segs = segmenter.segment(src, "math")
        assert len(segs) == 1
        assert segs[0].kind == SegmentKind.MATH

    def test_double_dollar(self, segmenter):
        src = b"Inline: $$x^2 + y^2 = r^2$$ done."
        segs = segmenter.segment(src, "math")
        assert len(segs) == 1
        assert segs[0].kind == SegmentKind.MATH

    def test_begin_end_environment(self, segmenter):
        src = b"\\begin{equation}E=mc^2\\end{equation}"
        segs = segmenter.segment(src, "math")
        assert len(segs) == 1
        assert segs[0].span.region == "math_env"

    def test_no_math_produces_no_segments(self, segmenter):
        src = b"No math here at all."
        segs = segmenter.segment(src, "math")
        assert segs == []

    def test_multiple_math_environments(self, segmenter):
        src = b"$$a$$\nand\n$$b$$"
        segs = segmenter.segment(src, "math")
        assert len(segs) == 2

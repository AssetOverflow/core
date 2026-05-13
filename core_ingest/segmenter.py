"""
StructuralSegmenter — D0 form-boundary segmentation.

Carves source documents at deterministic structural signals:
  prose      — blank-line paragraph breaks, ATX/Setext headings
  scripture  — verse markers (canonical chapter:verse format)
  code       — fenced code blocks (``` or ~~~)
  math       — LaTeX display environments (\\[...\\], $$...$$, \\begin{...})

The segmenter operates on the *form* of the source, not its content.
It does NOT interpret meaning. Meaning stays inside the versor field.

All segmenters produce SourceSpan objects with a determinism class of D0:
fully deterministic given the same source bytes, no external state.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

from core_ingest.types import SourceSpan


class SegmentKind(str, Enum):
    """Structural role of a segment within its source document."""
    HEADING   = "heading"
    BODY      = "body"
    VERSE     = "verse"
    CODE      = "code"
    MATH      = "math"
    UNKNOWN   = "unknown"


@dataclass(frozen=True, slots=True)
class Segment:
    """
    A single structural unit extracted from a source document.

    span     — SourceSpan with byte offsets and source SHA-256
    kind     — structural role of this segment
    text     — decoded surface text of the segment
    """
    span: SourceSpan
    kind: SegmentKind
    text: str


class StructuralSegmenter:
    """
    Entry point for D0 structural segmentation.

    Usage
    -----
    segmenter = StructuralSegmenter()
    for segment in segmenter.segment(source_bytes, modality_hint="prose"):
        ...

    modality_hint selects the sub-segmenter:
      "prose"     — blank-line paragraph + heading detection
      "scripture" — verse-marker based (chapter:verse or book.chapter.verse)
      "code"      — fenced code block extraction
      "math"      — LaTeX display math extraction
    """

    _SEGMENTERS = {
        "prose":     "_segment_prose",
        "scripture": "_segment_scripture",
        "code":      "_segment_code",
        "math":      "_segment_math",
    }

    def segment(
        self,
        source: bytes,
        modality_hint: str = "prose",
    ) -> list[Segment]:
        """
        Segment `source` according to `modality_hint`.

        Parameters
        ----------
        source        : Raw source bytes (UTF-8 expected).
        modality_hint : One of 'prose', 'scripture', 'code', 'math'.

        Returns
        -------
        List of Segment objects in document order.
        """
        source_sha = hashlib.sha256(source).hexdigest()
        method_name = self._SEGMENTERS.get(modality_hint, "_segment_prose")
        method = getattr(self, method_name)
        return list(method(source, source_sha))

    # ------------------------------------------------------------------
    # Prose segmenter
    # ------------------------------------------------------------------

    _HEADING_RE = re.compile(
        rb"^(?P<hashes>#{1,6})\s+(?P<text>.+)$|^(?P<text2>.+)\n[=\-]{2,}$",
        re.MULTILINE,
    )

    def _segment_prose(self, source: bytes, source_sha: str) -> Iterator[Segment]:
        """
        Split on blank lines. Classify leading ATX/Setext headings.
        Each non-empty block becomes one Segment.
        """
        # Split on one or more blank lines
        blocks = re.split(rb"\n{2,}", source)
        offset = 0
        for block in blocks:
            block = block.strip()
            if not block:
                offset += len(block) + 2  # account for separator
                continue
            start = source.find(block, offset)
            end   = start + len(block)
            text  = block.decode("utf-8", errors="replace")

            # Heading detection
            kind = SegmentKind.BODY
            if self._HEADING_RE.match(block):
                kind = SegmentKind.HEADING

            yield Segment(
                span=SourceSpan(
                    byte_start=start,
                    byte_end=end,
                    source_sha256=source_sha,
                    region=kind.value,
                ),
                kind=kind,
                text=text,
            )
            offset = end

    # ------------------------------------------------------------------
    # Scripture segmenter
    # ------------------------------------------------------------------

    # Matches: GEN.1.1, Gen 1:1, 1 Cor 13:4, etc.
    _VERSE_RE = re.compile(
        rb"(?:(?:[1-3]\s)?[A-Za-z]+\.?\s*\d{1,3}[:.\s]\d{1,3})",
        re.MULTILINE,
    )

    def _segment_scripture(
        self, source: bytes, source_sha: str
    ) -> Iterator[Segment]:
        """
        Split scripture source at verse boundaries.
        Each verse becomes one Segment with region='verse:<ref>'.
        """
        matches = list(self._VERSE_RE.finditer(source))
        for i, match in enumerate(matches):
            start = match.start()
            end   = matches[i + 1].start() if i + 1 < len(matches) else len(source)
            block = source[start:end].strip()
            if not block:
                continue
            ref = match.group(0).decode("utf-8", errors="replace").strip()
            yield Segment(
                span=SourceSpan(
                    byte_start=start,
                    byte_end=start + len(block),
                    source_sha256=source_sha,
                    region=f"verse:{ref}",
                ),
                kind=SegmentKind.VERSE,
                text=block.decode("utf-8", errors="replace"),
            )

    # ------------------------------------------------------------------
    # Code segmenter
    # ------------------------------------------------------------------

    _FENCE_RE = re.compile(
        rb"^(?P<fence>`{3,}|~{3,})(?P<lang>[^\n]*)\n(?P<body>.*?)^(?P=fence)\s*$",
        re.MULTILINE | re.DOTALL,
    )

    def _segment_code(self, source: bytes, source_sha: str) -> Iterator[Segment]:
        """Extract fenced code blocks (``` or ~~~)."""
        for match in self._FENCE_RE.finditer(source):
            start = match.start()
            end   = match.end()
            body  = match.group("body")
            lang  = match.group("lang").decode("utf-8", errors="replace").strip()
            region = f"code_block:{lang}" if lang else "code_block"
            yield Segment(
                span=SourceSpan(
                    byte_start=start,
                    byte_end=end,
                    source_sha256=source_sha,
                    region=region,
                ),
                kind=SegmentKind.CODE,
                text=body.decode("utf-8", errors="replace"),
            )

    # ------------------------------------------------------------------
    # Math segmenter
    # ------------------------------------------------------------------

    _MATH_RE = re.compile(
        rb"\\\[.*?\\\]|\$\$.*?\$\$|\\begin\{[^}]+\}.*?\\end\{[^}]+\}",
        re.DOTALL,
    )

    def _segment_math(self, source: bytes, source_sha: str) -> Iterator[Segment]:
        """Extract LaTeX display math environments."""
        for match in self._MATH_RE.finditer(source):
            start = match.start()
            end   = match.end()
            yield Segment(
                span=SourceSpan(
                    byte_start=start,
                    byte_end=end,
                    source_sha256=source_sha,
                    region="math_env",
                ),
                kind=SegmentKind.MATH,
                text=match.group(0).decode("utf-8", errors="replace"),
            )

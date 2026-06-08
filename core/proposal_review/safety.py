"""Safety dry-check over the proposal sink (RPT-c) — the load-bearing part of the reporter.

The reporter's value is not just visibility; it is **independent safety verification**. The
dry-check confirms — without trusting the emitter — that every artifact in the sink is inert:

```text
status == "proposal_only"
mounted == false
requires_review == true
content-address consistent: filename == sha256(failure_family : problem_text_sha256)
path under the sink
no malformed artifact (an unverifiable file in a safety-critical sink is a violation)
serving never imports/reads the sink
```

Any failure is a violation; the CLI exits non-zero. **Pure read** — verifies, never repairs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from core.proposal_review.model import MalformedArtifact, PendingProposal
from core.proposal_review.scan import DEFAULT_SINK

#: Serving-path roots that must never read the proposal sink (CLAUDE.md forbidden/serving sites).
_SERVING_TARGETS = (
    ("generate", "stream.py"),
    ("field", "propagate.py"),
    ("vault", "store.py"),
    ("generate", "derivation"),
    ("core", "reliability_gate"),
)
_SINK_MARKER = "comprehension_failures"


@dataclass(frozen=True, slots=True)
class SafetyVerdict:
    """The outcome of the dry-check: ``ok`` iff there are no violations."""

    ok: bool
    violations: tuple[str, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _serving_references_sink(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for parts in _SERVING_TARGETS:
        target = repo_root.joinpath(*parts)
        if not target.exists():
            continue
        files = [target] if target.is_file() else sorted(target.rglob("*.py"))
        for f in files:
            try:
                if _SINK_MARKER in f.read_text(encoding="utf-8"):
                    violations.append(f"serving reads the sink: {f.relative_to(repo_root)}")
            except (UnicodeDecodeError, OSError):  # pragma: no cover - defensive
                continue
    return violations


def dry_check(
    proposals: list[PendingProposal],
    malformed: list[MalformedArtifact],
    *,
    root: Path | None = None,
    repo_root: Path | None = None,
) -> SafetyVerdict:
    """Verify every artifact is inert and the sink is serving-unconsumed. Returns a SafetyVerdict."""
    base = (root if root is not None else DEFAULT_SINK).resolve()
    violations: list[str] = []

    for p in proposals:
        tag = p.content_hash
        if p.status != "proposal_only":
            violations.append(f"{tag}: status={p.status!r} (must be 'proposal_only')")
        if p.mounted:
            violations.append(f"{tag}: mounted=True (must be False)")
        if not p.requires_review:
            violations.append(f"{tag}: requires_review=False (must be True)")
        expected = hashlib.sha256(
            f"{p.failure_family}:{p.problem_text_sha256}".encode("utf-8")
        ).hexdigest()
        if p.content_hash != expected:
            violations.append(f"{tag}: content-address mismatch (expected {expected})")
        if not str(Path(p.path).resolve()).startswith(str(base)):
            violations.append(f"{tag}: path outside the sink")

    for m in malformed:
        violations.append(f"malformed (unverifiable): {m.path} — {m.reason}")

    violations.extend(_serving_references_sink(repo_root if repo_root is not None else _repo_root()))

    return SafetyVerdict(not violations, tuple(violations))


__all__ = ["SafetyVerdict", "dry_check"]

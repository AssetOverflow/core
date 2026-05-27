"""ADR-0167 W2-B — Deterministic claim-signature normalisation for LexicalClaim.

Produces a stable sha256 hex that collapses two GSM8K cases refusing on the
same lexical token into one teaching-corpus candidate.  Only ``sub_type ==
"lexical"`` evidence gets a non-empty signature in this PR; all other sub_types
are deferred to a follow-up ADR.

Normalisation pipeline (applied in order, documented here as a breaking-change
surface — modifying these rules changes all existing signatures):

    1. Lowercase the ``surface`` string.
    2. Strip leading and trailing characters that are members of the fixed
       punctuation set ``string.punctuation``:
       ``!"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~``
       This set is frozen; expansions are breaking changes.
    3. Extract the unknown-token from ``refusal_detail`` via the canonical
       regex  r"no primitive or lexicon match for '([^']+)'"
    4. If the regex does not match (e.g. fraction/percentage detail format),
       use the stripped-lowercase ``surface`` from step 2 as the token.
    5. Canonical string: ``"lexical:" + extracted_token``
    6. sha256 hex of canonical string encoded as UTF-8.

Returns a 64-character lowercase hex string.  Pure function.  Deterministic
across machines (sha256 of well-defined UTF-8 bytes).
"""

from __future__ import annotations

import hashlib
import re
import string

# Frozen punctuation set — documented as breaking-change surface.
_PUNCT_SET: str = string.punctuation  # !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

# Canonical regex matching lexicon-entry refusal details.
_LEXICON_DETAIL_RE: re.Pattern[str] = re.compile(
    r"no primitive or lexicon match for '([^']+)'"
)


def lexical_claim_signature(
    *,
    surface: str,
    refusal_detail: str,
) -> str:
    """Deterministic sha256 hex of a normalised lexical claim.

    See module docstring for the full normalisation pipeline.

    Parameters
    ----------
    surface:
        The raw token surface form (e.g. ``"crayons,"``).
    refusal_detail:
        The ``AuditRow.refusal_detail`` string verbatim.

    Returns
    -------
    str
        64-character lowercase hex.
    """
    # Step 1 — lowercase
    lowered = surface.lower()
    # Step 2 — strip punctuation set members from both ends
    stripped = lowered.strip(_PUNCT_SET)
    # Step 3 — attempt canonical extraction from refusal_detail
    match = _LEXICON_DETAIL_RE.search(refusal_detail)
    # Step 4 — fallback to stripped surface if regex doesn't match
    token = match.group(1) if match else stripped
    # Step 5 — canonical string
    canonical = "lexical:" + token
    # Step 6 — sha256 hex
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["lexical_claim_signature"]

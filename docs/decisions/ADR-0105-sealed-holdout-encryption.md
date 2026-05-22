# ADR-0105 — Sealed Holdout Encryption via age

Status: Accepted (2026-05-22)

## Context

Eval holdouts exist to measure generalization beyond public and development
splits. Plaintext holdouts inside the repository violate the intended trust
boundary because:

- case content is inspectable by contributors and automation,
- eval leakage becomes irreversible once committed,
- downstream tooling can accidentally consume holdout content.

Prior ADRs established SHA-pinned eval provenance and curriculum ratification,
but the holdout layer remained scaffolded.

## Decision

CORE adopts recipient-based `age` encryption for sealed holdouts.

Implementation requirements:

1. Holdouts are committed as `*.age` ciphertext files.
2. Decryption identities are supplied via `CORE_HOLDOUT_KEY`.
3. If an identity is explicitly supplied, decryption failures are fail-closed.
4. Plaintext fallback is permitted only for local development when no key is
   configured.
5. Decrypted content must remain memory-only and never be written back into the
   repository working tree.
6. Holdout sealing uses recipient-only encryption via `pyrage`.

## Consequences

Positive:

- reduces accidental eval leakage,
- preserves aggregate-only scoring semantics,
- allows public repository structure without exposing hidden eval content,
- keeps holdout management deterministic and scriptable.

Negative:

- contributors now require explicit identities for sealed evaluation,
- CI workflows must manage holdout identities securely,
- local plaintext workflows become transitional-only.

## Acceptance Gates

- `tests/test_holdout_encryption.py` passes.
- `scripts/seal_holdouts.py --dry-run` discovers seal targets correctly.
- Wrong identities fail closed.
- Dev fallback works only when no key is configured.
- Existing holdouts are resealed as `.age` artifacts.

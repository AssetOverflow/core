"""Object-store adapter seam for edge/cloud sync.

This module defines the transport boundary only.  It has no concrete S3
implementation and imports no vendor SDK.  Hot-path CORE modules must not import
this module; sync orchestration may depend on this protocol later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ObjectStoreError(RuntimeError):
    """Base error for object-store adapter failures."""


class ObjectNotFoundError(ObjectStoreError):
    """Raised when a requested object key does not exist."""


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Minimal metadata returned by object-store adapters."""

    key: str
    size_bytes: int
    content_type: str | None = None
    etag: str | None = None


@runtime_checkable
class ObjectStore(Protocol):
    """Protocol implemented by concrete object-store adapters.

    Implementations must map provider-specific exceptions into typed CORE sync
    errors.  Implementations must not be used by active cognition hot paths.
    """

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        """Store bytes at a key and return metadata."""

    def get_bytes(self, key: str) -> bytes:
        """Return bytes for a key or raise ObjectNotFoundError."""

    def exists(self, key: str) -> bool:
        """Return True if a key exists."""

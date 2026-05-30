"""Optional S3-compatible object-store adapter.

This module is intentionally outside CORE hot paths.  It imports boto3 lazily
inside the adapter constructor so importing core.sync remains safe on systems
without S3 dependencies installed.
"""

from __future__ import annotations

from typing import Any

from core.sync.object_store import ObjectMetadata, ObjectNotFoundError, ObjectStoreError


class S3ObjectStore:
    """ObjectStore implementation backed by an S3-compatible bucket."""

    def __init__(
        self,
        *,
        bucket: str,
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("bucket is required")
        self.bucket = bucket
        if client is not None:
            self._client = client
            return
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ObjectStoreError("boto3 is not installed; install optional S3 dependencies") from exc
        kwargs: dict[str, str] = {}
        if endpoint_url is not None:
            kwargs["endpoint_url"] = endpoint_url
        if region_name is not None:
            kwargs["region_name"] = region_name
        self._client = boto3.client("s3", **kwargs)

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        if not key:
            raise ValueError("key is required")
        try:
            response = self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except Exception as exc:  # noqa: BLE001 - provider SDK exceptions vary
            raise ObjectStoreError(f"put_object failed for key {key!r}: {exc}") from exc
        return ObjectMetadata(
            key=key,
            size_bytes=len(data),
            content_type=content_type,
            etag=_clean_etag(response.get("ETag")) if isinstance(response, dict) else None,
        )

    def get_bytes(self, key: str) -> bytes:
        if not key:
            raise ValueError("key is required")
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read()
        except Exception as exc:  # noqa: BLE001 - provider SDK exceptions vary
            if _looks_not_found(exc):
                raise ObjectNotFoundError(f"object not found: {key}") from exc
            raise ObjectStoreError(f"get_object failed for key {key!r}: {exc}") from exc
        if not isinstance(body, bytes):
            raise ObjectStoreError(f"get_object returned non-bytes body for key {key!r}")
        return body

    def exists(self, key: str) -> bool:
        if not key:
            raise ValueError("key is required")
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:  # noqa: BLE001 - provider SDK exceptions vary
            if _looks_not_found(exc):
                return False
            raise ObjectStoreError(f"head_object failed for key {key!r}: {exc}") from exc


def _clean_etag(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip('"')


def _looks_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            code = str(error.get("Code", ""))
            return code in {"NoSuchKey", "404", "NotFound"}
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    return "nosuchkey" in name or "not found" in text or "404" in text

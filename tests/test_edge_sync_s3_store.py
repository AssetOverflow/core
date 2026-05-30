from __future__ import annotations

import io
import sys

import pytest

from core.sync.object_store import ObjectNotFoundError, ObjectStoreError
from core.sync.s3_store import S3ObjectStore


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> dict:
        self.objects[(Bucket, Key)] = (Body, ContentType)
        return {"ETag": '"fake-etag"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        try:
            data, _ = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeNoSuchKey("not found") from exc
        return {"Body": io.BytesIO(data)}

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        if (Bucket, Key) not in self.objects:
            raise FakeNoSuchKey("not found")
        return {}


class FakeNoSuchKey(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


def test_s3_adapter_uses_injected_client_without_boto3() -> None:
    client = FakeS3Client()
    store = S3ObjectStore(bucket="bucket", client=client)

    meta = store.put_bytes("key", b"payload", content_type="application/octet-stream")

    assert meta.key == "key"
    assert meta.size_bytes == len(b"payload")
    assert meta.content_type == "application/octet-stream"
    assert meta.etag == "fake-etag"
    assert store.exists("key")
    assert store.get_bytes("key") == b"payload"


def test_s3_adapter_reports_missing_objects() -> None:
    store = S3ObjectStore(bucket="bucket", client=FakeS3Client())

    assert not store.exists("missing")
    with pytest.raises(ObjectNotFoundError):
        store.get_bytes("missing")


def test_s3_adapter_requires_bucket() -> None:
    with pytest.raises(ValueError, match="bucket is required"):
        S3ObjectStore(bucket="", client=FakeS3Client())


def test_s3_adapter_requires_key() -> None:
    store = S3ObjectStore(bucket="bucket", client=FakeS3Client())

    with pytest.raises(ValueError, match="key is required"):
        store.put_bytes("", b"payload", content_type="application/octet-stream")
    with pytest.raises(ValueError, match="key is required"):
        store.get_bytes("")
    with pytest.raises(ValueError, match="key is required"):
        store.exists("")


def test_s3_adapter_lazy_imports_boto3_only_when_constructed_without_client(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "boto3", None)

    with pytest.raises(ObjectStoreError, match="boto3 is not installed"):
        S3ObjectStore(bucket="bucket")

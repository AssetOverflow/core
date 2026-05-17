"""Tests for ``formation.cache`` — path-traversal-safe content-addressed cache."""

from __future__ import annotations

import pytest

from formation.cache import CacheKeyError, FormationCache, default_cache


@pytest.fixture
def cache(tmp_path):
    return FormationCache(tmp_path / ".formation_cache")


_VALID_SHA = "0" * 64
_OTHER_SHA = "a" * 64


class TestKeySanitization:
    @pytest.mark.parametrize("bad_subject", [
        "../escape",
        "/abs/path",
        "bad/slash",
        "bad space",
        "bad\\backslash",
        "bad\x00null",
        ".dotleading",
        "..",
        "",
    ])
    def test_subject_id_rejected(self, cache, bad_subject) -> None:
        with pytest.raises(CacheKeyError):
            cache.path_for(bad_subject, "ore", _VALID_SHA)

    def test_stage_must_be_allowlisted(self, cache) -> None:
        with pytest.raises(CacheKeyError, match="invalid stage"):
            cache.path_for("subject.x", "arbitrary", _VALID_SHA)

    @pytest.mark.parametrize("bad_sha", [
        "tooshort",
        "Z" * 64,            # uppercase / non-hex
        "0" * 63,             # short
        "0" * 65,             # long
        "../../bad",
        "",
    ])
    def test_input_sha_rejected(self, cache, bad_sha) -> None:
        with pytest.raises(CacheKeyError, match="invalid input_sha"):
            cache.path_for("subject.x", "ore", bad_sha)

    def test_valid_key_resolves_under_root(self, cache) -> None:
        path = cache.path_for("subject.x", "ore", _VALID_SHA)
        assert str(path).startswith(str(cache.root) + "/")
        assert path.suffix == ".json"


class TestPutGet:
    def test_put_then_get_round_trips(self, cache) -> None:
        payload = {"hello": "world", "n": 42}
        cache.put("subject.x", "ore", _VALID_SHA, payload)
        assert cache.has("subject.x", "ore", _VALID_SHA)
        assert cache.get("subject.x", "ore", _VALID_SHA) == payload

    def test_miss_returns_none(self, cache) -> None:
        assert cache.get("subject.x", "ore", _VALID_SHA) is None
        assert cache.has("subject.x", "ore", _VALID_SHA) is False

    def test_different_sha_isolated(self, cache) -> None:
        cache.put("subject.x", "ore", _VALID_SHA, {"v": 1})
        cache.put("subject.x", "ore", _OTHER_SHA, {"v": 2})
        assert cache.get("subject.x", "ore", _VALID_SHA) == {"v": 1}
        assert cache.get("subject.x", "ore", _OTHER_SHA) == {"v": 2}

    def test_written_bytes_are_canonical(self, cache) -> None:
        cache.put("subject.x", "ore", _VALID_SHA, {"b": 1, "a": 2})
        path = cache.path_for("subject.x", "ore", _VALID_SHA)
        assert path.read_bytes() == b'{"a":2,"b":1}'

    def test_put_floats_rejected(self, cache) -> None:
        with pytest.raises(TypeError):
            cache.put("subject.x", "ore", _VALID_SHA, {"v": 1.5})


class TestDefaultCache:
    def test_default_cache_relative_to_cwd(self, tmp_path) -> None:
        cache = default_cache(tmp_path)
        assert cache.root == (tmp_path / ".formation_cache").resolve()

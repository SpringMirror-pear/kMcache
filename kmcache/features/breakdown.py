"""Helpers related to cache breakdown and hot-key protection."""

from __future__ import annotations

from kmcache.models import CacheEnvelope


def is_hot_key_expired(envelope: CacheEnvelope) -> bool:
    """Return whether a cache entry is considered expired for hot-key logic."""

    return envelope.is_hard_expired()

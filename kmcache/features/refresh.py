"""Helpers for soft TTL refresh decisions."""

from __future__ import annotations

from kmcache.models import CacheEnvelope


def should_return_stale(envelope: CacheEnvelope, enable_stale: bool) -> bool:
    """判断是否应返回陈旧数据并触发后台刷新。

    参数:
        envelope: 当前缓存包装对象。
        enable_stale: 是否启用 stale 返回策略。

    返回:
        bool: 可返回 stale 数据时返回 True，否则返回 False。
    """

    if not enable_stale:
        return False
    return envelope.is_soft_expired() and not envelope.is_hard_expired()

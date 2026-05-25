"""Shared data models for cache records, policies, and warmup tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from kmcache.utils.time import utc_timestamp

CURRENT_CACHE_ENVELOPE_VERSION = 2
LEGACY_CACHE_ENVELOPE_VERSION = 1

Loader = Callable[[], Awaitable[Any] | Any]
LoaderFallback = Callable[[Exception], Awaitable[Any] | Any] | Any


@dataclass(slots=True)
class CacheEnvelope:
    """带过期元数据的缓存包装对象。"""

    value: Any
    created_at: float
    soft_expire_at: float | None
    hard_expire_at: float | None
    is_null: bool = False
    version: int = CURRENT_CACHE_ENVELOPE_VERSION

    def is_soft_expired(self, now: float | None = None) -> bool:
        """判断是否达到软过期时间。

        参数:
            now: 当前时间戳，未传入时自动使用当前 UTC 时间戳。

        返回:
            bool: 如果已达到 soft_ttl 返回 True，否则返回 False。
        """

        if self.soft_expire_at is None:
            return False
        current = utc_timestamp() if now is None else now
        return current >= self.soft_expire_at

    def is_hard_expired(self, now: float | None = None) -> bool:
        """判断是否达到硬过期时间。

        参数:
            now: 当前时间戳，未传入时自动使用当前 UTC 时间戳。

        返回:
            bool: 如果已达到 hard_ttl 返回 True，否则返回 False。
        """

        if self.hard_expire_at is None:
            return False
        current = utc_timestamp() if now is None else now
        return current >= self.hard_expire_at

    def remaining_ttl(self, now: float | None = None) -> int | None:
        """返回剩余硬过期 TTL 秒数。

        参数:
            now: 当前时间戳，未传入时自动使用当前 UTC 时间戳。

        返回:
            int | None: 剩余秒数；若未设置硬过期时间则返回 None。
        """

        if self.hard_expire_at is None:
            return None
        current = utc_timestamp() if now is None else now
        remaining = int(self.hard_expire_at - current)
        return max(remaining, 0)

    def resolve_value(self) -> Any | None:
        """解析对外可见的缓存值。

        参数:
            无。

        返回:
            Any | None: 普通缓存返回原始值，空值缓存返回 None。
        """

        if self.is_null:
            return None
        return self.value


@dataclass(slots=True)
class CachePolicy:
    """缓存读写与回源控制策略。"""

    ttl: int | None = None
    soft_ttl: int | None = None
    null_ttl: int | None = None
    ttl_jitter: int | None = None
    enable_stale: bool | None = None
    loader_timeout: float | None = None
    refresh_timeout: float | None = None

    def __post_init__(self) -> None:
        """初始化后校验缓存策略。"""

        for field_name in ("ttl", "soft_ttl", "null_ttl"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                msg = f"policy.{field_name} must be greater than 0"
                raise ValueError(msg)
        if self.ttl_jitter is not None and self.ttl_jitter < 0:
            msg = "policy.ttl_jitter must be greater than or equal to 0"
            raise ValueError(msg)
        for field_name in ("loader_timeout", "refresh_timeout"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                msg = f"policy.{field_name} must be greater than 0"
                raise ValueError(msg)


@dataclass(slots=True)
class WarmupItem:
    """声明式缓存预热项定义。"""

    key: str
    loader: Loader
    ttl: int
    soft_ttl: int | None = None

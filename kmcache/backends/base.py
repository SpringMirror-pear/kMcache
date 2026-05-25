"""Backend abstraction for cache storage layers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from kmcache.models import CacheEnvelope


class BaseCacheBackend(ABC):
    """缓存后端抽象接口。"""

    name: str

    @abstractmethod
    async def get(self, key: str) -> CacheEnvelope | None:
        """读取缓存数据。

        参数:
            key: 要读取的缓存 Key。

        返回:
            CacheEnvelope | None: 命中时返回缓存包装对象，未命中返回 None。
        """

    @abstractmethod
    async def set(self, key: str, value: CacheEnvelope, ttl: int | None = None) -> None:
        """写入缓存数据。

        参数:
            key: 要写入的缓存 Key。
            value: 要存储的缓存包装对象。
            ttl: 可选的 TTL 秒数。

        返回:
            None。
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存 Key。

        参数:
            key: 要删除的缓存 Key。

        返回:
            None。
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """判断缓存 Key 是否存在。

        参数:
            key: 要检查的缓存 Key。

        返回:
            bool: 存在返回 True，否则返回 False。
        """

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> None:
        """更新缓存 Key 的过期时间。

        参数:
            key: 要更新的缓存 Key。
            ttl: 新的 TTL 秒数。

        返回:
            None。
        """

    @abstractmethod
    async def clear(self) -> None:
        """清空当前后端管理的缓存数据。

        参数:
            无。

        返回:
            None。
        """

    @abstractmethod
    async def close(self) -> None:
        """释放后端资源。

        参数:
            无。

        返回:
            None。
        """


@runtime_checkable
class SupportsStaleRead(Protocol):
    """支持读取硬过期旧值的后端协议。"""

    async def get_stale(self, key: str) -> CacheEnvelope | None:
        """读取缓存并允许返回硬过期值。"""


@runtime_checkable
class SupportsBatchOperations(Protocol):
    """支持批量操作的后端协议。"""

    async def mget(self, keys: list[str]) -> list[CacheEnvelope | None]:
        """批量读取缓存包装对象。"""

    async def mset(self, values: dict[str, CacheEnvelope], ttl: int | None = None) -> None:
        """批量写入缓存包装对象。"""

    async def delete_many(self, keys: list[str]) -> None:
        """批量删除缓存 Key。"""


@runtime_checkable
class SupportsPrefixDelete(Protocol):
    """支持按前缀删除的后端协议。"""

    async def delete_prefix(self, prefix: str) -> None:
        """删除指定前缀下的缓存数据。"""

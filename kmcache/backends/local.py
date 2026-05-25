"""In-memory L1 cache backend."""

from __future__ import annotations

import asyncio
from collections import OrderedDict

from kmcache.backends.base import BaseCacheBackend
from kmcache.config import LocalCacheConfig
from kmcache.models import CacheEnvelope


class LocalCacheBackend(BaseCacheBackend):
    """支持 TTL 与 LRU 淘汰的异步友好本地缓存后端。"""

    def __init__(self, config: LocalCacheConfig | None = None) -> None:
        """初始化本地缓存后端。

        参数:
            config: 本地缓存配置，未传入时使用默认配置。

        返回:
            None。
        """

        self._config = config or LocalCacheConfig()
        self.name = self._config.name
        self._entries: OrderedDict[str, CacheEnvelope] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> CacheEnvelope | None:
        """读取本地缓存数据。

        参数:
            key: 要读取的缓存 Key。

        返回:
            CacheEnvelope | None: 命中时返回缓存包装对象，否则返回 None。
        """

        async with self._lock:
            envelope = self._entries.get(key)
            if envelope is None:
                return None
            if envelope.is_hard_expired():
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return envelope

    async def get_stale(self, key: str) -> CacheEnvelope | None:
        """读取本地缓存数据且允许返回硬过期旧值。

        参数:
            key: 要读取的缓存 Key。

        返回:
            CacheEnvelope | None: 命中时返回缓存包装对象，否则返回 None。
        """

        async with self._lock:
            envelope = self._entries.get(key)
            if envelope is None:
                return None
            self._entries.move_to_end(key)
            return envelope

    async def set(self, key: str, value: CacheEnvelope, ttl: int | None = None) -> None:
        """写入本地缓存数据。

        参数:
            key: 要写入的缓存 Key。
            value: 要存储的缓存包装对象。
            ttl: 可选 TTL，当前实现以包装对象中的过期时间为准。

        返回:
            None。
        """

        del ttl
        async with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            self._evict_if_needed()

    async def mget(self, keys: list[str]) -> list[CacheEnvelope | None]:
        """批量读取本地缓存数据。"""

        results: list[CacheEnvelope | None] = []
        for key in keys:
            results.append(await self.get(key))
        return results

    async def mset(self, values: dict[str, CacheEnvelope], ttl: int | None = None) -> None:
        """批量写入本地缓存数据。"""

        del ttl
        async with self._lock:
            for key, value in values.items():
                self._entries[key] = value
                self._entries.move_to_end(key)
            self._evict_if_needed()

    async def delete(self, key: str) -> None:
        """删除本地缓存 Key。

        参数:
            key: 要删除的缓存 Key。

        返回:
            None。
        """

        async with self._lock:
            self._entries.pop(key, None)

    async def delete_many(self, keys: list[str]) -> None:
        """批量删除本地缓存 Key。"""

        async with self._lock:
            for key in keys:
                self._entries.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        """删除指定前缀下的本地缓存 Key。"""

        async with self._lock:
            keys_to_delete = [key for key in self._entries if key.startswith(prefix)]
            for key in keys_to_delete:
                self._entries.pop(key, None)

    async def exists(self, key: str) -> bool:
        """判断本地缓存 Key 是否存在。

        参数:
            key: 要检查的缓存 Key。

        返回:
            bool: 存在返回 True，否则返回 False。
        """

        return await self.get(key) is not None

    async def expire(self, key: str, ttl: int) -> None:
        """更新本地缓存 Key 的硬过期时间。

        参数:
            key: 要更新的缓存 Key。
            ttl: 新的 TTL 秒数。

        返回:
            None。
        """

        async with self._lock:
            envelope = self._entries.get(key)
            if envelope is None:
                return
            envelope.hard_expire_at = envelope.created_at + ttl
            self._entries.move_to_end(key)

    async def clear(self) -> None:
        """清空本地缓存。

        参数:
            无。

        返回:
            None。
        """

        async with self._lock:
            self._entries.clear()

    async def close(self) -> None:
        """关闭本地缓存后端。

        参数:
            无。

        返回:
            None。
        """

        await self.clear()

    def _evict_if_needed(self) -> None:
        """按最大容量执行 LRU 淘汰。

        参数:
            无。

        返回:
            None。
        """

        while len(self._entries) > self._config.max_size:
            self._entries.popitem(last=False)

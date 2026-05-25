"""本地缓存后端测试。"""

from __future__ import annotations

import asyncio
import unittest

from kmcache.backends.local import LocalCacheBackend
from kmcache.config import LocalCacheConfig
from kmcache.models import CacheEnvelope
from kmcache.utils.time import utc_timestamp


class LocalCacheBackendTests(unittest.IsolatedAsyncioTestCase):
    """本地缓存后端异步测试。"""

    async def test_local_backend_returns_none_for_missing_key(self) -> None:
        """验证不存在的 Key 会返回 None。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        result = await backend.get("missing")
        self.assertIsNone(result)

    async def test_local_backend_removes_expired_key(self) -> None:
        """验证本地缓存会清理已过期数据。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        now = utc_timestamp()
        envelope = CacheEnvelope(
            value="value",
            created_at=now - 5,
            soft_expire_at=None,
            hard_expire_at=now - 1,
        )
        await backend.set("expired", envelope)

        result = await backend.get("expired")

        self.assertIsNone(result)
        self.assertFalse(await backend.exists("expired"))

    async def test_local_backend_evicts_lru_entry_when_capacity_exceeded(self) -> None:
        """验证容量超限时会按 LRU 淘汰。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend(LocalCacheConfig(max_size=2))
        now = utc_timestamp()
        first = CacheEnvelope("first", now, None, now + 60)
        second = CacheEnvelope("second", now, None, now + 60)
        third = CacheEnvelope("third", now, None, now + 60)

        await backend.set("first", first)
        await backend.set("second", second)
        await backend.get("first")
        await backend.set("third", third)

        self.assertIsNone(await backend.get("second"))
        self.assertIsNotNone(await backend.get("first"))
        self.assertIsNotNone(await backend.get("third"))

    async def test_local_backend_updates_expire_time(self) -> None:
        """验证调用 expire 后会更新硬过期时间。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        now = utc_timestamp()
        envelope = CacheEnvelope("value", now, None, now + 60)
        await backend.set("key", envelope)

        await backend.expire("key", 1)
        await asyncio.sleep(1.1)

        self.assertIsNone(await backend.get("key"))

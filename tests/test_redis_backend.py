"""Redis 缓存后端集成测试。"""

from __future__ import annotations

import asyncio
import unittest

from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import BroadcastConfig, CacheConfig, LocalCacheConfig, RedisCacheConfig
from kmcache.manager import CacheManager
from kmcache.models import CacheEnvelope
from kmcache.utils.time import utc_timestamp


class RedisCacheBackendTests(unittest.IsolatedAsyncioTestCase):
    """Redis 缓存后端异步集成测试。"""

    async def asyncSetUp(self) -> None:
        """初始化 Redis 测试后端并清理测试数据。

        参数:
            无。

        返回:
            None。
        """

        self._config = RedisCacheConfig(
            url="redis://127.0.0.1:6379/0",
            key_prefix="kmcache-test",
        )
        self._backend = RedisCacheBackend.from_url(self._config.url, self._config)
        await self._backend.clear()

    async def asyncTearDown(self) -> None:
        """清理 Redis 测试数据并关闭连接。

        参数:
            无。

        返回:
            None。
        """

        await self._backend.clear()
        await self._backend.close()

    async def test_redis_backend_set_and_get_round_trip(self) -> None:
        """验证 Redis 后端可以完成写入和读取闭环。

        参数:
            无。

        返回:
            None。
        """

        now = utc_timestamp()
        envelope = CacheEnvelope("value", now, now + 30, now + 60)

        await self._backend.set("user:1", envelope, ttl=60)
        result = await self._backend.get("user:1")

        self.assertIsNotNone(result)
        self.assertEqual(result.resolve_value(), "value")

    async def test_redis_backend_expire_removes_key(self) -> None:
        """验证 Redis 后端可以更新过期时间并使 Key 过期。

        参数:
            无。

        返回:
            None。
        """

        now = utc_timestamp()
        envelope = CacheEnvelope("value", now, None, now + 60)

        await self._backend.set("user:2", envelope, ttl=60)
        await self._backend.expire("user:2", 1)

        await asyncio.sleep(1.1)
        self.assertIsNone(await self._backend.get("user:2"))

    async def test_redis_backend_clear_removes_prefixed_keys(self) -> None:
        """验证 clear 仅清理当前前缀下的数据。

        参数:
            无。

        返回:
            None。
        """

        now = utc_timestamp()
        envelope = CacheEnvelope("value", now, None, now + 60)

        await self._backend.set("user:3", envelope, ttl=60)
        self.assertTrue(await self._backend.exists("user:3"))

        await self._backend.clear()

        self.assertFalse(await self._backend.exists("user:3"))

    async def test_redis_backend_supports_batch_operations_and_prefix_delete(self) -> None:
        """验证 Redis 后端支持批量读写和按前缀删除。"""

        now = utc_timestamp()
        await self._backend.mset(
            {
                "user:4": CacheEnvelope("alice", now, None, now + 60),
                "user:5": CacheEnvelope("bob", now, None, now + 60),
                "article:1": CacheEnvelope("news", now, None, now + 60),
            },
            ttl=60,
        )

        values = await self._backend.mget(["user:4", "user:5", "missing"])
        self.assertEqual([value.resolve_value() if value is not None else None for value in values], ["alice", "bob", None])

        await self._backend.delete_prefix("user:")

        self.assertFalse(await self._backend.exists("user:4"))
        self.assertFalse(await self._backend.exists("user:5"))
        self.assertTrue(await self._backend.exists("article:1"))

    async def test_redis_broadcast_invalidates_other_instance_local_cache(self) -> None:
        """验证广播事件会使其他实例的本地缓存失效。

        参数:
            无。

        返回:
            None。
        """

        key_prefix = "kmcache-broadcast-test"
        channel = "kmcache:test:broadcast"
        local_one = LocalCacheBackend(LocalCacheConfig(name="l1-a"))
        local_two = LocalCacheBackend(LocalCacheConfig(name="l1-b"))
        redis_one = RedisCacheBackend.from_url(
            "redis://127.0.0.1:6379/0",
            RedisCacheConfig(
                url="redis://127.0.0.1:6379/0",
                key_prefix=key_prefix,
            ),
        )
        redis_two = RedisCacheBackend.from_url(
            "redis://127.0.0.1:6379/0",
            RedisCacheConfig(
                url="redis://127.0.0.1:6379/0",
                key_prefix=key_prefix,
            ),
        )
        manager_one = CacheManager(
            [local_one, redis_one],
            CacheConfig(
                ttl_jitter=0,
                redis=RedisCacheConfig(
                    url="redis://127.0.0.1:6379/0",
                    key_prefix=key_prefix,
                ),
                broadcast=BroadcastConfig(
                    enabled=True,
                    channel=channel,
                    instance_id="instance-a",
                ),
            ),
        )
        manager_two = CacheManager(
            [local_two, redis_two],
            CacheConfig(
                ttl_jitter=0,
                redis=RedisCacheConfig(
                    url="redis://127.0.0.1:6379/0",
                    key_prefix=key_prefix,
                ),
                broadcast=BroadcastConfig(
                    enabled=True,
                    channel=channel,
                    instance_id="instance-b",
                ),
            ),
        )

        await redis_one.clear()
        await manager_one.start()
        await manager_two.start()
        await asyncio.sleep(0.2)

        try:
            now = utc_timestamp()
            await local_two.set(
                "default:user:88",
                CacheEnvelope("old", now, None, now + 60),
            )

            await manager_one.set("user:88", "new", ttl=60)
            await asyncio.sleep(0.2)

            self.assertIsNone(await local_two.get("default:user:88"))
            self.assertEqual(await manager_two.get("user:88"), "new")
        finally:
            await manager_one.close()
            await manager_two.close()

    async def test_distributed_lock_allows_only_one_loader_across_instances(self) -> None:
        """验证多实例并发 miss 时只会有一个实例执行真实回源。

        参数:
            无。

        返回:
            None。
        """

        key_prefix = "kmcache-lock-test"
        local_one = LocalCacheBackend(LocalCacheConfig(name="l1-lock-a"))
        local_two = LocalCacheBackend(LocalCacheConfig(name="l1-lock-b"))
        redis_config = RedisCacheConfig(
            url="redis://127.0.0.1:6379/0",
            key_prefix=key_prefix,
            lock_timeout=2.0,
            lock_sleep_interval=0.05,
        )
        redis_one = RedisCacheBackend.from_url(redis_config.url, redis_config)
        redis_two = RedisCacheBackend.from_url(redis_config.url, redis_config)
        manager_one = CacheManager(
            [local_one, redis_one],
            CacheConfig(
                ttl_jitter=0,
                redis=redis_config,
                broadcast=BroadcastConfig(
                    enabled=False,
                    instance_id="lock-a",
                ),
            ),
        )
        manager_two = CacheManager(
            [local_two, redis_two],
            CacheConfig(
                ttl_jitter=0,
                redis=redis_config,
                broadcast=BroadcastConfig(
                    enabled=False,
                    instance_id="lock-b",
                ),
            ),
        )

        await redis_one.clear()
        loader_calls = 0

        async def loader() -> str:
            nonlocal loader_calls
            loader_calls += 1
            await asyncio.sleep(0.2)
            return "shared"

        try:
            results = await asyncio.gather(
                manager_one.get_or_load("product:1", loader, ttl=30),
                manager_two.get_or_load("product:1", loader, ttl=30),
            )

            self.assertEqual(results, ["shared", "shared"])
            self.assertEqual(loader_calls, 1)
        finally:
            await manager_one.close()
            await manager_two.close()

"""缓存管理器测试。"""

from __future__ import annotations

import asyncio
import unittest

from kmcache.backends.base import BaseCacheBackend
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CircuitBreakerConfig
from kmcache.config import CacheConfig, LocalCacheConfig
from kmcache.exceptions import BackendError
from kmcache.manager import CacheManager
from kmcache.models import CacheEnvelope, CachePolicy
from kmcache.models import WarmupItem
from kmcache.observability.events import InMemoryEventHook
from kmcache.observability.metrics import InMemoryMetricsHook
from kmcache.utils.time import utc_timestamp


class FailingBackend(BaseCacheBackend):
    """用于测试熔断器行为的故障后端。"""

    def __init__(self, name: str = "failing") -> None:
        """初始化故障后端。

        参数:
            name: 后端名称。

        返回:
            None。
        """

        self.name = name
        self.calls = 0

    async def get(self, key: str) -> CacheEnvelope | None:
        """模拟读取失败。

        参数:
            key: 缓存 Key。

        返回:
            CacheEnvelope | None: 永不返回正常值。
        """

        del key
        self.calls += 1
        raise BackendError("backend get failed")

    async def set(self, key: str, value: CacheEnvelope, ttl: int | None = None) -> None:
        """模拟写入失败。

        参数:
            key: 缓存 Key。
            value: 缓存包装对象。
            ttl: TTL 秒数。

        返回:
            None。
        """

        del key, value, ttl
        self.calls += 1
        raise BackendError("backend set failed")

    async def delete(self, key: str) -> None:
        """模拟删除失败。

        参数:
            key: 缓存 Key。

        返回:
            None。
        """

        del key
        self.calls += 1
        raise BackendError("backend delete failed")

    async def exists(self, key: str) -> bool:
        """模拟存在性检查失败。

        参数:
            key: 缓存 Key。

        返回:
            bool: 永不返回正常结果。
        """

        del key
        self.calls += 1
        raise BackendError("backend exists failed")

    async def expire(self, key: str, ttl: int) -> None:
        """模拟过期时间更新失败。

        参数:
            key: 缓存 Key。
            ttl: TTL 秒数。

        返回:
            None。
        """

        del key, ttl
        self.calls += 1
        raise BackendError("backend expire failed")

    async def clear(self) -> None:
        """模拟清理失败。

        参数:
            无。

        返回:
            None。
        """

        self.calls += 1
        raise BackendError("backend clear failed")

    async def close(self) -> None:
        """关闭故障后端。

        参数:
            无。

        返回:
            None。
        """

        return None


class CacheManagerTests(unittest.IsolatedAsyncioTestCase):
    """缓存管理器异步测试。"""

    async def test_cache_manager_get_or_load_uses_singleflight_for_hot_key(self) -> None:
        """验证同一热点 Key 的并发回源只会执行一次。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))
        calls = 0

        async def loader() -> str:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return "value"

        results = await asyncio.gather(
            cache.get_or_load("user:1", loader),
            cache.get_or_load("user:1", loader),
            cache.get_or_load("user:1", loader),
        )

        self.assertEqual(results, ["value", "value", "value"])
        self.assertEqual(calls, 1)

    async def test_cache_manager_backfills_l1_after_second_backend_hit(self) -> None:
        """验证下层命中后会回填上层缓存。

        参数:
            无。

        返回:
            None。
        """

        l1 = LocalCacheBackend(LocalCacheConfig(name="l1"))
        l2 = LocalCacheBackend(LocalCacheConfig(name="l2"))
        cache = CacheManager([l1, l2], CacheConfig(ttl_jitter=0))

        await cache.set("user:2", "alice", ttl=60)
        await l1.delete("default:user:2")

        result = await cache.get("user:2")

        self.assertEqual(result, "alice")
        self.assertIsNotNone(await l1.get("default:user:2"))

    async def test_cache_manager_caches_none_with_null_ttl(self) -> None:
        """验证回源返回 None 时会按空值缓存策略写入缓存。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0, null_ttl=5))
        calls = 0

        async def loader() -> None:
            nonlocal calls
            calls += 1
            return None

        first = await cache.get_or_load("empty", loader)
        second = await cache.get_or_load("empty", loader)

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(calls, 1)

    async def test_cache_manager_warmup_populates_cache(self) -> None:
        """验证预热任务会提前写入缓存。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))
        items = [
            WarmupItem(
                key="article:1",
                loader=lambda: "warm",
                ttl=30,
                soft_ttl=10,
            )
        ]

        await cache.warmup(items)

        self.assertEqual(await cache.get("article:1"), "warm")

    async def test_cache_manager_returns_stale_and_refreshes_in_background(self) -> None:
        """验证软过期时返回旧值并在后台完成刷新。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0, enable_stale=True))
        now = utc_timestamp()
        stale_envelope = CacheEnvelope(
            value="old",
            created_at=now - 20,
            soft_expire_at=now - 1,
            hard_expire_at=now + 30,
        )
        await backend.set("default:profile:1", stale_envelope)
        calls = 0

        async def loader() -> str:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return "new"

        value = await cache.get_or_load("profile:1", loader, ttl=60, soft_ttl=10)
        await asyncio.sleep(0.1)
        refreshed = await cache.get("profile:1")

        self.assertEqual(value, "old")
        self.assertEqual(refreshed, "new")
        self.assertEqual(calls, 1)

    async def test_cache_manager_skips_open_circuit_backend_on_read(self) -> None:
        """验证后端熔断打开后读路径会跳过故障后端。

        参数:
            无。

        返回:
            None。
        """

        failing = FailingBackend()
        local = LocalCacheBackend()
        config = CacheConfig(
            ttl_jitter=0,
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=1,
                recovery_timeout=60.0,
                half_open_max_calls=1,
            ),
        )
        cache = CacheManager([failing, local], config)
        await local.set(
            "default:user:9",
            CacheEnvelope("fallback", utc_timestamp(), None, utc_timestamp() + 60),
        )

        first = await cache.get("user:9")
        second = await cache.get("user:9")

        self.assertEqual(first, "fallback")
        self.assertEqual(second, "fallback")
        self.assertEqual(failing.calls, 1)

    async def test_cache_manager_continues_write_when_one_backend_is_open(self) -> None:
        """验证某个后端熔断后写路径仍可写入其他后端。

        参数:
            无。

        返回:
            None。
        """

        failing = FailingBackend()
        local = LocalCacheBackend()
        config = CacheConfig(
            ttl_jitter=0,
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=1,
                recovery_timeout=60.0,
                half_open_max_calls=1,
            ),
        )
        cache = CacheManager([failing, local], config)

        await cache.set("user:10", "value", ttl=60)
        await cache.set("user:10", "value-2", ttl=60)

        self.assertEqual(await cache.get("user:10"), "value-2")
        self.assertEqual(failing.calls, 1)

    async def test_cache_manager_returns_expired_value_when_loader_fails(self) -> None:
        """验证回源失败时会返回仍可兜底的旧值。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))
        now = utc_timestamp()
        expired_envelope = CacheEnvelope(
            value="fallback",
            created_at=now - 120,
            soft_expire_at=now - 90,
            hard_expire_at=now - 1,
        )
        await backend.set("default:item:1", expired_envelope)

        async def loader() -> str:
            raise RuntimeError("loader failed")

        result = await cache.get_or_load("item:1", loader, ttl=60)

        self.assertEqual(result, "fallback")

    async def test_cache_manager_raises_loader_error_when_no_cached_value_exists(self) -> None:
        """验证没有可兜底缓存时会抛出回源异常。

        参数:
            无。

        返回:
            None。
        """

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))

        async def loader() -> str:
            raise RuntimeError("loader failed")

        with self.assertRaises(RuntimeError):
            await cache.get_or_load("missing-item", loader, ttl=60)

    async def test_cache_manager_supports_batch_set_get_and_delete(self) -> None:
        """验证缓存管理器支持批量读写和删除。"""

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))

        await cache.set_many({"user:1": "alice", "user:2": "bob"}, ttl=60)
        values = await cache.get_many(["user:1", "user:2", "user:3"], default="missing")

        self.assertEqual(
            values,
            {"user:1": "alice", "user:2": "bob", "user:3": "missing"},
        )

        await cache.delete_many(["user:1", "user:2"])

        self.assertIsNone(await cache.get("user:1"))
        self.assertIsNone(await cache.get("user:2"))

    async def test_cache_manager_delete_prefix_removes_matching_entries(self) -> None:
        """验证缓存管理器支持按前缀删除。"""

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))

        await cache.set_many(
            {
                "user:1": "alice",
                "user:2": "bob",
                "article:1": "news",
            },
            ttl=60,
        )

        await cache.delete_prefix("user:")

        self.assertIsNone(await cache.get("user:1"))
        self.assertIsNone(await cache.get("user:2"))
        self.assertEqual(await cache.get("article:1"), "news")

    async def test_cache_manager_supports_cache_policy_and_loader_timeout(self) -> None:
        """验证缓存策略可以控制 TTL、stale 和回源超时。"""

        backend = LocalCacheBackend()
        cache = CacheManager(
            [backend],
            CacheConfig(ttl_jitter=0, default_loader_timeout=1.0),
        )

        async def slow_loader() -> str:
            await asyncio.sleep(0.1)
            return "slow"

        with self.assertRaises(TimeoutError):
            await cache.get_or_load(
                "slow:item",
                slow_loader,
                policy=CachePolicy(ttl=60, loader_timeout=0.01),
            )

    async def test_cache_manager_uses_fallback_when_loader_fails(self) -> None:
        """验证 loader 失败时可以返回 fallback 值。"""

        backend = LocalCacheBackend()
        cache = CacheManager([backend], CacheConfig(ttl_jitter=0))

        async def loader() -> str:
            raise RuntimeError("loader failed")

        result = await cache.get_or_load(
            "fallback:item",
            loader,
            ttl=60,
            fallback=lambda exc: f"fallback:{exc.__class__.__name__}",
        )

        self.assertEqual(result, "fallback:RuntimeError")

    async def test_cache_manager_emits_metrics_and_events_for_new_flows(self) -> None:
        """验证批量与 fallback 等链路会触发指标和事件。"""

        metrics = InMemoryMetricsHook()
        events = InMemoryEventHook()
        cache = CacheManager(
            [LocalCacheBackend()],
            CacheConfig(ttl_jitter=0),
            metrics_hook=metrics,
            event_hook=events,
        )

        async def loader() -> str:
            return "value"

        await cache.set_many({"one": 1, "two": 2}, ttl=60)
        await cache.get_many(["one", "two"])
        await cache.get_or_load(
            "three",
            loader,
            policy=CachePolicy(ttl=60, refresh_timeout=1.0),
        )

        snapshot = metrics.snapshot()

        self.assertGreaterEqual(snapshot["cache_set_total"], 3)
        self.assertGreaterEqual(snapshot["cache_hit_total"], 2)
        self.assertGreaterEqual(snapshot["cache_loader_outcome_success_total"], 1)
        self.assertTrue(any(event["event"] == "set" for event in events.events))
        self.assertTrue(any(event["event"] == "loader_success" for event in events.events))

    async def test_cache_manager_health_snapshot_reports_backend_state(self) -> None:
        """验证健康快照会包含后端状态。"""

        cache = CacheManager(
            [FailingBackend(), LocalCacheBackend()],
            CacheConfig(
                ttl_jitter=0,
                circuit_breaker=CircuitBreakerConfig(
                    enabled=True,
                    failure_threshold=1,
                    recovery_timeout=60.0,
                    half_open_max_calls=1,
                ),
            ),
        )

        await cache.get("missing")
        snapshot = cache.health_snapshot()

        self.assertEqual(snapshot["status"], "degraded")
        self.assertEqual(snapshot["backends"][0]["name"], "failing")

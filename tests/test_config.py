"""配置模型测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from kmcache.config import (
    BroadcastConfig,
    CacheConfig,
    CircuitBreakerConfig,
    LocalCacheConfig,
    RedisCacheConfig,
    WarmupConfig,
)


class ConfigTests(unittest.TestCase):
    """配置模型边界测试。"""

    def test_local_cache_config_rejects_invalid_values(self) -> None:
        """验证本地缓存配置会拒绝非法值。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            LocalCacheConfig(max_size=0)
        with self.assertRaises(ValueError):
            LocalCacheConfig(default_ttl=0)

    def test_redis_cache_config_rejects_invalid_values(self) -> None:
        """验证 Redis 缓存配置会拒绝非法值。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            RedisCacheConfig(url="")
        with self.assertRaises(ValueError):
            RedisCacheConfig(socket_timeout=0)
        with self.assertRaises(ValueError):
            RedisCacheConfig(lock_timeout=0)
        with self.assertRaises(ValueError):
            RedisCacheConfig(lock_sleep_interval=0)

    def test_broadcast_config_requires_channel_when_enabled(self) -> None:
        """验证启用广播时必须提供频道。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            BroadcastConfig(enabled=True, channel="")
        with self.assertRaises(ValueError):
            BroadcastConfig(instance_id="")

    def test_circuit_breaker_config_rejects_invalid_values(self) -> None:
        """验证熔断器配置会拒绝非法值。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreakerConfig(recovery_timeout=0)
        with self.assertRaises(ValueError):
            CircuitBreakerConfig(half_open_max_calls=0)

    def test_warmup_config_rejects_invalid_interval(self) -> None:
        """验证预热配置会拒绝非法周期。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            WarmupConfig(interval_seconds=0)

    def test_cache_config_defaults_are_valid(self) -> None:
        """验证顶层配置默认值是合法的。

        参数:
            无。

        返回:
            None。
        """

        config = CacheConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.namespace, "default")
        self.assertEqual(config.default_ttl, 300)
        self.assertIsNone(config.default_soft_ttl)
        self.assertIsNone(config.default_loader_timeout)
        self.assertIsNone(config.default_refresh_timeout)
        self.assertTrue(config.local.enabled)
        self.assertTrue(config.redis.enabled)
        self.assertTrue(config.circuit_breaker.enabled)
        self.assertTrue(config.warmup.enabled)

    def test_cache_config_rejects_invalid_values(self) -> None:
        """验证顶层配置会拒绝非法值。

        参数:
            无。

        返回:
            None。
        """

        with self.assertRaises(ValueError):
            CacheConfig(namespace="")
        with self.assertRaises(ValueError):
            CacheConfig(default_ttl=0)
        with self.assertRaises(ValueError):
            CacheConfig(default_soft_ttl=0)
        with self.assertRaises(ValueError):
            CacheConfig(ttl_jitter=-1)
        with self.assertRaises(ValueError):
            CacheConfig(null_ttl=0)
        with self.assertRaises(ValueError):
            CacheConfig(default_loader_timeout=0)
        with self.assertRaises(ValueError):
            CacheConfig(default_refresh_timeout=0)

    def test_cache_config_can_be_built_from_env(self) -> None:
        """验证顶层配置可以从环境变量映射构建。"""

        config = CacheConfig.from_env(
            {
                "KMCACHE_NAMESPACE": "service-a",
                "KMCACHE_DEFAULT_TTL": "120",
                "KMCACHE_ENABLE_STALE": "false",
                "KMCACHE_DEFAULT_LOADER_TIMEOUT": "1.5",
                "KMCACHE_REDIS_URL": "redis://127.0.0.1:6379/1",
                "KMCACHE_BROADCAST_ENABLED": "true",
            }
        )

        self.assertEqual(config.namespace, "service-a")
        self.assertEqual(config.default_ttl, 120)
        self.assertFalse(config.enable_stale)
        self.assertEqual(config.default_loader_timeout, 1.5)
        self.assertEqual(config.redis.url, "redis://127.0.0.1:6379/1")
        self.assertTrue(config.broadcast.enabled)

    def test_cache_config_can_be_built_from_object(self) -> None:
        """验证顶层配置可以从 settings 对象构建。"""

        settings = SimpleNamespace(
            namespace="service-b",
            default_ttl=240,
            redis={"url": "redis://127.0.0.1:6379/2", "enabled": False},
            local={"max_size": 256},
        )

        config = CacheConfig.from_object(settings)

        self.assertEqual(config.namespace, "service-b")
        self.assertEqual(config.default_ttl, 240)
        self.assertEqual(config.local.max_size, 256)
        self.assertFalse(config.redis.enabled)
        self.assertEqual(config.redis.url, "redis://127.0.0.1:6379/2")

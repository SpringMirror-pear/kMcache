"""FastAPI 集成测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch
from types import SimpleNamespace
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig, WarmupConfig
from kmcache.integrations.decorators import cached
from kmcache.integrations.fastapi import (
    build_cache_config_from_env,
    build_cache_config_from_settings,
    create_cache_health_route,
    create_cache_lifespan,
    create_cache_lifespan_with_warmup,
    get_cache,
)
from kmcache.integrations.keys import build_cache_key, prefix_key_builder
from kmcache.manager import CacheManager
from kmcache.models import WarmupItem


class TrackingCacheManager(CacheManager):
    """用于测试生命周期关闭行为的缓存管理器。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """初始化可跟踪关闭状态的缓存管理器。

        参数:
            *args: 位置参数。
            **kwargs: 关键字参数。

        返回:
            None。
        """

        super().__init__(*args, **kwargs)
        self.closed = False

    async def close(self) -> None:
        """关闭缓存管理器并记录关闭状态。

        参数:
            无。

        返回:
            None。
        """

        self.closed = True
        await super().close()


class FastAPIIntegrationTests(unittest.TestCase):
    """FastAPI 集成相关测试。"""

    def test_create_cache_lifespan_mounts_cache_and_closes_it(self) -> None:
        """验证 lifespan 会挂载并关闭缓存管理器。

        参数:
            无。

        返回:
            None。
        """

        cache = TrackingCacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
        app = FastAPI(lifespan=create_cache_lifespan(cache))

        @app.get("/ping")
        async def ping() -> dict[str, bool]:
            return {"ok": True}

        with TestClient(app) as client:
            response = client.get("/ping")
            self.assertEqual(response.status_code, 200)
            self.assertIs(app.state.cache, cache)

        self.assertTrue(cache.closed)

    def test_get_cache_dependency_returns_same_manager_instance(self) -> None:
        """验证依赖注入返回应用状态中的缓存管理器。

        参数:
            无。

        返回:
            None。
        """

        cache = CacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
        app = FastAPI(lifespan=create_cache_lifespan(cache))

        @app.get("/cache-id")
        async def cache_id(dependency_cache: CacheManager = Depends(get_cache)) -> dict[str, bool]:
            return {"same": dependency_cache is cache}

        with TestClient(app) as client:
            response = client.get("/cache-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"same": True})

    def test_cached_decorator_avoids_duplicate_async_execution(self) -> None:
        """验证缓存装饰器可避免异步函数重复执行。

        参数:
            无。

        返回:
            None。
        """

        cache = CacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
        calls = 0

        @cached(
            cache=cache,
            key_builder=lambda user_id: f"user:{user_id}",
            ttl=60,
        )
        async def load_user(user_id: int) -> str:
            nonlocal calls
            calls += 1
            return f"user-{user_id}"

        import asyncio

        first = asyncio.run(load_user(1))
        second = asyncio.run(load_user(1))

        self.assertEqual(first, "user-1")
        self.assertEqual(second, "user-1")
        self.assertEqual(calls, 1)

    def test_lifespan_runs_startup_warmup_items(self) -> None:
        """验证生命周期启动时会执行预热任务。

        参数:
            无。

        返回:
            None。
        """

        cache = TrackingCacheManager(
            [LocalCacheBackend()],
            CacheConfig(
                ttl_jitter=0,
                warmup=WarmupConfig(
                    enabled=True,
                    run_on_startup=True,
                ),
            ),
            warmup_items=[
                WarmupItem(
                    key="config:site",
                    loader=lambda: "ready",
                    ttl=60,
                )
            ],
        )
        app = FastAPI(lifespan=create_cache_lifespan(cache))

        @app.get("/config")
        async def config_endpoint(dependency_cache: CacheManager = Depends(get_cache)) -> dict[str, str]:
            value = await dependency_cache.get("config:site")
            return {"value": value}

        with TestClient(app) as client:
            response = client.get("/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"value": "ready"})

    def test_lifespan_runs_periodic_warmup_items(self) -> None:
        """验证生命周期内会周期性执行预热任务。

        参数:
            无。

        返回:
            None。
        """

        calls = {"count": 0}

        def loader() -> str:
            calls["count"] += 1
            return f"value-{calls['count']}"

        cache = TrackingCacheManager(
            [LocalCacheBackend()],
            CacheConfig(
                ttl_jitter=0,
                warmup=WarmupConfig(
                    enabled=True,
                    run_on_startup=False,
                    interval_seconds=0.05,
                ),
            ),
            warmup_items=[
                WarmupItem(
                    key="periodic:item",
                    loader=loader,
                    ttl=1,
                )
            ],
        )
        app = FastAPI(lifespan=create_cache_lifespan(cache))

        @app.get("/periodic")
        async def periodic_endpoint(
            dependency_cache: CacheManager = Depends(get_cache),
        ) -> dict[str, str | None]:
            value = await dependency_cache.get("periodic:item")
            return {"value": value}

        import time

        with TestClient(app) as client:
            time.sleep(0.12)
            response = client.get("/periodic")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["value"])
        self.assertGreaterEqual(calls["count"], 1)

    def test_create_cache_health_route_returns_snapshot(self) -> None:
        """验证健康检查路由会返回缓存状态。"""

        cache = CacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
        app = FastAPI(lifespan=create_cache_lifespan(cache))
        app.add_api_route("/health/cache", create_cache_health_route(cache), methods=["GET"])

        with TestClient(app) as client:
            response = client.get("/health/cache")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_build_cache_config_from_settings_uses_settings_object(self) -> None:
        """验证 FastAPI 集成辅助可以从 settings 对象生成配置。"""

        settings = SimpleNamespace(namespace="service-fastapi", redis={"enabled": False})

        config = build_cache_config_from_settings(settings)

        self.assertEqual(config.namespace, "service-fastapi")
        self.assertFalse(config.redis.enabled)

    def test_build_cache_config_from_env_uses_environment_mapping(self) -> None:
        """验证 FastAPI 集成辅助可以从环境变量构建配置。"""

        with patch.dict(
            "os.environ",
            {
                "KMCACHE_NAMESPACE": "service-env",
                "KMCACHE_REDIS_ENABLED": "false",
                "KMCACHE_DEFAULT_TTL": "90",
            },
            clear=False,
        ):
            config = build_cache_config_from_env()

        self.assertEqual(config.namespace, "service-env")
        self.assertFalse(config.redis.enabled)
        self.assertEqual(config.default_ttl, 90)

    def test_prefix_key_builder_builds_stable_keys(self) -> None:
        """验证统一 key builder 可以生成稳定 Key。"""

        builder = prefix_key_builder("users")
        key = builder(1, status="active")

        self.assertEqual(key, "users:1:status=active")

    def test_build_cache_key_builds_stable_keys(self) -> None:
        """验证通用 key builder 会稳定排序命名参数。"""

        key = build_cache_key("users", 1, status="active", region="cn")

        self.assertEqual(key, "users:1:region=cn:status=active")

    def test_create_cache_lifespan_with_warmup_runs_explicit_items(self) -> None:
        """验证显式 warmup items 会在应用启动时执行。"""

        cache = TrackingCacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
        app = FastAPI(
            lifespan=create_cache_lifespan_with_warmup(
                cache,
                warmup_items=[
                    WarmupItem(
                        key="warmup:item",
                        loader=lambda: "ready",
                        ttl=60,
                    )
                ],
            )
        )

        @app.get("/warmup")
        async def warmup_endpoint(
            dependency_cache: CacheManager = Depends(get_cache),
        ) -> dict[str, str | None]:
            return {"value": await dependency_cache.get("warmup:item")}

        with TestClient(app) as client:
            response = client.get("/warmup")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"value": "ready"})

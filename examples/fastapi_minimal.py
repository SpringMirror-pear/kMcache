"""FastAPI 最小集成示例。"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import BroadcastConfig, CacheConfig, RedisCacheConfig
from kmcache.integrations.fastapi import (
    create_cache_health_route,
    create_cache_lifespan,
    get_cache,
)
from kmcache.manager import CacheManager
from kmcache.models import CachePolicy


def build_app() -> FastAPI:
    """构建一个可运行的 FastAPI 示例应用。

    参数:
        无。

    返回:
        FastAPI: 配置好缓存组件的应用实例。
    """

    redis_config = RedisCacheConfig(
        url="redis://127.0.0.1:6379/0",
        key_prefix="kmcache-example",
    )
    cache = CacheManager(
        [
            LocalCacheBackend(),
            RedisCacheBackend.from_url(redis_config.url, redis_config),
        ],
        CacheConfig(
            ttl_jitter=0,
            redis=redis_config,
            broadcast=BroadcastConfig(
                enabled=True,
                channel="kmcache:example:broadcast",
                instance_id="example-instance",
            ),
        ),
    )
    app = FastAPI(lifespan=create_cache_lifespan(cache))
    app.add_api_route("/health/cache", create_cache_health_route(cache), methods=["GET"])

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        dependency_cache: CacheManager = Depends(get_cache),
    ) -> dict[str, object]:
        """读取用户信息并优先从缓存返回。

        参数:
            user_id: 用户 ID。
            dependency_cache: 依赖注入得到的缓存管理器。

        返回:
            dict[str, object]: 用户信息字典。
        """

        key = f"user:{user_id}"
        result = await dependency_cache.get_or_load(
            key,
            loader=lambda: {"user_id": user_id, "name": f"user-{user_id}"},
            policy=CachePolicy(
                ttl=60,
                soft_ttl=30,
                loader_timeout=1.0,
                refresh_timeout=1.0,
            ),
        )
        return {"data": result}

    return app


app = build_app()

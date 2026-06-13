"""FastAPI 场景化缓存集成示例。"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Query

from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import BroadcastConfig, CacheConfig, RedisCacheConfig
from kmcache.integrations import (
    build_cache_key,
    cached,
    create_cache_health_route,
    create_cache_lifespan_with_warmup,
    get_cache,
    prefix_key_builder,
)
from kmcache.manager import CacheManager
from kmcache.models import CachePolicy, WarmupItem


def build_app() -> FastAPI:
    """构建一个包含多个缓存模式的 FastAPI 示例应用。"""

    redis_config = RedisCacheConfig(
        url="redis://127.0.0.1:6379/0",
        key_prefix="kmcache-patterns",
        lock_timeout=2.0,
        lock_sleep_interval=0.05,
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
                channel="kmcache:patterns:broadcast",
                instance_id="patterns-example",
            ),
        ),
    )
    app = FastAPI(
        lifespan=create_cache_lifespan_with_warmup(
            cache,
            warmup_items=[
                WarmupItem(
                    key="site:config",
                    loader=lambda: {"name": "kmcache-demo", "region": "cn"},
                    ttl=300,
                    soft_ttl=120,
                )
            ],
        )
    )
    app.add_api_route("/health/cache", create_cache_health_route(cache), methods=["GET"])

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        dependency_cache: CacheManager = Depends(get_cache),
    ) -> dict[str, object]:
        """用户详情缓存示例。"""

        return {
            "data": await dependency_cache.get_or_load(
                build_cache_key("user", user_id),
                loader=lambda: {"user_id": user_id, "name": f"user-{user_id}"},
                policy=CachePolicy(ttl=60, soft_ttl=30),
            )
        }

    @app.get("/users")
    async def list_users(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        dependency_cache: CacheManager = Depends(get_cache),
    ) -> dict[str, object]:
        """分页列表缓存示例。"""

        return {
            "data": await dependency_cache.get_or_load(
                build_cache_key("users", "page", page, size=size),
                loader=lambda: {
                    "page": page,
                    "size": size,
                    "items": [f"user-{index}" for index in range((page - 1) * size, page * size)],
                },
                policy=CachePolicy(ttl=30, soft_ttl=10),
            )
        }

    @app.get("/profiles/{user_id}")
    async def get_profile_or_none(
        user_id: int,
        dependency_cache: CacheManager = Depends(get_cache),
    ) -> dict[str, object | None]:
        """空值缓存示例。"""

        async def loader() -> dict[str, object] | None:
            if user_id % 2 == 0:
                return {"user_id": user_id, "bio": "cached profile"}
            return None

        return {
            "data": await dependency_cache.get_or_load(
                build_cache_key("profile", user_id),
                loader=loader,
                policy=CachePolicy(ttl=60, null_ttl=15),
            )
        }

    @app.get("/hot-products/{product_id}")
    async def get_hot_product(
        product_id: int,
        dependency_cache: CacheManager = Depends(get_cache),
    ) -> dict[str, object]:
        """热点 Key 分布式锁示例。"""

        return {
            "data": await dependency_cache.get_or_load(
                build_cache_key("hot-product", product_id),
                loader=lambda: {"product_id": product_id, "inventory": 99},
                policy=CachePolicy(ttl=20, soft_ttl=10, loader_timeout=1.0),
            )
        }

    article_key_builder = prefix_key_builder("article")

    @cached(
        cache=cache,
        key_builder=lambda article_id: article_key_builder(article_id, view="detail"),
        policy=CachePolicy(ttl=45, soft_ttl=20, refresh_timeout=0.5),
    )
    async def load_article(article_id: int) -> dict[str, object]:
        """SWR 示例的实际加载函数。"""

        return {"article_id": article_id, "title": f"article-{article_id}"}

    @app.get("/articles/{article_id}")
    async def get_article(article_id: int) -> dict[str, object]:
        """SWR 场景示例。"""

        return {"data": await load_article(article_id)}

    return app


app = build_app()

"""FastAPI 集成辅助实现。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kmcache.config import CacheConfig
from kmcache.manager import CacheManager


def create_cache_lifespan(cache: CacheManager):
    """创建 FastAPI 生命周期上下文管理器。

    参数:
        cache: 要挂载到应用上的缓存管理器实例。

    返回:
        callable: 可直接传给 FastAPI 的 lifespan 函数。
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """在应用生命周期内管理缓存管理器。

        参数:
            app: FastAPI 应用实例。

        返回:
            AsyncIterator[None]: 生命周期上下文。
        """

        app.state.cache = cache
        await cache.start()
        yield
        await cache.close()

    return lifespan


def get_cache(request: Request) -> CacheManager:
    """从 FastAPI 请求上下文中获取缓存管理器。

    参数:
        request: FastAPI 请求对象。

    返回:
        CacheManager: 当前应用状态中的缓存管理器实例。
    """

    return request.app.state.cache


def create_cache_health_route(cache: CacheManager):
    """创建可直接挂到 FastAPI 的缓存健康检查处理函数。"""

    async def handler() -> JSONResponse:
        snapshot = cache.health_snapshot()
        status_code = 200 if snapshot["status"] == "ok" else 503
        return JSONResponse(snapshot, status_code=status_code)

    return handler


def build_cache_config_from_settings(settings: object) -> CacheConfig:
    """从 settings 对象构建缓存配置。"""

    return CacheConfig.from_object(settings)

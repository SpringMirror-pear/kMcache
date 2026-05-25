"""基于装饰器的缓存集成辅助实现。"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from kmcache.manager import CacheManager
from kmcache.models import CachePolicy


def cached(
    *,
    cache: CacheManager,
    key_builder: Callable[..., str],
    ttl: int | None = None,
    soft_ttl: int | None = None,
    loader_timeout: float | None = None,
    refresh_timeout: float | None = None,
    policy: CachePolicy | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """为异步函数结果提供缓存装饰器。

    参数:
        cache: 要使用的缓存管理器实例。
        key_builder: 根据函数入参生成缓存 Key 的函数。
        ttl: 硬过期 TTL 秒数。
        soft_ttl: 软过期 TTL 秒数。

    返回:
        Callable[[Callable[..., Any]], Callable[..., Any]]: 可应用于异步函数的装饰器。
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """包装目标函数并注入缓存逻辑。

        参数:
            func: 被装饰的目标异步函数。

        返回:
            Callable[..., Any]: 包装后的异步函数。
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """执行带缓存逻辑的包装函数。

            参数:
                *args: 目标函数的位置参数。
                **kwargs: 目标函数的关键字参数。

            返回:
                Any: 缓存命中结果或目标函数执行结果。
            """

            key = key_builder(*args, **kwargs)
            return await cache.get_or_load(
                key,
                lambda: func(*args, **kwargs),
                ttl=ttl,
                soft_ttl=soft_ttl,
                loader_timeout=loader_timeout,
                refresh_timeout=refresh_timeout,
                policy=policy,
            )

        return wrapper

    return decorator

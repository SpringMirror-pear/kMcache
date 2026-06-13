"""Public package exports for kmcache."""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "CacheConfig",
    "CacheManager",
    "CachePolicy",
    "build_cache_config_from_env",
    "build_cache_config_from_settings",
    "build_cache_key",
    "LocalCacheBackend",
    "RedisCacheBackend",
    "cached",
    "create_cache_health_route",
    "create_cache_lifespan",
    "create_cache_lifespan_with_warmup",
    "get_cache",
    "prefix_key_builder",
]


def __getattr__(name: str):
    """按需导出稳定公共 API，避免强制加载可选依赖。"""

    if name == "CacheConfig":
        from kmcache.config import CacheConfig

        return CacheConfig
    if name == "CacheManager":
        from kmcache.manager import CacheManager

        return CacheManager
    if name == "CachePolicy":
        from kmcache.models import CachePolicy

        return CachePolicy
    if name == "LocalCacheBackend":
        from kmcache.backends.local import LocalCacheBackend

        return LocalCacheBackend
    if name == "RedisCacheBackend":
        from kmcache.backends.redis import RedisCacheBackend

        return RedisCacheBackend
    if name == "cached":
        from kmcache.integrations.decorators import cached

        return cached
    if name == "create_cache_lifespan":
        from kmcache.integrations.fastapi import create_cache_lifespan

        return create_cache_lifespan
    if name == "create_cache_health_route":
        from kmcache.integrations.fastapi import create_cache_health_route

        return create_cache_health_route
    if name == "get_cache":
        from kmcache.integrations.fastapi import get_cache

        return get_cache
    if name == "build_cache_config_from_settings":
        from kmcache.integrations.fastapi import build_cache_config_from_settings

        return build_cache_config_from_settings
    if name == "build_cache_config_from_env":
        from kmcache.integrations.fastapi import build_cache_config_from_env

        return build_cache_config_from_env
    if name == "build_cache_key":
        from kmcache.integrations.keys import build_cache_key

        return build_cache_key
    if name == "prefix_key_builder":
        from kmcache.integrations.keys import prefix_key_builder

        return prefix_key_builder
    if name == "create_cache_lifespan_with_warmup":
        from kmcache.integrations.fastapi import create_cache_lifespan_with_warmup

        return create_cache_lifespan_with_warmup
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

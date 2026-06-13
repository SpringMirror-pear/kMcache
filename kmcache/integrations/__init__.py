"""Framework integrations for kmcache."""

from kmcache.integrations.decorators import cached
from kmcache.integrations.fastapi import (
    build_cache_config_from_settings,
    build_cache_config_from_env,
    create_cache_health_route,
    create_cache_lifespan,
    create_cache_lifespan_with_warmup,
    get_cache,
)
from kmcache.integrations.keys import build_cache_key
from kmcache.integrations.keys import prefix_key_builder

__all__ = [
    "build_cache_config_from_env",
    "build_cache_config_from_settings",
    "build_cache_key",
    "cached",
    "create_cache_health_route",
    "create_cache_lifespan",
    "create_cache_lifespan_with_warmup",
    "get_cache",
    "prefix_key_builder",
]

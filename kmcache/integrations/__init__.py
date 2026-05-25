"""Framework integrations for kmcache."""

from kmcache.integrations.decorators import cached
from kmcache.integrations.fastapi import (
    build_cache_config_from_settings,
    create_cache_health_route,
    create_cache_lifespan,
    get_cache,
)
from kmcache.integrations.keys import prefix_key_builder

__all__ = [
    "build_cache_config_from_settings",
    "cached",
    "create_cache_health_route",
    "create_cache_lifespan",
    "get_cache",
    "prefix_key_builder",
]

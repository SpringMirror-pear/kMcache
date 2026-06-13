# Integration Guide

## Overview

This guide describes the recommended `kmcache` integration patterns for common FastAPI deployment stages.

## 1. Single Instance / Local Development

Use L1 local cache only when:

- you run a single FastAPI instance
- you want the simplest setup
- cache sharing across processes is not required

Recommended shape:

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)
```

## 2. Shared Cache with Redis

Use Redis-only or L1+L2 when:

- multiple application instances are deployed
- cached data should be shared across instances
- hot-key coordination matters

Recommended shape:

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import CacheConfig, RedisCacheConfig
from kmcache.manager import CacheManager

redis_config = RedisCacheConfig(
    url="redis://127.0.0.1:6379/0",
    key_prefix="kmcache-demo",
)

cache = CacheManager(
    [
        LocalCacheBackend(),
        RedisCacheBackend.from_url(redis_config.url, redis_config),
    ],
    CacheConfig(ttl_jitter=0, redis=redis_config),
)
```

## 3. Production Redis + Broadcast

Enable broadcast when:

- L1 local cache exists on more than one instance
- a delete or overwrite should invalidate peer instances quickly

Recommended config:

```python
from kmcache.config import BroadcastConfig, CacheConfig

config = CacheConfig(
    redis=redis_config,
    broadcast=BroadcastConfig(
        enabled=True,
        channel="kmcache:service:broadcast",
        instance_id="service-a-1",
    ),
)
```

## 4. FastAPI Lifespan and Warmup

Use the integration helpers to keep app startup predictable:

```python
from fastapi import FastAPI

from kmcache.integrations.fastapi import (
    create_cache_health_route,
    create_cache_lifespan_with_warmup,
)
from kmcache.models import WarmupItem

app = FastAPI(
    lifespan=create_cache_lifespan_with_warmup(
        cache,
        warmup_items=[
            WarmupItem(
                key="site:config",
                loader=lambda: {"name": "demo"},
                ttl=300,
                soft_ttl=120,
            )
        ],
    )
)

app.add_api_route("/health/cache", create_cache_health_route(cache), methods=["GET"])
```

## 5. Recommended Cache Policies

User detail:

- `ttl=60`
- `soft_ttl=30`

List pages:

- `ttl=30`
- `soft_ttl=10`

Hot keys:

- shorter `ttl`
- `loader_timeout`
- L2 Redis enabled

Nullable resources:

- use `null_ttl`

## 6. Metrics and Event Hooks

Recommended minimum observability:

- hit / miss count
- loader success / error
- stale return count
- refresh success / error
- lock wait count
- broadcast count
- circuit open count

Use:

- `InMemoryMetricsHook` for local development and tests
- custom metrics and event hooks for Prometheus or OpenTelemetry integration

## 7. Configuration Entry Points

Recommended options:

- `CacheConfig(...)` for explicit code-based config
- `CacheConfig.from_env()` or `build_cache_config_from_env()` for environment-driven config
- `CacheConfig.from_object()` or `build_cache_config_from_settings()` for settings-based config

## 8. Example Files

- [examples/fastapi_minimal.py](../examples/fastapi_minimal.py)
- [examples/fastapi_patterns.py](../examples/fastapi_patterns.py)

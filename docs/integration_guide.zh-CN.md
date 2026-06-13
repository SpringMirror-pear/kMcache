# 接入指南

## 概览

本文档给出 `kmcache` 在 FastAPI 项目中的推荐接入方式，覆盖本地开发、单实例、双层缓存、生产 Redis、多实例广播和基础观测接入。

## 1. 单实例 / 本地开发

适用场景：

- 只有一个 FastAPI 实例
- 希望配置最简单
- 不需要跨进程共享缓存

推荐写法：

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)
```

## 2. Redis 共享缓存

适用场景：

- 多实例部署
- 需要共享缓存
- 热点 Key 协调重要

推荐写法：

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

## 3. 生产 Redis + 广播失效

当以下条件成立时建议开启广播：

- 使用了本地 L1 缓存
- 服务有多个实例
- 一个实例的删除或覆盖需要尽快同步到其他实例

推荐配置：

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

## 4. FastAPI 生命周期和预热

推荐使用集成辅助，让启动行为更明确：

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

## 5. 推荐缓存策略

用户详情：

- `ttl=60`
- `soft_ttl=30`

分页列表：

- `ttl=30`
- `soft_ttl=10`

热点 Key：

- 较短 `ttl`
- 配置 `loader_timeout`
- 启用 L2 Redis

可空资源：

- 使用 `null_ttl`

## 6. 指标与事件钩子

建议最少接入以下观测项：

- hit / miss
- loader success / error
- stale return
- refresh success / error
- lock wait
- broadcast
- circuit open

推荐方式：

- 本地开发和测试使用 `InMemoryMetricsHook`
- 生产环境接 Prometheus 或 OpenTelemetry 时，自定义 metrics / event hook

## 7. 配置接入方式

推荐入口：

- `CacheConfig(...)`：显式代码配置
- `CacheConfig.from_env()` 或 `build_cache_config_from_env()`：环境变量驱动配置
- `CacheConfig.from_object()` 或 `build_cache_config_from_settings()`：settings 对象驱动配置

## 8. 示例文件

- [examples/fastapi_minimal.py](../examples/fastapi_minimal.py)
- [examples/fastapi_patterns.py](../examples/fastapi_patterns.py)

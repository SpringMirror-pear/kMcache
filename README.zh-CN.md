# kmcache

[English](./README.md) | 简体中文

`kmcache` 是一个面向 FastAPI 服务场景的异步缓存工具库，目标是在保持接入简单的同时，提供足够生产可用的缓存编排能力。它内置 L1/L2 分层缓存、热点保护、失效广播、预热、观测钩子和框架集成辅助，避免你在每个项目里重复实现同类逻辑。

## 核心能力

- 异步优先的缓存管理接口
- `L1` 本地缓存、`L2` Redis 缓存、以及 `L1 + L2` 两级缓存
- `single-flight` 热点 Key 去重
- 多实例场景下的分布式锁防击穿
- TTL 抖动、空值缓存、`stale-while-revalidate`
- 基于 Redis 的失效广播
- 批量读写与前缀失效
- 预热、熔断、健康快照、可观测性钩子
- FastAPI 生命周期集成、装饰器与 Key Builder 辅助
- 可选 MessagePack 与压缩序列化

## 安装

`kmcache` 的核心依赖保持最小化，按需安装即可：

```bash
python -m pip install kmcache
python -m pip install "kmcache[redis]"
python -m pip install "kmcache[fastapi]"
python -m pip install "kmcache[msgpack]"
python -m pip install "kmcache[all]"
```

如果你想直接运行当前仓库：

```bash
python -m pip install -r requirements.txt
```

## 兼容性

- Python: `3.11+`
- Redis 客户端: `redis.asyncio`，当前依赖 `redis==7.4.0`
- FastAPI 集成: `fastapi==0.136.1`

当前支持矩阵见 [docs/compatibility.md](./docs/compatibility.md)。

## 快速开始

### 仅使用 L1

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)
```

### 使用 L1 + L2

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

### `get_or_load`

```python
from kmcache import CachePolicy


async def load_user() -> dict[str, str]:
    return {"name": "alice"}


user = await cache.get_or_load(
    "user:1",
    loader=load_user,
    policy=CachePolicy(
        ttl=60,
        soft_ttl=30,
        loader_timeout=1.0,
        refresh_timeout=1.0,
    ),
)
```

### 批量接口

```python
await cache.set_many(
    {
        "user:1": {"name": "alice"},
        "user:2": {"name": "bob"},
    },
    ttl=60,
)

users = await cache.get_many(["user:1", "user:2"])
await cache.delete_many(["user:1", "user:2"])
await cache.delete_prefix("user:")
```

## FastAPI 集成

最小示例：

```python
from fastapi import Depends, FastAPI

from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.integrations.fastapi import create_cache_lifespan, get_cache
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)

app = FastAPI(lifespan=create_cache_lifespan(cache))


@app.get("/users/{user_id}")
async def get_user(user_id: int, dependency_cache: CacheManager = Depends(get_cache)):
    return await dependency_cache.get_or_load(
        f"user:{user_id}",
        loader=lambda: {"user_id": user_id},
        ttl=60,
    )
```

当前提供的辅助能力：

- `create_cache_lifespan`
- `get_cache`
- `create_cache_health_route`
- `cached`
- `prefix_key_builder`
- `build_cache_config_from_settings`

可运行示例见 [examples/fastapi_minimal.py](./examples/fastapi_minimal.py)。

## 公共 API

当前稳定的顶层导出包括：

- `CacheManager`
- `CacheConfig`
- `CachePolicy`
- `LocalCacheBackend`
- `RedisCacheBackend`
- `cached`
- `create_cache_lifespan`
- `create_cache_health_route`
- `get_cache`
- `prefix_key_builder`

## 可观测性

当前内置钩子支持：

- 命中与未命中计数
- loader 开始、失败、结果统计
- stale 返回与后台刷新统计
- 锁等待与 fallback 统计
- 广播与熔断统计
- 用于本地调试和测试的内存事件钩子

相关模块：

- [kmcache/observability/metrics.py](./kmcache/observability/metrics.py)
- [kmcache/observability/events.py](./kmcache/observability/events.py)

## 质量检查

运行完整本地校验流程：

```bash
python scripts/check.py
```

当前流程包含：

- `compileall`
- 全量 `unittest`
- wheel 构建 smoke test
- 依赖存在性检查

CI 配置见 [\.github/workflows/ci.yml](./.github/workflows/ci.yml)。

## 文档

- [README.md](./README.md)
- [CHANGELOG.md](./CHANGELOG.md)
- [CHANGELOG.zh-CN.md](./CHANGELOG.zh-CN.md)
- [docs/compatibility.md](./docs/compatibility.md)
- [docs/release_checklist.md](./docs/release_checklist.md)
- [docs/技术方案以及架构.md](./docs/技术方案以及架构.md)
- [docs/开发约束.md](./docs/开发约束.md)
- [docs/任务规划.md](./docs/任务规划.md)

## 当前状态

当前优势：

- 面向 FastAPI 服务的生产级缓存编排能力
- 清晰的 L1/L2 分层缓存路径
- 较完整的单测与集成测试基线
- 已具备开源仓库所需的打包、变更记录与 CI 基础

后续重点：

- benchmark 与回归门槛
- 更丰富的真实业务示例
- 1.0 API 冻结与迁移说明

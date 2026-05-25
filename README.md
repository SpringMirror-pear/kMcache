# kmcache

面向 FastAPI 的异步缓存工具，支持：

- `L1` 本地缓存
- `L2` Redis 缓存
- `L1 + L2` 两级缓存
- 缓存雪崩防护
- 缓存击穿防护
- 空值缓存
- `stale-while-revalidate`
- Redis 广播失效通知
- Redis 分布式锁
- 熔断器
- 预热与周期性预热
- 基础可观测性
- 批量读写与前缀失效
- 可插拔缓存策略
- 可选 MessagePack 与压缩序列化

当前版本为 `0.3.0`，基于 Python `3.11+`，Redis 客户端使用 `redis.asyncio`。

## 1. 安装

如果你只是运行当前仓库测试与示例：

```bash
python -m pip install -r requirements.txt
```

作为包使用时，核心依赖默认为空，按需安装 extras：

```bash
python -m pip install kmcache
python -m pip install "kmcache[redis]"
python -m pip install "kmcache[fastapi]"
python -m pip install "kmcache[msgpack]"
python -m pip install "kmcache[all]"
```

可选依赖：

- `fastapi==0.136.1`
- `httpx==0.28.1`
- `redis==7.4.0`
- `msgpack==1.1.2`

## 2. 项目结构

```text
kmcache/
  backends/         # L1 / L2 后端
  coordination/     # single-flight、锁、pubsub 抽象
  features/         # 广播、熔断、预热、雪崩防护
  integrations/     # FastAPI 集成、装饰器
  observability/    # 指标、日志、追踪占位
  serialization/    # 序列化层
  utils/            # 通用工具
```

核心入口：

- [kmcache/manager.py](./kmcache/manager.py)
- [kmcache/config.py](./kmcache/config.py)
- [kmcache/backends/local.py](./kmcache/backends/local.py)
- [kmcache/backends/redis.py](./kmcache/backends/redis.py)

## 3. 快速开始

### 3.1 仅使用 L1

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)
```

### 3.2 仅使用 L2

```python
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import CacheConfig, RedisCacheConfig
from kmcache.manager import CacheManager

redis_config = RedisCacheConfig(
    url="redis://127.0.0.1:6379/0",
    key_prefix="kmcache-demo",
)

cache = CacheManager(
    [RedisCacheBackend.from_url(redis_config.url, redis_config)],
    CacheConfig(ttl_jitter=0, redis=redis_config),
)
```

### 3.3 使用 L1 + L2

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

## 4. 常用 API

### 4.1 `get` / `set`

```python
await cache.set("user:1", {"name": "alice"}, ttl=60)
user = await cache.get("user:1")
```

### 4.2 `get_many` / `set_many` / `delete_many`

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
```

### 4.3 `get_or_load`

这是最重要的生产接口。

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

行为说明：

- 命中缓存直接返回
- 未命中时回源并写回缓存
- 支持空值缓存
- 支持 stale 返回与后台刷新
- 多实例下可结合 Redis 分布式锁避免击穿

支持额外控制：

- `fallback`
- `loader_timeout`
- `refresh_timeout`
- `policy`

### 4.4 `delete` / `clear` / `delete_prefix`

```python
await cache.delete("user:1")
await cache.delete_prefix("user:")
await cache.clear()
```

## 5. FastAPI 集成

### 5.1 最小应用

完整示例见：

- [examples/fastapi_minimal.py](./examples/fastapi_minimal.py)

核心写法：

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

### 5.2 装饰器缓存

```python
from kmcache.integrations.decorators import cached


@cached(
    cache=cache,
    key_builder=lambda user_id: f"user:{user_id}",
    ttl=60,
)
async def load_user(user_id: int) -> dict[str, int]:
    return {"user_id": user_id}
```

### 5.3 健康检查与统一 Key Builder

```python
from kmcache.integrations.fastapi import create_cache_health_route
from kmcache.integrations.keys import prefix_key_builder

app.add_api_route("/health/cache", create_cache_health_route(cache), methods=["GET"])

user_key_builder = prefix_key_builder("user")
assert user_key_builder(1, status="active") == "user:1:status=active"
```

## 6. 广播、熔断、分布式锁

### 6.1 广播通知

启用后，多实例之间会通过 Redis Pub/Sub 同步本地 L1 失效。

```python
from kmcache.config import BroadcastConfig

config = CacheConfig(
    redis=redis_config,
    broadcast=BroadcastConfig(
        enabled=True,
        channel="kmcache:demo:broadcast",
        instance_id="instance-a",
    ),
)
```

### 6.2 熔断器

```python
from kmcache.config import CircuitBreakerConfig

config = CacheConfig(
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=1,
    )
)
```

### 6.3 分布式锁

```python
redis_config = RedisCacheConfig(
    url="redis://127.0.0.1:6379/0",
    key_prefix="kmcache-demo",
    lock_timeout=5.0,
    lock_sleep_interval=0.05,
)
```

用于在多实例场景下保护热点 key 的回源路径。

## 7. 预热

### 7.1 手动预热

```python
from kmcache.models import WarmupItem

await cache.warmup(
    [
        WarmupItem(
            key="config:site",
            loader=lambda: {"name": "demo"},
            ttl=300,
            soft_ttl=120,
        )
    ]
)
```

### 7.2 启动预热和周期性预热

```python
from kmcache.config import WarmupConfig
from kmcache.models import WarmupItem

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(
        ttl_jitter=0,
        warmup=WarmupConfig(
            enabled=True,
            run_on_startup=True,
            interval_seconds=60.0,
        ),
    ),
    warmup_items=[
        WarmupItem(
            key="config:site",
            loader=lambda: {"name": "demo"},
            ttl=300,
        )
    ],
)
```

## 8. 可观测性

### 8.1 内存指标钩子

```python
from kmcache.observability.metrics import InMemoryMetricsHook

metrics = InMemoryMetricsHook()
cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
    metrics_hook=metrics,
)

snapshot = metrics.snapshot()
```

当前已支持的核心计数：

- `cache_hit_total`
- `cache_miss_total`
- `cache_set_total`
- `cache_delete_total`
- `cache_loader_total`
- `cache_loader_error_total`
- `cache_loader_outcome_success_total`
- `cache_stale_return_total`
- `cache_lock_wait_total`
- `cache_fallback_total`
- `cache_broadcast_total`
- `cache_circuit_open_total`

### 8.2 事件钩子

```python
from kmcache.observability.events import InMemoryEventHook

event_hook = InMemoryEventHook()
cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
    event_hook=event_hook,
)
```

## 9. 序列化扩展

```python
from kmcache.compression import GzipCompressor
from kmcache.serialization import CompressedSerializer, JsonSerializer, MessagePackSerializer

compressed_json = CompressedSerializer(JsonSerializer(), GzipCompressor())
msgpack_serializer = MessagePackSerializer()
```

## 10. 测试

当前已覆盖：

- 本地缓存行为
- `CacheManager` 基础编排
- TTL 抖动
- Redis 读写
- Redis 广播
- Redis 分布式锁
- FastAPI 集成
- 序列化边界
- 可观测性
- 打包元数据与 wheel smoke test

运行测试：

```bash
python -m unittest
```

## 11. 质量检查

标准质量检查入口：

```bash
python scripts/check.py
```

PowerShell 版本：

```powershell
./scripts/check.ps1
```

该流程当前包含：

- `compileall`
- 全量 `unittest`
- wheel 构建 smoke test
- 关键依赖存在性检查

## 12. 文档

设计与规划文档见：

- [docs/技术方案以及架构.md](./docs/技术方案以及架构.md)
- [docs/开发约束.md](./docs/开发约束.md)
- [docs/任务规划.md](./docs/任务规划.md)
- [CHANGELOG.md](./CHANGELOG.md)
- [docs/release_checklist.md](./docs/release_checklist.md)
- [docs/compatibility.md](./docs/compatibility.md)

## 13. 当前状态

当前项目已经具备：

- L1 / L2 / L1+L2 组合能力
- stale、熔断、广播、分布式锁、预热、基础可观测性
- 批量接口、前缀失效、策略对象、loader timeout/fallback
- 可选 MessagePack 与压缩序列化
- FastAPI 最小集成路径
- 健康检查与 settings 配置接入
- 完整的基础测试矩阵

当前仍待完善的方向：

- 基准测试
- 更丰富的接入示例
- 1.0 迁移说明与 API 冻结

# kmcache

English | [简体中文](./README.zh-CN.md)

`kmcache` is an async caching toolkit built for FastAPI-oriented services. It provides a composable L1/L2 cache architecture, production-focused cache protection features, and framework integration helpers so you can add caching without rewriting the same coordination logic in every project.

## Highlights

- Async-first cache manager API
- L1 local cache, L2 Redis cache, and L1+L2 layered cache
- `single-flight` hot-key deduplication
- Distributed lock protection for multi-instance cache breakdown
- TTL jitter, null caching, and `stale-while-revalidate`
- Redis-based invalidation broadcast
- Batch operations and prefix invalidation
- Warmup, circuit breaker, health snapshot, and observability hooks
- FastAPI lifespan integration, decorators, and key builder helpers
- Optional MessagePack and compressed serialization

## Installation

`kmcache` keeps the core dependency set minimal. Install only what you need:

```bash
python -m pip install kmcache
python -m pip install "kmcache[redis]"
python -m pip install "kmcache[fastapi]"
python -m pip install "kmcache[msgpack]"
python -m pip install "kmcache[all]"
```

If you want to run this repository locally:

```bash
python -m pip install -r requirements.txt
```

## Compatibility

- Python: `3.11+`
- Redis client: `redis.asyncio` via `redis==7.4.0`
- FastAPI integration: `fastapi==0.136.1`

See [docs/compatibility.md](./docs/compatibility.md) for the current support matrix.

## Quick Start

### L1 only

```python
from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig
from kmcache.manager import CacheManager

cache = CacheManager(
    [LocalCacheBackend()],
    CacheConfig(ttl_jitter=0),
)
```

### L1 + L2

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

### Batch operations

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

## FastAPI Integration

Minimal example:

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

Helpers included:

- `create_cache_lifespan`
- `get_cache`
- `create_cache_health_route`
- `cached`
- `prefix_key_builder`
- `build_cache_config_from_settings`

See [examples/fastapi_minimal.py](./examples/fastapi_minimal.py) for a runnable example.

## Public API

Stable top-level exports currently include:

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

## Observability

Built-in hooks currently support:

- Hit and miss counters
- Loader start, error, and outcome metrics
- Stale return and background refresh metrics
- Lock wait and fallback metrics
- Broadcast and circuit-open metrics
- In-memory event hooks for local debugging and tests

Related modules:

- [kmcache/observability/metrics.py](./kmcache/observability/metrics.py)
- [kmcache/observability/events.py](./kmcache/observability/events.py)

## Git Workflow

Recommended branch model:

- `main`: production-ready code only
- `develop`: default integration branch for ongoing work
- `release/0.x`: release hardening branch for the current major/minor line

Recommended short-lived working branches:

- `feature/<scope>-<name>`
- `fix/<scope>-<name>`
- `docs/<name>`
- `refactor/<scope>-<name>`
- `test/<scope>-<name>`
- `chore/<name>`
- `hotfix/<name>`

Recommended commit format:

```text
type(scope): short summary
```

Examples:

```text
feat(manager): add batch get_or_load support
fix(redis): handle lock timeout fallback
docs(readme): document branching strategy
test(manager): cover stale refresh lock path
chore(ci): add wheel smoke test
```

Recommended commit types:

- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `chore`
- `perf`
- `ci`
- `build`
- `revert`

Rules for this repository:

- branch from `develop` for normal feature work
- branch from `main` only for urgent `hotfix/*`
- keep one logical change per commit
- use pull requests to merge into `develop` or `main`
- prefer squash merge for feature branches unless history must be preserved
- do not push generated artifacts such as `dist/` or `__pycache__/`

## Quality

Run the full local verification workflow:

```bash
python scripts/check.py
```

This currently covers:

- `compileall`
- full `unittest`
- wheel smoke test
- dependency presence checks

CI is defined in [\.github/workflows/ci.yml](./.github/workflows/ci.yml).

## Documentation

- [README.zh-CN.md](./README.zh-CN.md)
- [CHANGELOG.md](./CHANGELOG.md)
- [CHANGELOG.zh-CN.md](./CHANGELOG.zh-CN.md)
- [docs/compatibility.md](./docs/compatibility.md)
- [docs/release_checklist.md](./docs/release_checklist.md)

## Status

Current strengths:

- production-oriented cache coordination for FastAPI services
- layered cache support with L1/L2 orchestration
- solid unit and integration test baseline
- packaging, changelog, and CI foundations for open-source usage

Planned next steps:

- benchmarks and regression thresholds
- richer real-world examples
- 1.0 API freeze and migration guide

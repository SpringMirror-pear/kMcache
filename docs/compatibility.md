# Compatibility

## Support Matrix

- Python: `3.11+`
- FastAPI: `0.136.1`
- Redis client: `redis==7.4.0`
- MessagePack serializer: `msgpack==1.1.2`，仅在安装 `kmcache[msgpack]` 后可用
- Compression helper: built-in `GzipCompressor`

## Public API Freeze for 1.x

The following interfaces are part of the stable public API for `1.x`:

- `CacheManager`
- `CacheConfig`
- `CachePolicy`
- `LocalCacheBackend`
- `RedisCacheBackend`
- `build_cache_config_from_env`
- `build_cache_config_from_settings`
- `build_cache_key`
- `cached`
- `create_cache_lifespan`
- `create_cache_lifespan_with_warmup`
- `create_cache_health_route`
- `get_cache`
- `prefix_key_builder`

## Compatibility Policy

- `1.x` will not casually change the core `CacheManager` method signatures.
- The existing `get_or_load(ttl=..., soft_ttl=...)` keyword style remains supported in `1.0.0`.
- `policy=` is the recommended shape for new code, but not the only supported shape.
- Optional dependencies continue to fail lazily with clear errors rather than breaking top-level import.
- Serializer payload migration is supported for legacy cache envelope version `1`.

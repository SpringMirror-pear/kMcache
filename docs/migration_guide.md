# Migration Guide

## 0.x to 1.0.0

`kmcache 1.0.0` freezes the public API documented in the README and compatibility guide. The goal of this release is stability rather than another large behavior shift.

## What stayed stable

The following APIs remain supported in `1.0.0`:

- `CacheManager`
- `CacheConfig`
- `CachePolicy`
- `LocalCacheBackend`
- `RedisCacheBackend`
- `cached`
- `create_cache_lifespan`
- `create_cache_lifespan_with_warmup`
- `create_cache_health_route`
- `get_cache`
- `build_cache_key`
- `prefix_key_builder`
- `build_cache_config_from_env`
- `build_cache_config_from_settings`

## Recommended migration updates

If you started from early `0.x` usage:

1. Prefer `CachePolicy(...)` for new call sites instead of continuing to expand positional or keyword TTL arguments.
2. Use `build_cache_key(...)` or `prefix_key_builder(...)` to keep key generation stable and testable.
3. Use `build_cache_config_from_env()` or `build_cache_config_from_settings()` when integrating with application settings.
4. Use `create_cache_lifespan_with_warmup(...)` when startup warmup is part of the application contract.
5. Use event hooks and metrics hooks instead of ad-hoc logging around cache code paths.

## Serialization compatibility

- `CacheEnvelope.version` is now treated as an explicit schema version.
- Legacy v1 payloads are migrated on read by the serializer layer.
- Future unsupported payload versions raise a clear `SerializationError`.

## Compatibility note on older `get_or_load(...)` usage

The older `ttl=` / `soft_ttl=` keyword style is still accepted in `1.0.0`.
It is no longer considered temporary compatibility code; it is part of the supported public API for this release line.

## Removed temporary ambiguity

The project now treats the following as stable rather than transitional:

- the public top-level exports listed in `kmcache.__all__`
- `CachePolicy` as the primary policy object
- serializer + compressor composition for extensible payload handling
- FastAPI-first helper entry points

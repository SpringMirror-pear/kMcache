# Changelog

English | [简体中文](./CHANGELOG.zh-CN.md)

All notable changes to this project will be documented in this file.

## 1.0.0 - 2026-06-14

### Added

- Stable release documentation for API freeze, migration guidance, and release standards.
- Benchmark runner with regression thresholds for L1 hit, L2 hit, miss-load, stale return, and dual-instance lock contention.

### Changed

- Froze the documented public API for the `1.x` line.
- Expanded compatibility documentation with the supported matrix and `1.x` stability policy.

## 0.5.0 - 2026-06-13

### Added

- FastAPI integration helpers for environment-based config construction.
- `create_cache_lifespan_with_warmup` for explicit startup warmup wiring.
- `build_cache_key` as a general stable key builder helper.
- A richer FastAPI patterns example covering user detail, list pagination, null caching, hot keys, and SWR.
- Dedicated integration guides for recommended single-instance, local dev, L1+L2, production Redis, broadcast, and metrics usage.

### Changed

- Expanded README documentation to better reflect the FastAPI-first integration path and helper surface.

## 0.4.0 - 2026-05-25

### Added

- Explicit cache envelope version migration support shared across serializers.
- Refresh lifecycle events: `refresh_start`, `refresh_success`, and `refresh_error`.
- Broadcast and circuit-open event hook emissions for external observability integrations.

### Changed

- `CacheEnvelope.version` now defaults to the current schema version and legacy payloads are migrated on read.
- Background refresh now applies `refresh_timeout` as its effective loader timeout when provided.

## 0.3.0 - 2026-05-25

### Added

- `CachePolicy` support for cache behavior tuning.
- `loader_timeout`, `refresh_timeout`, and `fallback` controls for `get_or_load`.
- Batch APIs: `get_many`, `set_many`, `delete_many`, and `get_many_or_load`.
- Prefix invalidation via `delete_prefix`.
- Optional serialization extensions: `MessagePackSerializer`, `CompressedSerializer`, and `GzipCompressor`.
- Top-level lazy exports for the stable public API surface.
- FastAPI health route helper, settings-based config builder, and reusable key builder.
- Event hooks, loader outcome metrics, lock wait metrics, fallback metrics, and health snapshots.
- Package metadata tests, wheel smoke tests, and a GitHub Actions CI workflow.

### Changed

- Moved framework and Redis dependencies into extras.
- Widened supported Python versions to `3.11+`.
- Reworked repository documentation to better fit GitHub open-source conventions.

## 0.1.0 - 2026-05-22

### Added

- Initial public prototype with async L1/L2 caching.
- Stale refresh, Redis broadcast invalidation, distributed locks, warmup, and FastAPI integration.

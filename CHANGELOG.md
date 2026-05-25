# Changelog

## 0.3.0 - 2026-05-25

- Added `CachePolicy`, `loader_timeout`, `refresh_timeout`, and `fallback` controls for `get_or_load`.
- Added batch APIs: `get_many`, `set_many`, `delete_many`, and `get_many_or_load`.
- Added prefix invalidation with `delete_prefix`.
- Added optional serialization extensions: `MessagePackSerializer`, `CompressedSerializer`, and `GzipCompressor`.
- Added top-level lazy exports for the stable public API surface.
- Added FastAPI health route helper, settings-based config builder, and reusable key builder.
- Expanded observability with event hooks, loader outcome metrics, lock wait metrics, fallback metrics, and health snapshots.
- Moved framework and Redis dependencies into extras and widened Python support to `3.11+`.
- Added package metadata tests, wheel smoke tests, and a GitHub Actions CI baseline.

## 0.1.0 - 2026-05-22

- Initial public prototype with L1/L2 async caching, stale refresh, Redis broadcast, distributed locks, warmup, and FastAPI integration.

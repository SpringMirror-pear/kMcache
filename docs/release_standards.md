# Release Standards

## 1.0.0 Release Criteria

A stable release is considered ready only when all of the following are true:

- documentation is complete and consistent
- CI is green across the supported Python matrix
- integration tests are stable
- public API surface is explicitly frozen
- examples are runnable and match the documented APIs

## Required verification

- `python scripts/check.py`
- `python -m unittest`
- `python scripts/benchmark.py`

## Documentation set

Required release documents:

- `README.md`
- `README.zh-CN.md`
- `CHANGELOG.md`
- `CHANGELOG.zh-CN.md`
- `docs/compatibility.md`
- `docs/migration_guide.md`
- `docs/release_checklist.md`
- `docs/release_standards.md`
- `docs/integration_guide.md`
- `docs/integration_guide.zh-CN.md`

## API freeze

Within `1.x`, do not casually change:

- `CacheManager` core public method signatures
- `CacheConfig` top-level model shape
- `CachePolicy` field contract
- public top-level exports

Breaking changes should be deferred to a future major version.

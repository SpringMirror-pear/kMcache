# 兼容性说明

## 支持矩阵

- Python: `3.11+`
- FastAPI: `0.136.1`
- Redis client: `redis==7.4.0`
- MessagePack serializer: `msgpack==1.1.2`，仅在安装 `kmcache[msgpack]` 后可用

## 公共 API 承诺

以下接口视为当前稳定公共 API：

- `CacheManager`
- `CacheConfig`
- `CachePolicy`
- `LocalCacheBackend`
- `RedisCacheBackend`
- `cached`
- `create_cache_lifespan`
- `create_cache_health_route`
- `get_cache`

## 兼容策略

- `0.x` 期间尽量保持向后兼容，但允许在小范围内调整实验性扩展接口
- 现有 `get_or_load(ttl=..., soft_ttl=...)` 形式继续支持
- 新增 `policy=` 形式与旧参数并存，当前版本无移除计划
- 可选依赖未安装时，相关模块按需失败并给出明确异常，而不是在顶层导入时失败

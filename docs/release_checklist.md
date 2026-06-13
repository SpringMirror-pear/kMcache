# 发布清单

## 发布前

- 更新 `kmcache/__init__.py`、`pyproject.toml`、`build_backend.py` 中的版本号
- 更新 [CHANGELOG.md](/c:/Users/Administrator/Desktop/project/python/kmcache/CHANGELOG.md)
- 运行 `python scripts/check.py`
- 运行 `python scripts/benchmark.py`
- 确认 `python -m unittest` 全绿
- 确认 Redis 集成测试已在本地可用环境执行
- 检查 README 与示例代码是否仍与当前公共 API 一致
- 检查 [docs/migration_guide.md](/c:/Users/Administrator/Desktop/project/python/kmcache/docs/migration_guide.md) 与 [docs/release_standards.md](/c:/Users/Administrator/Desktop/project/python/kmcache/docs/release_standards.md) 是否仍然准确

## 构建物检查

- 生成 wheel 与 sdist
- 检查 wheel 中的 `METADATA` 是否包含正确的 extras
- 检查 `Requires-Python` 与当前支持矩阵一致
- 在干净环境中验证 `kmcache`、`kmcache[redis]`、`kmcache[fastapi]`、`kmcache[msgpack]`

## 发布后

- 打标签并记录发布日期
- 同步更新接入项目的依赖版本
- 观察健康检查、缓存命中率、回源次数、锁等待和异常日志

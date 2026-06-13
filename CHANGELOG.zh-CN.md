# 更新日志

[English](./CHANGELOG.md) | 简体中文

本文件记录项目中的重要变更。

## 1.0.0 - 2026-06-14

### 新增

- 新增稳定版发布文档，覆盖 API 冻结、迁移指南和发布标准。
- 新增基准测试脚本，并为 L1 命中、L2 命中、miss 回源、stale 返回和双实例锁竞争定义回归门槛。

### 变更

- 冻结 `1.x` 版本线的公共 API。
- 补充支持矩阵和 `1.x` 稳定性策略文档。

## 0.5.0 - 2026-06-13

### 新增

- 新增 FastAPI 环境变量配置辅助入口。
- 新增 `create_cache_lifespan_with_warmup`，用于显式绑定启动预热。
- 新增通用稳定 Key 构造函数 `build_cache_key`。
- 新增覆盖用户详情、分页列表、空值缓存、热点 Key 和 SWR 的 FastAPI 场景化示例。
- 新增推荐接入文档，覆盖单实例、本地开发、双层缓存、生产 Redis、多实例广播和指标接入。

### 变更

- README 文档补充并强化了 FastAPI-first 的接入路径与辅助接口说明。

## 0.4.0 - 2026-05-25

### 新增

- 为序列化层增加统一的 `CacheEnvelope` 版本迁移策略。
- 新增刷新生命周期事件：`refresh_start`、`refresh_success`、`refresh_error`。
- 新增 `broadcast` 与 `circuit_open` 事件钩子发射，便于外接观测系统。

### 变更

- `CacheEnvelope.version` 默认提升为当前 schema 版本，读取旧载荷时会自动迁移。
- 后台刷新在配置 `refresh_timeout` 时会优先使用该超时时间。

## 0.3.0 - 2026-05-25

### 新增

- 新增 `CachePolicy`，用于统一描述缓存行为策略。
- 为 `get_or_load` 增加 `loader_timeout`、`refresh_timeout` 和 `fallback` 控制项。
- 新增批量接口：`get_many`、`set_many`、`delete_many`、`get_many_or_load`。
- 新增前缀失效能力 `delete_prefix`。
- 新增可选序列化扩展：`MessagePackSerializer`、`CompressedSerializer`、`GzipCompressor`。
- 新增稳定公共 API 的顶层 lazy export。
- 新增 FastAPI 健康检查路由辅助、基于 settings 的配置构建器和统一 key builder。
- 新增事件钩子、loader 结果指标、锁等待指标、fallback 指标和健康快照。
- 新增包元数据测试、wheel smoke test 和 GitHub Actions CI 工作流。

### 变更

- 将框架与 Redis 依赖下沉到 extras。
- Python 支持范围扩展为 `3.11+`。
- 重新整理仓库文档结构，使其更符合 GitHub 开源仓库习惯。

## 0.1.0 - 2026-05-22

### 新增

- 发布首个公开原型版本，包含异步 L1/L2 缓存能力。
- 包含 stale 刷新、Redis 广播失效、分布式锁、预热和 FastAPI 集成。

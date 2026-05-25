# 更新日志

[English](./CHANGELOG.md) | 简体中文

本文件记录项目中的重要变更。

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

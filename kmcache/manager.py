"""Top-level cache manager that orchestrates backend access."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import suppress
from time import perf_counter
from typing import Any

from kmcache.backends.base import BaseCacheBackend
from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.backends.base import SupportsBatchOperations, SupportsPrefixDelete, SupportsStaleRead
from kmcache.config import CacheConfig
from kmcache.exceptions import BackendError
from kmcache.exceptions import CircuitBreakerOpenError
from kmcache.exceptions import LockAcquisitionError
from kmcache.features.avalanche import apply_ttl_jitter
from kmcache.features.broadcast import (
    BaseBroadcaster,
    CacheEvent,
    EventType,
    NoOpBroadcaster,
    RedisBroadcaster,
)
from kmcache.features.circuit_breaker import CircuitBreaker
from kmcache.features.refresh import should_return_stale
from kmcache.features.warmup import WarmupEngine
from kmcache.models import CacheEnvelope, CachePolicy, Loader, LoaderFallback, WarmupItem
from kmcache.observability.events import BaseEventHook, NoOpEventHook
from kmcache.observability.logging import get_logger, log_cache_event
from kmcache.observability.metrics import BaseMetricsHook, NoOpMetricsHook
from kmcache.coordination.singleflight import SingleFlightGroup
from kmcache.utils.keys import join_key_parts
from kmcache.utils.time import utc_timestamp

_NO_FALLBACK = object()


class CacheManager:
    """统一编排 L1/L2 缓存访问、回源与回填流程。"""

    def __init__(
        self,
        backends: Sequence[BaseCacheBackend],
        config: CacheConfig | None = None,
        *,
        broadcaster: BaseBroadcaster | None = None,
        metrics_hook: BaseMetricsHook | None = None,
        event_hook: BaseEventHook | None = None,
        warmup_engine: WarmupEngine | None = None,
        warmup_items: list[WarmupItem] | None = None,
    ) -> None:
        """初始化缓存管理器。

        参数:
            backends: 按读取优先级排序的缓存后端列表。
            config: 缓存管理器全局配置，未传入时使用默认配置。
            broadcaster: 广播组件，未传入时使用空实现。
            metrics_hook: 指标钩子，未传入时使用空实现。
            event_hook: 事件钩子，未传入时使用空实现。
            warmup_engine: 预热引擎，未传入时使用默认实现。
            warmup_items: 生命周期启动后可自动执行的预热项列表。

        返回:
            None。
        """

        self._config = config or CacheConfig()
        self._backends = tuple(backends)
        self._broadcaster = self._build_broadcaster(broadcaster)
        self._metrics_hook = metrics_hook or NoOpMetricsHook()
        self._event_hook = event_hook or NoOpEventHook()
        self._singleflight = SingleFlightGroup()
        self._warmup_engine = warmup_engine or WarmupEngine()
        self._warmup_items = warmup_items or []
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._backend_circuits = self._build_backend_circuits()
        self._logger = get_logger()

    @property
    def backends(self) -> tuple[BaseCacheBackend, ...]:
        """返回已配置的缓存后端链。

        参数:
            无。

        返回:
            tuple[BaseCacheBackend, ...]: 按读取优先级排序的后端元组。
        """

        return self._backends

    @property
    def config(self) -> CacheConfig:
        """返回缓存管理器配置。

        参数:
            无。

        返回:
            CacheConfig: 当前缓存管理器使用的配置对象。
        """

        return self._config

    async def start(self) -> None:
        """启动缓存管理器运行时组件。

        参数:
            无。

        返回:
            None。
        """

        await self._broadcaster.start()
        await self._start_warmup_tasks()

    async def get(self, key: str, default: Any = None) -> Any:
        """读取缓存值。

        参数:
            key: 业务缓存 Key。
            default: 未命中时返回的默认值。

        返回:
            Any: 命中时返回缓存值，否则返回 default。
        """

        normalized_key = self._normalize_key(key)
        envelope, layer_name = await self._get_envelope_with_source(normalized_key)
        if envelope is None:
            await self._metrics_hook.on_miss(normalized_key)
            await self._event_hook.emit("miss", key=normalized_key)
            return default

        await self._metrics_hook.on_hit(normalized_key, layer=layer_name)
        await self._event_hook.emit("hit", key=normalized_key, layer=layer_name)
        return envelope.resolve_value()

    async def get_many(
        self,
        keys: Sequence[str],
        *,
        default: Any = None,
    ) -> dict[str, Any]:
        """批量读取缓存值。"""

        results = await asyncio.gather(*(self.get(key, default=default) for key in keys))
        return dict(zip(keys, results, strict=False))

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        soft_ttl: int | None = None,
        *,
        policy: CachePolicy | None = None,
    ) -> None:
        """写入缓存值到所有已配置后端。

        参数:
            key: 业务缓存 Key。
            value: 要写入的缓存值。
            ttl: 硬过期 TTL 秒数，未传入时使用默认 TTL。
            soft_ttl: 软过期 TTL 秒数，用于 stale-while-revalidate。

        返回:
            None。
        """

        normalized_key = self._normalize_key(key)
        resolved_policy = self._resolve_policy(
            ttl=ttl,
            soft_ttl=soft_ttl,
            policy=policy,
        )
        actual_ttl = self._resolve_ttl(resolved_policy.ttl, resolved_policy.ttl_jitter)
        envelope = self._build_envelope(
            value=value,
            ttl=actual_ttl,
            soft_ttl=resolved_policy.soft_ttl,
            is_null=False,
        )
        await self._write_envelope(normalized_key, envelope)
        await self._publish_event(EventType.SET, normalized_key)
        await self._event_hook.emit("set", key=normalized_key)

    async def set_many(
        self,
        values: Mapping[str, Any],
        ttl: int | None = None,
        soft_ttl: int | None = None,
        *,
        policy: CachePolicy | None = None,
    ) -> None:
        """批量写入缓存值到所有已配置后端。"""

        resolved_policy = self._resolve_policy(
            ttl=ttl,
            soft_ttl=soft_ttl,
            policy=policy,
        )
        actual_ttl = self._resolve_ttl(resolved_policy.ttl, resolved_policy.ttl_jitter)
        envelopes = {
            self._normalize_key(key): self._build_envelope(
                value=value,
                ttl=actual_ttl,
                soft_ttl=resolved_policy.soft_ttl,
                is_null=False,
            )
            for key, value in values.items()
        }
        await self._write_envelopes(envelopes)
        for key in envelopes:
            await self._publish_event(EventType.SET, key)
            await self._event_hook.emit("set", key=key)

    async def delete(self, key: str) -> None:
        """删除所有后端中的缓存 Key。

        参数:
            key: 业务缓存 Key。

        返回:
            None。
        """

        normalized_key = self._normalize_key(key)
        for backend in self._backends:
            await self._run_backend_call(backend, backend.delete, normalized_key)
        await self._metrics_hook.on_delete(normalized_key)
        await self._publish_event(EventType.DELETE, normalized_key)
        await self._event_hook.emit("delete", key=normalized_key)

    async def delete_many(self, keys: Sequence[str]) -> None:
        """批量删除所有后端中的缓存 Key。"""

        normalized_keys = [self._normalize_key(key) for key in keys]
        for backend in self._backends:
            if isinstance(backend, SupportsBatchOperations):
                await self._run_backend_call(backend, backend.delete_many, normalized_keys)
                continue
            for key in normalized_keys:
                await self._run_backend_call(backend, backend.delete, key)
        for key in normalized_keys:
            await self._metrics_hook.on_delete(key)
            await self._publish_event(EventType.DELETE, key)
            await self._event_hook.emit("delete", key=key)

    async def exists(self, key: str) -> bool:
        """判断缓存 Key 是否存在于任一后端。

        参数:
            key: 业务缓存 Key。

        返回:
            bool: 任一后端命中返回 True，否则返回 False。
        """

        normalized_key = self._normalize_key(key)
        envelope = await self._get_envelope(normalized_key)
        return envelope is not None

    async def clear(self) -> None:
        """清空所有后端中的缓存数据。

        参数:
            无。

        返回:
            None。
        """

        for backend in self._backends:
            await self._run_backend_call(backend, backend.clear)
        await self._publish_event(EventType.CLEAR, "")
        await self._event_hook.emit("clear")

    async def delete_prefix(self, prefix: str) -> None:
        """删除指定前缀下的所有缓存数据。"""

        normalized_prefix = self._normalize_key(prefix)
        for backend in self._backends:
            if isinstance(backend, SupportsPrefixDelete):
                await self._run_backend_call(backend, backend.delete_prefix, normalized_prefix)
                continue
            await self._run_backend_call(backend, backend.clear)
        await self._publish_event(EventType.DELETE_PREFIX, normalized_prefix)
        await self._event_hook.emit("delete_prefix", prefix=normalized_prefix)

    async def get_or_load(
        self,
        key: str,
        loader: Loader,
        ttl: int | None = None,
        soft_ttl: int | None = None,
        *,
        loader_timeout: float | None = None,
        refresh_timeout: float | None = None,
        fallback: LoaderFallback | object = _NO_FALLBACK,
        policy: CachePolicy | None = None,
    ) -> Any:
        """读取缓存，未命中时执行回源加载并写回缓存。

        参数:
            key: 业务缓存 Key。
            loader: 回源加载函数，支持同步或异步调用。
            ttl: 硬过期 TTL 秒数，未传入时使用默认 TTL。
            soft_ttl: 软过期 TTL 秒数，未传入时使用默认软过期配置。

        返回:
            Any: 命中的缓存值或回源加载后的结果。
        """

        resolved_policy = self._resolve_policy(
            ttl=ttl,
            soft_ttl=soft_ttl,
            loader_timeout=loader_timeout,
            refresh_timeout=refresh_timeout,
            policy=policy,
        )
        normalized_key = self._normalize_key(key)
        envelope, layer_name = await self._get_envelope_with_source(
            normalized_key,
            include_hard_expired=True,
        )
        if envelope is not None and not envelope.is_hard_expired():
            if should_return_stale(envelope, resolved_policy.enable_stale):
                await self._metrics_hook.on_stale_return(normalized_key)
                log_cache_event(
                    self._logger,
                    logging.DEBUG,
                    "stale_return",
                    key=normalized_key,
                )
                await self._event_hook.emit("stale_return", key=normalized_key)
                self._schedule_background_refresh(normalized_key, loader, resolved_policy)
            await self._metrics_hook.on_hit(normalized_key, layer=layer_name)
            await self._event_hook.emit("hit", key=normalized_key, layer=layer_name)
            return envelope.resolve_value()

        await self._metrics_hook.on_miss(normalized_key)
        await self._event_hook.emit("miss", key=normalized_key)
        try:
            return await self._singleflight.do(
                normalized_key,
                lambda: self._load_and_store_with_lock(
                    normalized_key,
                    loader,
                    policy=resolved_policy,
                    fallback=fallback,
                ),
            )
        except Exception as exc:
            if envelope is not None:
                log_cache_event(
                    self._logger,
                    logging.WARNING,
                    "loader_fallback",
                    key=normalized_key,
                )
                await self._metrics_hook.on_fallback(normalized_key, "stale")
                await self._event_hook.emit("fallback", key=normalized_key, source="stale")
                return envelope.resolve_value()
            if fallback is not _NO_FALLBACK:
                await self._metrics_hook.on_fallback(normalized_key, "fallback")
                await self._event_hook.emit("fallback", key=normalized_key, source="fallback")
                return await self._resolve_fallback(fallback, exc)
            raise

    async def get_many_or_load(
        self,
        loaders: Mapping[str, Loader],
        ttl: int | None = None,
        soft_ttl: int | None = None,
        *,
        loader_timeout: float | None = None,
        refresh_timeout: float | None = None,
        policy: CachePolicy | None = None,
    ) -> dict[str, Any]:
        """批量读取缓存，未命中时按 Key 执行回源。"""

        tasks = {
            key: asyncio.create_task(
                self.get_or_load(
                    key,
                    loader,
                    ttl=ttl,
                    soft_ttl=soft_ttl,
                    loader_timeout=loader_timeout,
                    refresh_timeout=refresh_timeout,
                    policy=policy,
                ),
            )
            for key, loader in loaders.items()
        }
        return {key: await task for key, task in tasks.items()}

    async def warmup(self, items: list[WarmupItem]) -> None:
        """执行缓存预热任务。

        参数:
            items: 预热项列表。

        返回:
            None。
        """

        await self._warmup_engine.run(self, items)

    def health_snapshot(self) -> dict[str, Any]:
        """返回当前缓存管理器的健康快照。"""

        backends: list[dict[str, Any]] = []
        degraded = False
        for backend in self._backends:
            circuit = self._backend_circuits.get(id(backend))
            circuit_state = None if circuit is None else circuit.state.value
            if circuit_state == "open":
                degraded = True
            backends.append(
                {
                    "name": backend.name,
                    "circuit_state": circuit_state,
                }
            )

        status = "degraded" if degraded else "ok"
        with suppress(RuntimeError):
            loop = asyncio.get_running_loop()
            loop.create_task(self._metrics_hook.on_health_snapshot(status))
            loop.create_task(self._event_hook.emit("health_snapshot", status=status))
        return {
            "status": status,
            "backends": backends,
            "broadcast_enabled": self._config.broadcast.enabled,
            "warmup_enabled": self._config.warmup.enabled,
        }

    async def close(self) -> None:
        """关闭缓存管理器及其所有运行时资源。

        参数:
            无。

        返回:
            None。
        """

        for task in tuple(self._background_tasks):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        await self._broadcaster.close()

        for backend in reversed(self._backends):
            await backend.close()

    async def _get_envelope(
        self,
        key: str,
        *,
        include_hard_expired: bool = False,
    ) -> CacheEnvelope | None:
        """按后端优先级读取缓存包装对象。

        参数:
            key: 规范化后的缓存 Key。
            include_hard_expired: 是否允许返回硬过期但尚未被清理的缓存值。

        返回:
            CacheEnvelope | None: 命中时返回缓存包装对象，否则返回 None。
        """

        envelope, _layer_name = await self._get_envelope_with_source(
            key,
            include_hard_expired=include_hard_expired,
        )
        return envelope

    async def _get_envelope_with_source(
        self,
        key: str,
        *,
        include_hard_expired: bool = False,
    ) -> tuple[CacheEnvelope | None, str | None]:
        """按后端优先级读取缓存包装对象并返回命中层名称。"""

        for index, backend in enumerate(self._backends):
            try:
                if include_hard_expired and isinstance(backend, SupportsStaleRead):
                    envelope = await self._run_backend_call(backend, backend.get_stale, key)
                else:
                    envelope = await self._run_backend_call(backend, backend.get, key)
            except (BackendError, CircuitBreakerOpenError):
                continue
            if envelope is None:
                continue

            if envelope.is_hard_expired():
                if include_hard_expired:
                    return envelope, backend.name
                try:
                    await self._run_backend_call(backend, backend.delete, key)
                except (BackendError, CircuitBreakerOpenError):
                    pass
                continue

            if index > 0:
                await self._backfill_front_layers(key, envelope, index)
            return envelope, backend.name
        return None, None

    async def _load_and_store(
        self,
        key: str,
        loader: Loader,
        *,
        policy: CachePolicy,
    ) -> Any:
        """执行回源加载并将结果写入缓存。

        参数:
            key: 规范化后的缓存 Key。
            loader: 回源加载函数，支持同步或异步。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            Any: 回源加载得到的值。
        """

        await self._metrics_hook.on_loader_start(key)
        await self._event_hook.emit("loader_start", key=key)
        started_at = perf_counter()
        try:
            loaded_value = await self._resolve_loader(loader, timeout=policy.loader_timeout)
        except Exception:
            await self._metrics_hook.on_loader_error(key)
            await self._metrics_hook.on_loader_complete(
                key,
                perf_counter() - started_at,
                outcome="error",
            )
            log_cache_event(
                self._logger,
                logging.ERROR,
                "loader_error",
                key=key,
            )
            await self._event_hook.emit("loader_error", key=key)
            raise
        await self._metrics_hook.on_loader_complete(
            key,
            perf_counter() - started_at,
            outcome="success",
        )
        await self._event_hook.emit("loader_success", key=key)
        if loaded_value is None and self._config.enable_null_cache:
            null_envelope = self._build_envelope(
                value=None,
                ttl=policy.null_ttl,
                soft_ttl=None,
                is_null=True,
            )
            await self._write_envelope(key, null_envelope)
            return None

        actual_ttl = self._resolve_ttl(policy.ttl, policy.ttl_jitter)
        loaded_envelope = self._build_envelope(
            value=loaded_value,
            ttl=actual_ttl,
            soft_ttl=policy.soft_ttl,
            is_null=False,
        )
        await self._write_envelope(key, loaded_envelope)
        return loaded_value

    async def _load_and_store_with_lock(
        self,
        key: str,
        loader: Loader,
        *,
        policy: CachePolicy,
        fallback: LoaderFallback | object = _NO_FALLBACK,
    ) -> Any:
        """在需要时结合分布式锁执行回源加载。

        参数:
            key: 规范化后的缓存 Key。
            loader: 回源加载函数。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            Any: 回源加载结果或等待其他实例填充后的缓存值。
        """

        redis_backend = self._get_redis_backend()
        if redis_backend is None:
            try:
                return await self._load_and_store(key, loader, policy=policy)
            except Exception as exc:
                if fallback is _NO_FALLBACK:
                    raise
                return await self._resolve_fallback(fallback, exc)

        try:
            acquired = await redis_backend.acquire_lock(key, self._config.redis.lock_timeout)
        except LockAcquisitionError:
            acquired = False

        if acquired:
            try:
                try:
                    return await self._load_and_store(key, loader, policy=policy)
                except Exception as exc:
                    if fallback is _NO_FALLBACK:
                        raise
                    return await self._resolve_fallback(fallback, exc)
            finally:
                try:
                    await redis_backend.release_lock(key)
                except LockAcquisitionError:
                    pass

        return await self._wait_for_populated_value(
            key,
            loader,
            policy=policy,
            fallback=fallback,
        )

    async def _backfill_front_layers(
        self,
        key: str,
        envelope: CacheEnvelope,
        source_index: int,
    ) -> None:
        """将下层缓存命中的数据回填到更前面的缓存层。

        参数:
            key: 规范化后的缓存 Key。
            envelope: 命中的缓存包装对象。
            source_index: 命中后端在后端链中的索引。

        返回:
            None。
        """

        ttl = envelope.remaining_ttl()
        for backend in self._backends[:source_index]:
            try:
                await self._run_backend_call(backend, backend.set, key, envelope, ttl=ttl)
            except (BackendError, CircuitBreakerOpenError):
                continue

    async def _write_envelope(self, key: str, envelope: CacheEnvelope) -> None:
        """将缓存包装对象写入所有已配置后端。

        参数:
            key: 规范化后的缓存 Key。
            envelope: 要写入的缓存包装对象。

        返回:
            None。
        """

        ttl = envelope.remaining_ttl()
        last_error: Exception | None = None
        success_count = 0
        for backend in self._backends:
            try:
                await self._run_backend_call(backend, backend.set, key, envelope, ttl=ttl)
                success_count += 1
            except (BackendError, CircuitBreakerOpenError) as exc:
                last_error = exc

        if success_count == 0 and last_error is not None:
            raise last_error
        await self._metrics_hook.on_set(key)

    async def _write_envelopes(self, values: Mapping[str, CacheEnvelope]) -> None:
        """将多个缓存包装对象写入所有已配置后端。"""

        if not values:
            return

        ttl = next(iter(values.values())).remaining_ttl()
        last_error: Exception | None = None
        success_count = 0
        for backend in self._backends:
            try:
                if isinstance(backend, SupportsBatchOperations):
                    await self._run_backend_call(backend, backend.mset, dict(values), ttl=ttl)
                else:
                    for key, envelope in values.items():
                        await self._run_backend_call(backend, backend.set, key, envelope, ttl=ttl)
                success_count += 1
            except (BackendError, CircuitBreakerOpenError) as exc:
                last_error = exc

        if success_count == 0 and last_error is not None:
            raise last_error
        for key in values:
            await self._metrics_hook.on_set(key)

    def _build_envelope(
        self,
        *,
        value: Any,
        ttl: int | None,
        soft_ttl: int | None,
        is_null: bool,
    ) -> CacheEnvelope:
        """根据值和过期策略构建缓存包装对象。

        参数:
            value: 要缓存的原始值。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。
            is_null: 是否为空值缓存。

        返回:
            CacheEnvelope: 构建完成的缓存包装对象。
        """

        created_at = utc_timestamp()
        hard_expire_at = created_at + ttl if ttl is not None else None
        soft_expire_at = created_at + soft_ttl if soft_ttl is not None else None
        return CacheEnvelope(
            value=value,
            created_at=created_at,
            soft_expire_at=soft_expire_at,
            hard_expire_at=hard_expire_at,
            is_null=is_null,
        )

    async def _publish_event(self, event_type: EventType, key: str) -> None:
        """发布缓存广播事件。

        参数:
            event_type: 广播事件类型。
            key: 规范化后的缓存 Key。

        返回:
            None。
        """

        event = CacheEvent(event=event_type, key=key, source=self._config.broadcast.instance_id)
        await self._broadcaster.publish(event)
        await self._metrics_hook.on_broadcast(key, event_type.value)
        await self._event_hook.emit("broadcast", key=key, event_type=event_type.value)

    def _resolve_policy(
        self,
        *,
        ttl: int | None = None,
        soft_ttl: int | None = None,
        loader_timeout: float | None = None,
        refresh_timeout: float | None = None,
        policy: CachePolicy | None = None,
    ) -> CachePolicy:
        """解析调用级策略并与全局默认配置合并。"""

        merged = policy or CachePolicy()
        return CachePolicy(
            ttl=ttl if ttl is not None else merged.ttl if merged.ttl is not None else self._config.default_ttl,
            soft_ttl=(
                soft_ttl
                if soft_ttl is not None
                else merged.soft_ttl
                if merged.soft_ttl is not None
                else self._config.default_soft_ttl
            ),
            null_ttl=merged.null_ttl if merged.null_ttl is not None else self._config.null_ttl,
            ttl_jitter=merged.ttl_jitter if merged.ttl_jitter is not None else self._config.ttl_jitter,
            enable_stale=(
                merged.enable_stale
                if merged.enable_stale is not None
                else self._config.enable_stale
            ),
            loader_timeout=(
                loader_timeout
                if loader_timeout is not None
                else merged.loader_timeout
                if merged.loader_timeout is not None
                else self._config.default_loader_timeout
            ),
            refresh_timeout=(
                refresh_timeout
                if refresh_timeout is not None
                else merged.refresh_timeout
                if merged.refresh_timeout is not None
                else self._config.default_refresh_timeout
            ),
        )

    def _resolve_refresh_policy(self, policy: CachePolicy) -> CachePolicy:
        """为后台刷新构建生效策略。"""

        refresh_timeout = (
            policy.refresh_timeout
            if policy.refresh_timeout is not None
            else policy.loader_timeout
        )
        return CachePolicy(
            ttl=policy.ttl,
            soft_ttl=policy.soft_ttl,
            null_ttl=policy.null_ttl,
            ttl_jitter=policy.ttl_jitter,
            enable_stale=policy.enable_stale,
            loader_timeout=refresh_timeout,
            refresh_timeout=policy.refresh_timeout,
        )

    def _resolve_ttl(self, ttl: int | None, ttl_jitter: int | None = None) -> int | None:
        """解析最终写入缓存使用的 TTL。

        参数:
            ttl: 调用方显式传入的 TTL 秒数。

        返回:
            int | None: 经过默认值与抖动处理后的 TTL。
        """

        base_ttl = ttl if ttl is not None else self._config.default_ttl
        if base_ttl is None:
            return None
        actual_jitter = self._config.ttl_jitter if ttl_jitter is None else ttl_jitter
        return apply_ttl_jitter(base_ttl, actual_jitter)

    async def _resolve_loader(self, loader: Loader, *, timeout: float | None = None) -> Any:
        """执行回源加载函数并兼容同步/异步结果。

        参数:
            loader: 回源加载函数。

        返回:
            Any: loader 执行后的结果。
        """

        result = loader()
        if not inspect.isawaitable(result):
            return result
        if timeout is None:
            return await result
        async with asyncio.timeout(timeout):
            return await result

    async def _resolve_fallback(
        self,
        fallback: LoaderFallback | object,
        exc: Exception,
    ) -> Any:
        """解析回源失败后的 fallback 值。"""

        if fallback is _NO_FALLBACK:
            raise exc
        if callable(fallback):
            result = fallback(exc)
            if inspect.isawaitable(result):
                return await result
            return result
        return fallback

    def _normalize_key(self, key: str) -> str:
        """规范化业务缓存 Key。

        参数:
            key: 调用方传入的业务缓存 Key。

        返回:
            str: 拼接命名空间后的内部缓存 Key。
        """

        return join_key_parts(self._config.namespace, key)

    def _schedule_background_refresh(
        self,
        key: str,
        loader: Loader,
        policy: CachePolicy,
    ) -> None:
        """调度后台刷新任务。

        参数:
            key: 规范化后的缓存 Key。
            loader: 回源加载函数。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            None。
        """

        if key in self._singleflight._futures:
            return
        task = asyncio.create_task(self._background_refresh(key, loader, policy))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _background_refresh(
        self,
        key: str,
        loader: Loader,
        policy: CachePolicy,
    ) -> None:
        """后台刷新陈旧缓存。

        参数:
            key: 规范化后的缓存 Key。
            loader: 回源加载函数。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            None。
        """

        started_at = perf_counter()
        refresh_policy = self._resolve_refresh_policy(policy)
        await self._event_hook.emit("refresh_start", key=key)
        try:
            await self._singleflight.do(
                key,
                lambda: self._load_and_store_with_lock(key, loader, policy=refresh_policy),
            )
            await self._metrics_hook.on_background_refresh_success(
                key,
                perf_counter() - started_at,
            )
            await self._event_hook.emit("refresh_success", key=key)
            await self._event_hook.emit("background_refresh_success", key=key)
        except Exception:
            await self._metrics_hook.on_background_refresh_error(key)
            await self._event_hook.emit("refresh_error", key=key)
            await self._event_hook.emit("background_refresh_error", key=key)

    async def _wait_for_populated_value(
        self,
        key: str,
        loader: Loader,
        *,
        policy: CachePolicy,
        fallback: LoaderFallback | object = _NO_FALLBACK,
    ) -> Any:
        """等待其他实例回填缓存，超时后自行回源。

        参数:
            key: 规范化后的缓存 Key。
            loader: 回源加载函数。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            Any: 等待命中的缓存值，或兜底自行回源后的结果。
        """

        attempts = max(
            1,
            int(self._config.redis.lock_timeout / self._config.redis.lock_sleep_interval),
        )
        wait_started_at = perf_counter()
        for _ in range(attempts):
            await asyncio.sleep(self._config.redis.lock_sleep_interval)
            envelope = await self._get_envelope(key)
            if envelope is not None and not envelope.is_hard_expired():
                await self._metrics_hook.on_lock_wait(
                    key,
                    perf_counter() - wait_started_at,
                )
                return envelope.resolve_value()

        redis_backend = self._get_redis_backend()
        if redis_backend is None:
            try:
                return await self._load_and_store(key, loader, policy=policy)
            except Exception as exc:
                if fallback is _NO_FALLBACK:
                    raise
                return await self._resolve_fallback(fallback, exc)

        try:
            acquired = await redis_backend.acquire_lock(key, self._config.redis.lock_timeout)
        except LockAcquisitionError:
            acquired = False

        if acquired:
            try:
                envelope = await self._get_envelope(key)
                if envelope is not None and not envelope.is_hard_expired():
                    await self._metrics_hook.on_lock_wait(
                        key,
                        perf_counter() - wait_started_at,
                    )
                    return envelope.resolve_value()
                try:
                    return await self._load_and_store(key, loader, policy=policy)
                except Exception as exc:
                    if fallback is _NO_FALLBACK:
                        raise
                    return await self._resolve_fallback(fallback, exc)
            finally:
                try:
                    await redis_backend.release_lock(key)
                except LockAcquisitionError:
                    pass

        envelope = await self._get_envelope(key)
        if envelope is not None and not envelope.is_hard_expired():
            await self._metrics_hook.on_lock_wait(key, perf_counter() - wait_started_at)
            return envelope.resolve_value()

        try:
            return await self._load_and_store(key, loader, policy=policy)
        except Exception as exc:
            if fallback is _NO_FALLBACK:
                raise
            return await self._resolve_fallback(fallback, exc)

    async def _start_warmup_tasks(self) -> None:
        """根据配置启动预热任务。

        参数:
            无。

        返回:
            None。
        """

        if not self._config.warmup.enabled or not self._warmup_items:
            return

        if self._config.warmup.run_on_startup:
            await self.warmup(self._warmup_items)

        if self._config.warmup.interval_seconds is None:
            return

        task = asyncio.create_task(
            self._warmup_engine.run_periodic(
                self,
                self._warmup_items,
                self._config.warmup,
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _build_backend_circuits(self) -> dict[int, CircuitBreaker]:
        """为每个后端实例构建独立熔断器。

        参数:
            无。

        返回:
            dict[int, CircuitBreaker]: 以后端对象标识为键的熔断器映射。
        """

        if not self._config.circuit_breaker.enabled:
            return {}
        return {
            id(backend): CircuitBreaker(self._config.circuit_breaker)
            for backend in self._backends
        }

    def _get_redis_backend(self) -> RedisCacheBackend | None:
        """返回后端链中的 Redis 后端实例。

        参数:
            无。

        返回:
            RedisCacheBackend | None: 找到时返回 Redis 后端，否则返回 None。
        """

        for backend in self._backends:
            if isinstance(backend, RedisCacheBackend):
                return backend
        return None

    def _build_broadcaster(self, broadcaster: BaseBroadcaster | None) -> BaseBroadcaster:
        """构建广播器实例。

        参数:
            broadcaster: 调用方显式传入的广播器。

        返回:
            BaseBroadcaster: 实际要使用的广播器实例。
        """

        if broadcaster is not None:
            return broadcaster
        if not self._config.broadcast.enabled or not self._config.redis.enabled:
            return NoOpBroadcaster()
        return RedisBroadcaster.from_url(
            self._config.redis.url,
            self._config.broadcast,
            event_handler=self._handle_broadcast_event,
        )

    async def _run_backend_call(self, backend: BaseCacheBackend, func, *args, **kwargs):
        """执行受熔断器保护的后端调用。

        参数:
            backend: 当前要调用的缓存后端。
            func: 后端具体方法。
            *args: 位置参数。
            **kwargs: 关键字参数。

        返回:
            Any: 后端方法返回值。

        异常:
            CircuitBreakerOpenError: 对应后端已熔断时抛出。
            Exception: 后端调用执行失败时透传原始异常。
        """

        circuit = self._backend_circuits.get(id(backend))
        if circuit is None:
            return await func(*args, **kwargs)

        try:
            circuit.allow()
        except CircuitBreakerOpenError:
            await self._metrics_hook.on_circuit_open(backend.name)
            await self._event_hook.emit("circuit_open", backend=backend.name)
            log_cache_event(
                self._logger,
                logging.WARNING,
                "circuit_open",
                backend=backend.name,
            )
            raise
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            circuit.record_failure()
            log_cache_event(
                self._logger,
                logging.ERROR,
                "backend_error",
                backend=backend.name,
                error=str(exc),
            )
            raise

        circuit.record_success()
        return result

    async def _handle_broadcast_event(self, event: CacheEvent) -> None:
        """处理收到的广播事件并同步本地 L1 状态。

        参数:
            event: 收到的缓存广播事件。

        返回:
            None。
        """

        if event.event is EventType.CLEAR:
            await self._clear_local_backends()
            return
        if event.event is EventType.DELETE_PREFIX:
            await self._delete_prefix_from_local_backends(event.key)
            return

        await self._delete_from_local_backends(event.key)

    async def _clear_local_backends(self) -> None:
        """清空所有本地缓存后端。

        参数:
            无。

        返回:
            None。
        """

        for backend in self._backends:
            if isinstance(backend, LocalCacheBackend):
                await backend.clear()

    async def _delete_from_local_backends(self, key: str) -> None:
        """从所有本地缓存后端删除指定 Key。

        参数:
            key: 要删除的规范化缓存 Key。

        返回:
            None。
        """

        for backend in self._backends:
            if isinstance(backend, LocalCacheBackend):
                await backend.delete(key)

    async def _delete_prefix_from_local_backends(self, prefix: str) -> None:
        """从所有本地缓存后端删除指定前缀。"""

        for backend in self._backends:
            if isinstance(backend, SupportsPrefixDelete):
                await backend.delete_prefix(prefix)

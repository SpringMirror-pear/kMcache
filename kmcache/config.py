"""Configuration models for kmcache."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from typing import Mapping

from kmcache.constants import (
    DEFAULT_BROADCAST_CHANNEL,
    DEFAULT_CACHE_NAME,
    DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
    DEFAULT_CIRCUIT_HALF_OPEN_MAX_CALLS,
    DEFAULT_CIRCUIT_RECOVERY_TIMEOUT,
    DEFAULT_LOCAL_MAX_SIZE,
    DEFAULT_NAMESPACE,
    DEFAULT_NULL_TTL,
    DEFAULT_REDIS_TIMEOUT,
    DEFAULT_TTL,
    DEFAULT_TTL_JITTER,
)


@dataclass(slots=True)
class LocalCacheConfig:
    """L1 本地缓存配置。"""

    enabled: bool = True
    name: str = "l1"
    max_size: int = DEFAULT_LOCAL_MAX_SIZE
    default_ttl: int = DEFAULT_TTL

    def __post_init__(self) -> None:
        """初始化后校验本地缓存配置。

        参数:
            无。

        返回:
            None。
        """

        if self.max_size <= 0:
            msg = "local.max_size must be greater than 0"
            raise ValueError(msg)
        if self.default_ttl <= 0:
            msg = "local.default_ttl must be greater than 0"
            raise ValueError(msg)


@dataclass(slots=True)
class RedisCacheConfig:
    """L2 Redis 缓存配置。"""

    enabled: bool = True
    name: str = "l2"
    url: str = "redis://localhost:6379/0"
    key_prefix: str = DEFAULT_CACHE_NAME
    socket_timeout: float = DEFAULT_REDIS_TIMEOUT
    lock_timeout: float = 5.0
    lock_sleep_interval: float = 0.05

    def __post_init__(self) -> None:
        """初始化后校验 Redis 缓存配置。

        参数:
            无。

        返回:
            None。
        """

        if not self.url:
            msg = "redis.url must not be empty"
            raise ValueError(msg)
        if self.socket_timeout <= 0:
            msg = "redis.socket_timeout must be greater than 0"
            raise ValueError(msg)
        if self.lock_timeout <= 0:
            msg = "redis.lock_timeout must be greater than 0"
            raise ValueError(msg)
        if self.lock_sleep_interval <= 0:
            msg = "redis.lock_sleep_interval must be greater than 0"
            raise ValueError(msg)


@dataclass(slots=True)
class BroadcastConfig:
    """广播失效通知配置。"""

    enabled: bool = False
    channel: str = DEFAULT_BROADCAST_CHANNEL
    instance_id: str = "local-instance"

    def __post_init__(self) -> None:
        """初始化后校验广播配置。

        参数:
            无。

        返回:
            None。
        """

        if self.enabled and not self.channel:
            msg = "broadcast.channel must not be empty when broadcast is enabled"
            raise ValueError(msg)
        if not self.instance_id:
            msg = "broadcast.instance_id must not be empty"
            raise ValueError(msg)


@dataclass(slots=True)
class CircuitBreakerConfig:
    """熔断器配置。"""

    enabled: bool = True
    failure_threshold: int = DEFAULT_CIRCUIT_FAILURE_THRESHOLD
    recovery_timeout: float = DEFAULT_CIRCUIT_RECOVERY_TIMEOUT
    half_open_max_calls: int = DEFAULT_CIRCUIT_HALF_OPEN_MAX_CALLS

    def __post_init__(self) -> None:
        """初始化后校验熔断器配置。

        参数:
            无。

        返回:
            None。
        """

        if self.failure_threshold <= 0:
            msg = "circuit_breaker.failure_threshold must be greater than 0"
            raise ValueError(msg)
        if self.recovery_timeout <= 0:
            msg = "circuit_breaker.recovery_timeout must be greater than 0"
            raise ValueError(msg)
        if self.half_open_max_calls <= 0:
            msg = "circuit_breaker.half_open_max_calls must be greater than 0"
            raise ValueError(msg)


@dataclass(slots=True)
class WarmupConfig:
    """缓存预热任务配置。"""

    enabled: bool = True
    run_on_startup: bool = False
    interval_seconds: float | None = None

    def __post_init__(self) -> None:
        """初始化后校验预热配置。

        参数:
            无。

        返回:
            None。
        """

        if self.interval_seconds is not None and self.interval_seconds <= 0:
            msg = "warmup.interval_seconds must be greater than 0"
            raise ValueError(msg)


@dataclass(slots=True)
class CacheConfig:
    """缓存管理器顶层配置。"""

    enabled: bool = True
    namespace: str = DEFAULT_NAMESPACE
    key_prefix: str = DEFAULT_CACHE_NAME
    default_ttl: int = DEFAULT_TTL
    default_soft_ttl: int | None = None
    ttl_jitter: int = DEFAULT_TTL_JITTER
    null_ttl: int = DEFAULT_NULL_TTL
    enable_stale: bool = True
    enable_null_cache: bool = True
    default_loader_timeout: float | None = None
    default_refresh_timeout: float | None = None
    local: LocalCacheConfig = field(default_factory=LocalCacheConfig)
    redis: RedisCacheConfig = field(default_factory=RedisCacheConfig)
    broadcast: BroadcastConfig = field(default_factory=BroadcastConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    warmup: WarmupConfig = field(default_factory=WarmupConfig)

    def __post_init__(self) -> None:
        """初始化后校验全局缓存配置。

        参数:
            无。

        返回:
            None。
        """

        if not self.namespace:
            msg = "namespace must not be empty"
            raise ValueError(msg)
        if self.default_ttl <= 0:
            msg = "default_ttl must be greater than 0"
            raise ValueError(msg)
        if self.default_soft_ttl is not None and self.default_soft_ttl <= 0:
            msg = "default_soft_ttl must be greater than 0"
            raise ValueError(msg)
        if self.ttl_jitter < 0:
            msg = "ttl_jitter must be greater than or equal to 0"
            raise ValueError(msg)
        if self.null_ttl <= 0:
            msg = "null_ttl must be greater than 0"
            raise ValueError(msg)
        if self.default_loader_timeout is not None and self.default_loader_timeout <= 0:
            msg = "default_loader_timeout must be greater than 0"
            raise ValueError(msg)
        if self.default_refresh_timeout is not None and self.default_refresh_timeout <= 0:
            msg = "default_refresh_timeout must be greater than 0"
            raise ValueError(msg)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        prefix: str = "KMCACHE_",
    ) -> "CacheConfig":
        """从环境变量映射构建缓存配置。"""

        source = env or os.environ
        normalized = {
            key[len(prefix) :].lower(): value
            for key, value in source.items()
            if key.startswith(prefix)
        }
        return cls.from_mapping(normalized)

    @classmethod
    def from_object(cls, settings: object) -> "CacheConfig":
        """从 settings 对象构建缓存配置。"""

        mapping = {
            name: getattr(settings, name)
            for name in dir(settings)
            if not name.startswith("_") and not callable(getattr(settings, name))
        }
        return cls.from_mapping(mapping)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CacheConfig":
        """从扁平或嵌套字典构建缓存配置。"""

        def read_value(name: str, default: Any = None) -> Any:
            if name in mapping:
                return mapping[name]
            return default

        def read_nested(section: str) -> Mapping[str, Any]:
            nested = mapping.get(section)
            if isinstance(nested, Mapping):
                return nested
            return {}

        def pick(section: str, name: str, default: Any = None) -> Any:
            flat_name = f"{section}_{name}"
            if flat_name in mapping:
                return mapping[flat_name]
            return read_nested(section).get(name, default)

        return cls(
            enabled=_parse_bool(read_value("enabled"), True),
            namespace=str(read_value("namespace", DEFAULT_NAMESPACE)),
            key_prefix=str(read_value("key_prefix", DEFAULT_CACHE_NAME)),
            default_ttl=_parse_int(read_value("default_ttl"), DEFAULT_TTL),
            default_soft_ttl=_parse_optional_int(read_value("default_soft_ttl")),
            ttl_jitter=_parse_int(read_value("ttl_jitter"), DEFAULT_TTL_JITTER),
            null_ttl=_parse_int(read_value("null_ttl"), DEFAULT_NULL_TTL),
            enable_stale=_parse_bool(read_value("enable_stale"), True),
            enable_null_cache=_parse_bool(read_value("enable_null_cache"), True),
            default_loader_timeout=_parse_optional_float(read_value("default_loader_timeout")),
            default_refresh_timeout=_parse_optional_float(read_value("default_refresh_timeout")),
            local=LocalCacheConfig(
                enabled=_parse_bool(pick("local", "enabled"), True),
                name=str(pick("local", "name", "l1")),
                max_size=_parse_int(pick("local", "max_size"), DEFAULT_LOCAL_MAX_SIZE),
                default_ttl=_parse_int(pick("local", "default_ttl"), DEFAULT_TTL),
            ),
            redis=RedisCacheConfig(
                enabled=_parse_bool(pick("redis", "enabled"), True),
                name=str(pick("redis", "name", "l2")),
                url=str(pick("redis", "url", "redis://localhost:6379/0")),
                key_prefix=str(pick("redis", "key_prefix", DEFAULT_CACHE_NAME)),
                socket_timeout=_parse_float(
                    pick("redis", "socket_timeout"),
                    DEFAULT_REDIS_TIMEOUT,
                ),
                lock_timeout=_parse_float(pick("redis", "lock_timeout"), 5.0),
                lock_sleep_interval=_parse_float(
                    pick("redis", "lock_sleep_interval"),
                    0.05,
                ),
            ),
            broadcast=BroadcastConfig(
                enabled=_parse_bool(pick("broadcast", "enabled"), False),
                channel=str(
                    pick("broadcast", "channel", DEFAULT_BROADCAST_CHANNEL),
                ),
                instance_id=str(pick("broadcast", "instance_id", "local-instance")),
            ),
            circuit_breaker=CircuitBreakerConfig(
                enabled=_parse_bool(pick("circuit_breaker", "enabled"), True),
                failure_threshold=_parse_int(
                    pick("circuit_breaker", "failure_threshold"),
                    DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
                ),
                recovery_timeout=_parse_float(
                    pick("circuit_breaker", "recovery_timeout"),
                    DEFAULT_CIRCUIT_RECOVERY_TIMEOUT,
                ),
                half_open_max_calls=_parse_int(
                    pick("circuit_breaker", "half_open_max_calls"),
                    DEFAULT_CIRCUIT_HALF_OPEN_MAX_CALLS,
                ),
            ),
            warmup=WarmupConfig(
                enabled=_parse_bool(pick("warmup", "enabled"), True),
                run_on_startup=_parse_bool(pick("warmup", "run_on_startup"), False),
                interval_seconds=_parse_optional_float(
                    pick("warmup", "interval_seconds"),
                ),
            ),
        )


def _parse_bool(value: Any, default: bool | None = None) -> bool:
    """解析布尔配置值。"""

    if value is None:
        if default is None:
            msg = "bool value is required"
            raise ValueError(msg)
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _parse_int(value: Any, default: int | None = None) -> int:
    """解析整数配置值。"""

    if value is None:
        if default is None:
            msg = "int value is required"
            raise ValueError(msg)
        return default
    return int(value)


def _parse_optional_int(value: Any) -> int | None:
    """解析可选整数配置值。"""

    if value in (None, ""):
        return None
    return int(value)


def _parse_float(value: Any, default: float | None = None) -> float:
    """解析浮点数配置值。"""

    if value is None:
        if default is None:
            msg = "float value is required"
            raise ValueError(msg)
        return default
    return float(value)


def _parse_optional_float(value: Any) -> float | None:
    """解析可选浮点数配置值。"""

    if value in (None, ""):
        return None
    return float(value)

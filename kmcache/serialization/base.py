"""缓存包装对象的序列化抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope
from kmcache.models import CURRENT_CACHE_ENVELOPE_VERSION
from kmcache.models import LEGACY_CACHE_ENVELOPE_VERSION


class BaseSerializer(ABC):
    """序列化器抽象接口。"""

    @abstractmethod
    def dumps(self, value: CacheEnvelope) -> str:
        """将缓存包装对象序列化为字符串。

        参数:
            value: 要序列化的缓存包装对象。

        返回:
            str: 序列化后的字符串载荷。
        """

    @abstractmethod
    def loads(self, payload: str) -> CacheEnvelope:
        """将字符串载荷反序列化为缓存包装对象。

        参数:
            payload: 待反序列化的字符串载荷。

        返回:
            CacheEnvelope: 反序列化后的缓存包装对象。
        """


def dump_envelope_payload(value: CacheEnvelope) -> dict[str, Any]:
    """构建统一的缓存包装对象序列化载荷。"""

    return {
        "value": value.value,
        "created_at": value.created_at,
        "soft_expire_at": value.soft_expire_at,
        "hard_expire_at": value.hard_expire_at,
        "is_null": value.is_null,
        "version": CURRENT_CACHE_ENVELOPE_VERSION,
    }


def load_envelope_payload(raw: Mapping[str, Any]) -> CacheEnvelope:
    """按版本策略解析并迁移缓存包装对象载荷。"""

    if not isinstance(raw, Mapping):
        raise SerializationError("cache envelope payload structure is invalid")

    version = _read_payload_version(raw)
    if version == CURRENT_CACHE_ENVELOPE_VERSION:
        normalized = dict(raw)
    elif version == LEGACY_CACHE_ENVELOPE_VERSION:
        try:
            normalized = _migrate_legacy_payload_v1(raw)
        except (KeyError, TypeError) as exc:
            raise SerializationError(
                "cache envelope payload structure is invalid",
            ) from exc
    else:
        msg = (
            "cache envelope version is unsupported: "
            f"expected <= {CURRENT_CACHE_ENVELOPE_VERSION}, got {version}"
        )
        raise SerializationError(msg)

    try:
        return CacheEnvelope(
            value=normalized.get("value"),
            created_at=normalized["created_at"],
            soft_expire_at=normalized.get("soft_expire_at"),
            hard_expire_at=normalized.get("hard_expire_at"),
            is_null=normalized.get("is_null", False),
            version=normalized["version"],
        )
    except (KeyError, TypeError) as exc:
        raise SerializationError("cache envelope payload structure is invalid") from exc


def _read_payload_version(raw: Mapping[str, Any]) -> int:
    """读取并标准化缓存包装对象版本。"""

    value = raw.get("version", LEGACY_CACHE_ENVELOPE_VERSION)
    try:
        version = int(value)
    except (TypeError, ValueError) as exc:
        raise SerializationError("cache envelope version is invalid") from exc
    if version <= 0:
        raise SerializationError("cache envelope version must be greater than 0")
    return version


def _migrate_legacy_payload_v1(raw: Mapping[str, Any]) -> dict[str, Any]:
    """将 v1 载荷迁移到当前版本。"""

    return {
        "value": raw.get("value"),
        "created_at": raw["created_at"],
        "soft_expire_at": raw.get("soft_expire_at"),
        "hard_expire_at": raw.get("hard_expire_at"),
        "is_null": raw.get("is_null", False),
        "version": CURRENT_CACHE_ENVELOPE_VERSION,
    }

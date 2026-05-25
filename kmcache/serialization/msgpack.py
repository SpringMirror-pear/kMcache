"""可选的 MessagePack 序列化实现。"""

from __future__ import annotations

import base64
import importlib
from typing import Any

from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope
from kmcache.serialization.base import BaseSerializer


class MessagePackSerializer(BaseSerializer):
    """基于可选 msgpack 依赖的缓存序列化器。"""

    def dumps(self, value: CacheEnvelope) -> str:
        """将缓存包装对象序列化为 MessagePack 字符串。"""

        payload = {
            "value": value.value,
            "created_at": value.created_at,
            "soft_expire_at": value.soft_expire_at,
            "hard_expire_at": value.hard_expire_at,
            "is_null": value.is_null,
            "version": value.version,
        }
        try:
            encoded = self._msgpack().packb(payload, use_bin_type=True)
            return base64.b64encode(encoded).decode("ascii")
        except SerializationError:
            raise
        except Exception as exc:
            raise SerializationError("msgpack serialization failed") from exc

    def loads(self, payload: str) -> CacheEnvelope:
        """将 MessagePack 字符串反序列化为缓存包装对象。"""

        try:
            decoded = base64.b64decode(payload.encode("ascii"))
            raw = self._msgpack().unpackb(decoded, raw=False)
        except SerializationError:
            raise
        except Exception as exc:
            raise SerializationError("msgpack deserialization failed") from exc

        try:
            return CacheEnvelope(
                value=raw.get("value"),
                created_at=raw["created_at"],
                soft_expire_at=raw.get("soft_expire_at"),
                hard_expire_at=raw.get("hard_expire_at"),
                is_null=raw.get("is_null", False),
                version=raw.get("version", 1),
            )
        except (KeyError, TypeError) as exc:
            raise SerializationError("msgpack payload structure is invalid") from exc

    def _msgpack(self) -> Any:
        """按需加载 msgpack 依赖。"""

        try:
            return importlib.import_module("msgpack")
        except ImportError as exc:
            raise SerializationError(
                "msgpack is not installed; install kmcache[msgpack] first",
            ) from exc

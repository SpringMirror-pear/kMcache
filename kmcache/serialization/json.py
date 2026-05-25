"""缓存包装对象的 JSON 序列化实现。"""

from __future__ import annotations

import json

from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope


class JsonSerializer:
    """基于标准库 json 的缓存序列化器。"""

    def dumps(self, value: CacheEnvelope) -> str:
        """将缓存包装对象序列化为 JSON 字符串。

        参数:
            value: 要序列化的缓存包装对象。

        返回:
            str: 序列化后的 JSON 字符串。
        """

        payload = {
            "value": value.value,
            "created_at": value.created_at,
            "soft_expire_at": value.soft_expire_at,
            "hard_expire_at": value.hard_expire_at,
            "is_null": value.is_null,
            "version": value.version,
        }
        try:
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except Exception as exc:
            raise SerializationError("json serialization failed") from exc

    def loads(self, payload: str) -> CacheEnvelope:
        """将 JSON 字符串反序列化为缓存包装对象。

        参数:
            payload: 待反序列化的 JSON 字符串。

        返回:
            CacheEnvelope: 解析后的缓存包装对象。
        """

        try:
            raw = json.loads(payload)
        except Exception as exc:
            raise SerializationError("json deserialization failed") from exc

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
            raise SerializationError("json payload structure is invalid") from exc

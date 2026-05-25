"""缓存包装对象的 JSON 序列化实现。"""

from __future__ import annotations

import json

from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope
from kmcache.serialization.base import dump_envelope_payload
from kmcache.serialization.base import load_envelope_payload


class JsonSerializer:
    """基于标准库 json 的缓存序列化器。"""

    def dumps(self, value: CacheEnvelope) -> str:
        """将缓存包装对象序列化为 JSON 字符串。

        参数:
            value: 要序列化的缓存包装对象。

        返回:
            str: 序列化后的 JSON 字符串。
        """

        payload = dump_envelope_payload(value)
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

        return load_envelope_payload(raw)

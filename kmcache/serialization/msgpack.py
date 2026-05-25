"""可选的 MessagePack 序列化实现。"""

from __future__ import annotations

import base64
import importlib
from typing import Any

from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope
from kmcache.serialization.base import BaseSerializer
from kmcache.serialization.base import dump_envelope_payload
from kmcache.serialization.base import load_envelope_payload


class MessagePackSerializer(BaseSerializer):
    """基于可选 msgpack 依赖的缓存序列化器。"""

    def dumps(self, value: CacheEnvelope) -> str:
        """将缓存包装对象序列化为 MessagePack 字符串。"""

        payload = dump_envelope_payload(value)
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

        return load_envelope_payload(raw)

    def _msgpack(self) -> Any:
        """按需加载 msgpack 依赖。"""

        try:
            return importlib.import_module("msgpack")
        except ImportError as exc:
            raise SerializationError(
                "msgpack is not installed; install kmcache[msgpack] first",
            ) from exc

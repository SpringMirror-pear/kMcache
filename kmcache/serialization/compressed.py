"""组合序列化器与压缩器的包装实现。"""

from __future__ import annotations

import base64

from kmcache.compression.base import BaseCompressor
from kmcache.serialization.base import BaseSerializer
from kmcache.models import CacheEnvelope


class CompressedSerializer(BaseSerializer):
    """通过 base64 将压缩后的二进制安全封装为字符串。"""

    def __init__(
        self,
        serializer: BaseSerializer,
        compressor: BaseCompressor,
    ) -> None:
        """初始化压缩序列化器。"""

        self._serializer = serializer
        self._compressor = compressor

    def dumps(self, value: CacheEnvelope) -> str:
        """序列化并压缩缓存包装对象。"""

        payload = self._serializer.dumps(value).encode("utf-8")
        compressed = self._compressor.compress(payload)
        return base64.b64encode(compressed).decode("ascii")

    def loads(self, payload: str) -> CacheEnvelope:
        """解压并反序列化缓存包装对象。"""

        raw = base64.b64decode(payload.encode("ascii"))
        decompressed = self._compressor.decompress(raw)
        return self._serializer.loads(decompressed.decode("utf-8"))

"""基于 gzip 的压缩器实现。"""

from __future__ import annotations

import gzip

from kmcache.compression.base import BaseCompressor


class GzipCompressor(BaseCompressor):
    """标准库 gzip 压缩器。"""

    def __init__(self, compresslevel: int = 6) -> None:
        """初始化 gzip 压缩器。"""

        if not 0 <= compresslevel <= 9:
            msg = "compresslevel must be between 0 and 9"
            raise ValueError(msg)
        self._compresslevel = compresslevel

    def compress(self, payload: bytes) -> bytes:
        """压缩原始字节载荷。"""

        return gzip.compress(payload, compresslevel=self._compresslevel)

    def decompress(self, payload: bytes) -> bytes:
        """解压字节载荷。"""

        return gzip.decompress(payload)

"""压缩器抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCompressor(ABC):
    """压缩器抽象接口。"""

    @abstractmethod
    def compress(self, payload: bytes) -> bytes:
        """压缩原始字节载荷。"""

    @abstractmethod
    def decompress(self, payload: bytes) -> bytes:
        """解压字节载荷。"""

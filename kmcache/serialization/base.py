"""缓存包装对象的序列化抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from kmcache.models import CacheEnvelope


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

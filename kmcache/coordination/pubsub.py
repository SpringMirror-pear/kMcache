"""广播集成所需的 Pub/Sub 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from kmcache.features.broadcast import CacheEvent


class BaseSubscriber(ABC):
    """缓存事件订阅者抽象接口。"""

    @abstractmethod
    async def start(self) -> None:
        """启动订阅监听。

        参数:
            无。

        返回:
            None。
        """

    @abstractmethod
    async def handle(self, event: CacheEvent) -> None:
        """处理单个缓存广播事件。

        参数:
            event: 收到的缓存广播事件。

        返回:
            None。
        """

    @abstractmethod
    async def close(self) -> None:
        """关闭订阅监听。

        参数:
            无。

        返回:
            None。
        """

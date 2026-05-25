"""事件钩子抽象。"""

from __future__ import annotations

from abc import ABC
from typing import Any


class BaseEventHook(ABC):
    """缓存事件钩子抽象接口。"""

    async def emit(self, event: str, **payload: Any) -> None:
        """发送缓存事件。"""

        del event, payload
        return None


class NoOpEventHook(BaseEventHook):
    """空事件钩子实现。"""


class InMemoryEventHook(BaseEventHook):
    """用于测试和调试的内存事件钩子。"""

    def __init__(self) -> None:
        """初始化内存事件钩子。"""

        self.events: list[dict[str, Any]] = []

    async def emit(self, event: str, **payload: Any) -> None:
        """记录事件及其载荷。"""

        self.events.append({"event": event, **payload})

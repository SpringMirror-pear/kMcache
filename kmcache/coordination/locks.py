"""异步锁辅助实现。"""

from __future__ import annotations

import asyncio


class KeyLockManager:
    """提供按缓存 Key 维度复用的异步锁。"""

    def __init__(self) -> None:
        """初始化 Key 级别锁管理器。

        参数:
            无。

        返回:
            None。
        """

        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get(self, key: str) -> asyncio.Lock:
        """获取指定 Key 的稳定锁对象。

        参数:
            key: 要获取锁的缓存 Key。

        返回:
            asyncio.Lock: 当前 Key 对应的异步锁对象。
        """

        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

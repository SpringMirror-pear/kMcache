"""Single-flight coordination for hot-key load deduplication."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class SingleFlightGroup:
    """保证同一 Key 在同一时刻只执行一次回源计算。"""

    def __init__(self) -> None:
        """初始化 single-flight 组。

        参数:
            无。

        返回:
            None。
        """

        self._futures: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()

    async def do(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        """执行按 Key 去重的异步计算。

        参数:
            key: 当前请求对应的缓存 Key。
            factory: 真正负责执行回源计算的异步工厂函数。

        返回:
            Any: 当前 Key 对应的共享计算结果。
        """

        async with self._lock:
            future = self._futures.get(key)
            if future is None:
                future = asyncio.get_running_loop().create_future()
                self._futures[key] = future
                owner = True
            else:
                owner = False

        if not owner:
            return await future

        try:
            result = await factory()
            future.set_result(result)
            return result
        except Exception as exc:
            future.add_done_callback(lambda completed: completed.exception())
            future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._futures.pop(key, None)

"""指标钩子抽象。"""

from __future__ import annotations

from abc import ABC
from collections import Counter


class BaseMetricsHook(ABC):
    """带默认空实现的异步指标钩子接口。"""

    async def on_hit(self, key: str, layer: str | None = None) -> None:
        """记录缓存命中事件。

        参数:
            key: 命中的缓存 Key。
            layer: 命中的缓存层名称。

        返回:
            None。
        """

        del key, layer
        return None

    async def on_miss(self, key: str) -> None:
        """记录缓存未命中事件。

        参数:
            key: 未命中的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_set(self, key: str) -> None:
        """记录缓存写入事件。

        参数:
            key: 被写入的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_delete(self, key: str) -> None:
        """记录缓存删除事件。

        参数:
            key: 被删除的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_background_refresh_error(self, key: str) -> None:
        """记录后台刷新失败事件。

        参数:
            key: 刷新失败的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_stale_return(self, key: str) -> None:
        """记录返回陈旧数据事件。

        参数:
            key: 返回陈旧数据的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_loader_start(self, key: str) -> None:
        """记录回源加载开始事件。

        参数:
            key: 开始回源的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_loader_error(self, key: str) -> None:
        """记录回源加载失败事件。

        参数:
            key: 回源失败的缓存 Key。

        返回:
            None。
        """

        del key
        return None

    async def on_loader_complete(
        self,
        key: str,
        duration_seconds: float,
        *,
        outcome: str,
    ) -> None:
        """记录回源加载完成事件。"""

        del key, duration_seconds, outcome
        return None

    async def on_broadcast(self, key: str, event: str) -> None:
        """记录广播事件。

        参数:
            key: 广播关联的缓存 Key。
            event: 广播事件类型。

        返回:
            None。
        """

        del key, event
        return None

    async def on_circuit_open(self, backend: str) -> None:
        """记录熔断器打开事件。

        参数:
            backend: 熔断对应的后端名称。

        返回:
            None。
        """

        del backend
        return None

    async def on_background_refresh_success(
        self,
        key: str,
        duration_seconds: float,
    ) -> None:
        """记录后台刷新成功事件。"""

        del key, duration_seconds
        return None

    async def on_lock_wait(self, key: str, duration_seconds: float) -> None:
        """记录锁等待事件。"""

        del key, duration_seconds
        return None

    async def on_fallback(self, key: str, source: str) -> None:
        """记录回退结果事件。"""

        del key, source
        return None

    async def on_health_snapshot(self, status: str) -> None:
        """记录健康快照事件。"""

        del status
        return None


class NoOpMetricsHook(BaseMetricsHook):
    """在未启用指标时使用的空实现。"""


class InMemoryMetricsHook(BaseMetricsHook):
    """用于测试和本地观测的内存指标实现。"""

    def __init__(self) -> None:
        """初始化内存指标钩子。

        参数:
            无。

        返回:
            None。
        """

        self._counters: Counter[str] = Counter()

    async def on_hit(self, key: str, layer: str | None = None) -> None:
        """记录缓存命中事件到内存计数器。

        参数:
            key: 命中的缓存 Key。
            layer: 命中的缓存层名称。

        返回:
            None。
        """

        del key
        self._counters["cache_hit_total"] += 1
        if layer is not None:
            self._counters[f"cache_{layer}_hit_total"] += 1

    async def on_miss(self, key: str) -> None:
        """记录缓存未命中事件到内存计数器。

        参数:
            key: 未命中的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_miss_total"] += 1

    async def on_set(self, key: str) -> None:
        """记录缓存写入事件到内存计数器。

        参数:
            key: 被写入的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_set_total"] += 1

    async def on_delete(self, key: str) -> None:
        """记录缓存删除事件到内存计数器。

        参数:
            key: 被删除的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_delete_total"] += 1

    async def on_background_refresh_error(self, key: str) -> None:
        """记录后台刷新失败事件到内存计数器。

        参数:
            key: 刷新失败的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_background_refresh_error_total"] += 1

    async def on_stale_return(self, key: str) -> None:
        """记录陈旧数据返回事件到内存计数器。

        参数:
            key: 返回陈旧数据的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_stale_return_total"] += 1

    async def on_loader_start(self, key: str) -> None:
        """记录回源开始事件到内存计数器。

        参数:
            key: 开始回源的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_loader_total"] += 1

    async def on_loader_error(self, key: str) -> None:
        """记录回源失败事件到内存计数器。

        参数:
            key: 回源失败的缓存 Key。

        返回:
            None。
        """

        del key
        self._counters["cache_loader_error_total"] += 1

    async def on_loader_complete(
        self,
        key: str,
        duration_seconds: float,
        *,
        outcome: str,
    ) -> None:
        """记录回源完成事件到内存计数器。"""

        del key
        self._counters[f"cache_loader_outcome_{outcome}_total"] += 1
        self._counters["cache_loader_duration_count"] += 1
        self._counters["cache_loader_duration_milliseconds_total"] += int(
            duration_seconds * 1000,
        )

    async def on_broadcast(self, key: str, event: str) -> None:
        """记录广播事件到内存计数器。

        参数:
            key: 广播关联的缓存 Key。
            event: 广播事件类型。

        返回:
            None。
        """

        del key, event
        self._counters["cache_broadcast_total"] += 1

    async def on_circuit_open(self, backend: str) -> None:
        """记录熔断器打开事件到内存计数器。

        参数:
            backend: 熔断对应的后端名称。

        返回:
            None。
        """

        del backend
        self._counters["cache_circuit_open_total"] += 1

    async def on_background_refresh_success(
        self,
        key: str,
        duration_seconds: float,
    ) -> None:
        """记录后台刷新成功事件到内存计数器。"""

        del key
        self._counters["cache_background_refresh_success_total"] += 1
        self._counters["cache_background_refresh_duration_count"] += 1
        self._counters["cache_background_refresh_duration_milliseconds_total"] += int(
            duration_seconds * 1000,
        )

    async def on_lock_wait(self, key: str, duration_seconds: float) -> None:
        """记录锁等待事件到内存计数器。"""

        del key
        self._counters["cache_lock_wait_total"] += 1
        self._counters["cache_lock_wait_milliseconds_total"] += int(
            duration_seconds * 1000,
        )

    async def on_fallback(self, key: str, source: str) -> None:
        """记录回退结果事件到内存计数器。"""

        del key
        self._counters["cache_fallback_total"] += 1
        self._counters[f"cache_fallback_{source}_total"] += 1

    async def on_health_snapshot(self, status: str) -> None:
        """记录健康快照事件到内存计数器。"""

        self._counters[f"cache_health_{status}_total"] += 1

    def snapshot(self) -> dict[str, int]:
        """返回当前指标快照。

        参数:
            无。

        返回:
            dict[str, int]: 当前内存指标计数字典。
        """

        return dict(self._counters)

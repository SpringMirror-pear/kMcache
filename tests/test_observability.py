"""可观测性测试。"""

from __future__ import annotations

import logging
import unittest

from kmcache.backends.local import LocalCacheBackend
from kmcache.config import CacheConfig, CircuitBreakerConfig
from kmcache.manager import CacheManager
from kmcache.observability.events import InMemoryEventHook
from kmcache.observability.logging import log_cache_event
from kmcache.observability.metrics import InMemoryMetricsHook
from tests.test_manager import FailingBackend


class ListHandler(logging.Handler):
    """用于捕获日志记录的测试处理器。"""

    def __init__(self) -> None:
        """初始化测试日志处理器。

        参数:
            无。

        返回:
            None。
        """

        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """收集格式化后的日志消息。

        参数:
            record: 日志记录对象。

        返回:
            None。
        """

        self.messages.append(record.getMessage())


class ObservabilityTests(unittest.IsolatedAsyncioTestCase):
    """可观测性相关测试。"""

    def setUp(self) -> None:
        """初始化测试日志配置。

        参数:
            无。

        返回:
            None。
        """

        self._logger = logging.getLogger("kmcache")
        self._previous_handlers = list(self._logger.handlers)
        self._previous_propagate = self._logger.propagate
        self._capture_handler = ListHandler()
        self._logger.handlers = [self._capture_handler]
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

    def tearDown(self) -> None:
        """恢复测试前的日志配置。

        参数:
            无。

        返回:
            None。
        """

        self._logger.handlers = self._previous_handlers
        self._logger.propagate = self._previous_propagate

    async def test_in_memory_metrics_hook_tracks_cache_events(self) -> None:
        """验证内存指标钩子会记录核心缓存事件。

        参数:
            无。

        返回:
            None。
        """

        metrics = InMemoryMetricsHook()
        cache = CacheManager(
            [LocalCacheBackend()],
            CacheConfig(ttl_jitter=0, enable_stale=False),
            metrics_hook=metrics,
        )

        async def loader() -> str:
            return "value"

        await cache.get("missing")
        await cache.get_or_load("item:1", loader, ttl=60)
        await cache.get("item:1")
        await cache.delete("item:1")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["cache_miss_total"], 2)
        self.assertEqual(snapshot["cache_loader_total"], 1)
        self.assertEqual(snapshot["cache_set_total"], 1)
        self.assertEqual(snapshot["cache_hit_total"], 1)
        self.assertEqual(snapshot["cache_delete_total"], 1)

    async def test_in_memory_metrics_hook_tracks_loader_error_and_circuit_open(self) -> None:
        """验证指标钩子会记录回源失败和熔断打开事件。

        参数:
            无。

        返回:
            None。
        """

        metrics = InMemoryMetricsHook()
        cache = CacheManager(
            [FailingBackend(), LocalCacheBackend()],
            CacheConfig(
                ttl_jitter=0,
                circuit_breaker=CircuitBreakerConfig(
                    enabled=True,
                    failure_threshold=1,
                    recovery_timeout=60.0,
                    half_open_max_calls=1,
                ),
            ),
            metrics_hook=metrics,
        )

        async def loader() -> str:
            raise RuntimeError("loader failed")

        with self.assertRaises(RuntimeError):
            await cache.get_or_load("item:2", loader, ttl=60)
        await cache.get("item:2")
        await cache.get("item:2")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["cache_loader_error_total"], 1)
        self.assertEqual(snapshot["cache_circuit_open_total"], 2)

    async def test_log_cache_event_writes_structured_message(self) -> None:
        """验证结构化日志函数会输出预期字段。

        参数:
            无。

        返回:
            None。
        """

        logger = logging.getLogger("kmcache.test")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = ListHandler()
        logger.addHandler(handler)

        log_cache_event(
            logger,
            logging.INFO,
            "cache_test",
            key="default:user:1",
            backend="l1",
        )

        self.assertEqual(len(handler.messages), 1)
        self.assertIn("event=cache_test", handler.messages[0])
        self.assertIn("key='default:user:1'", handler.messages[0])
        self.assertIn("backend='l1'", handler.messages[0])

    async def test_in_memory_event_hook_collects_emitted_events(self) -> None:
        """验证事件钩子可以收集关键缓存事件。"""

        event_hook = InMemoryEventHook()
        cache = CacheManager(
            [LocalCacheBackend()],
            CacheConfig(ttl_jitter=0),
            event_hook=event_hook,
        )

        async def loader() -> str:
            return "value"

        await cache.get("missing")
        await cache.get_or_load("item:1", loader, ttl=60)
        await cache.delete("item:1")

        event_names = [item["event"] for item in event_hook.events]
        self.assertIn("miss", event_names)
        self.assertIn("loader_success", event_names)
        self.assertIn("delete", event_names)

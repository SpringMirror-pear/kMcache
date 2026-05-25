"""跨实例缓存失效广播抽象。"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.asyncio.client import Redis as RedisClient

from kmcache.config import BroadcastConfig
from kmcache.exceptions import BackendError
from kmcache.utils.time import utc_timestamp


class EventType(StrEnum):
    """支持的广播事件类型。"""

    SET = "set"
    DELETE = "delete"
    DELETE_PREFIX = "delete_prefix"
    CLEAR = "clear"
    EXPIRE = "expire"


@dataclass(slots=True)
class CacheEvent:
    """可序列化的缓存失效广播事件。"""

    event: EventType
    key: str
    source: str
    timestamp: float = field(default_factory=utc_timestamp)

    def as_dict(self) -> dict[str, str | float]:
        """将事件转换为字典载荷。

        参数:
            无。

        返回:
            dict[str, str | float]: 可直接序列化的事件字典。
        """

        return asdict(self)


class BaseBroadcaster(ABC):
    """广播器抽象接口。"""

    @abstractmethod
    async def start(self) -> None:
        """启动广播器运行时资源。

        参数:
            无。

        返回:
            None。
        """

    @abstractmethod
    async def publish(self, event: CacheEvent) -> None:
        """发布缓存广播事件。

        参数:
            event: 要发布的缓存广播事件。

        返回:
            None。
        """

    @abstractmethod
    async def close(self) -> None:
        """关闭广播器资源。

        参数:
            无。

        返回:
            None。
        """


class NoOpBroadcaster(BaseBroadcaster):
    """在未启用广播时使用的空广播器实现。"""

    async def start(self) -> None:
        """启动空广播器。

        参数:
            无。

        返回:
            None。
        """

        return None

    async def publish(self, event: CacheEvent) -> None:
        """发布空广播事件，占位不执行任何逻辑。

        参数:
            event: 要发布的缓存广播事件。

        返回:
            None。
        """

        del event
        return None

    async def close(self) -> None:
        """关闭空广播器。

        参数:
            无。

        返回:
            None。
        """

        return None


class RedisBroadcaster(BaseBroadcaster):
    """基于 Redis Pub/Sub 的广播器实现。"""

    def __init__(
        self,
        client: RedisClient,
        config: BroadcastConfig,
        *,
        event_handler: Callable[[CacheEvent], Awaitable[None]] | None = None,
        owns_client: bool = False,
    ) -> None:
        """初始化 Redis 广播器。

        参数:
            client: Redis 异步客户端。
            config: 广播配置对象。
            event_handler: 收到事件后的异步处理函数。
            owns_client: 当前广播器是否负责关闭 Redis 客户端。

        返回:
            None。
        """

        self._client = client
        self._config = config
        self._event_handler = event_handler
        self._owns_client = owns_client
        self._pubsub: PubSub | None = None
        self._listener_task: asyncio.Task[None] | None = None

    @classmethod
    def from_url(
        cls,
        url: str,
        config: BroadcastConfig,
        *,
        event_handler: Callable[[CacheEvent], Awaitable[None]] | None = None,
    ) -> "RedisBroadcaster":
        """通过 Redis URL 创建广播器。

        参数:
            url: Redis 连接地址。
            config: 广播配置对象。
            event_handler: 收到事件后的异步处理函数。

        返回:
            RedisBroadcaster: 已初始化的 Redis 广播器实例。
        """

        client = Redis.from_url(url, decode_responses=True)
        return cls(
            client=client,
            config=config,
            event_handler=event_handler,
            owns_client=True,
        )

    async def start(self) -> None:
        """启动 Redis 广播监听。

        参数:
            无。

        返回:
            None。
        """

        if self._event_handler is None or self._listener_task is not None:
            return

        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(self._config.channel)
        self._listener_task = asyncio.create_task(self._listen())

    async def publish(self, event: CacheEvent) -> None:
        """发布 Redis 广播事件。

        参数:
            event: 要发布的缓存广播事件。

        返回:
            None。
        """

        payload = json.dumps(event.as_dict(), ensure_ascii=False, separators=(",", ":"))
        try:
            await self._client.publish(self._config.channel, payload)
        except Exception as exc:
            raise BackendError("redis broadcast publish failed") from exc

    async def close(self) -> None:
        """关闭 Redis 广播器资源。

        参数:
            无。

        返回:
            None。
        """

        if self._listener_task is not None:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        if self._pubsub is not None:
            await self._pubsub.unsubscribe(self._config.channel)
            await self._pubsub.aclose()
            self._pubsub = None

        if self._owns_client:
            await self._client.aclose()

    async def _listen(self) -> None:
        """监听 Redis 广播消息并分发事件。

        参数:
            无。

        返回:
            None。
        """

        if self._pubsub is None or self._event_handler is None:
            return

        while True:
            message = await self._pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message is None:
                await asyncio.sleep(0.05)
                continue

            raw = message.get("data")
            if not isinstance(raw, str):
                continue

            event = self._parse_event(raw)
            if event is None or event.source == self._config.instance_id:
                continue
            await self._event_handler(event)

    def _parse_event(self, payload: str) -> CacheEvent | None:
        """解析 Redis 广播消息为缓存事件。

        参数:
            payload: Redis Pub/Sub 原始消息。

        返回:
            CacheEvent | None: 解析成功时返回事件，否则返回 None。
        """

        try:
            raw = json.loads(payload)
            return CacheEvent(
                event=EventType(raw["event"]),
                key=raw["key"],
                source=raw["source"],
                timestamp=raw["timestamp"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

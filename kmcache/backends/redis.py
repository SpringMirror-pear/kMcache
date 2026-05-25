"""Redis L2 cache backend built on redis.asyncio."""

from __future__ import annotations

import uuid

from redis.asyncio import Redis
from redis.asyncio.client import Redis as RedisClient

from kmcache.backends.base import BaseCacheBackend
from kmcache.config import RedisCacheConfig
from kmcache.exceptions import BackendError
from kmcache.exceptions import LockAcquisitionError
from kmcache.models import CacheEnvelope
from kmcache.serialization.base import BaseSerializer
from kmcache.serialization.json import JsonSerializer
from kmcache.utils.keys import join_key_parts


class RedisCacheBackend(BaseCacheBackend):
    """基于 redis.asyncio 的 Redis L2 缓存后端。"""

    def __init__(
        self,
        client: RedisClient,
        config: RedisCacheConfig | None = None,
        *,
        serializer: BaseSerializer | None = None,
    ) -> None:
        """初始化 Redis 缓存后端。

        参数:
            client: 已创建好的 Redis 异步客户端。
            config: Redis 缓存配置，未传入时使用默认配置。
            serializer: 序列化器，未传入时使用 JSON 序列化器。

        返回:
            None。
        """

        self._config = config or RedisCacheConfig()
        self._client = client
        self._serializer = serializer or JsonSerializer()
        self.name = self._config.name
        self._lock_tokens: dict[str, str] = {}

    @classmethod
    def from_url(
        cls,
        url: str,
        config: RedisCacheConfig | None = None,
        *,
        serializer: BaseSerializer | None = None,
    ) -> "RedisCacheBackend":
        """通过 Redis URL 创建缓存后端。

        参数:
            url: Redis 连接地址。
            config: Redis 缓存配置，未传入时根据 url 构造默认配置。
            serializer: 序列化器，未传入时使用 JSON 序列化器。

        返回:
            RedisCacheBackend: 已初始化完成的 Redis 缓存后端实例。
        """

        resolved_config = config or RedisCacheConfig(url=url)
        client = Redis.from_url(
            url,
            socket_timeout=resolved_config.socket_timeout,
            decode_responses=True,
        )
        return cls(client=client, config=resolved_config, serializer=serializer)

    async def get(self, key: str) -> CacheEnvelope | None:
        """读取 Redis 缓存数据。

        参数:
            key: 要读取的缓存 Key。

        返回:
            CacheEnvelope | None: 命中时返回缓存包装对象，否则返回 None。
        """

        try:
            payload = await self._client.get(self._build_key(key))
        except Exception as exc:
            raise BackendError(f"redis get failed for key={key!r}") from exc

        if payload is None:
            return None
        return self._serializer.loads(payload)

    async def set(self, key: str, value: CacheEnvelope, ttl: int | None = None) -> None:
        """写入 Redis 缓存数据。

        参数:
            key: 要写入的缓存 Key。
            value: 要存储的缓存包装对象。
            ttl: 可选 TTL 秒数。

        返回:
            None。
        """

        try:
            payload = self._serializer.dumps(value)
            if ttl is None:
                await self._client.set(self._build_key(key), payload)
                return
            await self._client.set(self._build_key(key), payload, ex=ttl)
        except Exception as exc:
            raise BackendError(f"redis set failed for key={key!r}") from exc

    async def mget(self, keys: list[str]) -> list[CacheEnvelope | None]:
        """批量读取 Redis 缓存数据。"""

        try:
            payloads = await self._client.mget([self._build_key(key) for key in keys])
        except Exception as exc:
            raise BackendError("redis mget failed") from exc

        results: list[CacheEnvelope | None] = []
        for payload in payloads:
            if payload is None:
                results.append(None)
                continue
            results.append(self._serializer.loads(payload))
        return results

    async def mset(self, values: dict[str, CacheEnvelope], ttl: int | None = None) -> None:
        """批量写入 Redis 缓存数据。"""

        pipeline = self._client.pipeline()
        try:
            for key, value in values.items():
                payload = self._serializer.dumps(value)
                if ttl is None:
                    pipeline.set(self._build_key(key), payload)
                else:
                    pipeline.set(self._build_key(key), payload, ex=ttl)
            await pipeline.execute()
        except Exception as exc:
            raise BackendError("redis mset failed") from exc

    async def delete(self, key: str) -> None:
        """删除 Redis 缓存 Key。

        参数:
            key: 要删除的缓存 Key。

        返回:
            None。
        """

        try:
            await self._client.delete(self._build_key(key))
        except Exception as exc:
            raise BackendError(f"redis delete failed for key={key!r}") from exc

    async def delete_many(self, keys: list[str]) -> None:
        """批量删除 Redis 缓存 Key。"""

        if not keys:
            return
        try:
            await self._client.delete(*[self._build_key(key) for key in keys])
        except Exception as exc:
            raise BackendError("redis delete_many failed") from exc

    async def exists(self, key: str) -> bool:
        """判断 Redis 缓存 Key 是否存在。

        参数:
            key: 要检查的缓存 Key。

        返回:
            bool: 存在返回 True，否则返回 False。
        """

        try:
            return bool(await self._client.exists(self._build_key(key)))
        except Exception as exc:
            raise BackendError(f"redis exists failed for key={key!r}") from exc

    async def expire(self, key: str, ttl: int) -> None:
        """更新 Redis 缓存 Key 的 TTL。

        参数:
            key: 要更新的缓存 Key。
            ttl: 新的 TTL 秒数。

        返回:
            None。
        """

        try:
            await self._client.expire(self._build_key(key), ttl)
        except Exception as exc:
            raise BackendError(f"redis expire failed for key={key!r}") from exc

    async def clear(self) -> None:
        """清空当前前缀下的 Redis 缓存数据。

        参数:
            无。

        返回:
            None。
        """

        pattern = f"{self._config.key_prefix}:*"
        cursor = 0
        try:
            while True:
                cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            raise BackendError("redis clear failed") from exc

    async def delete_prefix(self, prefix: str) -> None:
        """删除指定前缀下的 Redis 缓存数据。"""

        pattern = f"{self._build_key(prefix)}*"
        cursor = 0
        try:
            while True:
                cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            raise BackendError("redis delete_prefix failed") from exc

    async def close(self) -> None:
        """关闭 Redis 客户端连接。

        参数:
            无。

        返回:
            None。
        """

        try:
            await self._client.aclose()
        except Exception as exc:
            raise BackendError("redis close failed") from exc

    async def acquire_lock(self, key: str, timeout: float | None = None) -> bool:
        """尝试获取 Redis 分布式锁。

        参数:
            key: 要加锁的缓存 Key。
            timeout: 锁过期秒数，未传入时使用配置默认值。

        返回:
            bool: 获取成功返回 True，否则返回 False。
        """

        lock_key = self._build_lock_key(key)
        token = uuid.uuid4().hex
        actual_timeout = timeout if timeout is not None else self._config.lock_timeout
        timeout_ms = max(1, int(actual_timeout * 1000))
        try:
            acquired = await self._client.set(lock_key, token, nx=True, px=timeout_ms)
        except Exception as exc:
            raise LockAcquisitionError(f"redis lock acquire failed for key={key!r}") from exc

        if acquired:
            self._lock_tokens[lock_key] = token
        return bool(acquired)

    async def release_lock(self, key: str) -> None:
        """释放 Redis 分布式锁。

        参数:
            key: 要释放的缓存 Key。

        返回:
            None。
        """

        lock_key = self._build_lock_key(key)
        token = self._lock_tokens.get(lock_key)
        if token is None:
            return

        script = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""
        try:
            await self._client.eval(script, 1, lock_key, token)
        except Exception as exc:
            raise LockAcquisitionError(f"redis lock release failed for key={key!r}") from exc
        finally:
            self._lock_tokens.pop(lock_key, None)

    def _build_key(self, key: str) -> str:
        """构造 Redis 实际存储使用的 Key。

        参数:
            key: 业务层传入的缓存 Key。

        返回:
            str: 带前缀的 Redis 实际存储 Key。
        """

        return join_key_parts(self._config.key_prefix, key)

    def _build_lock_key(self, key: str) -> str:
        """构造 Redis 分布式锁使用的 Key。

        参数:
            key: 业务层传入的缓存 Key。

        返回:
            str: 对应缓存 Key 的锁 Key。
        """

        return join_key_parts(self._config.key_prefix, "lock", key)

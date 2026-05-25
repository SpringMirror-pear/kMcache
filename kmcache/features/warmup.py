"""缓存预热辅助实现。"""

from __future__ import annotations

import asyncio
from typing import Protocol

from kmcache.config import WarmupConfig
from kmcache.models import WarmupItem


class SupportsGetOrLoad(Protocol):
    """供预热引擎使用的缓存协议。"""

    async def get_or_load(
        self,
        key: str,
        loader,
        ttl: int | None = None,
        soft_ttl: int | None = None,
    ):
        """在缓存未命中时加载并写入数据。

        参数:
            key: 业务缓存 Key。
            loader: 回源加载函数。
            ttl: 硬过期 TTL 秒数。
            soft_ttl: 软过期 TTL 秒数。

        返回:
            任意缓存值。
        """


class WarmupEngine:
    """顺序执行缓存预热任务。"""

    async def run(self, cache: SupportsGetOrLoad, items: list[WarmupItem]) -> None:
        """执行预热任务列表。

        参数:
            cache: 支持 get_or_load 的缓存对象。
            items: 要执行的预热任务列表。

        返回:
            None。
        """

        for item in items:
            await cache.get_or_load(
                item.key,
                item.loader,
                ttl=item.ttl,
                soft_ttl=item.soft_ttl,
            )

    async def run_periodic(
        self,
        cache: SupportsGetOrLoad,
        items: list[WarmupItem],
        config: WarmupConfig,
    ) -> None:
        """按固定周期循环执行预热任务。

        参数:
            cache: 支持 get_or_load 的缓存对象。
            items: 要执行的预热任务列表。
            config: 预热配置。

        返回:
            None。
        """

        if config.interval_seconds is None:
            return

        while True:
            await self.run(cache, items)
            await asyncio.sleep(config.interval_seconds)

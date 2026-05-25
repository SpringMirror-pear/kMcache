"""TTL jitter helpers used to reduce cache avalanche risk."""

from __future__ import annotations

import random


def apply_ttl_jitter(ttl: int, jitter: int) -> int:
    """为 TTL 增加随机抖动值。

    参数:
        ttl: 基础 TTL 秒数。
        jitter: 抖动上限秒数。

    返回:
        int: 增加正向随机抖动后的 TTL。
    """

    if jitter <= 0:
        return ttl
    return ttl + random.randint(0, jitter)

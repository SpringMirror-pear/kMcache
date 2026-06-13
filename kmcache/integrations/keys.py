"""常用缓存 Key 构造辅助。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kmcache.utils.keys import join_key_parts


def build_cache_key(*parts: Any, **named_parts: Any) -> str:
    """构建稳定的缓存 Key。"""

    ordered_named_parts = [f"{key}={value}" for key, value in sorted(named_parts.items())]
    return join_key_parts(*(str(part) for part in parts), *ordered_named_parts)


def prefix_key_builder(prefix: str) -> Callable[..., str]:
    """根据位置参数构造带固定前缀的缓存 Key。"""

    def builder(*parts: Any, **named_parts: Any) -> str:
        return build_cache_key(prefix, *parts, **named_parts)

    return builder

"""Helpers for cache key construction."""

from __future__ import annotations


def join_key_parts(*parts: str) -> str:
    """拼接缓存 Key 片段并跳过空值。

    参数:
        *parts: 参与拼接的 Key 片段。

    返回:
        str: 以冒号连接后的缓存 Key。
    """

    return ":".join(part for part in parts if part)

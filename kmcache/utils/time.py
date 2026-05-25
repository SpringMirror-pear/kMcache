"""Time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """返回当前 UTC 时间。

    参数:
        无。

    返回:
        datetime: 带时区信息的 UTC 时间对象。
    """

    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """返回当前 UTC 时间戳。

    参数:
        无。

    返回:
        float: 当前 UTC Unix 时间戳。
    """

    return utc_now().timestamp()

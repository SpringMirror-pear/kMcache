"""日志辅助函数。"""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str = "kmcache") -> logging.Logger:
    """获取包内统一日志对象。

    参数:
        name: 日志器名称。

    返回:
        logging.Logger: 对应名称的日志器实例。
    """

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def log_cache_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """输出结构化缓存事件日志。

    参数:
        logger: 目标日志器实例。
        level: 日志级别。
        event: 事件名称。
        **fields: 需要附带输出的上下文字段。

    返回:
        None。
    """

    parts = [f"event={event}"]
    parts.extend(f"{key}={value!r}" for key, value in fields.items() if value is not None)
    logger.log(level, " ".join(parts))

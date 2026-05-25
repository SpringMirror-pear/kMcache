"""缓存后端导出入口。"""

from __future__ import annotations

__all__ = ["BaseCacheBackend", "LocalCacheBackend", "RedisCacheBackend"]


def __getattr__(name: str):
    """按需导出后端实现，避免强制加载可选依赖。

    参数:
        name: 调用方请求的属性名称。

    返回:
        object: 对应名称的导出对象。
    """

    if name == "BaseCacheBackend":
        from kmcache.backends.base import BaseCacheBackend

        return BaseCacheBackend
    if name == "LocalCacheBackend":
        from kmcache.backends.local import LocalCacheBackend

        return LocalCacheBackend
    if name == "RedisCacheBackend":
        from kmcache.backends.redis import RedisCacheBackend

        return RedisCacheBackend
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

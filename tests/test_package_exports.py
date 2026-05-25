"""包导出与可选依赖导入测试。"""

from __future__ import annotations

import importlib
import unittest


class PackageExportTests(unittest.TestCase):
    """包导出策略测试。"""

    def test_top_level_package_does_not_require_optional_backends_on_import(self) -> None:
        """验证顶层包导入不依赖可选后端实现。

        参数:
            无。

        返回:
            None。
        """

        module = importlib.import_module("kmcache")
        self.assertEqual(module.__version__, "0.4.0")
        self.assertTrue(hasattr(module, "CacheManager"))
        self.assertTrue(hasattr(module, "CacheConfig"))
        self.assertTrue(hasattr(module, "cached"))
        self.assertTrue(hasattr(module, "create_cache_lifespan"))

    def test_backends_module_lazy_loads_redis_backend(self) -> None:
        """验证后端模块会延迟加载 Redis 后端。

        参数:
            无。

        返回:
            None。
        """

        backends = importlib.import_module("kmcache.backends")
        self.assertTrue(hasattr(backends, "LocalCacheBackend"))
        self.assertTrue(hasattr(backends, "RedisCacheBackend"))

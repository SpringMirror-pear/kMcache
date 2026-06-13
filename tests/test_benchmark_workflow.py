"""基准测试工作流入口测试。"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


class BenchmarkWorkflowTests(unittest.TestCase):
    """基准测试入口相关测试。"""

    def test_benchmark_script_exists_and_exports_main(self) -> None:
        """验证 benchmark 脚本存在且可加载。"""

        root = Path(__file__).resolve().parent.parent
        script_path = root / "scripts" / "benchmark.py"
        self.assertTrue(script_path.exists())

        spec = importlib.util.spec_from_file_location("kmcache_benchmark", script_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "main"))

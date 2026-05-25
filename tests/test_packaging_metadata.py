"""打包元数据测试。"""

from __future__ import annotations

import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

import build_backend


class PackagingMetadataTests(unittest.TestCase):
    """打包元数据相关测试。"""

    def test_pyproject_uses_optional_dependencies_for_frameworks_and_redis(self) -> None:
        """验证核心依赖为空且可选依赖声明完整。"""

        root = Path(__file__).resolve().parent.parent
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]

        self.assertEqual(project["version"], "0.4.0")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["dependencies"], [])
        self.assertIn("redis", project["optional-dependencies"])
        self.assertIn("fastapi", project["optional-dependencies"])
        self.assertIn("msgpack", project["optional-dependencies"])

    def test_build_backend_wheel_metadata_preserves_optional_dependencies(self) -> None:
        """验证自定义构建后端会写出预期的 wheel 元数据。"""

        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_name = build_backend.build_wheel(tmpdir)
            wheel_path = Path(tmpdir) / wheel_name

            with zipfile.ZipFile(wheel_path) as archive:
                metadata_name = "kmcache-0.4.0.dist-info/METADATA"
                metadata = archive.read(metadata_name).decode("utf-8")

        self.assertIn("Requires-Python: >=3.11", metadata)
        self.assertIn("Provides-Extra: fastapi", metadata)
        self.assertIn("Provides-Extra: redis", metadata)
        self.assertIn("Provides-Extra: msgpack", metadata)

"""质量检查流程入口测试。"""

from __future__ import annotations

import unittest
from pathlib import Path


class QualityWorkflowTests(unittest.TestCase):
    """质量检查流程文件测试。"""

    def test_quality_workflow_scripts_exist(self) -> None:
        """验证标准质量检查入口文件存在。

        参数:
            无。

        返回:
            None。
        """

        root = Path(__file__).resolve().parent.parent
        self.assertTrue((root / "scripts" / "check.py").exists())
        self.assertTrue((root / "scripts" / "check.ps1").exists())
        self.assertTrue((root / ".github" / "workflows" / "ci.yml").exists())

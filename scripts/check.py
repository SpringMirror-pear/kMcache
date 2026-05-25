"""标准化发布前质量检查入口。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(name: str, command: list[str]) -> None:
    """执行单个质量检查步骤。

    参数:
        name: 步骤名称。
        command: 要执行的命令参数列表。

    返回:
        None。
    """

    print(f"==> {name}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    """执行标准化质量检查流程。

    参数:
        无。

    返回:
        int: 成功时返回 0。
    """

    run_step(
        "Compile",
        [sys.executable, "-m", "compileall", "kmcache", "tests", "examples", "scripts"],
    )
    run_step(
        "Unit Tests",
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_local_backend",
            "tests.test_manager",
            "tests.test_avalanche",
            "tests.test_redis_backend",
            "tests.test_fastapi_integration",
            "tests.test_serialization",
            "tests.test_observability",
            "tests.test_config",
            "tests.test_package_exports",
            "tests.test_packaging_metadata",
            "tests.test_quality_workflow",
        ],
    )
    run_step(
        "Package Smoke",
        [
            sys.executable,
            "-c",
            (
                "import tempfile; from pathlib import Path; import build_backend; "
                "tmp = tempfile.TemporaryDirectory(); "
                "wheel_name = build_backend.build_wheel(tmp.name); "
                "wheel_path = Path(tmp.name) / wheel_name; "
                "assert wheel_path.exists(), wheel_path"
            ),
        ],
    )
    run_step(
        "Dependency Check",
        [sys.executable, "-m", "pip", "show", "fastapi"],
    )
    run_step(
        "Dependency Check",
        [sys.executable, "-m", "pip", "show", "redis"],
    )
    run_step(
        "Dependency Check",
        [sys.executable, "-m", "pip", "show", "httpx"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

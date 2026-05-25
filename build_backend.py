"""Pure-Python build backend for kmcache."""

from __future__ import annotations

import base64
import hashlib
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

PROJECT_NAME = "kmcache"
VERSION = "0.3.0"
WHEEL_TAG = "py3-none-any"
DIST_INFO = f"{PROJECT_NAME}-{VERSION}.dist-info"
ROOT = Path(__file__).resolve().parent


def _metadata_text() -> str:
    """Return wheel metadata content."""

    return "\n".join(
        [
            "Metadata-Version: 2.1",
            f"Name: {PROJECT_NAME}",
            f"Version: {VERSION}",
            "Summary: Async cache toolkit for FastAPI with pluggable L1/L2 backends.",
            "Requires-Python: >=3.11",
            "Provides-Extra: fastapi",
            "Requires-Dist: fastapi==0.136.1; extra == 'fastapi'",
            "Requires-Dist: httpx==0.28.1; extra == 'fastapi'",
            "Provides-Extra: redis",
            "Requires-Dist: redis==7.4.0; extra == 'redis'",
            "Provides-Extra: msgpack",
            "Requires-Dist: msgpack==1.1.2; extra == 'msgpack'",
            "Provides-Extra: all",
            "Requires-Dist: fastapi==0.136.1; extra == 'all'",
            "Requires-Dist: httpx==0.28.1; extra == 'all'",
            "Requires-Dist: redis==7.4.0; extra == 'all'",
            "Requires-Dist: msgpack==1.1.2; extra == 'all'",
            "",
        ]
    )


def _wheel_text() -> str:
    """Return wheel metadata content."""

    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: kmcache.build_backend",
            "Root-Is-Purelib: true",
            f"Tag: {WHEEL_TAG}",
            "",
        ]
    )


def _top_level_text() -> str:
    """Return top-level package listing."""

    return "kmcache\n"


def _record_hash(data: bytes) -> str:
    """Return a RECORD-compatible SHA256 digest."""

    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _iter_package_files() -> Iterable[Path]:
    """Yield all Python source files that should be packaged."""

    for path in sorted((ROOT / PROJECT_NAME).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _build_entries(editable: bool = False) -> list[tuple[str, bytes]]:
    """Build archive entries for a wheel."""

    entries: list[tuple[str, bytes]] = []

    if editable:
        entries.append((f"{PROJECT_NAME}.pth", f"{ROOT.as_posix()}\n".encode("utf-8")))
    else:
        for path in _iter_package_files():
            entries.append((path.relative_to(ROOT).as_posix(), path.read_bytes()))

    entries.extend(
        [
            (f"{DIST_INFO}/METADATA", _metadata_text().encode("utf-8")),
            (f"{DIST_INFO}/WHEEL", _wheel_text().encode("utf-8")),
            (f"{DIST_INFO}/top_level.txt", _top_level_text().encode("utf-8")),
        ]
    )
    return entries


def _write_wheel(wheel_path: Path, editable: bool = False) -> None:
    """Write a wheel archive."""

    entries = _build_entries(editable=editable)
    record_lines: list[str] = []

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative_path, data in entries:
            zf.writestr(relative_path, data)
            record_lines.append(
                ",".join([relative_path, _record_hash(data), str(len(data))])
            )

        record_lines.append(f"{DIST_INFO}/RECORD,,")
        zf.writestr(f"{DIST_INFO}/RECORD", ("\n".join(record_lines) + "\n").encode("utf-8"))


def _write_sdist(sdist_path: Path) -> None:
    """Write a source distribution archive."""

    with tarfile.open(sdist_path, "w:gz") as tar:
        for relative in [
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "build_backend.py",
        ]:
            tar.add(ROOT / relative, arcname=f"{PROJECT_NAME}-{VERSION}/{relative}")

        for folder in ["kmcache", "tests", "examples", "scripts", "docs"]:
            folder_path = ROOT / folder
            if not folder_path.exists():
                continue
            for path in sorted(folder_path.rglob("*")):
                if path.is_dir() or "__pycache__" in path.parts:
                    continue
                tar.add(path, arcname=f"{PROJECT_NAME}-{VERSION}/{path.relative_to(ROOT).as_posix()}")


def get_requires_for_build_wheel(config_settings=None):  # noqa: D401
    """Return build requirements for wheel builds."""

    del config_settings
    return []


def get_requires_for_build_sdist(config_settings=None):  # noqa: D401
    """Return build requirements for source distributions."""

    del config_settings
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):  # noqa: D401
    """Write metadata files for wheel builds."""

    del config_settings
    dist_info = Path(metadata_directory) / DIST_INFO
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_metadata_text(), encoding="utf-8")
    (dist_info / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    (dist_info / "top_level.txt").write_text(_top_level_text(), encoding="utf-8")
    (dist_info / "RECORD").write_text("", encoding="utf-8")
    return DIST_INFO


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):  # noqa: D401
    """Write metadata files for editable wheel builds."""

    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: D401
    """Build a standard wheel."""

    del config_settings, metadata_directory
    wheel_name = f"{PROJECT_NAME}-{VERSION}-{WHEEL_TAG}.whl"
    _write_wheel(Path(wheel_directory) / wheel_name, editable=False)
    return wheel_name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: D401
    """Build an editable wheel."""

    del config_settings, metadata_directory
    wheel_name = f"{PROJECT_NAME}-{VERSION}-{WHEEL_TAG}.whl"
    _write_wheel(Path(wheel_directory) / wheel_name, editable=True)
    return wheel_name


def build_sdist(sdist_directory, config_settings=None):  # noqa: D401
    """Build a source distribution."""

    del config_settings
    sdist_name = f"{PROJECT_NAME}-{VERSION}.tar.gz"
    _write_sdist(Path(sdist_directory) / sdist_name)
    return sdist_name

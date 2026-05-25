"""稳定 Key 推导所需的哈希辅助函数。"""

from __future__ import annotations

import hashlib


def stable_sha256(value: str) -> str:
    """计算字符串的稳定 SHA-256 摘要。

    参数:
        value: 待计算摘要的原始字符串。

    返回:
        str: 十六进制 SHA-256 摘要字符串。
    """

    return hashlib.sha256(value.encode("utf-8")).hexdigest()

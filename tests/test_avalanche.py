"""缓存雪崩防护相关测试。"""

from __future__ import annotations

import random
import unittest

from kmcache.features.avalanche import apply_ttl_jitter


class AvalancheTests(unittest.TestCase):
    """TTL 抖动逻辑测试。"""

    def test_apply_ttl_jitter_returns_original_ttl_when_jitter_is_zero(self) -> None:
        """验证抖动值为 0 时返回原始 TTL。

        参数:
            无。

        返回:
            None。
        """

        self.assertEqual(apply_ttl_jitter(60, 0), 60)

    def test_apply_ttl_jitter_returns_value_within_expected_range(self) -> None:
        """验证抖动结果始终落在预期范围内。

        参数:
            无。

        返回:
            None。
        """

        random.seed(12345)
        results = [apply_ttl_jitter(60, 10) for _ in range(20)]

        self.assertTrue(all(60 <= value <= 70 for value in results))
        self.assertTrue(any(value > 60 for value in results))

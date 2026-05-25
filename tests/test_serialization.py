"""序列化层测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from kmcache.compression.gzip import GzipCompressor
from kmcache.exceptions import SerializationError
from kmcache.models import CacheEnvelope
from kmcache.serialization.compressed import CompressedSerializer
from kmcache.serialization.json import JsonSerializer
from kmcache.serialization.msgpack import MessagePackSerializer


class JsonSerializerTests(unittest.TestCase):
    """JSON 序列化器测试。"""

    def test_json_serializer_round_trip_preserves_envelope_fields(self) -> None:
        """验证序列化后再反序列化可以保留关键字段。

        参数:
            无。

        返回:
            None。
        """

        serializer = JsonSerializer()
        envelope = CacheEnvelope(
            value={"user_id": 1, "name": "alice"},
            created_at=100.0,
            soft_expire_at=120.0,
            hard_expire_at=160.0,
            is_null=False,
            version=2,
        )

        payload = serializer.dumps(envelope)
        restored = serializer.loads(payload)

        self.assertEqual(restored.value, envelope.value)
        self.assertEqual(restored.created_at, envelope.created_at)
        self.assertEqual(restored.soft_expire_at, envelope.soft_expire_at)
        self.assertEqual(restored.hard_expire_at, envelope.hard_expire_at)
        self.assertEqual(restored.version, envelope.version)

    def test_json_serializer_preserves_null_value_marker(self) -> None:
        """验证空值缓存标记在反序列化后仍然可识别。

        参数:
            无。

        返回:
            None。
        """

        serializer = JsonSerializer()
        envelope = CacheEnvelope(
            value=None,
            created_at=100.0,
            soft_expire_at=None,
            hard_expire_at=130.0,
            is_null=True,
        )

        payload = serializer.dumps(envelope)
        restored = serializer.loads(payload)

        self.assertTrue(restored.is_null)
        self.assertIsNone(restored.resolve_value())

    def test_json_serializer_raises_serialization_error_for_invalid_json(self) -> None:
        """验证非法 JSON 字符串会抛出序列化异常。

        参数:
            无。

        返回:
            None。
        """

        serializer = JsonSerializer()

        with self.assertRaises(SerializationError):
            serializer.loads("{invalid-json")

    def test_json_serializer_raises_serialization_error_for_missing_required_fields(self) -> None:
        """验证缺少必要字段的 JSON 载荷会抛出序列化异常。

        参数:
            无。

        返回:
            None。
        """

        serializer = JsonSerializer()
        payload = '{"value":"demo","soft_expire_at":10.0,"hard_expire_at":20.0}'

        with self.assertRaises(SerializationError):
            serializer.loads(payload)

    def test_json_serializer_raises_serialization_error_for_non_serializable_value(self) -> None:
        """验证不可 JSON 序列化的值会抛出序列化异常。

        参数:
            无。

        返回:
            None。
        """

        serializer = JsonSerializer()
        envelope = CacheEnvelope(
            value={1, 2, 3},
            created_at=100.0,
            soft_expire_at=None,
            hard_expire_at=130.0,
        )

        with self.assertRaises(SerializationError):
            serializer.dumps(envelope)

    def test_compressed_serializer_round_trip_preserves_payload(self) -> None:
        """验证压缩序列化器可以完成闭环。"""

        serializer = CompressedSerializer(JsonSerializer(), GzipCompressor())
        envelope = CacheEnvelope(
            value={"payload": "x" * 128},
            created_at=100.0,
            soft_expire_at=120.0,
            hard_expire_at=160.0,
        )

        payload = serializer.dumps(envelope)
        restored = serializer.loads(payload)

        self.assertEqual(restored.value, envelope.value)
        self.assertEqual(restored.hard_expire_at, envelope.hard_expire_at)

    def test_msgpack_serializer_works_with_optional_dependency(self) -> None:
        """验证 MessagePack 序列化器在依赖可用时可以完成闭环。"""

        class FakeMsgpackModule:
            @staticmethod
            def packb(value, use_bin_type=True):  # noqa: ARG004
                import json

                return json.dumps(value).encode("utf-8")

            @staticmethod
            def unpackb(payload, raw=False):  # noqa: ARG004
                import json

                return json.loads(payload.decode("utf-8"))

        serializer = MessagePackSerializer()
        envelope = CacheEnvelope(
            value={"user_id": 1},
            created_at=1.0,
            soft_expire_at=2.0,
            hard_expire_at=3.0,
        )

        with patch("importlib.import_module", return_value=FakeMsgpackModule()):
            payload = serializer.dumps(envelope)
            restored = serializer.loads(payload)

        self.assertEqual(restored.value, envelope.value)
        self.assertEqual(restored.created_at, envelope.created_at)

    def test_msgpack_serializer_raises_when_dependency_is_missing(self) -> None:
        """验证未安装可选依赖时会抛出明确异常。"""

        serializer = MessagePackSerializer()
        envelope = CacheEnvelope(
            value={"user_id": 1},
            created_at=1.0,
            soft_expire_at=2.0,
            hard_expire_at=3.0,
        )

        with patch("importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(SerializationError):
                serializer.dumps(envelope)

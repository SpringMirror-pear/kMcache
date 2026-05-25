"""Compression helpers for kmcache."""

from kmcache.compression.base import BaseCompressor
from kmcache.compression.gzip import GzipCompressor

__all__ = ["BaseCompressor", "GzipCompressor"]

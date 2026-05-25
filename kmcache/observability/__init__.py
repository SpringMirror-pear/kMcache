"""Observability hooks."""

from kmcache.observability.events import BaseEventHook
from kmcache.observability.events import InMemoryEventHook
from kmcache.observability.events import NoOpEventHook
from kmcache.observability.metrics import BaseMetricsHook
from kmcache.observability.metrics import InMemoryMetricsHook
from kmcache.observability.metrics import NoOpMetricsHook

__all__ = [
    "BaseEventHook",
    "BaseMetricsHook",
    "InMemoryEventHook",
    "InMemoryMetricsHook",
    "NoOpEventHook",
    "NoOpMetricsHook",
]

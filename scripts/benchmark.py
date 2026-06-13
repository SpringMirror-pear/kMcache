"""Lightweight benchmark and regression-threshold runner for kmcache."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from statistics import quantiles
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kmcache.backends.local import LocalCacheBackend
from kmcache.backends.redis import RedisCacheBackend
from kmcache.config import BroadcastConfig
from kmcache.config import CacheConfig
from kmcache.config import LocalCacheConfig
from kmcache.config import RedisCacheConfig
from kmcache.manager import CacheManager
from kmcache.models import CacheEnvelope
from kmcache.models import CachePolicy
from kmcache.utils.time import utc_timestamp


REDIS_URL = "redis://127.0.0.1:6379/0"


@dataclass(slots=True)
class BenchmarkResult:
    """Single benchmark scenario result."""

    name: str
    samples: list[float]
    threshold_ms: float

    def p95_ms(self) -> float:
        """Return p95 latency in milliseconds."""

        if len(self.samples) == 1:
            return self.samples[0] * 1000
        return quantiles(self.samples, n=100)[94] * 1000

    def avg_ms(self) -> float:
        """Return mean latency in milliseconds."""

        return mean(self.samples) * 1000

    def passed(self) -> bool:
        """Return whether the benchmark satisfies the threshold."""

        return self.p95_ms() <= self.threshold_ms

    def as_dict(self) -> dict[str, float | str | bool]:
        """Serialize a benchmark result."""

        return {
            "name": self.name,
            "samples": len(self.samples),
            "avg_ms": round(self.avg_ms(), 3),
            "p95_ms": round(self.p95_ms(), 3),
            "threshold_ms": round(self.threshold_ms, 3),
            "passed": self.passed(),
        }


async def benchmark_l1_hit(iterations: int = 200) -> BenchmarkResult:
    """Measure L1 hit latency."""

    cache = CacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
    await cache.set("bench:l1", "value", ttl=60)
    samples = await _collect_samples(iterations, lambda: cache.get("bench:l1"))
    await cache.close()
    return BenchmarkResult("l1_hit", samples, threshold_ms=5.0)


async def benchmark_l2_hit(iterations: int = 100) -> BenchmarkResult:
    """Measure Redis L2 hit latency."""

    redis_config = RedisCacheConfig(url=REDIS_URL, key_prefix="kmcache-bench-l2")
    backend = RedisCacheBackend.from_url(redis_config.url, redis_config)
    cache = CacheManager([backend], CacheConfig(ttl_jitter=0, redis=redis_config))
    await backend.clear()
    await cache.set("bench:l2", "value", ttl=60)
    samples = await _collect_samples(iterations, lambda: cache.get("bench:l2"))
    await cache.close()
    return BenchmarkResult("l2_hit", samples, threshold_ms=25.0)


async def benchmark_miss_load(iterations: int = 50) -> BenchmarkResult:
    """Measure miss -> loader -> store latency."""

    cache = CacheManager([LocalCacheBackend()], CacheConfig(ttl_jitter=0))
    counter = {"value": 0}

    async def once(index: int) -> None:
        async def loader() -> dict[str, int]:
            counter["value"] += 1
            return {"value": index}

        await cache.delete(f"bench:miss:{index}")
        await cache.get_or_load(f"bench:miss:{index}", loader, policy=CachePolicy(ttl=30))

    samples = await _collect_samples(iterations, lambda index=counter["value"]: once(index))
    await cache.close()
    return BenchmarkResult("miss_load", samples, threshold_ms=20.0)


async def benchmark_stale_return(iterations: int = 100) -> BenchmarkResult:
    """Measure stale return latency."""

    backend = LocalCacheBackend()
    cache = CacheManager([backend], CacheConfig(ttl_jitter=0, enable_stale=True))
    now = utc_timestamp()
    await backend.set(
        "default:bench:stale",
        CacheEnvelope(
            value="old",
            created_at=now - 10,
            soft_expire_at=now - 1,
            hard_expire_at=now + 30,
        ),
    )

    async def loader() -> str:
        return "new"

    samples = await _collect_samples(
        iterations,
        lambda: cache.get_or_load(
            "bench:stale",
            loader,
            policy=CachePolicy(ttl=60, soft_ttl=10, refresh_timeout=0.5),
        ),
    )
    await cache.close()
    return BenchmarkResult("stale_return", samples, threshold_ms=10.0)


async def benchmark_dual_instance_lock() -> BenchmarkResult:
    """Measure two-instance lock contention behavior."""

    key_prefix = "kmcache-bench-lock"
    redis_config = RedisCacheConfig(
        url=REDIS_URL,
        key_prefix=key_prefix,
        lock_timeout=2.0,
        lock_sleep_interval=0.05,
    )
    local_one = LocalCacheBackend(LocalCacheConfig(name="bench-lock-a"))
    local_two = LocalCacheBackend(LocalCacheConfig(name="bench-lock-b"))
    redis_one = RedisCacheBackend.from_url(redis_config.url, redis_config)
    redis_two = RedisCacheBackend.from_url(redis_config.url, redis_config)
    cache_one = CacheManager(
        [local_one, redis_one],
        CacheConfig(
            ttl_jitter=0,
            redis=redis_config,
            broadcast=BroadcastConfig(enabled=False, instance_id="bench-a"),
        ),
    )
    cache_two = CacheManager(
        [local_two, redis_two],
        CacheConfig(
            ttl_jitter=0,
            redis=redis_config,
            broadcast=BroadcastConfig(enabled=False, instance_id="bench-b"),
        ),
    )
    await redis_one.clear()

    async def loader() -> str:
        await asyncio.sleep(0.05)
        return "shared"

    started_at = perf_counter()
    results = await asyncio.gather(
        cache_one.get_or_load("bench:lock", loader, policy=CachePolicy(ttl=30)),
        cache_two.get_or_load("bench:lock", loader, policy=CachePolicy(ttl=30)),
    )
    elapsed = perf_counter() - started_at
    await cache_one.close()
    await cache_two.close()
    if results != ["shared", "shared"]:
        raise AssertionError(f"unexpected lock benchmark results: {results!r}")
    return BenchmarkResult("dual_instance_lock", [elapsed], threshold_ms=300.0)


async def run_benchmarks() -> list[BenchmarkResult]:
    """Run all benchmark scenarios."""

    return [
        await benchmark_l1_hit(),
        await benchmark_l2_hit(),
        await benchmark_miss_load(),
        await benchmark_stale_return(),
        await benchmark_dual_instance_lock(),
    ]


async def _collect_samples(iterations: int, operation) -> list[float]:
    """Collect benchmark samples for an awaitable operation."""

    samples: list[float] = []
    for _ in range(iterations):
        started_at = perf_counter()
        await operation()
        samples.append(perf_counter() - started_at)
    return samples


def main() -> int:
    """Run benchmarks and enforce regression thresholds."""

    results = asyncio.run(run_benchmarks())
    payload = [result.as_dict() for result in results]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    failed = [result for result in results if not result.passed()]
    if failed:
        names = ", ".join(result.name for result in failed)
        raise SystemExit(f"benchmark thresholds failed: {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

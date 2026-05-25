"""用于后端和回源保护的熔断器基础组件。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kmcache.config import CircuitBreakerConfig
from kmcache.exceptions import CircuitBreakerOpenError
from kmcache.utils.time import utc_timestamp


class CircuitState(StrEnum):
    """熔断器支持的状态枚举。"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class CircuitBreaker:
    """简单的熔断器状态机实现。"""

    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float | None = None
    half_open_calls: int = 0

    def allow(self) -> None:
        """检查当前调用是否允许通过。

        参数:
            无。

        返回:
            None。

        异常:
            CircuitBreakerOpenError: 当前熔断器不允许请求通过时抛出。
        """

        now = utc_timestamp()
        if self.state is CircuitState.OPEN:
            if self.opened_at is not None and now - self.opened_at >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return
            raise CircuitBreakerOpenError("circuit breaker is open")

        if self.state is CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError("circuit breaker half-open call limit reached")
            self.half_open_calls += 1

    def record_success(self) -> None:
        """记录一次成功调用并重置熔断状态。

        参数:
            无。

        返回:
            None。
        """

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
        self.half_open_calls = 0

    def record_failure(self) -> None:
        """记录一次失败调用并按阈值推进熔断状态。

        参数:
            无。

        返回:
            None。
        """

        self.failure_count += 1
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = utc_timestamp()
            self.half_open_calls = 0

"""Package exception hierarchy."""


class CacheError(Exception):
    """Base exception for kmcache."""


class BackendError(CacheError):
    """Raised when a cache backend operation fails."""


class SerializationError(CacheError):
    """Raised when payload serialization or deserialization fails."""


class CircuitBreakerOpenError(CacheError):
    """Raised when a protected component is short-circuited."""


class LockAcquisitionError(CacheError):
    """Raised when lock acquisition fails."""


class InvalidConfigurationError(CacheError):
    """Raised when cache configuration is invalid."""

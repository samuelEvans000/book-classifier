"""Retry decorator for async provider calls."""

import asyncio
from functools import wraps
from typing import Callable, Any

from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from app.config import config
from app.utils.logger import logger


# Exceptions that warrant a retry
RETRYABLE = (
    Exception,  # broad — providers override with specific ones
)


def async_retry(
    max_attempts: int | None = None,
    min_wait: float = 2.0,
    max_wait: float = 60.0,
    exceptions: tuple = RETRYABLE,
):
    """
    Decorator factory for async functions.
    Uses exponential back-off with jitter.
    """
    attempts = max_attempts or config.MAX_RETRIES

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(exceptions),
                reraise=True,
            ):
                with attempt:
                    return await fn(*args, **kwargs)

        return wrapper

    return decorator
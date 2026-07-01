"""
Rate-limited DeepSeek provider wrapper with circuit breaker for
non-recoverable errors (billing, auth, DNS).
"""

import time

from aiolimiter import AsyncLimiter

from app.config import config
from app.providers.deepseek import DeepSeekProvider
from app.utils.logger import logger

_NON_RECOVERABLE_MARKERS = [
    "insufficient balance",
    "402",
    "getaddrinfo failed",
    "401",
    "invalid api key",
    "authentication",
]

CIRCUIT_BREAKER_COOLDOWN = 300
CIRCUIT_BREAKER_THRESHOLD = 3


class LoadBalancer:
    def __init__(self):
        self._provider: DeepSeekProvider | None = None
        self._limiter: AsyncLimiter | None = None
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def setup(self) -> None:
        if not config.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY not set — check your .env")

        self._provider = DeepSeekProvider()
        rpm = config.DEEPSEEK_RPM
        self._limiter = AsyncLimiter(max_rate=rpm, time_period=60)
        logger.info(f"Provider registered: deepseek @ {rpm} RPM")

    def _is_circuit_open(self) -> bool:
        return time.time() < self._circuit_open_until

    def _is_non_recoverable(self, error: Exception) -> bool:
        msg = str(error).lower()
        return any(marker in msg for marker in _NON_RECOVERABLE_MARKERS)

    def _trip_circuit(self) -> None:
        self._circuit_open_until = time.time() + CIRCUIT_BREAKER_COOLDOWN
        logger.warning(
            f"Circuit breaker OPEN for deepseek — skipping for "
            f"{CIRCUIT_BREAKER_COOLDOWN}s due to repeated non-recoverable errors."
        )

    async def classify_with_fallback(self, books, expected_md5s: list[str]):
        if self._is_circuit_open():
            logger.error("DeepSeek circuit breaker open — batch skipped")
            return [], expected_md5s

        try:
            async with self._limiter:
                classifications, failed = await self._provider.classify_batch(books)
            self._failure_count = 0
            return classifications, failed
        except Exception as e:
            self._failure_count += 1
            logger.warning(
                f"DeepSeek failed (failures={self._failure_count}): {e}"
            )
            if (
                self._is_non_recoverable(e)
                and self._failure_count >= CIRCUIT_BREAKER_THRESHOLD
            ):
                self._trip_circuit()
            return [], expected_md5s

    @property
    def provider_count(self) -> int:
        return 1 if self._provider else 0

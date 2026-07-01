"""Miscellaneous helper functions."""

import time
import math
from typing import TypeVar, Iterable

T = TypeVar("T")


def chunked(iterable: list[T], size: int) -> Iterable[list[T]]:
    """Yield successive chunks of `size` from a list."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def human_time(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def eta(processed: int, total: int, elapsed: float) -> str:
    """Estimate remaining time as a human string."""
    if processed == 0:
        return "unknown"
    rate = processed / elapsed
    remaining = (total - processed) / rate
    return human_time(remaining)


def max_output_tokens(batch_size: int) -> int:
    """Estimate output tokens needed for a classification batch."""
    return max(512, batch_size * 250)


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string using standard character-to-token approximation (4 chars/token)."""
    return max(1, len(text) // 4)
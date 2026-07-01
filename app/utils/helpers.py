"""Miscellaneous helper functions."""

import time
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
    """
    Calculate the max_tokens ceiling for a classification batch.

    Each output row contains:
      md5 (32 chars ≈ 8 tok) + category (≈5) + 10 subcategories (≈50) +
      audience (≈3) + commas/quotes overhead (≈10) ≈ 76 tokens/row

    We use 110 per book with a +200 buffer to be safe.
    Hard cap at 16000 — DeepSeek V4 Flash output limit.

    BUG FIXED: previous value was 250/book → 25,000 tokens for 100 books,
    which is 2.5× the actual need and prevented the ceiling from acting as
    a meaningful guard against runaway output.
    """
    return min(batch_size * 110 + 200, 16000)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using the standard 4-chars-per-token approximation.

    BUG FIXED: previously returned len(text) // 4 with no floor, which gave
    0 for empty strings and caused division errors in callers. Now floors at 1.

    Note: this is a fallback only — always prefer the actual usage object
    from the API response over this estimate.
    """
    if not text:
        return 1
    return max(1, len(text) // 4)
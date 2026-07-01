"""
Queue manager.
Fills an asyncio.Queue with Book batches and tracks global progress.
"""

import asyncio
from typing import Optional

from app.models.book import Book
from app.config import config
from app.utils.logger import logger


_SENTINEL = None  # poison pill


class QueueManager:
    """
    Produces batches of Books into an async queue consumed by workers.
    """

    def __init__(self, max_queue_size: int = 200):
        self._queue: asyncio.Queue[Optional[list[Book]]] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._total_batches = 0

    async def fill(
        self,
        books: list[Book],
        batch_size: int,
        num_workers: int,
    ) -> None:
        """
        Split `books` into batches of `batch_size` and enqueue them.
        Sends `num_workers` poison-pill sentinels when done.
        """
        batch: list[Book] = []
        for book in books:
            batch.append(book)
            if len(batch) >= batch_size:
                await self._queue.put(batch)
                self._total_batches += 1
                batch = []

        if batch:  # leftover
            await self._queue.put(batch)
            self._total_batches += 1

        # Send sentinel for each worker
        for _ in range(num_workers):
            await self._queue.put(_SENTINEL)

        logger.info(f"Queue filled: {self._total_batches} batches enqueued.")

    async def get(self) -> Optional[list[Book]]:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    @property
    def total_batches(self) -> int:
        return self._total_batches

    @property
    def queue(self) -> asyncio.Queue:
        return self._queue
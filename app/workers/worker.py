"""
Async worker.
Each worker drains the shared queue, calls the router,
writes results to the CSV writer, and updates the checkpoint.

Failed books from a batch are retried in mini-batches (not one-by-one)
so we don't resend the full system prompt per single book — this keeps
token usage down and lets DeepSeek's prompt cache stay warm.
"""

import asyncio
from typing import Optional

from app.config import config
from app.models.book import Book
from app.models.classification import Classification
from app.router.router import Router
from app.parser.csv_writer import CSVWriter
from app.utils.logger import logger
from app.utils.helpers import chunked


class Worker:
    def __init__(
        self,
        worker_id: int,
        router: Router,
        writer: CSVWriter,
        progress_callback=None,  # callable(n_done: int) -> None
    ):
        self._id = worker_id
        self._router = router
        self._writer = writer
        self._progress_cb = progress_callback
        self.processed = 0
        self.failed = 0

    async def run(self, queue: asyncio.Queue) -> None:
        """Consume batches from queue until sentinel received."""
        while True:
            batch: Optional[list[Book]] = await queue.get()
            if batch is None:  # sentinel
                queue.task_done()
                break

            try:
                await self._process_batch(batch)
            except Exception as e:
                logger.error(f"[worker-{self._id}] Unhandled error on batch: {e}", exc_info=True)
                self.failed += len(batch)
            finally:
                queue.task_done()

    async def _process_batch(self, books: list[Book]) -> None:
        classifications, failed_md5s = await self._router.classify_batch(books)

        # Write successful results immediately
        if classifications:
            await self._write_results(classifications)

        # Retry failed books in smaller mini-batches rather than one at a
        # time — preserves the system-prompt-once-per-call structure that
        # DeepSeek's cache (and every provider's batching efficiency) relies on.
        if failed_md5s:
            md5_to_book = {b.md5: b for b in books}
            failed_books = [md5_to_book[m] for m in failed_md5s if m in md5_to_book]
            await self._retry_failed(failed_books)

    async def _retry_failed(self, failed_books: list[Book]) -> None:
        """Retry in mini-batches to avoid resending the system prompt per book."""
        for mini_batch in chunked(failed_books, config.RETRY_BATCH_SIZE):
            classifications, still_failed_md5s = await self._router.classify_batch(mini_batch)

            if classifications:
                await self._write_results(classifications)

            # If a mini-batch still has failures, fall back to single-book
            # classification as the last resort for just those books —
            # this is where true one-by-one retry is justified, since the
            # mini-batch itself already isolated the problem to a handful
            # of books instead of the full original batch.
            if still_failed_md5s:
                md5_to_book = {b.md5: b for b in mini_batch}
                still_failed_books = [
                    md5_to_book[m] for m in still_failed_md5s if m in md5_to_book
                ]
                for book in still_failed_books:
                    result = await self._router.classify_single(book)
                    if result:
                        await self._write_results([result])
                    else:
                        logger.warning(
                            f"[worker-{self._id}] Permanently failed: {book.md5} | {book.title}"
                        )
                        self.failed += 1

    async def _write_results(self, classifications: list[Classification]) -> None:
        rows = [c.to_csv_row() for c in classifications]
        await self._writer.write_rows(rows)
        self.processed += len(classifications)
        if self._progress_cb:
            self._progress_cb(len(classifications))
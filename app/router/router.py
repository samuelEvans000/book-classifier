"""
Router wraps the load balancer and adds single-book retry logic
for books that fail in batch mode.
"""

import asyncio
from app.models.book import Book
from app.models.classification import Classification
from app.router.load_balancer import LoadBalancer
from app.utils.logger import logger


class Router:
    def __init__(self, balancer: LoadBalancer):
        self._balancer = balancer

    async def classify_batch(
        self, books: list[Book]
    ) -> tuple[list[Classification], list[str]]:
        """
        Classify a batch. Returns (ok_classifications, failed_md5s).
        Failed md5s are retried one-by-one by the worker.
        """
        if not books:
            return [], []

        # Map original MD5 to sequential dummy IDs to reduce tokens
        dummy_to_md5 = {}
        md5_to_dummy = {}
        dummy_books = []
        for i, book in enumerate(books, 1):
            dummy_id = str(i)
            dummy_to_md5[dummy_id] = book.md5
            md5_to_dummy[book.md5] = dummy_id
            dummy_books.append(
                Book(
                    title=book.title,
                    author=book.author,
                    md5=dummy_id
                )
            )

        expected_dummy_ids = list(dummy_to_md5.keys())

        # Classify using dummy books
        dummy_results, dummy_failed = await self._balancer.classify_with_fallback(
            dummy_books, expected_dummy_ids
        )

        # Unparse dummy IDs back to original MD5s
        real_results = []
        for c in dummy_results:
            real_md5 = dummy_to_md5.get(c.md5)
            if real_md5:
                c.md5 = real_md5
                real_results.append(c)

        real_failed = [
            dummy_to_md5[d] for d in dummy_failed if d in dummy_to_md5
        ]

        return real_results, real_failed

    async def classify_single(self, book: Book) -> Classification | None:
        """
        Classify a single book with full fallback.
        Used for re-trying books that failed in a batch.
        """
        dummy_book = Book(
            title=book.title,
            author=book.author,
            md5="1"
        )
        dummy_results, _ = await self._balancer.classify_with_fallback([dummy_book], ["1"])
        if dummy_results:
            res = dummy_results[0]
            res.md5 = book.md5
            return res
        return None
from dataclasses import dataclass
from typing import List

from app.models.book import Book


@dataclass(slots=True)
class BookBatch:
    start_row: int
    end_row: int
    books: List[Book]

    @property
    def size(self) -> int:
        return len(self.books)
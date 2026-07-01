"""Abstract base class for all LLM providers."""

from abc import ABC, abstractmethod
from app.models.book import Book
from app.models.classification import Classification


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def classify_batch(self, books: list[Book]) -> tuple[list[Classification], list[str]]:
        """
        Classify a batch of books.

        Returns:
            (classifications, failed_md5s)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider has a valid API key configured."""
        ...

    def __repr__(self) -> str:
        return f"<Provider:{self.name}>"
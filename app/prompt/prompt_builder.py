"""Builds user-turn prompts for the classification LLM."""

import os
from app.models.book import Book
from app.config import config


def _load_system_prompt() -> str:
    path = config.SYSTEM_PROMPT_FILE
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    raise FileNotFoundError(f"System prompt not found at {path}")


# Cache once at import time
_SYSTEM_PROMPT: str | None = None


def get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = _load_system_prompt()
    return _SYSTEM_PROMPT


def build_user_prompt(books: list[Book]) -> str:
    """
    Build the user-turn message for a batch of books.
    Sends a mini CSV (title,author,md5) to the model.
    """
    lines = ["title,author,md5"]
    for book in books:
        # Escape any quotes inside fields
        title = book.title.replace('"', '""')
        author = book.author.replace('"', '""')
        lines.append(f'"{title}","{author}",{book.md5}')
    return "\n".join(lines)
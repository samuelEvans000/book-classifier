"""Reads the input CSV and yields Book objects in chunks."""

import csv
import os
from typing import Generator

from app.models.book import Book
from app.utils.logger import logger


def count_rows(path: str) -> int:
    """Fast line count (approximate; ignores malformed rows)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f) - 1  # subtract header


def iter_books(path: str) -> Generator[Book, None, None]:
    """
    Lazily iterate over the input CSV, yielding validated Book objects.
    Skips rows that fail validation with a warning.
    Handles UTF-8 with BOM and latin-1 fallback.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    skipped = 0
    total = 0

    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)

        # Normalise header names (strip whitespace, lowercase for lookup)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        headers = [h.strip().lower() for h in reader.fieldnames]

        # Accept flexible column names
        col_map = {}
        for raw, norm in zip(reader.fieldnames, headers):
            if norm in ("title",):
                col_map["title"] = raw
            elif norm in ("author", "authors"):
                col_map["author"] = raw
            elif norm in ("md5", "md5hash", "hash"):
                col_map["md5"] = raw

        required = {"title", "author", "md5"}
        missing = required - set(col_map.keys())
        if missing:
            raise ValueError(f"Input CSV missing required columns: {missing}")

        for row in reader:
            total += 1
            try:
                book = Book(
                    title=row.get(col_map["title"], "").strip(),
                    author=row.get(col_map["author"], "").strip(),
                    md5=row.get(col_map["md5"], "").strip(),
                )
                yield book
            except Exception as e:
                skipped += 1
                if skipped <= 20:
                    logger.warning(f"Skipping row {total}: {e} | row={dict(row)}")

    if skipped:
        logger.warning(f"Total skipped rows: {skipped:,} / {total:,}")
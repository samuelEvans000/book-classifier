"""Appends classified rows to the output CSV file."""

import os
import asyncio
import aiofiles

from app.utils.logger import logger


class CSVWriter:
    """
    Async-safe writer that appends rows to the output file.
    Uses an asyncio lock so multiple workers don't interleave writes.
    """

    def __init__(self, path: str):
        self._path = path
        self._lock = asyncio.Lock()
        self._written = 0

    def prepare(self) -> None:
        """Create output directory. Does NOT write a header (output is headerless)."""
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)

    async def write_rows(self, rows: list[str]) -> None:
        """Append a list of CSV row strings to the output file."""
        if not rows:
            return
        content = "\n".join(rows) + "\n"
        async with self._lock:
            async with aiofiles.open(self._path, "a", encoding="utf-8") as f:
                await f.write(content)
            self._written += len(rows)

    async def write_row(self, row: str) -> None:
        await self.write_rows([row])

    @property
    def written(self) -> int:
        return self._written

    def get_existing_md5s(self) -> set[str]:
        """
        Read the output file (if it exists) and return md5s already written.
        Used on startup to rebuild the completed set without re-reading the
        checkpoint (handles the case where checkpoint was lost but output was not).
        """
        md5s: set[str] = set()
        if not os.path.exists(self._path):
            return md5s
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    md5 = line.split(",")[0].strip()
                    if md5:
                        md5s.add(md5)
            logger.info(f"Output file has {len(md5s):,} existing rows.")
        except Exception as e:
            logger.warning(f"Could not scan output file: {e}")
        return md5s
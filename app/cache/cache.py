"""
Lightweight MD5 → CSV-row in-memory cache backed by a JSON file.
This is separate from the checkpoint (which tracks batch progress).
Use the cache to skip individual books already classified in previous runs
without re-reading the full output CSV on startup.
"""

import json
import os
import asyncio
from typing import Optional

import aiofiles

from app.utils.logger import logger


class ClassificationCache:
    """
    Thread-safe (asyncio) in-memory + on-disk cache.
    Key: md5 string
    Value: classified CSV row string
    """

    def __init__(self, cache_file: str = "cache/cache.json"):
        self._file = cache_file
        self._data: dict[str, str] = {}
        self._dirty = False
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Load cache from disk if it exists."""
        if not os.path.exists(self._file):
            return
        try:
            async with aiofiles.open(self._file, "r", encoding="utf-8") as f:
                content = await f.read()
            self._data = json.loads(content)
            logger.info(f"Cache loaded: {len(self._data):,} entries from {self._file}")
        except Exception as e:
            logger.warning(f"Cache load failed ({e}); starting fresh")
            self._data = {}

    async def save(self) -> None:
        """Flush dirty cache to disk."""
        if not self._dirty:
            return
        async with self._lock:
            os.makedirs(os.path.dirname(self._file) or ".", exist_ok=True)
            async with aiofiles.open(self._file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self._data, ensure_ascii=False))
            self._dirty = False

    def get(self, md5: str) -> Optional[str]:
        return self._data.get(md5)

    def set(self, md5: str, row: str) -> None:
        self._data[md5] = row
        self._dirty = True

    def has(self, md5: str) -> bool:
        return md5 in self._data

    def __len__(self) -> int:
        return len(self._data)
"""
Checkpoint manager.
Saves/loads the set of md5s that have been successfully classified
so the pipeline can resume after a crash or interruption.
"""

import json
import os
from typing import Set

import aiofiles

from app.config import config
from app.utils.logger import logger


class CheckpointManager:
    def __init__(self, path: str | None = None):
        self._path = path or config.CHECKPOINT_FILE
        self._done: Set[str] = set()

    async def load(self) -> Set[str]:
        """Load previously completed md5s from disk."""
        if not os.path.exists(self._path):
            logger.info("No checkpoint found — starting from scratch.")
            return self._done

        try:
            async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            self._done = set(data.get("completed_md5s", []))
            logger.info(
                f"Checkpoint loaded: {len(self._done):,} books already classified."
            )
        except Exception as e:
            logger.warning(f"Checkpoint load error ({e}); starting from scratch.")
            self._done = set()

        return self._done

    async def save(self, completed: Set[str]) -> None:
        """Persist the set of completed md5s."""
        self._done = completed
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(
                        {"completed_md5s": list(completed), "count": len(completed)},
                        ensure_ascii=False,
                    )
                )
            os.replace(tmp, self._path)  # atomic on POSIX
        except Exception as e:
            logger.error(f"Checkpoint save failed: {e}")

    def mark_done(self, md5: str) -> None:
        self._done.add(md5)

    def mark_done_batch(self, md5s: list[str]) -> None:
        self._done.update(md5s)

    def is_done(self, md5: str) -> bool:
        return md5 in self._done

    @property
    def completed(self) -> Set[str]:
        return self._done

    def __len__(self) -> int:
        return len(self._done)
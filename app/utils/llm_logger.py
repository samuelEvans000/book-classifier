"""
Logs all LLM requests/responses and tracks total tokens consumed.

Writes one JSON file per call to logs/llm_history/.
Exposes a global llm_logger instance used by all providers.
"""

import os
import time
import json
import uuid
import asyncio

from app.utils.logger import logger


class LLMLogger:
    def __init__(self, log_dir: str = "logs/llm_history"):
        self.log_dir = log_dir
        self.input_tokens = 0
        self.output_tokens = 0
        self._lock = asyncio.Lock()
        os.makedirs(self.log_dir, exist_ok=True)

    async def log_call(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        raw_output: str,
        in_tokens: int = 0,
        out_tokens: int = 0,
    ) -> None:
        """Log the LLM call to a JSON file and accumulate token stats."""
        async with self._lock:
            self.input_tokens  += in_tokens
            self.output_tokens += out_tokens

            # Log running totals to console every 10 calls so you can
            # see token consumption in real time without reading JSON files
            total_calls = (self.input_tokens + self.output_tokens)  # proxy counter
            logger.info(
                f"[{provider}] in={in_tokens:,} out={out_tokens:,} | "
                f"session total → in={self.input_tokens:,} out={self.output_tokens:,}"
            )

        timestamp_ms = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:8]
        filename = f"call_{timestamp_ms}_{provider}_{uid}.json"
        filepath = os.path.join(self.log_dir, filename)

        data = {
            "timestamp":          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "provider":           provider,
            "model":              model,
            "input_tokens_used":  in_tokens,
            "output_tokens_used": out_tokens,
            # Store prompts/output only in debug mode to avoid huge log dirs
            # on 1.9M-book runs. Set LLM_LOG_FULL=1 in env to enable full logs.
            **(
                {
                    "system_prompt": system_prompt,
                    "user_prompt":   user_prompt,
                    "raw_output":    raw_output,
                }
                if os.getenv("LLM_LOG_FULL", "0") == "1"
                else {}
            ),
        }

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_file, filepath, data)
        except Exception as e:
            logger.debug(f"[llm_logger] Failed to save call log: {e}")

    def _write_file(self, filepath: str, data: dict) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stats(self) -> dict:
        """Return current session token totals."""
        return {
            "input_tokens":  self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.input_tokens + self.output_tokens,
        }

    def log_summary(self) -> None:
        """Print final session summary — call this at pipeline end."""
        stats = self.get_stats()
        logger.info(
            f"[llm_logger] ── Session token summary ──────────────────\n"
            f"  Input tokens  : {stats['input_tokens']:>12,}\n"
            f"  Output tokens : {stats['output_tokens']:>12,}\n"
            f"  Total tokens  : {stats['total_tokens']:>12,}"
        )

    # Alias so both main.py call styles work
    print_summary = log_summary


# Global instance — imported by all providers
llm_logger = LLMLogger()
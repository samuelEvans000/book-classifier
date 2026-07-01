"""Logs all LLM requests/responses and tracks total tokens consumed."""

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
        out_tokens: int = 0
    ) -> None:
        """Log the LLM call to a JSON file and increment token statistics."""
        async with self._lock:
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens

        # Create filename based on timestamp, provider, and random suffix
        timestamp = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:8]
        filename = f"call_{timestamp}_{provider}_{uid}.json"
        filepath = os.path.join(self.log_dir, filename)

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "provider": provider,
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_output": raw_output,
            "input_tokens_used": in_tokens,
            "output_tokens_used": out_tokens
        }

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_file, filepath, data)
        except Exception as e:
            logger.debug(f"Failed to save LLM logs: {e}")

    def _write_file(self, filepath: str, data: dict) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stats(self) -> tuple[int, int]:
        return self.input_tokens, self.output_tokens

# Global instance for the pipeline run
llm_logger = LLMLogger()

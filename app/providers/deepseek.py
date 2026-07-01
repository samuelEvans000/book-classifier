"""
DeepSeek provider using their OpenAI-compatible API.

Model: deepseek-v4-flash (explicit name — the legacy 'deepseek-chat' alias
retires 2026-07-24, so we call the real model name directly).

Caching: DeepSeek's disk-based context cache is automatic. It matches on
exact prefix, so our system prompt (loaded once, byte-identical every call)
gets cached and only the per-batch book list is billed at full rate.
"""

from app.config import config
from app.models.book import Book
from app.models.classification import Classification
from app.providers.base import BaseProvider
from app.prompt.prompt_builder import get_system_prompt, build_user_prompt
from app.validator.response_validator import parse_response
from app.utils.logger import logger
from app.utils.retry import async_retry
from app.utils.helpers import estimate_tokens, max_output_tokens
from app.utils.llm_logger import llm_logger


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    MODEL = "deepseek-v4-flash"          # explicit name, not the retiring alias
    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self):
        self._client = None
        self._total_hit = 0
        self._total_miss = 0
        self._call_count = 0

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=config.DEEPSEEK_API_KEY,
                    base_url=self.BASE_URL,
                )
            except ImportError:
                raise RuntimeError("openai not installed. Run: pip install openai")
        return self._client

    def is_available(self) -> bool:
        return bool(config.DEEPSEEK_API_KEY)

    @async_retry(min_wait=3.0, max_wait=60.0)
    async def classify_batch(self, books: list[Book]) -> tuple[list[Classification], list[str]]:
        client = self._get_client()
        prompt = build_user_prompt(books)
        expected_md5s = [b.md5 for b in books]

        out_tokens_limit = max_output_tokens(len(books))
        response = await client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=out_tokens_limit,
        )

        # Log cache hit/miss so we can verify caching is actually engaging.
        # DeepSeek returns prompt_cache_hit_tokens / prompt_cache_miss_tokens
        # in usage when context caching is active.
        in_tokens = 0
        out_tokens = 0
        usage = getattr(response, "usage", None)
        if usage:
            hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
            miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
            total = hit + miss
            self._total_hit += hit
            self._total_miss += miss
            self._call_count += 1

            in_tokens = getattr(usage, "prompt_tokens", 0) or 0
            out_tokens = getattr(usage, "completion_tokens", 0) or 0

            if total > 0:
                pct = (hit / total) * 100
                logger.debug(
                    f"[deepseek] cache hit={hit} miss={miss} ({pct:.0f}% hit rate)"
                )

            # Every 20 calls, log a running summary so you can see the
            # cache warming up over the course of the run.
            if self._call_count % 20 == 0:
                grand_total = self._total_hit + self._total_miss
                if grand_total > 0:
                    running_pct = (self._total_hit / grand_total) * 100
                    logger.info(
                        f"[deepseek] running cache hit rate: {running_pct:.0f}% "
                        f"over {self._call_count} calls "
                        f"({self._total_hit:,} hit / {self._total_miss:,} miss tokens)"
                    )

        raw = response.choices[0].message.content or ""

        if not in_tokens:
            in_tokens = estimate_tokens(get_system_prompt() + prompt)
        if not out_tokens:
            out_tokens = estimate_tokens(raw)

        await llm_logger.log_call(
            provider=self.name,
            model=self.MODEL,
            system_prompt=get_system_prompt(),
            user_prompt=prompt,
            raw_output=raw,
            in_tokens=in_tokens,
            out_tokens=out_tokens
        )

        classifications, failed = parse_response(raw, expected_md5s)
        logger.debug(
            f"[deepseek] batch={len(books)} ok={len(classifications)} failed={len(failed)}"
        )
        return classifications, failed
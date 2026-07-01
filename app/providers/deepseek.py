"""
DeepSeek provider using their OpenAI-compatible API.
Model: deepseek-v4-flash

Token snowball fix:
  - messages list built fresh every call — never mutated across calls
  - max_tokens calculated per batch size — hard ceiling prevents runaway output
  - stream=False explicitly set

Caching: automatic disk-based context cache. System prompt is byte-identical
every call so cache hits after the first request. Cache hits cost ~98% less.
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
    MODEL = "deepseek-v4-flash"
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

        # Fresh messages list every call — prevents output token snowballing
        prompt = build_user_prompt(books)
        expected_md5s = [b.md5 for b in books]
        sys_prompt = get_system_prompt()

        response = await client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=max_output_tokens(len(books)),
            stream=False,
        )

        # Extract usage — DeepSeek returns cache hit/miss breakdown
        in_tokens = out_tokens = cache_hit = cache_miss = 0
        usage = getattr(response, "usage", None)
        if usage:
            cache_hit  = getattr(usage, "prompt_cache_hit_tokens",  0) or 0
            cache_miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
            in_tokens  = getattr(usage, "prompt_tokens",            0) or 0
            out_tokens = getattr(usage, "completion_tokens",        0) or 0

            self._total_hit  += cache_hit
            self._total_miss += cache_miss
            self._call_count += 1

            if self._call_count % 20 == 0:
                grand = self._total_hit + self._total_miss
                if grand > 0:
                    logger.info(
                        f"[deepseek] cache hit rate: {self._total_hit/grand*100:.0f}% "
                        f"over {self._call_count} calls"
                    )

        raw = response.choices[0].message.content or ""

        # Fall back to estimates if API didn't return usage
        if not in_tokens:
            in_tokens = estimate_tokens(sys_prompt + prompt)
        if not out_tokens:
            out_tokens = estimate_tokens(raw)

        # Log to token tracker
        await llm_logger.log_call(
            provider=self.name,
            model=self.MODEL,
            system_prompt=sys_prompt,
            user_prompt=prompt,
            raw_output=raw,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            cache_hit_tokens=cache_hit,
            cache_miss_tokens=cache_miss,
            books_in_batch=len(books),
        )

        classifications, failed = parse_response(raw, expected_md5s)
        logger.debug(
            f"[deepseek] batch={len(books)} ok={len(classifications)} failed={len(failed)}"
        )
        return classifications, failed
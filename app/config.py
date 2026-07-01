"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # Pipeline settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "600"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))

    # File paths
    INPUT_FILE: str = os.getenv("INPUT_FILE", "data/books.csv")
    OUTPUT_FILE: str = os.getenv("OUTPUT_FILE", "output/classified.csv")
    CHECKPOINT_FILE: str = os.getenv("CHECKPOINT_FILE", "checkpoints/checkpoint.json")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    SYSTEM_PROMPT_FILE: str = os.getenv("SYSTEM_PROMPT_FILE", "app/prompt/system_prompt.txt")

    # Rate limiting (requests per minute)
    DEEPSEEK_RPM: int = int(os.getenv("DEEPSEEK_RPM", "60"))

    # Batch settings
    MAX_BOOKS_PER_BATCH: int = int(os.getenv("MAX_BOOKS_PER_BATCH", "6000"))
    RETRY_BATCH_SIZE: int = int(os.getenv("RETRY_BATCH_SIZE", "10"))

    @classmethod
    def validate(cls) -> None:
        if not cls.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required. Set it in your .env file.")


config = Config()

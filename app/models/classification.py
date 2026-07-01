"""Pydantic model for a single classification result."""

from pydantic import BaseModel, field_validator
from app.constants import MAIN_CATEGORIES, TARGET_AUDIENCES, MIN_TAGS, MAX_TAGS, REQUIRED_SUBCATEGORIES


class Classification(BaseModel):
    md5: str
    main_category: str
    subcategories: list[str]   # exactly 4
    tags: list[str]            # 7-8
    target_audience: str

    @field_validator("main_category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        # Normalise capitalisation
        for cat in MAIN_CATEGORIES:
            if cat.lower() == v.strip().lower():
                return cat
        raise ValueError(f"Unknown main category: {v!r}")

    @field_validator("subcategories")
    @classmethod
    def four_subcategories(cls, v: list[str]) -> list[str]:
        if len(v) != REQUIRED_SUBCATEGORIES:
            raise ValueError(f"Expected {REQUIRED_SUBCATEGORIES} subcategories, got {len(v)}")
        return [s.strip() for s in v]

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, v: list[str]) -> list[str]:
        if not (MIN_TAGS <= len(v) <= MAX_TAGS):
            raise ValueError(f"Expected {MIN_TAGS}-{MAX_TAGS} tags, got {len(v)}")
        return [t.strip() for t in v]

    @field_validator("target_audience")
    @classmethod
    def valid_audience(cls, v: str) -> str:
        for aud in TARGET_AUDIENCES:
            if aud.lower() == v.strip().lower():
                return aud
        raise ValueError(f"Unknown target audience: {v!r}")

    def to_csv_row(self) -> str:
        """Return the canonical CSV line for this classification."""
        subs = ",".join(self.subcategories)
        tags = ",".join(self.tags)
        return f'{self.md5},{self.main_category},"{subs}","{tags}",{self.target_audience}'
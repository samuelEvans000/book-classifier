"""
Pydantic model for a single classification result.

Output format (no tags, 6 subcategories):
  {serial_id},{category},"{sub1},{sub2},{sub3},{sub4},{sub5},{sub6}",{audience}
"""

from pydantic import BaseModel, field_validator
from app.constants import MAIN_CATEGORIES, TARGET_AUDIENCES, REQUIRED_SUBCATEGORIES


class Classification(BaseModel):
    md5: str                    # holds serial_id or md5 — whatever the input uses
    main_category: str
    subcategories: list[str]    # exactly 6 learning-outcome subcategories
    target_audience: str

    @field_validator("main_category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        v = v.strip()
        for cat in MAIN_CATEGORIES:
            if cat.lower() == v.lower():
                return cat
        # Accept unknown categories gracefully (prompt says "not limited to list")
        # Log but don't crash — the LLM may correctly invent a valid category
        return v

    @field_validator("subcategories")
    @classmethod
    def six_subcategories(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if len(cleaned) != REQUIRED_SUBCATEGORIES:
            raise ValueError(
                f"Expected {REQUIRED_SUBCATEGORIES} subcategories, got {len(cleaned)}"
            )
        return cleaned

    @field_validator("target_audience")
    @classmethod
    def valid_audience(cls, v: str) -> str:
        v = v.strip()
        for aud in TARGET_AUDIENCES:
            if aud.lower() == v.lower():
                return aud
        raise ValueError(f"Unknown target audience: {v!r}")

    def to_csv_row(self) -> str:
        """Return the canonical CSV line — no tags field."""
        subs = ",".join(self.subcategories)
        return f'{self.md5},{self.main_category},"{subs}",{self.target_audience}'
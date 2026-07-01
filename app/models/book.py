"""Pydantic model for a single book input row."""

from pydantic import BaseModel, field_validator


class Book(BaseModel):
    title: str
    author: str
    md5: str

    @field_validator("md5")
    @classmethod
    def md5_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("md5 must not be empty")
        return v

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        return v.strip()
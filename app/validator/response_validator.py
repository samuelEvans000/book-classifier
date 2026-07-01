"""
Parses and validates the raw CSV text returned by an LLM provider
into a list of Classification objects.
"""

import csv
import io
import re
from typing import Optional

from app.models.classification import Classification
from app.utils.logger import logger


def _clean_response(raw: str) -> str:
    """Strip markdown fences, BOM, leading/trailing whitespace."""
    text = raw.strip()
    # Remove ```csv ... ``` or ``` ... ```
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text, flags=re.IGNORECASE)
    # Remove BOM
    text = text.lstrip("\ufeff")
    return text.strip()


def parse_response(raw: str, expected_md5s: list[str]) -> tuple[list[Classification], list[str]]:
    """
    Parse LLM output into Classification objects.

    Returns:
        (classifications, failed_md5s)
        - classifications: successfully parsed items
        - failed_md5s: md5s we couldn't parse (need retry)
    """
    text = _clean_response(raw)
    if not text:
        logger.warning("Empty response from provider")
        return [], list(expected_md5s)

    classifications: list[Classification] = []
    parsed_md5s: set[str] = set()
    errors: list[str] = []

    try:
        reader = csv.reader(io.StringIO(text))
        for line_no, row in enumerate(reader, 1):
            if not row or len(row) < 5:
                if row:  # not a blank line
                    errors.append(f"Line {line_no}: too few columns: {row}")
                continue

            md5 = row[0].strip()
            main_category = row[1].strip()
            subcategories_raw = row[2].strip()
            tags_raw = row[3].strip()
            audience = row[4].strip()

            subcategories = [s.strip() for s in subcategories_raw.split(",") if s.strip()]
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

            try:
                c = Classification(
                    md5=md5,
                    main_category=main_category,
                    subcategories=subcategories,
                    tags=tags,
                    target_audience=audience,
                )
                classifications.append(c)
                parsed_md5s.add(md5)
            except Exception as e:
                errors.append(f"Line {line_no} (md5={md5}): validation error — {e}")

    except Exception as e:
        logger.error(f"CSV parse error: {e}\nRaw snippet: {text[:300]}")
        return [], list(expected_md5s)

    if errors:
        for err in errors[:10]:  # cap log spam
            logger.debug(f"Parse issue: {err}")
        if len(errors) > 10:
            logger.debug(f"... and {len(errors) - 10} more parse issues")

    failed = [md5 for md5 in expected_md5s if md5 not in parsed_md5s]
    return classifications, failed


def parse_single(raw: str, md5: str) -> Optional[Classification]:
    """Parse a single-book response (used in fallback/retry path)."""
    results, _ = parse_response(raw, [md5])
    return results[0] if results else None
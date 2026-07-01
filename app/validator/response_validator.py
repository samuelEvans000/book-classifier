"""
Parses and validates the raw CSV text returned by an LLM provider
into a list of Classification objects.

Expected format (4 columns, no tags):
  {serial_id},{category},"{sub1},{sub2},{sub3},{sub4},{sub5},{sub6}",{audience}
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
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text, flags=re.IGNORECASE)
    text = text.lstrip("\ufeff")
    return text.strip()


def parse_response(raw: str, expected_md5s: list[str]) -> tuple[list[Classification], list[str]]:
    """
    Parse LLM output into Classification objects.

    Returns:
        (classifications, failed_md5s)
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
            if not row:
                continue

            # New format: 4 columns — serial_id, category, subcategories, audience
            # Old format: 5 columns — md5, category, subcategories, tags, audience
            # Support both so old checkpoints/partial outputs still work.
            if len(row) == 4:
                serial_id   = row[0].strip()
                category    = row[1].strip()
                subs_raw    = row[2].strip()
                audience    = row[3].strip()
            elif len(row) == 5:
                # legacy 5-column format — tags in position 3, drop them
                serial_id   = row[0].strip()
                category    = row[1].strip()
                subs_raw    = row[2].strip()
                # row[3] = tags (ignored)
                audience    = row[4].strip()
            else:
                if row:
                    errors.append(f"Line {line_no}: expected 4 columns, got {len(row)}: {row}")
                continue

            subcategories = [s.strip() for s in subs_raw.split(",") if s.strip()]

            try:
                c = Classification(
                    md5=serial_id,
                    main_category=category,
                    subcategories=subcategories,
                    target_audience=audience,
                )
                classifications.append(c)
                parsed_md5s.add(serial_id)
            except Exception as e:
                errors.append(f"Line {line_no} (id={serial_id}): {e}")

    except Exception as e:
        logger.error(f"CSV parse error: {e}\nRaw snippet: {text[:300]}")
        return [], list(expected_md5s)

    if errors:
        for err in errors[:10]:
            logger.debug(f"Parse issue: {err}")
        if len(errors) > 10:
            logger.debug(f"... and {len(errors) - 10} more parse issues")

    failed = [m for m in expected_md5s if m not in parsed_md5s]
    return classifications, failed


def parse_single(raw: str, md5: str) -> Optional[Classification]:
    results, _ = parse_response(raw, [md5])
    return results[0] if results else None
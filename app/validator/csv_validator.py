"""
Post-processing validator for the final output CSV.
Run this after the pipeline finishes to report quality metrics.
"""

import csv
from app.constants import MAIN_CATEGORIES, TARGET_AUDIENCES, MIN_TAGS, MAX_TAGS, REQUIRED_SUBCATEGORIES
from app.utils.logger import logger


def validate_output_csv(path: str) -> dict:
    """
    Scan the output CSV and return a stats dict.
    Prints a summary to the logger.
    """
    stats = {
        "total": 0,
        "valid": 0,
        "invalid_category": 0,
        "invalid_subcategory_count": 0,
        "invalid_tag_count": 0,
        "invalid_audience": 0,
        "duplicate_md5s": 0,
    }
    seen_md5s: set[str] = set()

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 5:
                continue
            stats["total"] += 1
            md5, category, subs_raw, tags_raw, audience = row[0], row[1], row[2], row[3], row[4]

            valid = True

            if md5 in seen_md5s:
                stats["duplicate_md5s"] += 1
                valid = False
            seen_md5s.add(md5)

            if category not in MAIN_CATEGORIES:
                stats["invalid_category"] += 1
                valid = False

            subs = [s.strip() for s in subs_raw.split(",") if s.strip()]
            if len(subs) != REQUIRED_SUBCATEGORIES:
                stats["invalid_subcategory_count"] += 1
                valid = False

            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            if not (MIN_TAGS <= len(tags) <= MAX_TAGS):
                stats["invalid_tag_count"] += 1
                valid = False

            if audience not in TARGET_AUDIENCES:
                stats["invalid_audience"] += 1
                valid = False

            if valid:
                stats["valid"] += 1

    pct = (stats["valid"] / stats["total"] * 100) if stats["total"] else 0
    logger.info(
        f"Output validation: {stats['valid']:,}/{stats['total']:,} valid ({pct:.1f}%) | "
        f"bad_category={stats['invalid_category']} bad_subs={stats['invalid_subcategory_count']} "
        f"bad_tags={stats['invalid_tag_count']} bad_audience={stats['invalid_audience']} "
        f"dupes={stats['duplicate_md5s']}"
    )
    return stats
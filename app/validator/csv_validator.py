"""Post-processing validator for the final output CSV."""

from app.constants import MAIN_CATEGORIES, TARGET_AUDIENCES, REQUIRED_SUBCATEGORIES
from app.utils.logger import logger
import csv


def validate_output_csv(path: str) -> dict:
    stats = {
        "total": 0,
        "valid": 0,
        "invalid_subcategory_count": 0,
        "invalid_audience": 0,
        "duplicate_ids": 0,
    }
    seen: set[str] = set()

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 4:
                continue
            stats["total"] += 1
            serial_id, category, subs_raw, audience = row[0], row[1], row[2], row[3]

            valid = True

            if serial_id in seen:
                stats["duplicate_ids"] += 1
                valid = False
            seen.add(serial_id)

            subs = [s.strip() for s in subs_raw.split(",") if s.strip()]
            if len(subs) != REQUIRED_SUBCATEGORIES:
                stats["invalid_subcategory_count"] += 1
                valid = False

            if audience not in TARGET_AUDIENCES:
                stats["invalid_audience"] += 1
                valid = False

            if valid:
                stats["valid"] += 1

    pct = (stats["valid"] / stats["total"] * 100) if stats["total"] else 0
    logger.info(
        f"Output validation: {stats['valid']:,}/{stats['total']:,} valid ({pct:.1f}%) | "
        f"bad_subs={stats['invalid_subcategory_count']} "
        f"bad_audience={stats['invalid_audience']} "
        f"dupes={stats['duplicate_ids']}"
    )
    return stats
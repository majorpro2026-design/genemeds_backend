from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from etl.utils.validation import normalize_numeric, normalize_text


@dataclass(frozen=True)
class AlleleRecord:
    star_allele: str
    functionality: str | None
    activity_value: float | None


def parse_allele_records(raw_records: list[dict[str, Any]]) -> list[AlleleRecord]:
    records: list[AlleleRecord] = []
    for item in raw_records:
        star_allele = normalize_text(item.get("name"))
        if star_allele is None:
            continue
        functionality = normalize_text(item.get("clinicalfunctionalstatus")) or normalize_text(
            item.get("functionalstatus")
        )
        records.append(
            AlleleRecord(
                star_allele=star_allele,
                functionality=functionality,
                activity_value=normalize_numeric(item.get("activityvalue")),
            )
        )
    return records

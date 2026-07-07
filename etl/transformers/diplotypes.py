from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from etl.utils.validation import normalize_numeric, normalize_text


@dataclass(frozen=True)
class DiplotypeRecord:
    allele1: str
    allele2: str
    activity_score: float | None
    phenotype_name: str
    phenotype_description: str | None


def parse_diplotype_records(
    raw_records: list[dict[str, Any]], gene_symbol: str
) -> list[DiplotypeRecord]:
    records: list[DiplotypeRecord] = []
    for item in raw_records:
        diplotype = normalize_text(item.get("diplotype"))
        result = normalize_text(item.get("generesult"))
        if diplotype is None or result is None or "/" not in diplotype:
            continue

        allele1, _, allele2 = diplotype.partition("/")
        records.append(
            DiplotypeRecord(
                allele1=allele1.strip(),
                allele2=allele2.strip(),
                activity_score=normalize_numeric(item.get("totalactivityscore")),
                phenotype_name=f"{gene_symbol} {result}",
                phenotype_description=normalize_text(item.get("description")),
            )
        )
    return records

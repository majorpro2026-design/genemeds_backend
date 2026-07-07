from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from etl.utils.validation import normalize_text


@dataclass(frozen=True)
class RecommendationCondition:
    gene_symbol: str
    phenotype_name: str


@dataclass(frozen=True)
class RecommendationRecord:
    conditions: list[RecommendationCondition]
    recommendation_text: str
    implication: str | None
    classification: str | None
    recommendation_strength: str | None = None
    source: str = "CPIC"
    cpic_guideline_version: str | None = None
    evidence_level: str | None = None
    recommendation_order: int = 1


def _format_conditions(phenotypes: dict[str, Any]) -> list[RecommendationCondition]:
    conditions = []
    for gene_symbol, phenotype_value in phenotypes.items():
        phenotype_name = normalize_text(phenotype_value)
        if phenotype_name is None:
            continue
        conditions.append(
            RecommendationCondition(
                gene_symbol=gene_symbol, phenotype_name=f"{gene_symbol} {phenotype_name}"
            )
        )
    return conditions


def parse_recommendation_records(
    raw_records: list[dict[str, Any]],
    guideline_version: str | None,
) -> list[RecommendationRecord]:
    records: list[RecommendationRecord] = []
    for order, item in enumerate(raw_records, start=1):
        recommendation_text = normalize_text(item.get("drugrecommendation"))
        if recommendation_text is None:
            continue

        conditions = _format_conditions(item.get("phenotypes") or {})
        if not conditions:
            continue

        population = normalize_text(item.get("population"))
        if population is not None:
            recommendation_text = f"[{population}] {recommendation_text}"

        implications: dict[str, Any] = item.get("implications") or {}
        implication_parts = [
            f"{gene_symbol}: {text}"
            for gene_symbol, text in implications.items()
            if normalize_text(text) is not None
        ]

        records.append(
            RecommendationRecord(
                conditions=conditions,
                recommendation_text=recommendation_text,
                implication="; ".join(implication_parts) or None,
                classification=normalize_text(item.get("classification")),
                cpic_guideline_version=guideline_version,
                recommendation_order=order,
            )
        )
    return records

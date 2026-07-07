from __future__ import annotations

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.models import PgxRecommendation, PgxRecommendationGene, PgxRecommendationPhenotype
from etl.parsers.recommendations import RecommendationWorkbook
from etl.loaders.reference import ReferenceCache, get_or_create_drug, get_or_create_gene, get_or_create_phenotype, upsert_drug_gene_mapping


async def _find_existing_recommendation(
    session: AsyncSession,
    drug_id: int,
    recommendation_text: str,
    implication: str | None,
    recommendation_strength: str | None,
    classification: str | None,
    source: str,
    recommendation_order: int | None,
) -> int | None:
    result = await session.execute(
        select(PgxRecommendation.recommendation_id).where(
            and_(
                PgxRecommendation.drug_id == drug_id,
                PgxRecommendation.recommendation_text == recommendation_text,
                PgxRecommendation.implication == implication,
                PgxRecommendation.recommendation_strength == recommendation_strength,
                PgxRecommendation.classification == classification,
                PgxRecommendation.source == source,
                PgxRecommendation.recommendation_order == recommendation_order,
            )
        )
    )
    return result.scalar_one_or_none()


async def load_recommendation_table(
    session: AsyncSession,
    workbook: RecommendationWorkbook,
    cache: ReferenceCache,
    drug_name: str,
) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    drug_id = await get_or_create_drug(session, cache, drug_name)
    if drug_id is None:
        counts["skipped"] += len(workbook.rows)
        return counts

    for row in workbook.rows:
        gene_ids: list[int] = []
        phenotype_ids: list[tuple[int, int]] = []
        skip_row = False
        for condition in row.conditions:
            gene_id = await get_or_create_gene(session, cache, condition.gene_symbol)
            if gene_id is None:
                skip_row = True
                break
            phenotype_id = await get_or_create_phenotype(session, cache, condition.phenotype_name)
            if phenotype_id is None:
                skip_row = True
                break
            gene_ids.append(gene_id)
            phenotype_ids.append((gene_id, phenotype_id))

        if skip_row or not gene_ids:
            counts["skipped"] += 1
            continue

        for gene_id in gene_ids:
            await upsert_drug_gene_mapping(session, drug_id, gene_id)

        existing_id = await _find_existing_recommendation(
            session,
            drug_id=drug_id,
            recommendation_text=row.recommendation_text,
            implication=row.implication,
            recommendation_strength=row.recommendation_strength,
            classification=row.classification,
            source=row.source,
            recommendation_order=row.recommendation_order,
        )
        if existing_id is not None:
            recommendation_id = existing_id
            await session.execute(
                update(PgxRecommendation)
                .where(PgxRecommendation.recommendation_id == recommendation_id)
                .values(
                    recommendation_text=row.recommendation_text,
                    implication=row.implication,
                    recommendation_strength=row.recommendation_strength,
                    classification=row.classification,
                    source=row.source,
                    cpic_guideline_version=row.cpic_guideline_version,
                    evidence_level=row.evidence_level,
                    recommendation_order=row.recommendation_order,
                )
            )
            counts["updated"] += 1
        else:
            statement = pg_insert(PgxRecommendation).values(
                drug_id=drug_id,
                recommendation_text=row.recommendation_text,
                implication=row.implication,
                recommendation_strength=row.recommendation_strength,
                classification=row.classification,
                source=row.source,
                cpic_guideline_version=row.cpic_guideline_version,
                evidence_level=row.evidence_level,
                recommendation_order=row.recommendation_order,
            )
            result = await session.execute(statement.returning(PgxRecommendation.recommendation_id))
            recommendation_id = result.scalar_one_or_none()
            if recommendation_id is not None:
                counts["inserted"] += 1
            else:
                counts["skipped"] += 1
                continue

        for gene_id in gene_ids:
            await session.execute(
                pg_insert(PgxRecommendationGene)
                .values(recommendation_id=recommendation_id, gene_id=gene_id)
                .on_conflict_do_nothing(
                    index_elements=[
                        PgxRecommendationGene.recommendation_id,
                        PgxRecommendationGene.gene_id,
                    ]
                )
            )

        for gene_id, phenotype_id in phenotype_ids:
            await session.execute(
                pg_insert(PgxRecommendationPhenotype)
                .values(
                    recommendation_id=recommendation_id,
                    gene_id=gene_id,
                    phenotype_id=phenotype_id,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        PgxRecommendationPhenotype.recommendation_id,
                        PgxRecommendationPhenotype.gene_id,
                        PgxRecommendationPhenotype.phenotype_id,
                    ]
                )
            )

    return counts

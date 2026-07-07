from __future__ import annotations

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.loaders.reference import ReferenceCache, get_or_create_gene, get_or_create_phenotype
from etl.models import GenotypePhenotypeMapping
from etl.transformers.diplotypes import DiplotypeRecord


async def _find_existing_mapping(
    session: AsyncSession,
    gene_id: int,
    allele1: str,
    allele2: str,
    phenotype_id: int | None,
) -> int | None:
    statement = select(GenotypePhenotypeMapping.mapping_id).where(
        and_(
            GenotypePhenotypeMapping.gene_id == gene_id,
            GenotypePhenotypeMapping.allele1 == allele1,
            GenotypePhenotypeMapping.allele2 == allele2,
            GenotypePhenotypeMapping.phenotype_id == phenotype_id,
        )
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def load_diplotype_table(
    session: AsyncSession,
    cache: ReferenceCache,
    gene_symbol: str,
    records: list[DiplotypeRecord],
) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    gene_id = await get_or_create_gene(session, cache, gene_symbol)
    if gene_id is None:
        counts["skipped"] += len(records)
        return counts

    for record in records:
        phenotype_id = await get_or_create_phenotype(
            session,
            cache,
            record.phenotype_name,
            record.phenotype_description,
        )
        if phenotype_id is None:
            counts["skipped"] += 1
            continue

        existing_id = await _find_existing_mapping(
            session,
            gene_id=gene_id,
            allele1=record.allele1,
            allele2=record.allele2,
            phenotype_id=phenotype_id,
        )
        if existing_id is not None:
            await session.execute(
                update(GenotypePhenotypeMapping)
                .where(GenotypePhenotypeMapping.mapping_id == existing_id)
                .values(
                    activity_score=record.activity_score,
                    phenotype_id=phenotype_id,
                )
            )
            counts["updated"] += 1
            continue

        statement = pg_insert(GenotypePhenotypeMapping).values(
            gene_id=gene_id,
            allele1=record.allele1,
            allele2=record.allele2,
            activity_score=record.activity_score,
            phenotype_id=phenotype_id,
        )
        result = await session.execute(statement.returning(GenotypePhenotypeMapping.mapping_id))
        if result.scalar_one_or_none() is not None:
            counts["inserted"] += 1
        else:
            counts["skipped"] += 1
    return counts

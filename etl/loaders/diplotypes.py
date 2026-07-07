from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.models import GenotypePhenotypeMapping
from etl.parsers.diplotypes import DiplotypeWorkbook
from etl.loaders.reference import ReferenceCache, get_or_create_drug, get_or_create_gene, get_or_create_phenotype, upsert_drug_gene_mapping


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
    workbook: DiplotypeWorkbook,
    cache: ReferenceCache,
    drug_name: str,
) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    drug_id = await get_or_create_drug(session, cache, drug_name)
    if drug_id is None:
        counts["skipped"] += len(workbook.rows)
        return counts

    for row in workbook.rows:
        gene_id = await get_or_create_gene(session, cache, row.gene_symbol)
        if gene_id is None:
            counts["skipped"] += 1
            continue

        phenotype_id = await get_or_create_phenotype(
            session,
            cache,
            row.phenotype_name,
            row.phenotype_description,
        )
        if phenotype_id is None:
            counts["skipped"] += 1
            continue

        await upsert_drug_gene_mapping(session, drug_id, gene_id)

        existing_id = await _find_existing_mapping(
            session,
            gene_id=gene_id,
            allele1=row.allele1,
            allele2=row.allele2,
            phenotype_id=phenotype_id,
        )
        if existing_id is not None:
            await session.execute(
                update(GenotypePhenotypeMapping)
                .where(GenotypePhenotypeMapping.mapping_id == existing_id)
                .values(
                    activity_score=row.activity_score,
                    phenotype_id=phenotype_id,
                )
            )
            counts["updated"] += 1
            continue

        statement = pg_insert(GenotypePhenotypeMapping).values(
            gene_id=gene_id,
            allele1=row.allele1,
            allele2=row.allele2,
            activity_score=row.activity_score,
            phenotype_id=phenotype_id,
        )
        result = await session.execute(statement.returning(GenotypePhenotypeMapping.mapping_id))
        if result.scalar_one_or_none() is not None:
            counts["inserted"] += 1
        else:
            counts["skipped"] += 1
    return counts

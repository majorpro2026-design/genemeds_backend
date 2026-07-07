from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.models import Allele
from etl.parsers.alleles import AlleleWorkbook
from etl.loaders.reference import ReferenceCache, get_or_create_drug, get_or_create_gene, upsert_drug_gene_mapping


async def load_allele_definition(
    session: AsyncSession,
    workbook: AlleleWorkbook,
    cache: ReferenceCache,
    drug_name: str,
) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    gene_id = await get_or_create_gene(session, cache, workbook.gene_symbol)
    if gene_id is None:
        counts["skipped"] += len(workbook.rows)
        return counts

    drug_id = await get_or_create_drug(session, cache, drug_name)
    if drug_id is not None:
        await upsert_drug_gene_mapping(session, drug_id, gene_id)

    for row in workbook.rows:
        existing = await session.execute(
            select(Allele.allele_id).where(
                Allele.gene_id == gene_id,
                Allele.star_allele == row.star_allele,
            )
        )
        existing_id = existing.scalar_one_or_none()
        if existing_id is not None:
            await session.execute(
                update(Allele)
                .where(Allele.allele_id == existing_id)
                .values(
                    functionality=row.functionality,
                    activity_value=row.activity_value,
                )
            )
            counts["updated"] += 1
            continue

        statement = pg_insert(Allele).values(
            gene_id=gene_id,
            star_allele=row.star_allele,
            functionality=row.functionality,
            activity_value=row.activity_value,
        )
        result = await session.execute(statement.returning(Allele.allele_id))
        if result.scalar_one_or_none() is not None:
            counts["inserted"] += 1
        else:
            counts["skipped"] += 1
    return counts

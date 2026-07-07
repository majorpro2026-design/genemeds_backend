from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.loaders.reference import ReferenceCache, get_or_create_gene
from etl.models import Allele
from etl.transformers.alleles import AlleleRecord


async def load_allele_definition(
    session: AsyncSession,
    cache: ReferenceCache,
    gene_symbol: str,
    records: list[AlleleRecord],
) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    gene_id = await get_or_create_gene(session, cache, gene_symbol)
    if gene_id is None:
        counts["skipped"] += len(records)
        return counts

    for record in records:
        existing = await session.execute(
            select(Allele.allele_id).where(
                Allele.gene_id == gene_id,
                Allele.star_allele == record.star_allele,
            )
        )
        existing_id = existing.scalar_one_or_none()
        if existing_id is not None:
            await session.execute(
                update(Allele)
                .where(Allele.allele_id == existing_id)
                .values(
                    functionality=record.functionality,
                    activity_value=record.activity_value,
                )
            )
            counts["updated"] += 1
            continue

        statement = pg_insert(Allele).values(
            gene_id=gene_id,
            star_allele=record.star_allele,
            functionality=record.functionality,
            activity_value=record.activity_value,
        )
        result = await session.execute(statement.returning(Allele.allele_id))
        if result.scalar_one_or_none() is not None:
            counts["inserted"] += 1
        else:
            counts["skipped"] += 1
    return counts

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from etl.models import (
    Drug,
    DrugGeneMapping,
    Gene,
    Phenotype,
)
from etl.utils.validation import normalize_text


class ReferenceCache:
    def __init__(self) -> None:
        self.gene_ids: dict[str, int] = {}
        self.drug_ids: dict[str, int] = {}
        self.phenotype_ids: dict[str, int] = {}


async def get_gene_id(session: AsyncSession, cache: ReferenceCache, gene_symbol: str) -> int | None:
    symbol = normalize_text(gene_symbol)
    if symbol is None:
        return None
    cached = cache.gene_ids.get(symbol.upper())
    if cached is not None:
        return cached

    statement = select(Gene.gene_id).where(Gene.gene_symbol == symbol)
    result = await session.execute(statement)
    gene_id = result.scalar_one_or_none()
    if gene_id is not None:
        cache.gene_ids[symbol.upper()] = gene_id
    return gene_id


async def upsert_gene(session: AsyncSession, cache: ReferenceCache, gene_symbol: str, gene_name: str | None = None) -> int:
    symbol = normalize_text(gene_symbol)
    if symbol is None:
        raise ValueError("gene_symbol is required")

    statement = pg_insert(Gene).values(gene_symbol=symbol, gene_name=normalize_text(gene_name))
    statement = statement.on_conflict_do_update(
        index_elements=[Gene.gene_symbol],
        set_={"gene_name": func.coalesce(statement.excluded.gene_name, Gene.gene_name)},
    ).returning(Gene.gene_id)
    result = await session.execute(statement)
    gene_id = result.scalar_one()
    cache.gene_ids[symbol.upper()] = gene_id
    return gene_id


async def get_or_create_gene(session: AsyncSession, cache: ReferenceCache, gene_symbol: str) -> int | None:
    gene_id = await get_gene_id(session, cache, gene_symbol)
    if gene_id is not None:
        return gene_id
    return await upsert_gene(session, cache, gene_symbol)


async def get_drug_id(session: AsyncSession, cache: ReferenceCache, generic_name: str) -> int | None:
    name = normalize_text(generic_name)
    if name is None:
        return None
    cached = cache.drug_ids.get(name.lower())
    if cached is not None:
        return cached
    result = await session.execute(select(Drug.drug_id).where(Drug.generic_name == name))
    drug_id = result.scalar_one_or_none()
    if drug_id is not None:
        cache.drug_ids[name.lower()] = drug_id
    return drug_id


async def upsert_drug(session: AsyncSession, cache: ReferenceCache, generic_name: str, drug_class: str | None = None) -> int:
    name = normalize_text(generic_name)
    if name is None:
        raise ValueError("generic_name is required")

    statement = pg_insert(Drug).values(generic_name=name, drug_class=normalize_text(drug_class))
    statement = statement.on_conflict_do_update(
        index_elements=[Drug.generic_name],
        set_={"drug_class": func.coalesce(statement.excluded.drug_class, Drug.drug_class)},
    ).returning(Drug.drug_id)
    result = await session.execute(statement)
    drug_id = result.scalar_one()
    cache.drug_ids[name.lower()] = drug_id
    return drug_id


async def get_or_create_drug(session: AsyncSession, cache: ReferenceCache, generic_name: str) -> int | None:
    drug_id = await get_drug_id(session, cache, generic_name)
    if drug_id is not None:
        return drug_id
    return await upsert_drug(session, cache, generic_name)


async def get_phenotype_id(session: AsyncSession, cache: ReferenceCache, phenotype_name: str) -> int | None:
    name = normalize_text(phenotype_name)
    if name is None:
        return None
    cached = cache.phenotype_ids.get(name.lower())
    if cached is not None:
        return cached
    result = await session.execute(select(Phenotype.phenotype_id).where(Phenotype.phenotype_name == name))
    phenotype_id = result.scalar_one_or_none()
    if phenotype_id is not None:
        cache.phenotype_ids[name.lower()] = phenotype_id
    return phenotype_id


async def upsert_phenotype(
    session: AsyncSession,
    cache: ReferenceCache,
    phenotype_name: str,
    phenotype_description: str | None = None,
) -> int:
    name = normalize_text(phenotype_name)
    if name is None:
        raise ValueError("phenotype_name is required")

    statement = pg_insert(Phenotype).values(
        phenotype_name=name,
        phenotype_description=normalize_text(phenotype_description),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[Phenotype.phenotype_name],
        set_={
            "phenotype_description": func.coalesce(
                statement.excluded.phenotype_description,
                Phenotype.phenotype_description,
            ),
        },
    ).returning(Phenotype.phenotype_id)
    result = await session.execute(statement)
    phenotype_id = result.scalar_one()
    cache.phenotype_ids[name.lower()] = phenotype_id
    return phenotype_id


async def get_or_create_phenotype(
    session: AsyncSession,
    cache: ReferenceCache,
    phenotype_name: str,
    phenotype_description: str | None = None,
) -> int | None:
    phenotype_id = await get_phenotype_id(session, cache, phenotype_name)
    if phenotype_id is not None:
        return phenotype_id
    return await upsert_phenotype(session, cache, phenotype_name, phenotype_description)


async def upsert_drug_gene_mapping(session: AsyncSession, drug_id: int, gene_id: int) -> tuple[int, bool]:
    statement = pg_insert(DrugGeneMapping).values(drug_id=drug_id, gene_id=gene_id)
    statement = statement.on_conflict_do_nothing(
        index_elements=[DrugGeneMapping.drug_id, DrugGeneMapping.gene_id]
    ).returning(DrugGeneMapping.mapping_id)
    result = await session.execute(statement)
    mapping_id = result.scalar_one_or_none()
    if mapping_id is not None:
        return mapping_id, True
    return 0, False

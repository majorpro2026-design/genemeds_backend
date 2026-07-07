from __future__ import annotations

import asyncio
import sys
from time import perf_counter

from app.core.database import SessionLocal as AsyncSessionFactory
from app.core.database import initialize_database
from etl.cpic_client import CpicApiClient
from etl.loaders.alleles import load_allele_definition
from etl.loaders.diplotypes import load_diplotype_table
from etl.loaders.recommendations import load_recommendation_table
from etl.loaders.reference import (
    ReferenceCache,
    get_or_create_drug,
    get_or_create_gene,
    upsert_drug_gene_mapping,
)
from etl.transformers.alleles import parse_allele_records
from etl.transformers.diplotypes import parse_diplotype_records
from etl.transformers.recommendations import parse_recommendation_records
from etl.utils.logging import get_etl_logger, humanize_seconds
from etl.utils.report import ETLReport, WorkbookSummary

logger = get_etl_logger()

GENES = ["CYP2C19", "CYP2D6", "CYP2C9", "VKORC1"]
DRUGS = ["clopidogrel", "metoprolol", "sertraline", "warfarin"]
GENE_DRUG_PAIRS = [
    ("CYP2C19", "clopidogrel"),
    ("CYP2C19", "sertraline"),
    ("CYP2D6", "metoprolol"),
    ("CYP2C9", "warfarin"),
    ("VKORC1", "warfarin"),
]


async def process_gene(
    client: CpicApiClient, session, cache: ReferenceCache, gene_symbol: str
) -> WorkbookSummary:
    started = perf_counter()
    summary = WorkbookSummary(file=f"gene:{gene_symbol}", workbook_type="gene")
    try:
        async with session.begin():
            allele_raw = await client.get_alleles(gene_symbol)
            allele_records = parse_allele_records(allele_raw)
            allele_counts = await load_allele_definition(
                session, cache, gene_symbol, allele_records
            )

            diplotype_raw = await client.get_diplotypes(gene_symbol)
            diplotype_records = parse_diplotype_records(diplotype_raw, gene_symbol)
            diplotype_counts = await load_diplotype_table(
                session, cache, gene_symbol, diplotype_records
            )

        for counts in (allele_counts, diplotype_counts):
            summary.inserted += counts["inserted"]
            summary.updated += counts["updated"]
            summary.skipped += counts["skipped"]
    except Exception as exc:  # noqa: BLE001
        summary.errors.append(str(exc))
        logger.exception("Gene fetch failed: %s", gene_symbol)

    summary.duration_seconds = perf_counter() - started
    return summary


async def process_drug(
    client: CpicApiClient, session, cache: ReferenceCache, drug_name: str
) -> tuple[WorkbookSummary, str | None]:
    started = perf_counter()
    summary = WorkbookSummary(file=f"drug:{drug_name}", workbook_type="drug")
    drug_id: str | None = None
    try:
        async with session.begin():
            drugs = await client.get_drugs([drug_name])
            if not drugs:
                raise ValueError(f"CPIC API returned no drug record for '{drug_name}'")
            drug_record = drugs[0]
            drug_id = drug_record["drugid"]
            await get_or_create_drug(session, cache, drug_name)

            guideline_version = None
            guideline_id = drug_record.get("guidelineid")
            if guideline_id is not None:
                guideline = await client.get_guideline(guideline_id)
                if guideline is not None and guideline.get("version") is not None:
                    guideline_version = str(guideline["version"])

            recommendation_raw = await client.get_recommendations(drug_id)
            recommendation_records = parse_recommendation_records(
                recommendation_raw, guideline_version
            )
            counts = await load_recommendation_table(
                session, cache, drug_name, recommendation_records
            )

        summary.inserted += counts["inserted"]
        summary.updated += counts["updated"]
        summary.skipped += counts["skipped"]
    except Exception as exc:  # noqa: BLE001
        summary.errors.append(str(exc))
        logger.exception("Drug fetch failed: %s", drug_name)

    summary.duration_seconds = perf_counter() - started
    return summary, drug_id


async def process_pair(
    client: CpicApiClient,
    session,
    cache: ReferenceCache,
    gene_symbol: str,
    drug_name: str,
    drug_id: str | None,
) -> WorkbookSummary:
    started = perf_counter()
    summary = WorkbookSummary(file=f"pair:{gene_symbol}-{drug_name}", workbook_type="pair")
    if drug_id is None:
        summary.errors.append(f"No CPIC drugid resolved for '{drug_name}'; skipping gene-drug link")
        summary.skipped += 1
        summary.duration_seconds = perf_counter() - started
        return summary

    try:
        async with session.begin():
            pairs = await client.get_pairs(gene_symbol, drug_id)
            if not pairs:
                summary.skipped += 1
            else:
                gene_id = await get_or_create_gene(session, cache, gene_symbol)
                drug_row_id = await get_or_create_drug(session, cache, drug_name)
                _, created = await upsert_drug_gene_mapping(session, drug_row_id, gene_id)
                if created:
                    summary.inserted += 1
                else:
                    summary.updated += 1
    except Exception as exc:  # noqa: BLE001
        summary.errors.append(str(exc))
        logger.exception("Gene-drug pair link failed: %s/%s", gene_symbol, drug_name)

    summary.duration_seconds = perf_counter() - started
    return summary


def _record(report: ETLReport, summary: WorkbookSummary) -> None:
    report.workbooks_processed += 1
    report.rows_inserted += summary.inserted
    report.rows_updated += summary.updated
    report.rows_skipped += summary.skipped
    report.workbook_summaries.append(summary)
    report.errors.extend(summary.errors)
    logger.info(
        "Processed %s | type=%s | inserted=%s updated=%s skipped=%s | %s",
        summary.file,
        summary.workbook_type,
        summary.inserted,
        summary.updated,
        summary.skipped,
        humanize_seconds(summary.duration_seconds),
    )


async def run_etl() -> ETLReport:
    report = ETLReport()
    cache = ReferenceCache()

    await initialize_database()

    async with CpicApiClient() as client, AsyncSessionFactory() as session:
        for gene_symbol in GENES:
            _record(report, await process_gene(client, session, cache, gene_symbol))

        drug_ids: dict[str, str] = {}
        for drug_name in DRUGS:
            summary, drug_id = await process_drug(client, session, cache, drug_name)
            if drug_id is not None:
                drug_ids[drug_name] = drug_id
            _record(report, summary)

        for gene_symbol, drug_name in GENE_DRUG_PAIRS:
            drug_id = drug_ids.get(drug_name)
            summary = await process_pair(client, session, cache, gene_symbol, drug_name, drug_id)
            _record(report, summary)

    return report


def main() -> None:
    if sys.platform.startswith("win"):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            report = runner.run(run_etl())
    else:
        report = asyncio.run(run_etl())
    logger.info(
        "ETL summary | units=%s inserted=%s updated=%s skipped=%s errors=%s",
        report.workbooks_processed,
        report.rows_inserted,
        report.rows_updated,
        report.rows_skipped,
        len(report.errors),
    )
    for error in report.errors:
        logger.error(error)


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

from app.core.database import SessionLocal as AsyncSessionFactory, initialize_database
from etl.loaders.alleles import load_allele_definition
from etl.loaders.diplotypes import load_diplotype_table
from etl.loaders.reference import ReferenceCache
from etl.loaders.recommendations import load_recommendation_table
from etl.parsers.alleles import parse_allele_definition_workbook
from etl.parsers.diplotypes import parse_diplotype_workbook
from etl.parsers.recommendations import parse_recommendation_workbook
from etl.utils.logging import get_etl_logger, humanize_seconds
from etl.utils.report import ETLReport, WorkbookSummary
from etl.utils.workbooks import classify_workbook, discover_workbooks, infer_drug_name


logger = get_etl_logger()


async def process_workbook(session, cache: ReferenceCache, path: Path) -> WorkbookSummary:
    started = perf_counter()
    summary = WorkbookSummary(file=str(path), workbook_type="unknown")

    try:
        workbook_type = classify_workbook(path)
        summary.workbook_type = workbook_type or "unknown"
        if workbook_type is None:
            raise ValueError("Unable to classify workbook")

        drug_name = infer_drug_name(path)
        if not drug_name:
            raise ValueError("Unable to infer drug name from workbook path")

        async with session.begin():
            if workbook_type == "allele_definition":
                parsed = parse_allele_definition_workbook(path)
                if parsed is None:
                    raise ValueError("No allele definition sheet detected")
                counts = await load_allele_definition(session, parsed, cache, drug_name)
            elif workbook_type == "diplotype_phenotype":
                parsed = parse_diplotype_workbook(path)
                if parsed is None:
                    raise ValueError("No diplotype sheet detected")
                counts = await load_diplotype_table(session, parsed, cache, drug_name)
            elif workbook_type == "recommendation":
                parsed = parse_recommendation_workbook(path)
                if parsed is None:
                    raise ValueError("No recommendation sheet detected")
                counts = await load_recommendation_table(session, parsed, cache, drug_name)
            else:
                raise ValueError(f"Unsupported workbook type: {workbook_type}")

            summary.inserted += counts["inserted"]
            summary.updated += counts["updated"]
            summary.skipped += counts["skipped"]
    except Exception as exc:  # noqa: BLE001
        summary.errors.append(str(exc))
        logger.exception("Workbook failed: %s", path)

    summary.duration_seconds = perf_counter() - started
    return summary


async def run_etl(root: Path | str = "cpic") -> ETLReport:
    report = ETLReport()
    workbooks = discover_workbooks(root)
    cache = ReferenceCache()

    await initialize_database()

    async with AsyncSessionFactory() as session:
        for path in workbooks:
            summary = await process_workbook(session, cache, path)
            report.workbooks_processed += 1
            report.rows_inserted += summary.inserted
            report.rows_updated += summary.updated
            report.rows_skipped += summary.skipped
            report.workbook_summaries.append(summary)
            report.errors.extend(summary.errors)
            logger.info(
                "Processed %s | type=%s | inserted=%s updated=%s skipped=%s | %s",
                path.name,
                summary.workbook_type,
                summary.inserted,
                summary.updated,
                summary.skipped,
                humanize_seconds(summary.duration_seconds),
            )

    return report


def main() -> None:
    if sys.platform.startswith("win"):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            report = runner.run(run_etl())
    else:
        report = asyncio.run(run_etl())
    logger.info(
        "ETL summary | workbooks=%s inserted=%s updated=%s skipped=%s errors=%s",
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

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkbookSummary:
    file: str
    workbook_type: str
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class ETLReport:
    workbooks_processed: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    workbook_summaries: list[WorkbookSummary] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


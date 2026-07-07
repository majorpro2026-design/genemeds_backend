from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from etl.utils.validation import normalize_text, row_has_data


@dataclass(frozen=True)
class HeaderMatch:
    sheet_name: str
    header_row: int
    headers: list[str]


def clean_header_values(values: list[Any]) -> list[str]:
    return [normalize_text(value) or "" for value in values]


def find_header_row(sheet, required_terms: list[str], scan_rows: int = 15) -> HeaderMatch | None:
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=1, max_row=scan_rows, values_only=True),
        start=1,
    ):
        values = clean_header_values(list(row))
        blob = " | ".join(values).lower()
        if all(term.lower() in blob for term in required_terms):
            return HeaderMatch(sheet_name=sheet.title, header_row=row_number, headers=values)
    return None


def iter_nonempty_rows(sheet, start_row: int):
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=start_row, values_only=True),
        start=start_row,
    ):
        values = list(row)
        if row_has_data(values):
            yield row_number, values


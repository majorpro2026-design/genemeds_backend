from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationIssue:
    message: str
    row_number: int | None = None


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def normalize_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = normalize_text(value)
    if text is None:
        return None
    if text.lower() in {"n/a", "na", "none", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def row_has_data(values: list[Any]) -> bool:
    return any(normalize_text(value) is not None for value in values)


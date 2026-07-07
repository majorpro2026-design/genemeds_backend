from __future__ import annotations

import logging
from collections.abc import Iterable


def get_etl_logger() -> logging.Logger:
    logger = logging.getLogger("genemeds.etl")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def humanize_seconds(seconds: float) -> str:
    return f"{seconds:.2f}s"


def join_errors(errors: Iterable[str]) -> str:
    return "; ".join(errors)


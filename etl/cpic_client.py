from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

import httpx

from app.core.config import get_settings

_PAGE_SIZE = 1000
_MAX_ATTEMPTS = 3


class CpicApiError(RuntimeError):
    pass


class CpicApiClient:
    """Async client for the CPIC PostgREST API (https://api.cpicpgx.org/v1)."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(
            base_url=base_url or settings.cpic_api_base_url,
            timeout=timeout or settings.cpic_api_timeout,
        )

    async def __aenter__(self) -> CpicApiClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _get_page(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        raise CpicApiError(
            f"Request to {path} failed after {_MAX_ATTEMPTS} attempts"
        ) from last_error

    async def _get_all(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = await self._get_page(path, {**params, "limit": _PAGE_SIZE, "offset": offset})
            results.extend(page)
            if len(page) < _PAGE_SIZE:
                return results
            offset += _PAGE_SIZE

    @staticmethod
    def _in_filter(values: list[str]) -> str:
        return "in.(" + ",".join(values) + ")"

    async def get_genes(self, symbols: list[str]) -> list[dict[str, Any]]:
        return await self._get_all("/gene", {"symbol": self._in_filter(symbols)})

    async def get_drugs(self, names: list[str]) -> list[dict[str, Any]]:
        return await self._get_all("/drug", {"name": self._in_filter(names)})

    async def get_alleles(self, gene_symbol: str) -> list[dict[str, Any]]:
        return await self._get_all("/allele", {"genesymbol": f"eq.{gene_symbol}"})

    async def get_diplotypes(self, gene_symbol: str) -> list[dict[str, Any]]:
        return await self._get_all("/diplotype", {"genesymbol": f"eq.{gene_symbol}"})

    async def get_pairs(self, gene_symbol: str, drug_id: str) -> list[dict[str, Any]]:
        return await self._get_all(
            "/pair",
            {
                "genesymbol": f"eq.{gene_symbol}",
                "drugid": f"eq.{drug_id}",
                "usedforrecommendation": "eq.true",
            },
        )

    async def get_recommendations(self, drug_id: str) -> list[dict[str, Any]]:
        return await self._get_all("/recommendation", {"drugid": f"eq.{drug_id}"})

    async def get_guideline(self, guideline_id: int) -> dict[str, Any] | None:
        results = await self._get_all("/guideline", {"id": f"eq.{guideline_id}"})
        return results[0] if results else None

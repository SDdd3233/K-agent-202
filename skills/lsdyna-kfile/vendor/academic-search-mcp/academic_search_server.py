"""Search-only academic MCP server embedded in K-Agent.

The public tool surface is intentionally limited to multi-source paper search
and optional source-specific Scopus/ScienceDirect searches.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import FastMCP

from sources import (
    ArxivSource,
    CrossRefSource,
    PubMedSource,
    ScienceDirectSource,
    ScopusSource,
)
from utils import DataSourceError, setup_logging


mcp = FastMCP("academic-search")
logger = setup_logging()

_crossref = CrossRefSource()
_pubmed = PubMedSource()
_arxiv = ArxivSource()
_scopus = ScopusSource()
_sciencedirect = ScienceDirectSource()


def _json_ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _json_error(message: str, source: str | None = None) -> str:
    payload: dict[str, Any] = {"error": message}
    if source:
        payload["source"] = source
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def _search_crossref(query: str, rows: int, filter_type: str | None) -> dict:
    return await asyncio.to_thread(_crossref.search, query, rows, filter_type)


async def _search_pubmed(query: str, rows: int) -> dict:
    return await asyncio.to_thread(_pubmed.search, query, rows)


async def _search_arxiv(query: str, rows: int) -> dict:
    return await asyncio.to_thread(_arxiv.search, query, rows)


async def _search_scopus(query: str, rows: int) -> dict:
    return await asyncio.to_thread(_scopus.search, query, rows)


async def _search_sciencedirect(query: str, rows: int) -> dict:
    return await asyncio.to_thread(_sciencedirect.search, query, rows)


async def _search_all(
    query: str,
    sources: list[str],
    rows: int,
    filter_type: str | None,
) -> dict:
    tasks: list[asyncio.Task] = []
    source_order: list[str] = []

    if "crossref" in sources:
        tasks.append(asyncio.create_task(_search_crossref(query, rows, filter_type)))
        source_order.append("crossref")
    if "pubmed" in sources:
        tasks.append(asyncio.create_task(_search_pubmed(query, rows)))
        source_order.append("pubmed")
    if "arxiv" in sources:
        tasks.append(asyncio.create_task(_search_arxiv(query, rows)))
        source_order.append("arxiv")
    if "scopus" in sources:
        tasks.append(asyncio.create_task(_search_scopus(query, rows)))
        source_order.append("scopus")
    if "sciencedirect" in sources:
        tasks.append(asyncio.create_task(_search_sciencedirect(query, rows)))
        source_order.append("sciencedirect")

    if not tasks:
        return {"total": 0, "sources_queried": [], "result_count": 0, "results": [], "errors": None}

    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    merged_results: list[dict] = []
    errors: list[dict] = []
    total = 0

    for source, outcome in zip(source_order, outcomes):
        if isinstance(outcome, BaseException):
            logger.error("Source %s failed: %s", source, outcome)
            errors.append({"source": source, "error": str(outcome)})
            continue
        total += outcome.get("total", 0)
        merged_results.extend(outcome.get("results", []))

    return {
        "total": total,
        "sources_queried": source_order,
        "result_count": len(merged_results),
        "results": merged_results,
        "errors": errors or None,
    }


@mcp.tool()
async def search_papers(
    query: str,
    sources: list[str] | None = None,
    rows: int = 5,
    type: str | None = None,
) -> str:
    """Search papers across CrossRef, PubMed, arXiv, and opt-in Elsevier sources."""
    if not query or not query.strip():
        return _json_error("Empty search query")

    sources = ["crossref", "pubmed", "arxiv"] if sources is None else sources
    valid_sources = {"crossref", "pubmed", "arxiv", "scopus", "sciencedirect"}
    invalid = [source for source in sources if source not in valid_sources]
    if invalid:
        return _json_error(f"Invalid sources: {invalid}. Valid: {sorted(valid_sources)}")

    rows = max(1, min(rows, 50))
    logger.info(
        "search_papers called",
        extra={"tool": "search_papers", "query": query, "sources": sources, "rows": rows},
    )

    try:
        result = await _search_all(query, sources, rows, type)
    except Exception as exc:
        logger.exception("search_papers failed")
        return _json_error(f"Search failed: {exc}")
    return _json_ok(result)


@mcp.tool()
def search_scopus(
    query: str,
    rows: int = 5,
    view: str | None = None,
    subscriber: bool = True,
) -> str:
    """Search Scopus documents using an advanced-search query."""
    if not query or not query.strip():
        return _json_error("Empty search query", source="scopus")
    try:
        return _json_ok(_scopus.search(query, rows, view=view, subscriber=subscriber))
    except DataSourceError as exc:
        logger.error("search_scopus failed: %s", exc)
        return _json_error(str(exc), source=exc.source)
    except Exception as exc:
        logger.exception("search_scopus failed unexpectedly")
        return _json_error(f"Unexpected error: {exc}", source="scopus")


@mcp.tool()
def search_sciencedirect(
    query: str,
    rows: int = 5,
    view: str | None = None,
) -> str:
    """Search ScienceDirect article metadata."""
    if not query or not query.strip():
        return _json_error("Empty search query", source="sciencedirect")
    try:
        return _json_ok(_sciencedirect.search(query, rows=rows, view=view))
    except DataSourceError as exc:
        logger.error("search_sciencedirect failed: %s", exc)
        return _json_error(str(exc), source=exc.source)
    except Exception as exc:
        logger.exception("search_sciencedirect failed unexpectedly")
        return _json_error(f"Unexpected error: {exc}", source="sciencedirect")


if __name__ == "__main__":
    mcp.run(transport="stdio")

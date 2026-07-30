"""Search-only Scopus data source via pybliometrics."""

from __future__ import annotations

from typing import Any

from pybliometrics.utils import URLS, get_content

from utils.errors import DataSourceError

from .elsevier_common import ensure_pybliometrics_config, year_from_date


SOURCE_NAME = "scopus"


class ScopusSource:
    """Search Scopus documents and normalize the first result page."""

    SOURCE_NAME = SOURCE_NAME

    def search(
        self,
        query: str,
        rows: int = 5,
        view: str | None = None,
        refresh: bool | int = False,
        subscriber: bool = True,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise DataSourceError(SOURCE_NAME, "Empty search query")

        rows = max(1, min(rows, 50))

        def run() -> dict[str, Any]:
            effective_view = view or ("COMPLETE" if subscriber else "STANDARD")
            data = self._search_api(
                "ScopusSearch",
                {"query": query.strip(), "count": rows, "start": 0, "view": effective_view},
            )
            records = _search_entries(data)
            return {
                "total": _total_results(data),
                "query": query,
                "source": SOURCE_NAME,
                "results": [self._normalize_search_entry(record) for record in records[:rows]],
            }

        return self._run("Scopus search", run)

    def _run(self, operation: str, callback):
        ensure_pybliometrics_config(SOURCE_NAME)
        try:
            return callback()
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                SOURCE_NAME,
                f"{operation} failed: {exc}",
                original_error=exc,
            ) from exc

    @staticmethod
    def _search_api(api: str, params: dict[str, Any]) -> dict[str, Any]:
        response = get_content(URLS[api], api, params=params)
        return response.json()

    @staticmethod
    def _normalize_search_entry(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": data.get("dc:title"),
            "authors": _extract_authors(data),
            "year": year_from_date(data.get("prism:coverDate")),
            "doi": data.get("prism:doi"),
            "eid": data.get("eid"),
            "pii": data.get("pii"),
            "pmid": data.get("pubmed-id"),
            "journal": data.get("prism:publicationName"),
            "volume": data.get("prism:volume"),
            "issue": data.get("prism:issueIdentifier"),
            "pages": data.get("prism:pageRange"),
            "subtype": data.get("subtype"),
            "subtype_description": data.get("subtypeDescription"),
            "citation_count": _int_or_none(data.get("citedby-count")),
            "openaccess": data.get("openaccess"),
            "source": SOURCE_NAME,
        }


def _search_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = data.get("search-results", {}).get("entry", [])
    return _as_list(entries)


def _total_results(data: dict[str, Any]) -> int:
    total = data.get("search-results", {}).get("opensearch:totalResults", 0)
    return _int_or_none(total) or 0


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_authors(data: dict[str, Any]) -> list[str]:
    authors = []
    for item in _as_list(data.get("author")):
        name = item.get("authname") or item.get("ce:indexed-name")
        if name:
            authors.append(name)
    creator = data.get("dc:creator")
    if not authors and creator:
        authors.append(creator)
    return authors


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

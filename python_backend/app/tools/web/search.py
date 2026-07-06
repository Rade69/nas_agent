"""Web search tool handler (FAZA 16).

Migrated from electron/main.cjs `webSearch()`. Uses ExaClient to run the
search and renders results as a Markdown research brief artifact (same format
as the legacy Electron handler, so the artifact panel behavior is unchanged).

Risk: low (read-only web search, no confirmation required). The OpenAI/Exa
API key is held only on the Python backend side (Security Gate 0 / FAZA 6
pattern extended to Exa in this phase).
"""
from __future__ import annotations

from typing import Any

from app.services.exa_client import ExaClient


def make_handlers(client: ExaClient) -> dict[str, Any]:
    def web_search(arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "")
        if not query.strip():
            raise ValueError("web_search requires a non-empty 'query' string argument.")
        num_results = arguments.get("numResults", 5)
        results = client.search(query=query, num_results=int(num_results) if num_results else 5)
        artifact = {
            "title": f"Web Search: {query}",
            "kind": "markdown",
            "content": _format_search_markdown(query, results),
        }
        return {"results": results, "artifact": artifact}

    return {"web_search": web_search}


def _format_search_markdown(query: str, results: list[dict[str, Any]]) -> str:
    clean_query = query.strip() or "Search"
    if not results:
        return (
            f"# {clean_query}\n\nNo strong web results came back for this search. "
            "Try a narrower query or ask Ricky to search a specific site."
        )

    sections = []
    for index, result in enumerate(results[:8]):
        title = _clean_text(result.get("title") or result.get("url") or f"Result {index + 1}")
        url = str(result.get("url") or "")
        source = _clean_text(result.get("author") or _hostname(url) or "Source")
        text = _clean_text(result.get("text") or result.get("summary") or "")[:700]
        published = result.get("publishedDate")
        published_line = f"\n- Published: {_clean_text(published)}" if published else ""
        link = f"[Open source]({url})" if url else "Source link unavailable"
        snippet = text or "No snippet was returned for this result."
        sections.append(
            f"### {index + 1}. {title}\n\n{snippet}\n\n- Source: {source}{published_line}\n- {link}"
        )

    count = len(results)
    plural = "" if count == 1 else "s"
    return "\n\n".join([f"# {clean_query}", f"Ricky found {count} source{plural}.", *sections])


def _clean_text(value: Any) -> str:
    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
        .replace("  ", " ")
        .replace("<", "")
        .replace(">", "")
        .strip()
    )


def _hostname(url: str) -> str:
    try:
        from urllib.parse import urlparse

        host = urlparse(url).hostname or ""
        return host.replace("www.", "") if host else ""
    except Exception:
        return ""

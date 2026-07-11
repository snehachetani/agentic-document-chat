from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
EXA_SEARCH_URL = "https://api.exa.ai/search"

NASA_DOMAINS = ["nasa.gov"]
NOAA_DOMAINS = ["noaa.gov"]


def general_web_search_tool(
    query: str,
    allowed_domains: list[str],
    max_results: int = 5,
) -> dict[str, Any]:
    results = _search(
        query=query,
        domains=allowed_domains,
        max_results=max_results,
    )

    return {
        "results": [
            {
                "title": item["title"],
                "url": item["url"],
                "source_domain": _domain(item["url"]),
                "snippet": item["snippet"],
                "retrieved_text": item["retrieved_text"],
            }
            for item in results
        ]
    }


def nasa_search_tool(
    query: str,
    section_id: str,
    max_results: int = 5,
) -> dict[str, Any]:
    results = _search(
        query=query,
        domains=NASA_DOMAINS,
        max_results=max_results,
    )

    return {
        "results": [
            {
                "source_title": item["title"],
                "source_url": item["url"],
                "retrieved_text": item["retrieved_text"],
                "relevance_reason": (
                    f"NASA evidence retrieved for verifying `{section_id}`."
                ),
            }
            for item in results
        ]
    }


def noaa_climate_search_tool(
    query: str,
    section_id: str,
    max_results: int = 5,
) -> dict[str, Any]:
    results = _search(
        query=query,
        domains=NOAA_DOMAINS,
        max_results=max_results,
    )

    return {
        "results": [
            {
                "source_title": item["title"],
                "source_url": item["url"],
                "retrieved_text": item["retrieved_text"],
                "relevance_reason": (
                    f"NOAA evidence retrieved for verifying `{section_id}`."
                ),
            }
            for item in results
        ]
    }


def _search(
    query: str,
    domains: list[str],
    max_results: int,
) -> list[dict[str, str]]:
    results = _search_tavily(
        query=query,
        domains=domains,
        max_results=max_results,
    )
    if results:
        return results

    results = _search_exa(
        query=query,
        domains=domains,
        max_results=max_results,
    )
    if results:
        return results

    return _offline_sample_results(
        domains=domains,
        max_results=max_results,
    )


def _search_tavily(
    query: str,
    domains: list[str],
    max_results: int,
) -> list[dict[str, str]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "topic": "general",
        "include_domains": domains,
        "include_raw_content": True,
    }

    request = urllib.request.Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "retrieved_text": item.get("raw_content") or item.get("content", ""),
            "score": item.get("score"),
        }
        for item in data.get("results", [])
        if item.get("url") and (item.get("raw_content") or item.get("content"))
    ]


def _search_exa(
    query: str,
    domains: list[str],
    max_results: int,
) -> list[dict[str, str]]:
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return []

    payload = {
        "query": query,
        "numResults": max_results,
        "includeDomains": domains,
        "type": "auto",
        "contents": {
            "text": True,
            "highlights": True,
        },
    }

    request = urllib.request.Request(
        EXA_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": _exa_snippet(item),
            "retrieved_text": _exa_retrieved_text(item),
        }
        for item in data.get("results", [])
        if item.get("url") and _exa_retrieved_text(item)
    ]


def _exa_snippet(item: dict[str, Any]) -> str:
    highlights = item.get("highlights") or []
    if highlights:
        return str(highlights[0])

    summary = item.get("summary")
    if summary:
        return str(summary)

    return str(item.get("text", ""))[:500]


def _exa_retrieved_text(item: dict[str, Any]) -> str:
    text = item.get("text")
    if text:
        return str(text)

    highlights = item.get("highlights") or []
    if highlights:
        return " ".join(str(value) for value in highlights)

    summary = item.get("summary")
    return str(summary) if summary else ""


def _offline_sample_results(
    domains: list[str],
    max_results: int,
) -> list[dict[str, str]]:
    domain = domains[0] if domains else "example.org"
    source_url = f"https://www.{domain}/" if domain in {"nasa.gov", "noaa.gov"} else f"https://{domain}/"

    text = (
        "Clouds influence Earth's climate by reflecting incoming sunlight and "
        "affecting outgoing infrared radiation. Cloud formation and cloud "
        "properties depend on atmospheric temperature, water vapor, particles, "
        "and air motion."
    )

    return [
        {
            "title": f"Offline sample evidence from {domain}",
            "url": source_url,
            "snippet": text,
            "retrieved_text": text,
        }
        for _ in range(max(1, min(max_results, 2)))
    ]


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc

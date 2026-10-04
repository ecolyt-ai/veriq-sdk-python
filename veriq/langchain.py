"""LangChain-compatible adapters backed by :class:`veriq.VeriqClient`."""

from __future__ import annotations

import os
from typing import Any, Literal

from veriq.client import DEFAULT_BASE_URL, Purpose, VeriqClient
from veriq.models import JobAcceptedResponse, SearchResponse


class VeriqSearchResults:
    """Drop-in, dependency-free replacement for TavilySearchResults."""

    name: str = "veriq_search"
    description: str = (
        "Search the web using Veriq's AI search engine. "
        "Returns relevant results with titles, URLs, and content snippets. "
        "Input should be a search query string."
    )

    def __init__(
        self,
        api_key: str | None = None,
        max_results: int = 5,
        search_depth: Literal["basic", "advanced"] = "basic",
        include_answer: bool = False,
        include_raw_content: bool = False,
        topic: Literal["general", "news", "academic"] = "general",
        freshness_mode: Literal["strict", "best_effort"] = "best_effort",
        purpose: Purpose = "user_directed_retrieval",
        cache_mode: Literal["default", "bypass"] = "default",
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        resolved_api_key = api_key or os.environ.get("VERIQ_API_KEY", "")
        if not resolved_api_key:
            raise ValueError("VERIQ_API_KEY must be set (pass api_key= or set env var)")
        self.api_key = resolved_api_key
        self.max_results = max_results
        self.search_depth = search_depth
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content
        self.topic = topic
        self.freshness_mode = freshness_mode
        self.purpose = purpose
        self.cache_mode = cache_mode
        self.base_url = base_url
        self._client = VeriqClient(resolved_api_key, base_url=base_url)

    def invoke(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Run a search and return Tavily-compatible result dictionaries."""
        return self._search(query)

    def run(self, query: str, **kwargs: Any) -> str:
        """Run a search and return Tavily-compatible formatted text."""
        results = self._search(query)
        return "\n".join(
            f"Title: {result['title']}\nURL: {result['url']}\n"
            f"Content: {result['content']}\n"
            for result in results
        )

    def __call__(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Support direct calls."""
        return self._search(query)

    def _search(self, query: str) -> list[dict[str, Any]]:
        response = self._client.search(
            query,
            max_results=self.max_results,
            search_depth=self.search_depth,
            include_answer=self.include_answer,
            include_raw_content=self.include_raw_content,
            topic=self.topic,
            freshness_mode=self.freshness_mode,
            purpose=self.purpose,
            cache_mode=self.cache_mode,
        )
        return self._tavily_results(response)

    async def ainvoke(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Run an asynchronous search."""
        return await self._async_search(query)

    async def _async_search(self, query: str) -> list[dict[str, Any]]:
        response = await self._client.async_search(
            query,
            max_results=self.max_results,
            search_depth=self.search_depth,
            include_answer=self.include_answer,
            include_raw_content=self.include_raw_content,
            topic=self.topic,
            freshness_mode=self.freshness_mode,
            purpose=self.purpose,
            cache_mode=self.cache_mode,
        )
        return self._tavily_results(response)

    @staticmethod
    def _tavily_results(response: SearchResponse) -> list[dict[str, Any]]:
        return [
            {
                "title": result.title,
                "url": result.url,
                "content": result.snippet,
                "raw_content": result.raw_content or result.content,
                "score": result.score,
                "freshness_status": result.freshness_status,
                "raw_content_metadata": result.raw_content_metadata,
            }
            for result in response.results
        ]


class VeriqExtract:
    """Dependency-free LangChain-compatible extraction tool."""

    name: str = "veriq_extract"
    description: str = (
        "Extract clean content from web URLs. Returns markdown-formatted text. "
        "Input should be a URL or comma-separated list of URLs."
    )

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        resolved_api_key = api_key or os.environ.get("VERIQ_API_KEY", "")
        if not resolved_api_key:
            raise ValueError("VERIQ_API_KEY must be set (pass api_key= or set env var)")
        self.api_key = resolved_api_key
        self.base_url = base_url
        self._client = VeriqClient(resolved_api_key, base_url=base_url)

    def invoke(self, urls: str | list[str], **kwargs: Any) -> str:
        """Extract content, explicitly representing accepted asynchronous jobs."""
        normalized_urls = (
            [url.strip() for url in urls.split(",") if url.strip()]
            if isinstance(urls, str)
            else list(urls)
        )
        response = self._client.extract(normalized_urls)
        if isinstance(response, JobAcceptedResponse):
            return (
                f"Veriq extraction job accepted: {response.job_id} "
                f"(status: {response.status}, request_id: {response.request_id})"
            )
        parts = [
            f"## {result.title or result.url}\n\n{result.content}"
            for result in response.results
            if result.content
        ]
        return "\n\n---\n\n".join(parts)

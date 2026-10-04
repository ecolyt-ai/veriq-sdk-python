"""Synchronous and asynchronous clients for the Veriq REST API."""

from __future__ import annotations

import asyncio
import json
import math
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import quote
from uuid import uuid4

import httpx

from veriq._version import __version__
from veriq.errors import (
    VeriqApiError,
    VeriqError,
    VeriqJobTimeoutError,
    VeriqNetworkError,
    VeriqResponseError,
)
from veriq.models import (
    CrawlJobResponse,
    ExtractResponse,
    JobAcceptedResponse,
    JobCancellationResponse,
    JobResultsPage,
    JobStatusResponse,
    MapResponse,
    SearchResponse,
)

DEFAULT_BASE_URL = "https://1xph5yqrc2.execute-api.us-east-1.amazonaws.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_RETRY_DELAY = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 50 * 1024 * 1024
DEFAULT_WAIT_TIMEOUT = 300.0
DEFAULT_POLL_INTERVAL = 1.0
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
_CHARGED_CREATE_PATHS = frozenset({"/v1/search", "/v1/extract", "/v1/crawl", "/v1/map"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
_TERMINAL_LIFECYCLES = frozenset({"terminal", "expired"})
_USER_AGENT = f"veriq-python/{__version__}"

ExecutionMode = Literal["auto", "sync", "async"]
Purpose = Literal[
    "search_indexing",
    "user_directed_retrieval",
    "extraction",
    "rag_context",
    "model_training",
    "customer_owned_site",
    "licensed_collection",
]


@dataclass(frozen=True)
class _JsonResponse:
    status_code: int
    data: dict[str, Any]


class VeriqClient:
    """Veriq API client supporting sync and async usage."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if not math.isfinite(max_retry_delay) or max_retry_delay < 0:
            raise ValueError("max_retry_delay must be a non-negative finite number")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes <= 0
        ):
            raise ValueError("max_response_bytes must be a positive integer")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_retry_delay = max_retry_delay
        self.max_response_bytes = max_response_bytes

    def search(
        self,
        query: str,
        *,
        search_depth: Literal["basic", "advanced"] = "basic",
        topic: Literal["general", "news", "academic"] = "general",
        max_results: int = 10,
        include_answer: bool | Literal["basic", "advanced"] = False,
        include_raw_content: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        days: int | None = None,
        freshness_mode: Literal["strict", "best_effort"] = "best_effort",
        purpose: Purpose = "user_directed_retrieval",
        cache_mode: Literal["default", "bypass"] = "default",
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> SearchResponse:
        """Search synchronously with explicit freshness, purpose, and cache controls."""
        payload = self._build_search_payload(
            query=query,
            search_depth=search_depth,
            topic=topic,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            days=days,
            freshness_mode=freshness_mode,
            purpose=purpose,
            cache_mode=cache_mode,
        )
        response = self._request_json(
            "POST",
            "/v1/search",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        return SearchResponse.from_dict(response.data)

    async def async_search(
        self,
        query: str,
        *,
        search_depth: Literal["basic", "advanced"] = "basic",
        topic: Literal["general", "news", "academic"] = "general",
        max_results: int = 10,
        include_answer: bool | Literal["basic", "advanced"] = False,
        include_raw_content: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        days: int | None = None,
        freshness_mode: Literal["strict", "best_effort"] = "best_effort",
        purpose: Purpose = "user_directed_retrieval",
        cache_mode: Literal["default", "bypass"] = "default",
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> SearchResponse:
        """Search asynchronously with explicit freshness, purpose, and cache controls."""
        payload = self._build_search_payload(
            query=query,
            search_depth=search_depth,
            topic=topic,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            days=days,
            freshness_mode=freshness_mode,
            purpose=purpose,
            cache_mode=cache_mode,
        )
        response = await self._async_request_json(
            "POST",
            "/v1/search",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        return SearchResponse.from_dict(response.data)

    def extract(
        self,
        urls: list[str],
        *,
        format: Literal["markdown", "text", "html"] = "markdown",
        include_metadata: bool = True,
        purpose: Purpose = "extraction",
        render: Literal["http_only", "browser_render"] = "http_only",
        execution_mode: ExecutionMode = "auto",
        idempotency_key: str | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        request_id: str | None = None,
    ) -> ExtractResponse | JobAcceptedResponse:
        """Extract URLs inline or submit an asynchronous job."""
        payload = self._build_extract_payload(
            urls=urls,
            format=format,
            include_metadata=include_metadata,
            purpose=purpose,
            render=render,
            execution_mode=execution_mode,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            callback_secret=callback_secret,
        )
        response = self._request_json(
            "POST",
            "/v1/extract",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        if response.status_code == 202:
            return JobAcceptedResponse.from_dict(response.data)
        return ExtractResponse.from_dict(response.data)

    async def async_extract(
        self,
        urls: list[str],
        *,
        format: Literal["markdown", "text", "html"] = "markdown",
        include_metadata: bool = True,
        purpose: Purpose = "extraction",
        render: Literal["http_only", "browser_render"] = "http_only",
        execution_mode: ExecutionMode = "auto",
        idempotency_key: str | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        request_id: str | None = None,
    ) -> ExtractResponse | JobAcceptedResponse:
        """Extract URLs through an asynchronous HTTP client."""
        payload = self._build_extract_payload(
            urls=urls,
            format=format,
            include_metadata=include_metadata,
            purpose=purpose,
            render=render,
            execution_mode=execution_mode,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            callback_secret=callback_secret,
        )
        response = await self._async_request_json(
            "POST",
            "/v1/extract",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        if response.status_code == 202:
            return JobAcceptedResponse.from_dict(response.data)
        return ExtractResponse.from_dict(response.data)

    def map(
        self,
        url: str,
        *,
        max_depth: int = 2,
        max_urls: int = 100,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        purpose: Purpose = "user_directed_retrieval",
        allowed_domains: list[str] | None = None,
        preserve_query: bool = True,
        execution_mode: ExecutionMode = "auto",
        idempotency_key: str | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        request_id: str | None = None,
    ) -> MapResponse | JobAcceptedResponse:
        """Discover URLs inline or submit an asynchronous Map job."""
        payload = self._build_map_payload(
            url=url,
            max_depth=max_depth,
            max_urls=max_urls,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            purpose=purpose,
            allowed_domains=allowed_domains,
            preserve_query=preserve_query,
            execution_mode=execution_mode,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            callback_secret=callback_secret,
        )
        response = self._request_json(
            "POST",
            "/v1/map",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        if response.status_code == 202:
            return JobAcceptedResponse.from_dict(response.data)
        return MapResponse.from_dict(response.data)

    async def async_map(
        self,
        url: str,
        *,
        max_depth: int = 2,
        max_urls: int = 100,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        purpose: Purpose = "user_directed_retrieval",
        allowed_domains: list[str] | None = None,
        preserve_query: bool = True,
        execution_mode: ExecutionMode = "auto",
        idempotency_key: str | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        request_id: str | None = None,
    ) -> MapResponse | JobAcceptedResponse:
        """Discover URLs through an asynchronous HTTP client."""
        payload = self._build_map_payload(
            url=url,
            max_depth=max_depth,
            max_urls=max_urls,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            purpose=purpose,
            allowed_domains=allowed_domains,
            preserve_query=preserve_query,
            execution_mode=execution_mode,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            callback_secret=callback_secret,
        )
        response = await self._async_request_json(
            "POST",
            "/v1/map",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        if response.status_code == 202:
            return JobAcceptedResponse.from_dict(response.data)
        return MapResponse.from_dict(response.data)

    def crawl(
        self,
        url: str,
        *,
        max_depth: int = 2,
        max_pages: int = 50,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        idempotency_key: str | None = None,
        purpose: Purpose = "user_directed_retrieval",
        allowed_domains: list[str] | None = None,
        max_billable_units: int | None = None,
        request_id: str | None = None,
    ) -> CrawlJobResponse:
        """Submit a bounded asynchronous Crawl job."""
        payload = self._build_crawl_payload(
            url,
            max_depth,
            max_pages,
            include_patterns,
            exclude_patterns,
            callback_url,
            callback_secret,
            idempotency_key,
            purpose,
            allowed_domains,
            max_billable_units,
        )
        response = self._request_json(
            "POST",
            "/v1/crawl",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        return CrawlJobResponse.from_dict(response.data)

    async def async_crawl(
        self,
        url: str,
        *,
        max_depth: int = 2,
        max_pages: int = 50,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        callback_url: str | None = None,
        callback_secret: str | None = None,
        idempotency_key: str | None = None,
        purpose: Purpose = "user_directed_retrieval",
        allowed_domains: list[str] | None = None,
        max_billable_units: int | None = None,
        request_id: str | None = None,
    ) -> CrawlJobResponse:
        """Submit a bounded asynchronous Crawl job asynchronously."""
        payload = self._build_crawl_payload(
            url,
            max_depth,
            max_pages,
            include_patterns,
            exclude_patterns,
            callback_url,
            callback_secret,
            idempotency_key,
            purpose,
            allowed_domains,
            max_billable_units,
        )
        response = await self._async_request_json(
            "POST",
            "/v1/crawl",
            body=payload,
            idempotency_key=idempotency_key,
            retry_eligible=idempotency_key is not None,
            request_id=request_id,
        )
        return CrawlJobResponse.from_dict(response.data)

    def get_job(self, job_id: str, *, request_id: str | None = None) -> JobStatusResponse:
        """Get tenant-authorized job state and a fresh result URL when available."""
        response = self._request_json(
            "GET",
            f"/v1/jobs/{quote(job_id, safe='')}",
            retry_eligible=True,
            request_id=request_id,
        )
        return JobStatusResponse.from_dict(response.data)

    async def async_get_job(
        self, job_id: str, *, request_id: str | None = None
    ) -> JobStatusResponse:
        """Get job state asynchronously."""
        response = await self._async_request_json(
            "GET",
            f"/v1/jobs/{quote(job_id, safe='')}",
            retry_eligible=True,
            request_id=request_id,
        )
        return JobStatusResponse.from_dict(response.data)

    def get_job_results(
        self,
        job_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        request_id: str | None = None,
    ) -> JobResultsPage:
        """Get a stable page of completed asynchronous job results."""
        params = self._result_params(limit, cursor)
        response = self._request_json(
            "GET",
            f"/v1/jobs/{quote(job_id, safe='')}/results",
            params=params,
            retry_eligible=True,
            request_id=request_id,
        )
        return JobResultsPage.from_dict(response.data)

    async def async_get_job_results(
        self,
        job_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        request_id: str | None = None,
    ) -> JobResultsPage:
        """Get a stable result page through an asynchronous HTTP client."""
        params = self._result_params(limit, cursor)
        response = await self._async_request_json(
            "GET",
            f"/v1/jobs/{quote(job_id, safe='')}/results",
            params=params,
            retry_eligible=True,
            request_id=request_id,
        )
        return JobResultsPage.from_dict(response.data)

    def cancel_job(
        self, job_id: str, *, request_id: str | None = None
    ) -> JobCancellationResponse:
        """Request cancellation; this does not imply immediate worker termination."""
        response = self._request_json(
            "DELETE",
            f"/v1/jobs/{quote(job_id, safe='')}",
            retry_eligible=True,
            request_id=request_id,
        )
        return JobCancellationResponse.from_dict(response.data)

    async def async_cancel_job(
        self, job_id: str, *, request_id: str | None = None
    ) -> JobCancellationResponse:
        """Request job cancellation asynchronously."""
        response = await self._async_request_json(
            "DELETE",
            f"/v1/jobs/{quote(job_id, safe='')}",
            retry_eligible=True,
            request_id=request_id,
        )
        return JobCancellationResponse.from_dict(response.data)

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        request_id: str | None = None,
    ) -> JobStatusResponse:
        """Poll a job until terminal state or a bounded timeout."""
        self._validate_polling(timeout, poll_interval)
        logical_request_id = request_id if request_id is not None else str(uuid4())
        started_at = time.monotonic()
        last_request_id = logical_request_id
        while True:
            job = self.get_job(job_id, request_id=logical_request_id)
            last_request_id = job.request_id or last_request_id
            if self._is_terminal(job):
                return job
            remaining = timeout - (time.monotonic() - started_at)
            if remaining <= 0:
                raise VeriqJobTimeoutError(
                    job_id, timeout, request_id=last_request_id
                )
            time.sleep(min(poll_interval, remaining))
            if time.monotonic() - started_at >= timeout:
                raise VeriqJobTimeoutError(
                    job_id, timeout, request_id=last_request_id
                )

    async def async_wait_for_job(
        self,
        job_id: str,
        *,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        request_id: str | None = None,
    ) -> JobStatusResponse:
        """Asynchronously poll a job until terminal state or a bounded timeout."""
        self._validate_polling(timeout, poll_interval)
        logical_request_id = request_id if request_id is not None else str(uuid4())
        started_at = time.monotonic()
        last_request_id = logical_request_id
        while True:
            job = await self.async_get_job(job_id, request_id=logical_request_id)
            last_request_id = job.request_id or last_request_id
            if self._is_terminal(job):
                return job
            remaining = timeout - (time.monotonic() - started_at)
            if remaining <= 0:
                raise VeriqJobTimeoutError(
                    job_id, timeout, request_id=last_request_id
                )
            await asyncio.sleep(min(poll_interval, remaining))
            if time.monotonic() - started_at >= timeout:
                raise VeriqJobTimeoutError(
                    job_id, timeout, request_id=last_request_id
                )

    def fetch_job_result(
        self, job_id: str, *, request_id: str | None = None
    ) -> dict[str, Any]:
        """Fetch a completed job's object-JSON document without API credentials."""
        logical_request_id = request_id if request_id is not None else str(uuid4())
        job = self.get_job(job_id, request_id=logical_request_id)
        if not job.results_url:
            retryable = (
                job.lifecycle_state != "expired" and job.status not in _TERMINAL_STATUSES
            )
            raise VeriqResponseError(
                f"Job {job_id} does not currently have a results_url",
                request_id=job.request_id or logical_request_id,
                retryable=retryable,
            )
        response = self._request_json(
            "GET",
            job.results_url,
            retry_eligible=True,
            request_id=logical_request_id,
            authenticated=False,
        )
        return response.data

    async def async_fetch_job_result(
        self, job_id: str, *, request_id: str | None = None
    ) -> dict[str, Any]:
        """Asynchronously fetch a completed job's object-JSON result document."""
        logical_request_id = request_id if request_id is not None else str(uuid4())
        job = await self.async_get_job(job_id, request_id=logical_request_id)
        if not job.results_url:
            retryable = (
                job.lifecycle_state != "expired" and job.status not in _TERMINAL_STATUSES
            )
            raise VeriqResponseError(
                f"Job {job_id} does not currently have a results_url",
                request_id=job.request_id or logical_request_id,
                retryable=retryable,
            )
        response = await self._async_request_json(
            "GET",
            job.results_url,
            retry_eligible=True,
            request_id=logical_request_id,
            authenticated=False,
        )
        return response.data

    def _request_json(
        self,
        method: Literal["GET", "POST", "DELETE"],
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        params: Mapping[str, str | int] | None = None,
        idempotency_key: str | None = None,
        retry_eligible: bool,
        request_id: str | None = None,
        authenticated: bool = True,
    ) -> _JsonResponse:
        logical_request_id = request_id if request_id is not None else str(uuid4())
        generated_key = (
            method == "POST"
            and authenticated
            and path in _CHARGED_CREATE_PATHS
            and idempotency_key is None
        )
        effective_idempotency_key = str(uuid4()) if generated_key else idempotency_key
        effective_retry_eligible = retry_eligible or generated_key
        url = path if path.startswith(("https://", "http://")) else f"{self.base_url}{path}"
        serialized_body = self._serialize_body(body, logical_request_id)
        headers = self._request_headers(
            logical_request_id,
            effective_idempotency_key,
            authenticated=authenticated,
        )
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.timeout, follow_redirects=not authenticated
                ) as client:
                    with client.stream(
                        method,
                        url,
                        headers=headers,
                        content=serialized_body,
                        params=params,
                    ) as response:
                        if self._should_retry_status(
                            response.status_code, effective_retry_eligible, attempt
                        ):
                            delay = self._retry_delay(
                                attempt, response.headers.get("Retry-After")
                            )
                        else:
                            body_bytes = self._read_response_bytes(
                                response, logical_request_id
                            )
                            try:
                                return self._decode_response(
                                    response.status_code,
                                    response.headers,
                                    body_bytes,
                                    logical_request_id,
                                    authenticated=authenticated,
                                )
                            except VeriqApiError as error:
                                if not self._should_retry_idempotency_in_progress(
                                    method,
                                    effective_idempotency_key,
                                    effective_retry_eligible,
                                    error,
                                    attempt,
                                ):
                                    raise
                                delay = self._retry_delay(
                                    attempt, response.headers.get("Retry-After")
                                )
                time.sleep(delay)
            except VeriqError:
                raise
            except httpx.HTTPError as cause:
                if effective_retry_eligible and attempt < self.max_retries:
                    time.sleep(self._retry_delay(attempt))
                    continue
                timed_out = isinstance(cause, httpx.TimeoutException)
                message = (
                    f"Veriq request timed out after {self.timeout:g}s"
                    if timed_out
                    else "Veriq network request failed"
                )
                raise VeriqNetworkError(
                    message,
                    request_id=logical_request_id,
                    retryable=effective_retry_eligible,
                    timed_out=timed_out,
                ) from cause
        raise AssertionError("unreachable")

    async def _async_request_json(
        self,
        method: Literal["GET", "POST", "DELETE"],
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        params: Mapping[str, str | int] | None = None,
        idempotency_key: str | None = None,
        retry_eligible: bool,
        request_id: str | None = None,
        authenticated: bool = True,
    ) -> _JsonResponse:
        logical_request_id = request_id if request_id is not None else str(uuid4())
        generated_key = (
            method == "POST"
            and authenticated
            and path in _CHARGED_CREATE_PATHS
            and idempotency_key is None
        )
        effective_idempotency_key = str(uuid4()) if generated_key else idempotency_key
        effective_retry_eligible = retry_eligible or generated_key
        url = path if path.startswith(("https://", "http://")) else f"{self.base_url}{path}"
        serialized_body = self._serialize_body(body, logical_request_id)
        headers = self._request_headers(
            logical_request_id,
            effective_idempotency_key,
            authenticated=authenticated,
        )
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=not authenticated
                ) as client:
                    async with client.stream(
                        method,
                        url,
                        headers=headers,
                        content=serialized_body,
                        params=params,
                    ) as response:
                        if self._should_retry_status(
                            response.status_code, effective_retry_eligible, attempt
                        ):
                            delay = self._retry_delay(
                                attempt, response.headers.get("Retry-After")
                            )
                        else:
                            body_bytes = await self._async_read_response_bytes(
                                response, logical_request_id
                            )
                            try:
                                return self._decode_response(
                                    response.status_code,
                                    response.headers,
                                    body_bytes,
                                    logical_request_id,
                                    authenticated=authenticated,
                                )
                            except VeriqApiError as error:
                                if not self._should_retry_idempotency_in_progress(
                                    method,
                                    effective_idempotency_key,
                                    effective_retry_eligible,
                                    error,
                                    attempt,
                                ):
                                    raise
                                delay = self._retry_delay(
                                    attempt, response.headers.get("Retry-After")
                                )
                await asyncio.sleep(delay)
            except VeriqError:
                raise
            except httpx.HTTPError as cause:
                if effective_retry_eligible and attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                timed_out = isinstance(cause, httpx.TimeoutException)
                message = (
                    f"Veriq request timed out after {self.timeout:g}s"
                    if timed_out
                    else "Veriq network request failed"
                )
                raise VeriqNetworkError(
                    message,
                    request_id=logical_request_id,
                    retryable=effective_retry_eligible,
                    timed_out=timed_out,
                ) from cause
        raise AssertionError("unreachable")

    def _read_response_bytes(
        self, response: httpx.Response, request_id: str
    ) -> bytes:
        self._check_content_length(response, request_id)
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > self.max_response_bytes:
                raise VeriqResponseError(
                    f"Veriq response exceeded the {self.max_response_bytes}-byte response limit",
                    request_id=response.headers.get("X-Request-ID") or request_id,
                    status=response.status_code,
                )
            chunks.append(chunk)
        return b"".join(chunks)

    async def _async_read_response_bytes(
        self, response: httpx.Response, request_id: str
    ) -> bytes:
        self._check_content_length(response, request_id)
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self.max_response_bytes:
                raise VeriqResponseError(
                    f"Veriq response exceeded the {self.max_response_bytes}-byte response limit",
                    request_id=response.headers.get("X-Request-ID") or request_id,
                    status=response.status_code,
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _check_content_length(self, response: httpx.Response, request_id: str) -> None:
        value = response.headers.get("Content-Length")
        try:
            content_length = int(value) if value is not None else None
        except ValueError:
            content_length = None
        if content_length is not None and content_length > self.max_response_bytes:
            raise VeriqResponseError(
                f"Veriq response exceeded the {self.max_response_bytes}-byte response limit",
                request_id=response.headers.get("X-Request-ID") or request_id,
                status=response.status_code,
            )

    def _decode_response(
        self,
        status_code: int,
        headers: httpx.Headers,
        body: bytes,
        request_id: str,
        *,
        authenticated: bool,
    ) -> _JsonResponse:
        header_request_id = headers.get("X-Request-ID") or request_id
        try:
            parsed: object = json.loads(body) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as cause:
            if status_code < 200 or status_code >= 300:
                raise VeriqApiError(
                    status_code, {}, request_id=header_request_id
                ) from cause
            raise VeriqResponseError(
                "Veriq response was not valid JSON",
                request_id=header_request_id,
                status=status_code,
            ) from cause
        if not isinstance(parsed, dict):
            if status_code < 200 or status_code >= 300:
                raise VeriqApiError(
                    status_code, {}, request_id=header_request_id
                )
            raise VeriqResponseError(
                "Veriq response JSON must be an object",
                request_id=header_request_id,
                status=status_code,
            )
        data = {str(key): value for key, value in parsed.items()}
        if status_code < 200 or status_code >= 300:
            raise VeriqApiError(status_code, data, request_id=header_request_id)
        if authenticated and not isinstance(data.get("request_id"), str):
            data["request_id"] = header_request_id
        return _JsonResponse(status_code=status_code, data=data)

    def _request_headers(
        self,
        request_id: str,
        idempotency_key: str | None,
        *,
        authenticated: bool,
    ) -> dict[str, str]:
        if not authenticated:
            return {}
        headers = {
            "X-Api-Key": self.api_key,
            "X-Request-ID": request_id,
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _serialize_body(
        body: Mapping[str, Any] | None, request_id: str
    ) -> bytes | None:
        if body is None:
            return None
        try:
            return json.dumps(body, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as cause:
            raise VeriqResponseError(
                "Veriq request body was not JSON serializable", request_id=request_id
            ) from cause

    def _should_retry_status(
        self, status_code: int, retry_eligible: bool, attempt: int
    ) -> bool:
        return (
            retry_eligible
            and attempt < self.max_retries
            and status_code in _RETRYABLE_STATUS_CODES
        )

    def _should_retry_idempotency_in_progress(
        self,
        method: Literal["GET", "POST", "DELETE"],
        idempotency_key: str | None,
        retry_eligible: bool,
        error: VeriqApiError,
        attempt: int,
    ) -> bool:
        return (
            method == "POST"
            and idempotency_key is not None
            and retry_eligible
            and attempt < self.max_retries
            and error.status == 409
            and error.code == "idempotency_in_progress"
        )

    def _retry_delay(self, attempt: int, retry_after: str | None = None) -> float:
        server_delay = self._parse_retry_after(retry_after)
        if server_delay is not None:
            return min(server_delay, self.max_retry_delay)
        exponential = 0.25 * float(2**attempt)
        jittered: float = exponential * random.uniform(0.75, 1.25)
        return min(jittered, self.max_retry_delay)

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, retry_at.timestamp() - datetime.now(UTC).timestamp())
        return seconds if seconds >= 0 else None

    @staticmethod
    def _validate_polling(timeout: float, poll_interval: float) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        if not math.isfinite(poll_interval) or poll_interval < 0:
            raise ValueError("poll_interval must be a non-negative finite number")

    @staticmethod
    def _is_terminal(job: JobStatusResponse) -> bool:
        return (
            job.lifecycle_state in _TERMINAL_LIFECYCLES
            or job.status in _TERMINAL_STATUSES
        )

    @staticmethod
    def _result_params(
        limit: int | None, cursor: str | None
    ) -> dict[str, str | int]:
        params: dict[str, str | int] = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        return params

    @staticmethod
    def _build_search_payload(
        *,
        query: str,
        search_depth: str,
        topic: str,
        max_results: int,
        include_answer: bool | str,
        include_raw_content: bool,
        include_domains: list[str] | None,
        exclude_domains: list[str] | None,
        days: int | None,
        freshness_mode: str,
        purpose: str,
        cache_mode: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "freshness_mode": freshness_mode,
            "purpose": purpose,
            "cache_mode": cache_mode,
        }
        if include_domains:
            payload["include_domains"] = list(include_domains)
        if exclude_domains:
            payload["exclude_domains"] = list(exclude_domains)
        if days is not None:
            payload["days"] = days
        return payload

    @staticmethod
    def _build_extract_payload(
        *,
        urls: list[str],
        format: str,
        include_metadata: bool,
        purpose: str,
        render: str,
        execution_mode: str,
        idempotency_key: str | None,
        callback_url: str | None,
        callback_secret: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "urls": list(urls),
            "format": format,
            "include_metadata": include_metadata,
            "purpose": purpose,
            "render": render,
            "execution_mode": execution_mode,
        }
        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key
        if callback_url is not None:
            payload["callback_url"] = callback_url
        if callback_secret is not None:
            payload["callback_secret"] = callback_secret
        return payload

    @staticmethod
    def _build_map_payload(
        *,
        url: str,
        max_depth: int,
        max_urls: int,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        purpose: str,
        allowed_domains: list[str] | None,
        preserve_query: bool,
        execution_mode: str,
        idempotency_key: str | None,
        callback_url: str | None,
        callback_secret: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "max_depth": max_depth,
            "max_urls": max_urls,
            "include_patterns": list(include_patterns or []),
            "exclude_patterns": list(exclude_patterns or []),
            "purpose": purpose,
            "allowed_domains": list(allowed_domains or []),
            "preserve_query": preserve_query,
            "execution_mode": execution_mode,
        }
        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key
        if callback_url is not None:
            payload["callback_url"] = callback_url
        if callback_secret is not None:
            payload["callback_secret"] = callback_secret
        return payload

    @staticmethod
    def _build_crawl_payload(
        url: str,
        max_depth: int,
        max_pages: int,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        callback_url: str | None,
        callback_secret: str | None,
        idempotency_key: str | None,
        purpose: str,
        allowed_domains: list[str] | None,
        max_billable_units: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "max_depth": max_depth,
            "max_pages": max_pages,
            "include_patterns": list(include_patterns or []),
            "exclude_patterns": list(exclude_patterns or []),
            "purpose": purpose,
            "allowed_domains": list(allowed_domains or []),
        }
        if callback_url is not None:
            payload["callback_url"] = callback_url
        if callback_secret is not None:
            payload["callback_secret"] = callback_secret
        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key
        if max_billable_units is not None:
            payload["max_billable_units"] = max_billable_units
        return payload

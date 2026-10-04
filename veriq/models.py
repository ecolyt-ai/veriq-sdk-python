"""Forward-compatible response models for the Veriq Python SDK."""

from dataclasses import dataclass, field, fields
from typing import Any, Mapping, TypeVar, cast

_ModelT = TypeVar("_ModelT")


def _model_from_dict(model_type: type[_ModelT], data: Mapping[str, Any]) -> _ModelT:
    """Construct a dataclass from known fields without mutating or dropping unknown data."""
    known = {
        item.name
        for item in fields(cast(Any, model_type))
        if item.name != "additional_fields"
    }
    values = {name: data[name] for name in known if name in data}
    values["additional_fields"] = {
        name: value for name, value in data.items() if name not in known
    }
    return model_type(**values)


@dataclass
class SearchResult:
    """A canonicalized search result with optional structured content metadata."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    score: float = 0.0
    content: str | None = None
    raw_content: str | None = None
    published_date: str | None = None
    source: str | None = None
    canonical_url: str | None = None
    sources: list[str] = field(default_factory=list)
    freshness_status: str = "not_requested"
    raw_content_metadata: dict[str, Any] = field(default_factory=dict)
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SearchResult":
        return _model_from_dict(cls, data)


@dataclass
class SearchResponse:
    """Response from /v1/search, including additive outcome metadata."""

    query: str = ""
    answer: str | None = None
    results: list[SearchResult] = field(default_factory=list)
    search_depth: str = "basic"
    ranking_mode: str = "none"
    serp_source: str = "searxng"
    latency_ms: int = 0
    cached: bool = False
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "terminal"
    completion_state: str = "complete"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    purpose: str = "user_directed_retrieval"
    candidate_budget: int = 0
    candidate_count: int = 0
    filtered_count: int = 0
    duplicate_count: int = 0
    returned_count: int = 0
    shortfall_reason: str | None = None
    freshness_mode: str = "best_effort"
    freshness_unknown_count: int = 0
    provider_attempts: list[dict[str, Any]] = field(default_factory=list)
    ranking_requested: str = "bm25"
    ranking_fallback: bool = False
    score_interpretation: str = "relative_within_response_not_cross_query_calibrated"
    answer_metadata: dict[str, Any] = field(default_factory=dict)
    raw_content_attempted_count: int = 0
    cache: dict[str, Any] = field(default_factory=dict)
    billing: dict[str, Any] = field(default_factory=dict)
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SearchResponse":
        payload = dict(data)
        raw_results = payload.pop("results", [])
        response = _model_from_dict(cls, payload)
        response.results = [
            SearchResult.from_dict(item)
            for item in raw_results
            if isinstance(item, Mapping)
        ]
        return response


@dataclass
class ExtractResult:
    """An independent extraction outcome."""

    url: str = ""
    status: str = "error"
    title: str | None = None
    author: str | None = None
    published_date: str | None = None
    content: str | None = None
    word_count: int | None = None
    render_mode: str | None = None
    error: str | None = None
    reason: str | None = None
    retryable: bool = False
    latency_ms: int = 0
    content_type: str | None = None
    bytes_fetched: int = 0
    bytes_returned: int = 0
    truncated: bool = False
    metadata: dict[str, Any] | None = None
    policy: dict[str, Any] = field(default_factory=dict)
    fetch: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExtractResult":
        return _model_from_dict(cls, data)


@dataclass
class ExtractResponse:
    """Response from /v1/extract."""

    results: list[ExtractResult] = field(default_factory=list)
    format: str = "markdown"
    latency_ms: int = 0
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "terminal"
    completion_state: str = "complete"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    billing: dict[str, Any] = field(default_factory=dict)
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExtractResponse":
        payload = dict(data)
        raw_results = payload.pop("results", [])
        response = _model_from_dict(cls, payload)
        response.results = [
            ExtractResult.from_dict(item)
            for item in raw_results
            if isinstance(item, Mapping)
        ]
        return response


@dataclass
class MapResult:
    """A URL discovery outcome; this does not imply extraction success."""

    url: str = ""
    depth: int = 0
    title: str | None = None
    discovery_source: str = "html"
    submitted_url: str | None = None
    final_url: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    status: str = "discovered"
    reason: str | None = None
    retryable: bool = False
    fetch: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MapResult":
        return _model_from_dict(cls, data)


@dataclass
class MapResponse:
    """Response from /v1/map."""

    root_url: str = ""
    urls: list[MapResult] = field(default_factory=list)
    total_discovered: int = 0
    max_depth_reached: int = 0
    latency_ms: int = 0
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "terminal"
    completion_state: str = "complete"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    attempted_fetch_count: int = 0
    failed_fetch_count: int = 0
    policy_exclusion_count: int = 0
    duplicate_count: int = 0
    truncated: bool = False
    termination_reasons: list[str] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)
    billing: dict[str, Any] = field(default_factory=dict)
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MapResponse":
        payload = dict(data)
        raw_urls = payload.pop("urls", [])
        response = _model_from_dict(cls, payload)
        response.urls = [
            MapResult.from_dict(item)
            for item in raw_urls
            if isinstance(item, Mapping)
        ]
        return response


@dataclass
class JobAcceptedResponse:
    """Accepted Extract or Map job returned with HTTP 202."""

    job_id: str = ""
    job_type: str = ""
    status: str = "queued"
    status_url: str = ""
    results_url: str | None = None
    results_page_url: str | None = None
    accepted_count: int = 0
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "accepted"
    completion_state: str = "not_applicable"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    estimated_time_seconds: int | None = None
    estimate_confidence: str = "low"
    policy: dict[str, Any] = field(default_factory=dict)
    billing: dict[str, Any] = field(default_factory=dict)
    retention_policy_id: str | None = None
    callback_delivery: str = "not_requested"
    idempotent_replay: bool = False
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JobAcceptedResponse":
        return _model_from_dict(cls, data)


@dataclass
class CrawlJobResponse:
    """Accepted or idempotently replayed Crawl job."""

    job_id: str = ""
    status: str = "queued"
    status_url: str = ""
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "accepted"
    completion_state: str = "not_applicable"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    estimated_time_seconds: int | None = None
    estimate_confidence: str = "low"
    accepted_limits: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    billing: dict[str, Any] = field(default_factory=dict)
    result_expires_at: str | None = None
    job_metadata_expires_at: str | None = None
    retention_policy_id: str | None = None
    callback_delivery: str = "not_requested"
    idempotent_replay: bool = False
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CrawlJobResponse":
        return _model_from_dict(cls, data)


@dataclass
class JobResultsPage:
    """Tenant-bound stable page from a completed asynchronous result."""

    job_id: str = ""
    job_type: str = ""
    snapshot: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    total_items: int = 0
    result_expires_at: str | None = None
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "terminal"
    completion_state: str = "complete"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JobResultsPage":
        payload = dict(data)
        raw_items = payload.pop("items", [])
        response = _model_from_dict(cls, payload)
        response.items = [dict(item) for item in raw_items if isinstance(item, Mapping)]
        return response


@dataclass
class JobStatusResponse:
    """Tenant-authorized asynchronous job status."""

    job_id: str = ""
    status: str = "queued"
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "queued"
    completion_state: str = "not_applicable"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    progress: int = 0
    total: int = 0
    progress_detail: dict[str, Any] = field(default_factory=dict)
    results_url: str | None = None
    results_page_url: str | None = None
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    result_expires_at: str | None = None
    job_metadata_expires_at: str | None = None
    can_cancel: bool = False
    cancellation_requested_at: str | None = None
    callback_delivery: str = "not_requested"
    billing: dict[str, Any] = field(default_factory=dict)
    billing_state: str = "not_applicable"
    retention_policy_id: str | None = None
    entitlement_tier_snapshot: str | None = None
    subscription_status_snapshot: str | None = None
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JobStatusResponse":
        return _model_from_dict(cls, data)


@dataclass
class JobCancellationResponse:
    """Acknowledgement that job cancellation was requested."""

    job_id: str = ""
    status: str = "queued"
    api_version: str = "v1"
    request_id: str = ""
    lifecycle_state: str = "running"
    completion_state: str = "not_applicable"
    service_mode: str = "normal"
    reason: str | None = None
    retryable: bool = False
    cancellation_requested_at: str | None = None
    can_cancel: bool = False
    additional_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JobCancellationResponse":
        return _model_from_dict(cls, data)

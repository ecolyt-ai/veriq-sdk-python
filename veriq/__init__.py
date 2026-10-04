"""Veriq Python SDK for policy-aware search, extraction, mapping, and crawling."""

from veriq._version import __version__
from veriq.client import ExecutionMode, Purpose, VeriqClient
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
    ExtractResult,
    JobAcceptedResponse,
    JobCancellationResponse,
    JobResultsPage,
    JobStatusResponse,
    MapResponse,
    MapResult,
    SearchResponse,
    SearchResult,
)
from veriq.webhook import (
    DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
    VERIQ_EVENT_ID_HEADER,
    VERIQ_SIGNATURE_HEADER,
    VERIQ_TIMESTAMP_HEADER,
    VerifiedWebhook,
    VeriqWebhookVerificationError,
    WebhookVerificationErrorCode,
    verify_webhook_signature,
)

__all__ = [
    "CrawlJobResponse",
    "DEFAULT_WEBHOOK_TOLERANCE_SECONDS",
    "ExecutionMode",
    "ExtractResponse",
    "ExtractResult",
    "JobAcceptedResponse",
    "JobCancellationResponse",
    "JobResultsPage",
    "JobStatusResponse",
    "MapResponse",
    "MapResult",
    "Purpose",
    "SearchResponse",
    "SearchResult",
    "VERIQ_EVENT_ID_HEADER",
    "VERIQ_SIGNATURE_HEADER",
    "VERIQ_TIMESTAMP_HEADER",
    "VerifiedWebhook",
    "VeriqApiError",
    "VeriqClient",
    "VeriqError",
    "VeriqJobTimeoutError",
    "VeriqNetworkError",
    "VeriqResponseError",
    "VeriqWebhookVerificationError",
    "WebhookVerificationErrorCode",
    "__version__",
    "verify_webhook_signature",
]

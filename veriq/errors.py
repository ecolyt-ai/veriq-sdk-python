"""Typed exceptions raised by the Veriq Python SDK."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class VeriqError(Exception):
    """Base class for SDK failures with correlation and retry metadata."""

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.retryable = retryable


class VeriqApiError(VeriqError):
    """A structured non-success response from the Veriq API."""

    def __init__(
        self,
        status: int,
        body: Mapping[str, Any],
        *,
        request_id: str | None = None,
    ) -> None:
        body_request_id = body.get("request_id")
        resolved_request_id = body_request_id if isinstance(body_request_id, str) else request_id
        message_value = body.get("message")
        message = (
            message_value
            if isinstance(message_value, str)
            else f"Veriq API request failed with status {status}"
        )
        retryable_value = body.get("retryable")
        super().__init__(
            message,
            request_id=resolved_request_id,
            retryable=retryable_value if isinstance(retryable_value, bool) else False,
        )
        self.status = status
        self.status_code = status
        self.code = self._optional_str(body.get("code"))
        self.detail = self._optional_str(body.get("detail"))
        retry_after = body.get("retry_after_seconds")
        self.retry_after_seconds = (
            float(retry_after)
            if isinstance(retry_after, (int, float)) and not isinstance(retry_after, bool)
            else None
        )
        violations = body.get("field_violations")
        self.field_violations = self._field_violations(violations)
        self.documentation_url = self._optional_str(body.get("documentation_url"))

    @staticmethod
    def _optional_str(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _field_violations(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return []
        return [dict(item) for item in value if isinstance(item, Mapping)]


class VeriqNetworkError(VeriqError):
    """A network or per-attempt timeout failure."""

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        retryable: bool = False,
        timed_out: bool = False,
    ) -> None:
        super().__init__(message, request_id=request_id, retryable=retryable)
        self.timed_out = timed_out


class VeriqResponseError(VeriqError):
    """A malformed, unsupported, or oversized response."""

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        retryable: bool = False,
        status: int | None = None,
    ) -> None:
        super().__init__(message, request_id=request_id, retryable=retryable)
        self.status = status
        self.status_code = status


class VeriqJobTimeoutError(VeriqError):
    """Raised when bounded job polling reaches its deadline."""

    def __init__(
        self,
        job_id: str,
        timeout_seconds: float,
        *,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Timed out waiting {timeout_seconds:g}s for job {job_id}",
            request_id=request_id,
            retryable=True,
        )
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds

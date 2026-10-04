"""Verification helpers for signed Veriq webhook requests."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

VERIQ_EVENT_ID_HEADER = "Veriq-Event-Id"
VERIQ_TIMESTAMP_HEADER = "Veriq-Timestamp"
VERIQ_SIGNATURE_HEADER = "Veriq-Signature"
DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300

WebhookVerificationErrorCode = Literal[
    "missing_header",
    "invalid_timestamp",
    "timestamp_outside_tolerance",
    "invalid_secret",
    "invalid_signature",
]
_SIGNATURE_PATTERN = re.compile(r"v1=([0-9a-fA-F]{64})\Z")


@dataclass(frozen=True)
class VerifiedWebhook:
    """Verified webhook signature metadata."""

    event_id: str
    timestamp: int
    signature: str


class VeriqWebhookVerificationError(ValueError):
    """Raised when a Veriq webhook cannot be authenticated."""

    def __init__(self, code: WebhookVerificationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    target = name.casefold()
    for key, value in headers.items():
        if key.casefold() == target:
            return value
    return None


def verify_webhook_signature(
    raw_body: bytes | str,
    headers: Mapping[str, str],
    secret: bytes | str,
    *,
    tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
    now: datetime | float | None = None,
) -> VerifiedWebhook:
    """Verify a webhook signature over the exact, unparsed request body.

    The signed bytes are ``${timestamp}.${eventId}.${rawBody}``, where the first
    two values are taken verbatim from their headers. The timestamp is Unix time
    in seconds and must fall within ``tolerance_seconds`` of ``now``.
    """
    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not secret_bytes:
        raise VeriqWebhookVerificationError(
            "invalid_secret", "Webhook secret must not be empty"
        )
    if not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be a non-negative finite number")

    event_id = _get_header(headers, VERIQ_EVENT_ID_HEADER)
    timestamp_value = _get_header(headers, VERIQ_TIMESTAMP_HEADER)
    signature_value = _get_header(headers, VERIQ_SIGNATURE_HEADER)
    for name, value in (
        (VERIQ_EVENT_ID_HEADER, event_id),
        (VERIQ_TIMESTAMP_HEADER, timestamp_value),
        (VERIQ_SIGNATURE_HEADER, signature_value),
    ):
        if not value:
            raise VeriqWebhookVerificationError("missing_header", f"Missing {name}")

    assert event_id is not None
    assert timestamp_value is not None
    assert signature_value is not None
    try:
        timestamp = int(timestamp_value)
    except ValueError as exc:
        raise VeriqWebhookVerificationError(
            "invalid_timestamp",
            f"{VERIQ_TIMESTAMP_HEADER} must be a Unix timestamp in seconds",
        ) from exc
    if timestamp < 0 or str(timestamp) != timestamp_value:
        raise VeriqWebhookVerificationError(
            "invalid_timestamp",
            f"{VERIQ_TIMESTAMP_HEADER} must be a Unix timestamp in seconds",
        )

    if isinstance(now, datetime):
        now_seconds = int(now.timestamp())
    elif now is None:
        now_seconds = int(time.time())
    elif math.isfinite(now):
        now_seconds = int(now)
    else:
        raise ValueError("now must be a finite Unix timestamp")
    if abs(now_seconds - timestamp) > tolerance_seconds:
        raise VeriqWebhookVerificationError(
            "timestamp_outside_tolerance",
            "Webhook timestamp is outside the allowed tolerance",
        )

    signature_match = _SIGNATURE_PATTERN.fullmatch(signature_value)
    supplied_signature = signature_match.group(1).lower() if signature_match else ""
    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    signed_prefix = f"{timestamp_value}.{event_id}.".encode("utf-8")
    expected_signature = hmac.new(
        secret_bytes,
        signed_prefix + body_bytes,
        hashlib.sha256,
    ).hexdigest()
    if not supplied_signature or not hmac.compare_digest(
        supplied_signature, expected_signature
    ):
        raise VeriqWebhookVerificationError(
            "invalid_signature", "Webhook signature is invalid"
        )

    return VerifiedWebhook(
        event_id=event_id,
        timestamp=timestamp,
        signature=expected_signature,
    )

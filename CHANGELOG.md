# Changelog

All notable changes to `veriq-sdk` (Python) are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

> **Beta:** the Veriq API and this SDK are in beta (`Development Status :: 4 - Beta`).
> Interfaces may change between minor versions until 1.0.

## [0.2.0] - 2026-10-04 (beta)

First public release on PyPI as `veriq-sdk` (import name `veriq`).

### Added

- `VeriqClient` with sync and async (`async_*`) methods for every endpoint.
- `search()` with optional generated answer (`include_answer`), result limits, and a
  `purpose` field for policy-aware retrieval.
- `extract()` for one or more URLs, `map()` for site URL discovery, and `crawl()` for
  asynchronous crawl jobs.
- Job helpers: `get_job()`, `get_job_results()`, `cancel_job()`, `wait_for_job()`, and
  `fetch_job_result()`.
- Typed response models (`SearchResponse`, `ExtractResponse`, `MapResponse`,
  `CrawlJobResponse`, `JobStatusResponse`, `JobResultsPage`, and related types).
- Error hierarchy: `VeriqError`, `VeriqApiError`, `VeriqNetworkError`,
  `VeriqResponseError`, and `VeriqJobTimeoutError`.
- Configurable timeout, bounded retries (`max_retries`, `max_retry_delay`), and a response
  size cap (`max_response_bytes`). Idempotency keys make writes safe to retry.
- `verify_webhook_signature()` for HMAC-signed webhook deliveries, with timestamp tolerance.
- LangChain-style tools in `veriq.langchain`: `VeriqSearchResults` and `VeriqExtract`.
- Python 3.10 through 3.13 support.
- CI builds the sdist and wheel, runs `twine check --strict`, and smoke-tests the installed
  wheel on every supported Python version.
- Releases publish from GitHub Actions through PyPI Trusted Publishing (no stored tokens).

[0.2.0]: https://github.com/ecolyt-ai/veriq-sdk-python/releases/tag/v0.2.0

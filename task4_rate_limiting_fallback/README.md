
# Task 4 — Rate Limiting and Provider Fallback

## Overview

This project implements a resilient FastAPI-based AI gateway with:

- Per-tenant token rate limiting
- SQLite-backed persistent usage tracking
- Sliding-window rate limiting
- Concurrency-safe token reservations
- Primary and backup model providers
- Automatic provider fallback
- Token refunds for failed requests
- Sanitized API error responses
- Automated tests

## Rate Limiting

Each tenant is identified using the `X-API-Key` request header.

The default rate limit is:

- 50,000 tokens
- Per tenant
- Per rolling 60-second window

Usage records are stored in `rate_limits.db`.

SQLite transactions use `BEGIN IMMEDIATE` to prevent
concurrent requests from exceeding the token limit.

## Token Accounting

The gateway estimates input tokens using:

    ceil(len(prompt) / 4)

The initial reservation is:

    estimated_input_tokens + max_tokens

If the provider request fails, the gateway attempts to
refund the reservation using its unique database ID.

Successful requests retain their reserved token budget.

Important limitation: input token estimation is heuristic.
The implementation does not yet reconcile successful
reservations against exact provider-reported token usage.

## Provider Fallback

The gateway sends requests to the primary provider first.

It attempts the backup provider when the primary provider:

- Returns HTTP 429
- Exceeds the 3-second timeout

The backup provider is also subject to a 3-second timeout.

Other primary-provider errors are returned as sanitized
gateway errors rather than automatically triggering fallback.

## API Endpoints

### GET /health

Returns:

    {"status": "ok"}

### POST /completions

Required header:

    X-API-Key: tenant-example

Example request:

    {
      "prompt": "Hello AI Gateway",
      "max_tokens": 100
    }

Successful responses include:

- Provider name
- Provider response data
- Estimated input tokens
- Reserved output tokens
- Total reserved tokens
- Remaining token allowance

## Running the Gateway

From the Task 4 directory:

    python -m uvicorn gateway:app --host 127.0.0.1 --port 8000

The default provider URLs are:

    http://127.0.0.1:9001/completions
    http://127.0.0.1:9002/completions

These can be overridden using:

    PRIMARY_MODEL_URL
    BACKUP_MODEL_URL

Optional provider API key environment variables:

    PRIMARY_MODEL_API_KEY
    BACKUP_MODEL_API_KEY

## Mock Providers

The mock provider supports the following modes:

- success
- rate_limit
- timeout
- error

Example PowerShell command for the primary provider:

    $env:PROVIDER_NAME="primary"
    $env:PROVIDER_MODE="success"
    python -m uvicorn mock_provider:app --port 9001

Example PowerShell command for the backup provider:

    $env:PROVIDER_NAME="backup"
    $env:PROVIDER_MODE="success"
    python -m uvicorn mock_provider:app --port 9002

Run the providers in separate terminals.

## Automated Tests

Run all Task 4 tests from the project directory:

    python -m pytest task4_rate_limiting_fallback -v

Test coverage includes:

- Token reservations and rate-limit enforcement
- Tenant isolation
- Sliding-window expiration
- Concurrent requests
- Provider fallback and timeout handling
- Successful and rejected refunds
- Cross-tenant refund protection
- Gateway refund integration
- Sanitized error responses

Latest verified result:

    20 passed

## Project Files

    database.py
    gateway.py
    mock_provider.py
    provider_router.py
    rate_limiter.py
    token_counter.py
    test_rate_limiter.py
    test_provider_router.py
    test_refunds.py
    test_gateway_refunds.py
    README.md

The SQLite database file is generated at runtime.

## Current Limitations

1. Input tokens are estimated rather than counted with
   a model-specific tokenizer.
2. Successful requests retain the maximum reserved output
   budget instead of reconciling actual output usage.
3. Failed-request refunds are attempted, but a database
   failure during refund may leave a reservation in place.
4. SQLite is suitable for this assessment and local
   execution; larger deployments may require a different
   shared storage architecture.

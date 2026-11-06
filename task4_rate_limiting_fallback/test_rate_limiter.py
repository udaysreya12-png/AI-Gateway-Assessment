
import asyncio
import time
import uuid

import pytest

from database import get_connection
from rate_limiter import RateLimitExceeded, TokenRateLimiter


def unique_tenant():
    return f"test_{uuid.uuid4().hex}"


@pytest.mark.asyncio
async def test_successful_reservation():
    limiter = TokenRateLimiter()
    result = await limiter.reserve(unique_tenant(), 100)

    assert result["used_tokens"] == 100
    assert result["remaining_tokens"] == 49900


@pytest.mark.asyncio
async def test_exact_token_limit():
    limiter = TokenRateLimiter()
    result = await limiter.reserve(unique_tenant(), 50000)

    assert result["used_tokens"] == 50000
    assert result["remaining_tokens"] == 0


@pytest.mark.asyncio
async def test_exceed_token_limit():
    limiter = TokenRateLimiter()
    tenant = unique_tenant()

    await limiter.reserve(tenant, 49900)

    with pytest.raises(RateLimitExceeded):
        await limiter.reserve(tenant, 101)


@pytest.mark.asyncio
async def test_tenant_isolation():
    limiter = TokenRateLimiter()
    tenant_a = unique_tenant()
    tenant_b = unique_tenant()

    await limiter.reserve(tenant_a, 50000)
    result = await limiter.reserve(tenant_b, 100)

    assert result["remaining_tokens"] == 49900


@pytest.mark.asyncio
async def test_invalid_token_amount():
    limiter = TokenRateLimiter()

    with pytest.raises(ValueError):
        await limiter.reserve(unique_tenant(), -1)

    with pytest.raises(ValueError):
        await limiter.reserve(unique_tenant(), 0)


@pytest.mark.asyncio
async def test_sliding_window_expiration():
    limiter = TokenRateLimiter(
        token_limit=100,
        window_seconds=60,
    )
    tenant = unique_tenant()

    await limiter.reserve(tenant, 90)

    # Move the recorded usage outside the sliding window.
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE token_usage
            SET timestamp = ?
            WHERE tenant_key = ?
            """,
            (time.time() - 61, tenant),
        )
        connection.commit()

    result = await limiter.reserve(tenant, 100)

    assert result["used_tokens"] == 100
    assert result["remaining_tokens"] == 0


@pytest.mark.asyncio
async def test_concurrent_requests():
    limiter = TokenRateLimiter(
        token_limit=100,
        window_seconds=60,
    )
    tenant = unique_tenant()

    results = await asyncio.gather(
        *[
            limiter.reserve(tenant, 10)
            for _ in range(20)
        ],
        return_exceptions=True,
    )

    successes = [
        result
        for result in results
        if isinstance(result, dict)
    ]

    rejected = [
        result
        for result in results
        if isinstance(result, RateLimitExceeded)
    ]

    assert len(successes) == 10
    assert len(rejected) == 10

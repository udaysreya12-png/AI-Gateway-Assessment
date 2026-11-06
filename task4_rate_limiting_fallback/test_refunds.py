
import uuid

import pytest

from database import get_connection
from rate_limiter import TokenRateLimiter


def unique_tenant():
    return f"refund_test_{uuid.uuid4().hex}"


@pytest.mark.asyncio
async def test_successful_refund():
    limiter = TokenRateLimiter(token_limit=100)
    tenant = unique_tenant()

    reservation = await limiter.reserve(tenant, 80)

    refunded = await limiter.refund(
        reservation["reservation_id"],
        tenant,
    )

    assert refunded is True

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM token_usage
            WHERE id = ?
            """,
            (reservation["reservation_id"],),
        ).fetchone()

    assert row[0] == 0

    new_reservation = await limiter.reserve(tenant, 100)

    assert new_reservation["remaining_tokens"] == 0


@pytest.mark.asyncio
async def test_double_refund():
    limiter = TokenRateLimiter()
    tenant = unique_tenant()

    reservation = await limiter.reserve(tenant, 100)

    first_refund = await limiter.refund(
        reservation["reservation_id"],
        tenant,
    )

    second_refund = await limiter.refund(
        reservation["reservation_id"],
        tenant,
    )

    assert first_refund is True
    assert second_refund is False


@pytest.mark.asyncio
async def test_other_tenant_cannot_refund():
    limiter = TokenRateLimiter()

    tenant_a = unique_tenant()
    tenant_b = unique_tenant()

    reservation = await limiter.reserve(tenant_a, 100)

    refunded = await limiter.refund(
        reservation["reservation_id"],
        tenant_b,
    )

    assert refunded is False

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT tokens
            FROM token_usage
            WHERE id = ?
            """,
            (reservation["reservation_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == 100


@pytest.mark.asyncio
async def test_invalid_reservation_id():
    limiter = TokenRateLimiter()

    with pytest.raises(ValueError):
        await limiter.refund(-1, unique_tenant())

    with pytest.raises(ValueError):
        await limiter.refund(0, unique_tenant())


import uuid

import httpx
import pytest

import gateway
from database import get_connection
from provider_router import GatewayError, ProviderResponse


def unique_tenant():
    return f"gateway_refund_{uuid.uuid4().hex}"


def get_reserved_tokens(tenant):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(tokens), 0)
            FROM token_usage
            WHERE tenant_key = ?
            """,
            (tenant,),
        ).fetchone()

    return row[0]


@pytest.mark.asyncio
async def test_refund_when_providers_fail(monkeypatch):
    tenant = unique_tenant()

    async def failing_provider(payload):
        raise GatewayError(
            code="BACKUP_PROVIDER_FAILED",
            message="Model providers are temporarily unavailable.",
            status_code=502,
        )

    monkeypatch.setattr(
        gateway.router,
        "complete",
        failing_provider,
    )

    transport = httpx.ASGITransport(app=gateway.app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/completions",
            headers={"X-API-Key": tenant},
            json={
                "prompt": "Refund failed request",
                "max_tokens": 100,
            },
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == (
        "BACKUP_PROVIDER_FAILED"
    )
    assert get_reserved_tokens(tenant) == 0


@pytest.mark.asyncio
async def test_successful_request_keeps_reservation(monkeypatch):
    tenant = unique_tenant()

    async def successful_provider(payload):
        return ProviderResponse(
            provider="primary",
            data={
                "model": "primary",
                "text": "Success",
                "output_tokens": 20,
            },
        )

    monkeypatch.setattr(
        gateway.router,
        "complete",
        successful_provider,
    )

    transport = httpx.ASGITransport(app=gateway.app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/completions",
            headers={"X-API-Key": tenant},
            json={
                "prompt": "Successful request",
                "max_tokens": 100,
            },
        )

    assert response.status_code == 200

    reserved_tokens = response.json()["usage"][
        "total_reserved_tokens"
    ]

    assert reserved_tokens > 100
    assert get_reserved_tokens(tenant) == reserved_tokens


@pytest.mark.asyncio
async def test_unexpected_provider_error_refunds(monkeypatch):
    tenant = unique_tenant()

    async def unexpected_error(payload):
        raise RuntimeError("Secret upstream error")

    monkeypatch.setattr(
        gateway.router,
        "complete",
        unexpected_error,
    )

    transport = httpx.ASGITransport(app=gateway.app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/completions",
            headers={"X-API-Key": tenant},
            json={
                "prompt": "Unexpected failure",
                "max_tokens": 100,
            },
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == (
        "GATEWAY_INTERNAL_ERROR"
    )
    assert "Secret upstream error" not in response.text
    assert get_reserved_tokens(tenant) == 0

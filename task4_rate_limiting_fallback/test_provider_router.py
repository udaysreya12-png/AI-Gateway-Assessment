
import asyncio

import httpx
import pytest

from provider_router import GatewayError, ProviderRouter


class MockProvider:
    def __init__(
        self,
        response=None,
        status_code=None,
        delay=0,
        fail=False,
    ):
        self.response = response
        self.status_code = status_code
        self.delay = delay
        self.fail = fail
        self.calls = 0

    async def complete(self, payload):
        self.calls += 1

        if self.delay:
            await asyncio.sleep(self.delay)

        if self.fail:
            raise RuntimeError("Internal secret provider error")

        if self.status_code is not None:
            request = httpx.Request(
                "POST",
                "https://mock-provider.test/completions",
            )
            response = httpx.Response(
                self.status_code,
                request=request,
            )
            raise httpx.HTTPStatusError(
                "Upstream request failed",
                request=request,
                response=response,
            )

        return self.response


@pytest.mark.asyncio
async def test_primary_success():
    primary = MockProvider(response={"text": "Primary response"})
    backup = MockProvider(response={"text": "Backup response"})

    router = ProviderRouter(primary, backup)
    result = await router.complete({"prompt": "Hello"})

    assert result.provider == "primary"
    assert result.data["text"] == "Primary response"
    assert primary.calls == 1
    assert backup.calls == 0


@pytest.mark.asyncio
async def test_fallback_on_429():
    primary = MockProvider(status_code=429)
    backup = MockProvider(response={"text": "Backup response"})

    router = ProviderRouter(primary, backup)
    result = await router.complete({"prompt": "Hello"})

    assert result.provider == "backup"
    assert result.data["text"] == "Backup response"
    assert backup.calls == 1


@pytest.mark.asyncio
async def test_fallback_on_timeout():
    primary = MockProvider(delay=0.2)
    backup = MockProvider(response={"text": "Backup response"})

    router = ProviderRouter(
        primary,
        backup,
        primary_timeout=0.05,
    )

    result = await router.complete({"prompt": "Hello"})

    assert result.provider == "backup"
    assert backup.calls == 1


@pytest.mark.asyncio
async def test_no_fallback_on_500():
    primary = MockProvider(status_code=500)
    backup = MockProvider(response={"text": "Backup response"})

    router = ProviderRouter(primary, backup)

    with pytest.raises(GatewayError) as error:
        await router.complete({"prompt": "Hello"})

    assert error.value.code == "PRIMARY_PROVIDER_FAILED"
    assert backup.calls == 0


@pytest.mark.asyncio
async def test_backup_failure_is_sanitized():
    primary = MockProvider(status_code=429)
    backup = MockProvider(fail=True)

    router = ProviderRouter(primary, backup)

    with pytest.raises(GatewayError) as error:
        await router.complete({"prompt": "Hello"})

    payload = error.value.to_payload()

    assert error.value.code == "BACKUP_PROVIDER_FAILED"
    assert "Internal secret" not in str(payload)
    assert "Internal secret" not in str(error.value)


@pytest.mark.asyncio
async def test_primary_exception_is_sanitized():
    primary = MockProvider(fail=True)
    backup = MockProvider(response={"text": "Backup response"})

    router = ProviderRouter(primary, backup)

    with pytest.raises(GatewayError) as error:
        await router.complete({"prompt": "Hello"})

    assert error.value.code == "PRIMARY_PROVIDER_FAILED"
    assert "Internal secret" not in str(error.value)
    assert backup.calls == 0

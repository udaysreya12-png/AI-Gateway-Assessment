
import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


PRIMARY_TIMEOUT_SECONDS = 3.0


@dataclass
class ProviderResponse:
    provider: str
    data: Any


class GatewayError(Exception):
    """A safe, standardized gateway error."""

    def __init__(self, code, message, status_code=502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_payload(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }


class ModelProvider(Protocol):
    async def complete(self, payload: dict) -> Any:
        ...


class HTTPModelProvider:
    def __init__(self, url: str, api_key: str | None = None):
        self.url = url
        self.api_key = api_key

    async def complete(self, payload: dict):
        headers = {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=None,
            )

            response.raise_for_status()
            return response.json()


class ProviderRouter:
    def __init__(
        self,
        primary: ModelProvider,
        backup: ModelProvider,
        primary_timeout=PRIMARY_TIMEOUT_SECONDS,
    ):
        if primary_timeout <= 0:
            raise ValueError("Timeout must be positive")

        self.primary = primary
        self.backup = backup
        self.primary_timeout = primary_timeout

    async def _call_backup(self, payload):
        try:
            result = await self.backup.complete(payload)

            return ProviderResponse(
                provider="backup",
                data=result,
            )

        except Exception:
            raise GatewayError(
                code="BACKUP_PROVIDER_FAILED",
                message="Model providers are temporarily unavailable.",
                status_code=502,
            ) from None

    async def complete(self, payload: dict):
        try:
            result = await asyncio.wait_for(
                self.primary.complete(payload),
                timeout=self.primary_timeout,
            )

            return ProviderResponse(
                provider="primary",
                data=result,
            )

        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                return await self._call_backup(payload)

            raise GatewayError(
                code="PRIMARY_PROVIDER_FAILED",
                message="The model provider could not process the request.",
                status_code=502,
            ) from None

        except (TimeoutError, httpx.TimeoutException):
            return await self._call_backup(payload)

        except Exception:
            raise GatewayError(
                code="PRIMARY_PROVIDER_FAILED",
                message="The model provider could not process the request.",
                status_code=502,
            ) from None

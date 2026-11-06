
import json
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pii_redactor import redact_stream

app = FastAPI(
    title="AI Gateway - Streaming PII Guardrails",
    version="1.0.0",
)

PROVIDER_URL = os.getenv(
    "LLM_PROVIDER_URL",
    "http://127.0.0.1:9000/v1/chat/completions",
)
PROVIDER_API_KEY = os.getenv("LLM_PROVIDER_API_KEY", "")
MODEL_NAME = os.getenv("LLM_MODEL", "mock-model")


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)


async def provider_text_stream(
    prompt: str,
) -> AsyncIterator[str]:
    """
    Read OpenAI-compatible SSE response deltas.

    The upstream provider should return events with
    choices[0].delta.content.
    """
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    if PROVIDER_API_KEY:
        headers["Authorization"] = (
            f"Bearer {PROVIDER_API_KEY}"
        )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": True,
    }

    timeout = httpx.Timeout(
        connect=5.0,
        read=None,
        write=10.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:
        async with client.stream(
            "POST",
            PROVIDER_URL,
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = event.get("choices", [])

                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content")

                if isinstance(content, str) and content:
                    yield content


@app.post("/v1/generate")
async def generate(request: CompletionRequest):
    """
    Stream redacted text to the client.
    """
    async def guarded_stream():
        async for safe_chunk in redact_stream(
            provider_text_stream(request.prompt)
        ):
            yield safe_chunk

    return StreamingResponse(
        guarded_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}

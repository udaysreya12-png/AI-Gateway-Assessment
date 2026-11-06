
import asyncio
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Mock LLM Provider")

PROVIDER_NAME = os.getenv("PROVIDER_NAME", "primary")
PROVIDER_MODE = os.getenv("PROVIDER_MODE", "success")


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_tokens: int = Field(default=100, ge=1)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": PROVIDER_NAME,
        "mode": PROVIDER_MODE,
    }


@app.post("/completions")
async def completions(request: CompletionRequest):
    if PROVIDER_MODE == "rate_limit":
        raise HTTPException(
            status_code=429,
            detail="Provider rate limit exceeded",
        )

    if PROVIDER_MODE == "timeout":
        await asyncio.sleep(5)

    if PROVIDER_MODE == "error":
        raise HTTPException(
            status_code=500,
            detail="Internal provider error",
        )

    return {
        "model": PROVIDER_NAME,
        "text": f"Mock response to: {request.prompt}",
        "output_tokens": min(request.max_tokens, 20),
    }

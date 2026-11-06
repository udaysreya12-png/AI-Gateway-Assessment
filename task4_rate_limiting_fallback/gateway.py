
import os

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from provider_router import (
    GatewayError,
    HTTPModelProvider,
    ProviderRouter,
)
from rate_limiter import RateLimitExceeded, TokenRateLimiter
from token_counter import (
    calculate_token_budget,
    estimate_input_tokens,
)


app = FastAPI(title="Task 4 - Resilient LLM Gateway")

limiter = TokenRateLimiter()

router = ProviderRouter(
    primary=HTTPModelProvider(
        url=os.getenv(
            "PRIMARY_MODEL_URL",
            "http://127.0.0.1:9001/completions",
        ),
        api_key=os.getenv("PRIMARY_MODEL_API_KEY"),
    ),
    backup=HTTPModelProvider(
        url=os.getenv(
            "BACKUP_MODEL_URL",
            "http://127.0.0.1:9002/completions",
        ),
        api_key=os.getenv("BACKUP_MODEL_API_KEY"),
    ),
)


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_tokens: int = Field(default=100, ge=1, le=50000)


def error_response(status_code: int, code: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/completions")
async def completions(
    request: CompletionRequest,
    x_api_key: str | None = Header(default=None),
):
    if not x_api_key:
        return error_response(
            401,
            "MISSING_API_KEY",
            "A tenant API key is required.",
        )

    try:
        input_tokens = estimate_input_tokens(request.prompt)

        token_budget = calculate_token_budget(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
        )

        usage = await limiter.reserve(
            tenant_key=x_api_key,
            tokens=token_budget,
        )

    except RateLimitExceeded:
        return error_response(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Tenant token rate limit exceeded.",
        )

    except Exception:
        return error_response(
            500,
            "GATEWAY_INTERNAL_ERROR",
            "Unable to process the request.",
        )

    try:
        result = await router.complete(
            {
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
            }
        )

    except GatewayError as error:
        try:
            await limiter.refund(
                usage["reservation_id"],
                x_api_key,
            )
        except Exception:
            pass

        return JSONResponse(
            status_code=error.status_code,
            content=error.to_payload(),
        )

    except Exception:
        try:
            await limiter.refund(
                usage["reservation_id"],
                x_api_key,
            )
        except Exception:
            pass

        return error_response(
            500,
            "GATEWAY_INTERNAL_ERROR",
            "Unable to process the request.",
        )

    return {
        "provider": result.provider,
        "response": result.data,
        "usage": {
            "estimated_input_tokens": input_tokens,
            "reserved_output_tokens": request.max_tokens,
            "total_reserved_tokens": token_budget,
            "remaining_tokens": usage["remaining_tokens"],
        },
    }

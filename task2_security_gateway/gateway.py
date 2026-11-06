
import logging
import os
import secrets
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="MCP Security Gateway")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_security_gateway")

DOWNSTREAM_URL = os.getenv(
    "DOWNSTREAM_MCP_URL",
    "http://127.0.0.1:8001/mcp",
)

# Local assessment tokens only.
# In production, use signed JWTs or an identity provider.
DEMO_TOKENS = {
    "admin-demo-token": "admin",
    "viewer-demo-token": "viewer",
}


def jsonrpc_error(
    request_id: Any,
    code: int,
    message: str,
) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def get_role(authorization: str | None) -> str | None:
    if not authorization:
        return None

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    supplied_token = parts[1]

    for token, role in DEMO_TOKENS.items():
        if secrets.compare_digest(supplied_token, token):
            return role

    return None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "mcp-security-gateway",
    }


@app.post("/mcp")
async def mcp_gateway(request: Request):
    # Step 1: Authenticate the incoming Bearer token.
    role = get_role(request.headers.get("authorization"))

    if role is None:
        return JSONResponse(
            status_code=401,
            content=jsonrpc_error(
                None,
                -32001,
                "Unauthorized Tool Call",
            ),
        )

    # Step 2: Parse the JSON-RPC payload.
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(
            content=jsonrpc_error(
                None, -32700, "Parse error"
            )
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            content=jsonrpc_error(
                None, -32600, "Invalid Request"
            )
        )

    request_id = payload.get("id")
    method = payload.get("method")

    if (
        payload.get("jsonrpc") != "2.0"
        or not isinstance(method, str)
        or not method
        or isinstance(request_id, (dict, list, bool))
    ):
        return JSONResponse(
            content=jsonrpc_error(
                None, -32600, "Invalid Request"
            )
        )

    # Step 3: Apply method-level authorization.
    if method == "tools/call":
        params = payload.get("params")

        if not isinstance(params, dict):
            return JSONResponse(
                content=jsonrpc_error(
                    request_id, -32602, "Invalid params"
                )
            )

        tool_name = params.get("name")

        if not isinstance(tool_name, str):
            return JSONResponse(
                content=jsonrpc_error(
                    request_id, -32602, "Invalid params"
                )
            )

        if tool_name.startswith("admin_") and role != "admin":
            logger.warning(
                "Blocked admin tool: %s for role: %s",
                tool_name,
                role,
            )

            # Security requirement:
            # Do NOT contact downstream when unauthorized.
            return JSONResponse(
                status_code=403,
                content=jsonrpc_error(
                    request_id,
                    -32001,
                    "Unauthorized Tool Call",
                ),
            )

    # Step 4: Forward authorized requests unchanged.
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream_response = await client.post(
                DOWNSTREAM_URL,
                content=await request.body(),
                headers={
                    "Content-Type": request.headers.get(
                        "content-type", "application/json"
                    ),
                    "Accept": request.headers.get(
                        "accept", "application/json"
                    ),
                },
            )

        logger.info(
            "Forwarded method=%s role=%s upstream_status=%s",
            method,
            role,
            upstream_response.status_code,
        )

        # Preserve downstream HTTP status and response body.
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            media_type=upstream_response.headers.get(
                "content-type", "application/json"
            ),
        )

    except httpx.TimeoutException:
        logger.error("Downstream MCP server timed out")

        return JSONResponse(
            status_code=504,
            content=jsonrpc_error(
                request_id,
                -32000,
                "Downstream server timeout",
            ),
        )

    except httpx.RequestError:
        logger.error("Downstream MCP server unavailable")

        return JSONResponse(
            status_code=502,
            content=jsonrpc_error(
                request_id,
                -32000,
                "Downstream server unavailable",
            ),
        )

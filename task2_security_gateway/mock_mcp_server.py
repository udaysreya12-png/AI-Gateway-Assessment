
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock MCP Server")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_mcp_server")


TOOLS = [
    {
        "name": "get_customer_record",
        "description": "Retrieve a customer record",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "admin_reset_key",
        "description": "Reset an API key (admin only)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_id": {"type": "string"}
            },
            "required": ["key_id"],
        },
    },
]


def jsonrpc_result(request_id: Any, result: dict):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def jsonrpc_error(request_id: Any, code: int, message: str):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(
            jsonrpc_error(None, -32700, "Parse error")
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            jsonrpc_error(None, -32600, "Invalid Request")
        )

    request_id = payload.get("id")

    if (
        payload.get("jsonrpc") != "2.0"
        or not isinstance(payload.get("method"), str)
        or isinstance(request_id, (dict, list, bool))
    ):
        return JSONResponse(
            jsonrpc_error(None, -32600, "Invalid Request")
        )

    method = payload["method"]
    params = payload.get("params", {})

    if method == "tools/list":
        logger.info("Received tools/list request")
        return JSONResponse(
            jsonrpc_result(request_id, {"tools": TOOLS})
        )

    if method == "tools/call":
        if not isinstance(params, dict):
            return JSONResponse(
                jsonrpc_error(
                    request_id, -32602, "Invalid params"
                )
            )

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            return JSONResponse(
                jsonrpc_error(
                    request_id, -32602, "Invalid params"
                )
            )

        logger.info("Executing downstream tool: %s", tool_name)

        if tool_name == "get_customer_record":
            customer_id = arguments.get("customer_id")

            if not isinstance(customer_id, str):
                return JSONResponse(
                    jsonrpc_error(
                        request_id, -32602, "Invalid customer_id"
                    )
                )

            return JSONResponse(
                jsonrpc_result(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Customer record for {customer_id}",
                            }
                        ]
                    },
                )
            )

        if tool_name == "admin_reset_key":
            key_id = arguments.get("key_id")

            if not isinstance(key_id, str):
                return JSONResponse(
                    jsonrpc_error(
                        request_id, -32602, "Invalid key_id"
                    )
                )

            return JSONResponse(
                jsonrpc_result(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Mock reset completed for {key_id}",
                            }
                        ]
                    },
                )
            )

        return JSONResponse(
            jsonrpc_error(
                request_id, -32602, "Unknown tool"
            )
        )

    return JSONResponse(
        jsonrpc_error(
            request_id, -32601, "Method not found"
        )
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-mcp-server"}

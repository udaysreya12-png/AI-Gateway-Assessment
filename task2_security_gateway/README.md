
# Task 2 — MCP Security Gateway

## Overview

This project implements a lightweight HTTP/JSON-RPC reverse proxy that acts as a security gateway between an AI agent and a downstream mock MCP server.

The gateway authenticates incoming Bearer tokens, determines the caller's role, and enforces tool-level authorization before forwarding requests.

## Architecture

AI Agent
   |
   | HTTP POST /mcp
   | Authorization: Bearer token
   v
MCP Security Gateway (Port 8000)
   |
   | Authentication and authorization
   |
   +-- Unauthorized admin tool --> JSON-RPC error -32001
   |
   +-- Authorized request --> Downstream MCP Server (Port 8001)

## Technologies

- Python 3.12
- FastAPI
- Uvicorn
- HTTPX
- pytest

## Authentication

The gateway uses two fixed demonstration tokens:

| Token | Role |
|---|---|
| `admin-demo-token` | admin |
| `viewer-demo-token` | viewer |

These tokens are intended only for local assessment testing. Production deployments should use secure token validation.

## Authorization Rules

- `tools/list` is forwarded to the downstream server for authenticated users.
- `tools/call` is inspected for the requested tool name.
- Tool names beginning with `admin_` require the `admin` role.
- Viewers attempting to execute admin tools receive JSON-RPC error `-32001`, with the message `Unauthorized Tool Call`.
- Unauthorized tool calls are rejected without contacting the downstream server.
- Authenticated users may execute regular tools.

## Installation

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r task2_security_gateway\requirements.txt
```

## Run the Downstream Mock Server

From the repository root:

```powershell
python -m uvicorn task2_security_gateway.mock_mcp_server:app --host 127.0.0.1 --port 8001
```

## Run the Security Gateway

Open a second terminal:

```powershell
python -m uvicorn task2_security_gateway.gateway:app --host 127.0.0.1 --port 8000
```

## Health Check

Open:

http://127.0.0.1:8000/health

Expected response:

```json
{
  "status": "ok",
  "service": "mcp-security-gateway"
}
```

## Automated Tests

From the repository root:

```powershell
python -m pytest task2_security_gateway/test_gateway.py -v
```

The test suite covers:

1. Missing Bearer token rejection.
2. Invalid Bearer token rejection.
3. Viewer blocked from executing admin tools.
4. Admin permitted to execute admin tools.
5. Viewer permitted to execute regular tools.
6. Transparent forwarding of `tools/list`.

## Project Files

- `gateway.py` — Authentication, authorization, and HTTP forwarding.
- `mock_mcp_server.py` — Simulated downstream MCP server.
- `test_gateway.py` — Automated security and forwarding tests.
- `requirements.txt` — Python dependencies.

## Security Notes

The mock server performs simulated operations only.

The gateway does not forward the incoming Bearer token to the downstream server.

The demonstration credentials must not be used in production.

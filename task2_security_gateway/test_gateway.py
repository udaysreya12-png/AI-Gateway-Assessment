
import httpx
from fastapi.testclient import TestClient

from task2_security_gateway.gateway import app

client = TestClient(app)


def send_request(token, method, params=None, request_id=1):
    headers = {"Content-Type": "application/json"}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }

    return client.post("/mcp", headers=headers, json=payload)


def test_missing_token():
    response = send_request(None, "tools/list")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == -32001


def test_invalid_token():
    response = send_request("invalid-token", "tools/list")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == -32001


def test_viewer_cannot_call_admin_tool(monkeypatch):
    calls = []

    async def fake_post(self, url, **kwargs):
        calls.append(url)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = send_request(
        "viewer-demo-token",
        "tools/call",
        {
            "name": "admin_reset_key",
            "arguments": {"key_id": "KEY-123"},
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": -32001,
        "message": "Unauthorized Tool Call",
    }

    # The downstream server must never be contacted.
    assert calls == []


def test_admin_can_call_admin_tool(monkeypatch):
    calls = []

    async def fake_post(self, url, **kwargs):
        calls.append(url)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "OK"}]},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = send_request(
        "admin-demo-token",
        "tools/call",
        {
            "name": "admin_reset_key",
            "arguments": {"key_id": "KEY-123"},
        },
        request_id=2,
    )

    assert response.status_code == 200
    assert response.json()["result"]["content"][0]["text"] == "OK"
    assert len(calls) == 1


def test_viewer_can_call_regular_tool(monkeypatch):
    calls = []

    async def fake_post(self, url, **kwargs):
        calls.append(url)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "result": {"content": [{"type": "text", "text": "Customer"}]},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = send_request(
        "viewer-demo-token",
        "tools/call",
        {
            "name": "get_customer_record",
            "arguments": {"customer_id": "CUST-101"},
        },
        request_id=3,
    )

    assert response.status_code == 200
    assert response.json()["result"]["content"][0]["text"] == "Customer"
    assert len(calls) == 1


def test_tools_list_forwarded_unchanged(monkeypatch):
    original_response = {
        "jsonrpc": "2.0",
        "id": 4,
        "result": {
            "tools": [
                {"name": "get_customer_record"},
                {"name": "admin_reset_key"},
            ]
        },
    }

    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json=original_response,
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = send_request(
        "viewer-demo-token",
        "tools/list",
        request_id=4,
    )

    assert response.status_code == 200
    assert response.json() == original_response


import asyncio
import sys

import anyio

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCRequest


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"]
    )

    async with stdio_client(server_params) as (read, write):

        # Create an invalid JSON-RPC method request
        request = JSONRPCRequest(
            jsonrpc="2.0",
            id=999,
            method="invalid/method"
        )

        # Wrap request in MCP message structures
        message = SessionMessage(
            message=JSONRPCMessage(root=request)
        )

        print("Sending invalid JSON-RPC method...")

        # Send request to MCP server
        await write.send(message)

        # Wait for response
        with anyio.fail_after(5):
            response = await read.receive()

        print("\nServer response:")
        print(response)


if __name__ == "__main__":
    asyncio.run(main())

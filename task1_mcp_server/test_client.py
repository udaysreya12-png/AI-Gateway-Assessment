
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Configure MCP server connection
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"]
    )

    # Connect to MCP server using stdio
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Initialize MCP session
            await session.initialize()

            # List available MCP tools
            tools = await session.list_tools()

            print("Available tools:")

            for tool in tools.tools:
                print("-", tool.name)

            # Test unexpected input field
            result = await session.call_tool(
                "unknown_tool",
                arguments={
                    "customer_id": "CUST-00001",
                    "admin_override": True
                }
            )

            print("\nCustomer record result:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())

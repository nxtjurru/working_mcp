import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List all documents
            docs = await session.call_tool("list_documents", {})
            print("Documents:", docs)

            # Read trial_document.txt
            content = await session.call_tool(
                "read_document",
                {"filename": "trial_document.txt"}
            )
            print("Content:", content)


if __name__ == "__main__":
    asyncio.run(main())

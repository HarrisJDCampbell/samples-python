from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server")


@mcp.tool()
def echo(message: str) -> str:
    """Return the message with a note that this stdio MCP server handled it."""
    return f"{message} (echoed by the stdio MCP server)"


if __name__ == "__main__":
    mcp.run()

import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.mcp.workflow import McpWorkflow
from claude_agent_sdk_plugin.offline import Answer, offline_api_if_requested, tool_use

OFFLINE_ANSWERS: dict[str, Answer] = {
    "hello from MCP": tool_use(
        "toolu_echo", "mcp__echo__echo", message="hello from MCP"
    ),
    "tool_result:toolu_echo": "The MCP server echoed: hello from MCP",
}


# @@@SNIPSTART python-claude-agent-sdk-mcp-worker
async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_if_requested(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-mcp",
            workflows=[McpWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


# @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())

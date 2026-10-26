from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

ECHO_SERVER = str(Path(__file__).with_name("echo_mcp_server.py"))


@workflow.defn
class McpWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        options = ClaudeAgentOptions(
            mcp_servers={
                "echo": {"type": "stdio", "command": "python", "args": [ECHO_SERVER]}
            },
            strict_mcp_config=True,
            tools=[],
            allowed_tools=["mcp__echo__echo"],
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(prompt)
            result = ""
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    result = message.result or ""
        return result

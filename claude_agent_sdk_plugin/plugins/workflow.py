import os

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "haiku-writer")


@workflow.defn
class PluginsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        options = ClaudeAgentOptions(
            plugins=[{"type": "local", "path": PLUGIN_DIR}],
            tools=["Skill"],
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        reply = ""
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    reply = message.result or "\n".join(message.errors or [])
        return reply

import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import Answer, offline_api_if_requested, tool_use
from claude_agent_sdk_plugin.plugins.workflow import PluginsWorkflow

OFFLINE_ANSWERS: dict[str, Answer] = {
    "tool_result:toolu_skill": (
        "Workers fall and rise\n"
        "history remembers all\n"
        "the work carries on\n"
        "\n"
        "~ haiku-writer"
    ),
    "haiku": tool_use("toolu_skill", "Skill", skill="haiku-writer:haiku"),
}


# @@@SNIPSTART python-claude-agent-sdk-plugins-worker
async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_if_requested(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-plugins",
            workflows=[PluginsWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


# @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())

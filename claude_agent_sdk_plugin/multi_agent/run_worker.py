import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.multi_agent.offline_answers import ANSWERS
from claude_agent_sdk_plugin.multi_agent.workflow import MultiAgentWorkflow
from claude_agent_sdk_plugin.offline import offline_api_if_requested


# @@@SNIPSTART python-claude-agent-sdk-multi-agent-worker
async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_if_requested(ANSWERS):
        async with Worker(
            client,
            task_queue="claude-agent-sdk-multi-agent",
            workflows=[MultiAgentWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print("Worker started. Ctrl+C to exit.")
            await asyncio.Event().wait()


# @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import offline_api_if_requested
from claude_agent_sdk_plugin.streaming.workflow import StreamingWorkflow

OFFLINE_ANSWERS = {
    "Count": ["One. ", "Two. ", "Three. ", "Four. ", "Five."],
}


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    # @@@SNIPSTART python-claude-agent-sdk-streaming-worker
    worker = Worker(
        client,
        task_queue="claude-agent-sdk-streaming",
        workflows=[StreamingWorkflow],
        plugins=[ClaudeAgentSDKPlugin()],
    )
    # @@@SNIPEND
    with offline_api_if_requested(OFFLINE_ANSWERS):
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

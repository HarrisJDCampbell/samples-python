import asyncio
import os
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import (
    Answer,
    offline_api_if_requested,
    tool_use,
)
from claude_agent_sdk_plugin.sandbox.activities import SBX_ACTIVITIES
from claude_agent_sdk_plugin.sandbox.workflow import SandboxWorkflow


def tool_result(body: dict[str, Any], tool_use_id: str) -> dict[str, Any]:
    return next(
        block
        for message in body["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block.get("tool_use_id") == tool_use_id
    )


def after_delete(body: dict[str, Any]) -> str:
    if tool_result(body, "toolu_delete").get("is_error"):
        return "I wrote the primes to primes.txt. You denied deleting it, so it stays."
    return "I wrote the primes to primes.txt, then deleted it."


OFFLINE_ANSWERS: dict[str, Answer] = {
    "primes": tool_use(
        "toolu_write",
        "Bash",
        command="echo 2 3 5 7 11 > primes.txt && cat primes.txt",
        description="Write the primes",
    ),
    "tool_result:toolu_write": tool_use(
        "toolu_delete", "Bash", command="rm primes.txt", description="Delete the file"
    ),
    "tool_result:toolu_delete": after_delete,
}


# @@@SNIPSTART python-claude-agent-sdk-sandbox-worker
async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_if_requested(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-sandbox",
            workflows=[SandboxWorkflow],
            plugins=[ClaudeAgentSDKPlugin(activities=SBX_ACTIVITIES)],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


# @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())

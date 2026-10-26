import json
import uuid
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import Answer, scripted_api, tool_use
from claude_agent_sdk_plugin.plugins.workflow import PluginsWorkflow

HAIKU = "Workers fall and rise\nhistory remembers all\nthe work carries on"
REPLY = f"{HAIKU}\n\n~ haiku-writer"


def user_blocks(request: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        block
        for message in request["messages"]
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
    ]


async def test_plugin_skill(client: Client) -> None:
    answers: dict[str, Answer] = {
        "tool_result:toolu_skill": REPLY,
        "haiku": tool_use("toolu_skill", "Skill", skill="haiku-writer:haiku"),
    }
    task_queue = f"claude-agent-sdk-plugins-{uuid.uuid4()}"

    with scripted_api(answers) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[PluginsWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                PluginsWorkflow.run,
                "Write a haiku about durable execution.",
                id=f"claude-agent-sdk-plugins-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == REPLY
    assert api.asked == ["haiku", "tool_result:toolu_skill"]

    first, second = api.requests
    assert [t["name"] for t in first["tools"]] == ["Skill"]
    assert "- haiku-writer:haiku: Write the answer as a haiku." in json.dumps(first)

    blocks = user_blocks(second)
    tool_result = next(b for b in blocks if b.get("type") == "tool_result")
    assert tool_result["tool_use_id"] == "toolu_skill"
    assert tool_result["content"] == "Launching skill: haiku-writer:haiku"
    skill_text = "\n".join(b["text"] for b in blocks if b.get("type") == "text")
    assert "Answer with a single haiku" in skill_text
    assert "~ haiku-writer" in skill_text

    history = await handle.fetch_history()
    await Replayer(
        workflows=[PluginsWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(history)

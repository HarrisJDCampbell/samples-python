import uuid
from typing import Any

from temporalio.api.enums.v1 import EventType
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.mcp.workflow import ECHO_SERVER, McpWorkflow
from claude_agent_sdk_plugin.offline import Answer, scripted_api, tool_use

TRANSPORT_ACTIVITIES = {
    "claude-code-launch",
    "claude-code-write-stdin",
    "claude-code-watch-output",
    "claude-code-close",
}


def tool_results(requests: list[dict[str, Any]]) -> list[str]:
    return [
        str(block["content"])
        for request in requests
        for message in request["messages"]
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]


async def test_mcp(client: Client) -> None:
    answers: dict[str, Answer] = {
        "hello from MCP": tool_use(
            "toolu_echo", "mcp__echo__echo", message="hello from MCP"
        ),
        "tool_result:toolu_echo": "Echoed: hello from MCP",
    }
    task_queue = f"claude-agent-sdk-mcp-{uuid.uuid4()}"

    with scripted_api(answers) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[McpWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                McpWorkflow.run,
                "Use the echo tool on 'hello from MCP'.",
                id=f"claude-agent-sdk-mcp-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == "Echoed: hello from MCP"
    assert api.asked == ["hello from MCP", "tool_result:toolu_echo"]
    assert [tool["name"] for tool in api.requests[0]["tools"]] == ["mcp__echo__echo"]
    results = tool_results(api.requests)
    assert len(results) == 1
    assert "hello from MCP (echoed by the stdio MCP server)" in results[0]

    history = await handle.fetch_history()
    scheduled = {
        event.activity_task_scheduled_event_attributes.activity_type.name
        for event in history.events
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
    }
    assert scheduled <= TRANSPORT_ACTIVITIES
    assert ECHO_SERVER in str(history)

    await Replayer(
        workflows=[McpWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(history)

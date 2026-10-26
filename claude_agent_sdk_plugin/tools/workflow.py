from datetime import timedelta
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    create_sdk_mcp_server,
    tool,
)
from temporalio import activity, workflow
from temporalio.claude_agent_sdk import TemporalTransport


@activity.defn
async def fetch_weather(city: str) -> str:
    return f"It is 21 C and sunny in {city}."


@tool(
    "count_letter",
    "Count how often a letter appears in a word",
    {"word": str, "letter": str},
)
async def count_letter(args: dict[str, Any]) -> dict[str, Any]:
    count = args["word"].lower().count(args["letter"].lower())
    return {"content": [{"type": "text", "text": str(count)}]}


@tool("get_weather", "Get the current weather in a city", {"city": str})
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    weather = await workflow.execute_activity(
        fetch_weather, args["city"], start_to_close_timeout=timedelta(seconds=30)
    )
    return {"content": [{"type": "text", "text": weather}]}


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        options = ClaudeAgentOptions(
            tools=[],
            mcp_servers={
                "demo": create_sdk_mcp_server("demo", tools=[count_letter, get_weather])
            },
            allowed_tools=["mcp__demo__count_letter", "mcp__demo__get_weather"],
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        result = ""
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    result = message.result or "\n".join(message.errors or [])
        return result

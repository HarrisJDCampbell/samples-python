from dataclasses import dataclass, field

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

COORDINATOR = "coordinator"


@dataclass
class Briefing:
    result: str
    messages_by_agent: dict[str, list[str]] = field(default_factory=dict)


# @@@SNIPSTART python-claude-agent-sdk-multi-agent-workflow
@workflow.defn
class MultiAgentWorkflow:
    @workflow.run
    async def run(self, topic: str) -> Briefing:
        options = ClaudeAgentOptions(
            agents={
                "researcher": AgentDefinition(
                    description="Finds the key facts about a topic.",
                    prompt="You are a researcher. Reply with a short list of key facts.",
                    tools=["WebSearch", "WebFetch"],
                ),
                "writer": AgentDefinition(
                    description="Turns notes into a short, readable briefing.",
                    prompt="You are a writer. Turn the notes you are given into a briefing.",
                    tools=[],
                ),
            },
            tools=["Agent", "WebSearch", "WebFetch"],
            allowed_tools=["Agent", "WebSearch", "WebFetch"],
            permission_mode="default",
            forward_subagent_text=True,
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        roles: dict[str, str] = {}
        messages_by_agent: dict[str, list[str]] = {}
        result = ""

        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(
                "Delegate the research to the researcher, then have the writer "
                f"draft a short briefing on this topic: {topic}"
            )
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    role = roles.get(message.parent_tool_use_id or "", COORDINATOR)
                    for block in message.content:
                        if isinstance(block, ToolUseBlock) and block.name == "Agent":
                            roles[block.id] = block.input["subagent_type"]
                        elif isinstance(block, TextBlock):
                            workflow.logger.info("%s: %s", role, block.text)
                            messages_by_agent.setdefault(role, []).append(block.text)
                elif isinstance(message, ResultMessage):
                    result = message.result or ""
        return Briefing(result, messages_by_agent)


# @@@SNIPEND

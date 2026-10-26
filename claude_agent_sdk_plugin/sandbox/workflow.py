from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ToolPermissionContext,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

from claude_agent_sdk_plugin.sandbox.activities import SBX_ACTIVITIES


@dataclass
class ToolCall:
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


@dataclass
class ToolDecision:
    tool_use_id: str
    approved: bool


# @@@SNIPSTART python-claude-agent-sdk-sandbox-workflow
@workflow.defn
class SandboxWorkflow:
    def __init__(self) -> None:
        self.pending: dict[str, ToolCall] = {}
        self.decisions: dict[str, bool] = {}

    @workflow.run
    async def run(self, prompt: str) -> str:
        options = ClaudeAgentOptions(
            permission_mode="default",
            can_use_tool=self.approve,
            setting_sources=[],
        )
        transport = TemporalTransport(options, SBX_ACTIVITIES)
        result = ""
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    result = message.result or "\n".join(message.errors or [])
        return result

    async def approve(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResult:
        tool_use_id = context.tool_use_id or ""
        self.pending[tool_use_id] = ToolCall(tool_use_id, tool_name, tool_input)
        try:
            await workflow.wait_condition(lambda: tool_use_id in self.decisions)
        finally:
            del self.pending[tool_use_id]
        if self.decisions[tool_use_id]:
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"The reviewer denied {tool_name}")

    @workflow.query
    def pending_tool_calls(self) -> list[ToolCall]:
        return list(self.pending.values())

    @workflow.update
    def decide_tool(self, decision: ToolDecision) -> None:
        self.decisions[decision.tool_use_id] = decision.approved


# @@@SNIPEND

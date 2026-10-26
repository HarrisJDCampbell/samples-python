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


@dataclass
class ToolRequest:
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


@dataclass
class Decision:
    tool_use_id: str
    approved: bool


@workflow.defn
class HumanInTheLoopWorkflow:
    def __init__(self) -> None:
        self.pending: dict[str, ToolRequest] = {}
        self.decisions: dict[str, bool] = {}

    @workflow.run
    async def run(self, task: str) -> str:
        options = ClaudeAgentOptions(
            tools=["Bash"],
            permission_mode="default",
            can_use_tool=self.ask_human,
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        result = ""
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(task)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    result = message.result or ""
        return result

    async def ask_human(
        self, tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResult:
        tool_use_id = context.tool_use_id or ""
        self.pending[tool_use_id] = ToolRequest(tool_use_id, tool_name, tool_input)
        try:
            await workflow.wait_condition(lambda: tool_use_id in self.decisions)
        finally:
            del self.pending[tool_use_id]
        if self.decisions[tool_use_id]:
            return PermissionResultAllow()
        return PermissionResultDeny(message="A person denied this tool call")

    @workflow.query
    def pending_tool_calls(self) -> list[ToolRequest]:
        return list(self.pending.values())

    @workflow.update
    def decide(self, decision: Decision) -> None:
        self.decisions[decision.tool_use_id] = decision.approved

    @decide.validator
    def validate_decide(self, decision: Decision) -> None:
        if decision.tool_use_id not in self.pending:
            raise ValueError(f"No pending tool call {decision.tool_use_id}")

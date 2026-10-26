# @@@SNIPSTART python-claude-agent-sdk-structured-output-workflow
from typing import Literal

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.exceptions import ApplicationError


class SupportTicket(BaseModel):
    category: Literal["billing", "bug", "feature_request"]
    priority: int = Field(ge=1, le=5)
    summary: str


@workflow.defn
class TriageTicketWorkflow:
    @workflow.run
    async def run(self, text: str) -> SupportTicket:
        options = ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": SupportTicket.model_json_schema(),
            },
            setting_sources=[],
        )
        transport = TemporalTransport(options)
        outcome: ResultMessage | None = None
        async for message in query(
            prompt=f"Triage this customer message:\n{text}",
            options=options,
            transport=transport,
        ):
            if isinstance(message, ResultMessage):
                outcome = message
        if outcome is None or outcome.structured_output is None:
            raise ApplicationError(
                "Claude Code returned no structured output", non_retryable=True
            )
        return SupportTicket.model_validate(outcome.structured_output)


# @@@SNIPEND

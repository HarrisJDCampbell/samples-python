import asyncio
from dataclasses import dataclass

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.exceptions import ApplicationError


@dataclass
class ChatInput:
    session_id: str | None = None
    turns_per_run: int = 3


@workflow.defn
class ChatWorkflow:
    @workflow.init
    def __init__(self, input: ChatInput) -> None:
        self.session_id = input.session_id
        self.turns_per_run = input.turns_per_run
        self.turns = 0
        self.ended = False
        self.client: ClaudeSDKClient | None = None
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        options = ClaudeAgentOptions(resume=input.session_id, setting_sources=[])
        transport = TemporalTransport(options)
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            self.client = client
            await workflow.wait_condition(
                lambda: (self.ended or self.run_is_full())
                and workflow.all_handlers_finished()
            )
        if not self.ended:
            workflow.continue_as_new(ChatInput(self.session_id, self.turns_per_run))

    @workflow.update
    async def send_message(self, message: str) -> str:
        self.turns += 1
        await workflow.wait_condition(lambda: self.client is not None)
        assert self.client is not None
        reply = ""
        async with self.lock:
            await self.client.query(message)
            async for response in self.client.receive_response():
                if isinstance(response, ResultMessage):
                    self.session_id = response.session_id
                    reply = response.result or "\n".join(response.errors or [])
        return reply

    @send_message.validator
    def validate_send_message(self, message: str) -> None:
        if self.ended:
            raise ApplicationError("The conversation has ended")
        if self.run_is_full():
            raise ApplicationError("The chat is continuing as new. Send it again.")

    @workflow.update
    def end_conversation(self) -> None:
        self.ended = True

    def run_is_full(self) -> bool:
        return (
            self.turns >= self.turns_per_run
            or workflow.info().is_continue_as_new_suggested()
        )

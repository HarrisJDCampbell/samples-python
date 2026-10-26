from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.contrib.workflow_streams import WorkflowStream


@workflow.defn
class StreamingWorkflow:
    @workflow.init
    def __init__(self, prompt: str) -> None:
        self.events = WorkflowStream().topic("events")

    @workflow.run
    async def run(self, prompt: str) -> str:
        options = ClaudeAgentOptions(include_partial_messages=True, setting_sources=[])
        transport = TemporalTransport(options, stream=self.events)
        result = ""
        async with ClaudeSDKClient(options=options, transport=transport) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    result = message.result or ""
        await workflow.sleep(timedelta(milliseconds=500))
        return result

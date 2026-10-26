# Streaming

Stream Claude's output token by token through a [Workflow Stream](https://docs.temporal.io/develop/python/workflows/workflow-streams) (experimental), and finish the same way whether or not anyone is subscribed.

## What this shows

- `include_partial_messages=True` makes Claude Code emit a `stream_event` for every delta. `TemporalTransport(options, stream=...)` takes a topic of a `WorkflowStream` created in `@workflow.init`, and the watch Activity publishes each `stream_event` to that topic instead of Signalling it to the Workflow. The two options go together: passing one without the other raises `ValueError`.
- The Workflow does not see `stream_event`s. It still receives every complete message, so `ResultMessage.result` is the final text.
- `run_workflow.py` subscribes with `WorkflowStreamClient` and prints each text delta as it arrives. The Temporal CLI cannot subscribe to a Workflow Stream, which is why this scenario has a client script. Each item's `data` is the `stream_event` message as a `dict`; text is in `data["event"]["delta"]["text"]` when `delta["type"] == "text_delta"`.
- Nothing in the Workflow depends on a subscriber. With no subscriber the stream is simply never polled, and the Workflow returns the same result.
- The Workflow sleeps 500 ms before returning so a subscriber's final poll can read the last events before the Workflow, and its in-memory stream, completes. If a Worker fails mid-turn, a subscriber may see a few events twice.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

### Live

Export `ANTHROPIC_API_KEY` in the environment of the Worker, then start it:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/streaming/run_worker.py
```

### Offline

A scripted model, no credentials. The same Worker, plugin, Workflow, and Claude Code subprocess run:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/streaming/run_worker.py
```

### Start the Workflow with a live subscriber

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/streaming/run_workflow.py
```

Offline, the deltas print as `One. Two. Three. Four. Five.` and then `Final result: One. Two. Three. Four. Five.` Live, the text is Claude's. Pass your own prompt as arguments.

### Start the Workflow with no subscriber

```bash
temporal workflow execute \
  --type StreamingWorkflow \
  --task-queue claude-agent-sdk-streaming \
  --workflow-id claude-agent-sdk-streaming-nosub \
  --input '"Count from one to five, one number per sentence."'
```

The Workflow completes with the same result.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/streaming_test.py
```

The tests script the model to answer in five chunks. One checks that a subscriber receives the chunks in order, that they concatenate to the Workflow result, and that the history replays. The other checks that a run with no subscriber returns the same result.

# Agent Chat

A multi-turn chat with Claude that lives in one Workflow. Each message is a `send_message` Update that returns Claude's reply, and `end_conversation` ends the chat. Start here.

## What this shows

- The Workflow keeps one `ClaudeSDKClient` open for the run, so one Claude Code process on the Worker holds the conversation. Each turn is `client.query(...)` followed by `client.receive_response()` until the `ResultMessage`.
- After `turns_per_run` messages (3 by default), or once Temporal suggests it, the Workflow continues as new to bound its history. It first waits for every in-flight `send_message` to finish, then closes the client, which ends Claude Code's input and lets it exit.
- The conversation itself is not carried into the next run, only Claude Code's session ID, taken from the `ResultMessage`. The next run passes it as `ClaudeAgentOptions(resume=...)`, and Claude Code reloads the conversation from its session file.
- Claude Code keeps session files on the Worker host, under `CLAUDE_CONFIG_DIR` (default `~/.claude`) and keyed by its working directory. Resuming needs the same host and working directory, so run the Worker from the same directory. With Workers on several hosts, pass `TemporalTransport` a `task_queue` that only one host polls.
- A message sent while a run is handing off is rejected with "The chat is continuing as new. Send it again."

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

### Live

Export `ANTHROPIC_API_KEY` in the environment of the Worker, then start it:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/agent_chat/run_worker.py
```

### Offline

Scripted model, no credentials. The same Worker, plugin, Workflow, and Claude Code subprocess run, and each reply counts the earlier replies Claude Code sent in its request:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/agent_chat/run_worker.py
```

### Chat

Start the chat:

```bash
temporal workflow start \
  --type ChatWorkflow \
  --task-queue claude-agent-sdk-agent-chat \
  --workflow-id claude-agent-sdk-agent-chat \
  --input '{}'
```

Send messages, one at a time:

```bash
temporal workflow update execute \
  --workflow-id claude-agent-sdk-agent-chat \
  --name send_message \
  --input '"Hi, my name is Ada."'
```

Each command prints Claude's reply. Offline, the first four replies are `"Offline reply 1 in this conversation."` through `"Offline reply 4 in this conversation."`. The fourth comes from a new run, and its number shows that Claude Code resumed the earlier turns. Live, ask "What is my name?" after the third message, and Claude still knows it.

See the runs, one `ContinuedAsNew` and one `Running`:

```bash
temporal workflow list --query 'WorkflowId="claude-agent-sdk-agent-chat"'
```

End the chat:

```bash
temporal workflow update execute \
  --workflow-id claude-agent-sdk-agent-chat \
  --name end_conversation
```

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/agent_chat_test.py
```

The test chats across a Continue-As-New, checks that the request after it includes the earlier turns and that the session ID was carried, and replays both runs' histories.

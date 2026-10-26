# Human in the Loop

Claude Code pauses before each tool call until a person approves or denies it. The Workflow sets `can_use_tool` on `ClaudeAgentOptions`. Claude Code calls it before every tool call, and it waits durably with `workflow.wait_condition` until a decision arrives through an Update. The wait can last minutes or days, and it survives Worker restarts.

- `pending_tool_calls` Query: the tool calls waiting for a decision, each with its `tool_use_id`, tool name, and input.
- `decide` Update: approve or deny one pending call. The validator rejects an ID that isn't pending.
- An approved call runs. A denied call doesn't run, and the model receives the denial as the tool's result.
- Cancelling the Workflow while it waits ends the turn and stops Claude Code.

The only tool here is Bash, with `permission_mode="default"`, so every command needs a decision. Tools listed in `allowed_tools` would be approved before `can_use_tool` runs, and the Claude Agent SDK warns about that with `CanUseToolShadowedWarning`.

## Run it

Start a Temporal dev server:

```bash
temporal server start-dev
```

Start the Worker from the repository root. Claude Code works in the Worker's current directory.

```bash
# Live: uses your Anthropic API key
export ANTHROPIC_API_KEY=...
uv run --group claude-agent-sdk claude_agent_sdk_plugin/human_in_the_loop/run_worker.py

# Offline: a scripted local model, no credentials
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/human_in_the_loop/run_worker.py
```

Start a task:

```bash
temporal workflow start \
  --type HumanInTheLoopWorkflow \
  --task-queue claude-agent-sdk-human-in-the-loop \
  --workflow-id human-in-the-loop \
  --input '"Create hello.txt with a greeting."'
```

See what is waiting for a decision:

```bash
temporal workflow query --workflow-id human-in-the-loop --name pending_tool_calls -o json
```

Offline, that's one Bash call:

```json
{
  "tool_input": {
    "command": "echo 'Hello from Claude Code' > hello.txt"
  },
  "tool_name": "Bash",
  "tool_use_id": "toolu_hello"
}
```

Approve it, using the `tool_use_id` from the Query. A live model picks its own IDs and may ask for more than one call; decide each one.

```bash
temporal workflow update execute \
  --workflow-id human-in-the-loop \
  --name decide \
  --input '{"tool_use_id": "toolu_hello", "approved": true}'
```

Then get the result:

```bash
temporal workflow result --workflow-id human-in-the-loop
```

Offline, the result is `"Created hello.txt."`, and `hello.txt` is in the Worker's directory.

To deny instead, send `"approved": false`. The command doesn't run, and offline the result is `"Understood. I did not create hello.txt."`.

To cancel, start another task with a new Workflow ID, then cancel it while a call is pending:

```bash
temporal workflow cancel --workflow-id <workflow-id>
```

The Workflow ends as Canceled. Its history shows the `claude-code-close` Activity that stopped Claude Code.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/human_in_the_loop_test.py
```

# Tools

Claude calls two custom tools, and each runs on a different side of Temporal's determinism boundary.

| Tool | Runs as | Why |
| --- | --- | --- |
| `count_letter` | Workflow code | Pure computation, so it replays to the same result. |
| `get_weather` | Activity (`fetch_weather`) | I/O. The `@tool` handler calls `workflow.execute_activity`, so the call gets timeouts, retries, and a recorded result. |

Both are defined with `@tool`, served by `create_sdk_mcp_server`, and pre-approved in `allowed_tools`. `tools=[]` removes Claude Code's built-in tools so only these two are available. Their handlers run in the Workflow; Claude Code itself runs in a subprocess on the Worker, reached through the integration's own Activities (`claude-code-launch`, `claude-code-write-stdin`, `claude-code-watch-output`, `claude-code-close`).

## Run

Commands run from the repository root. Start a Temporal dev server first:

```bash
temporal server start-dev
```

### Live

The Worker's environment supplies the credentials; they never go through the options.

```bash
export ANTHROPIC_API_KEY=...
uv run --group claude-agent-sdk claude_agent_sdk_plugin/tools/run_worker.py
```

### Offline

A scripted local Messages API stands in for Anthropic. The Worker, plugin, Workflow, and Activities are the same.

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/tools/run_worker.py
```

### Start the Workflow

```bash
temporal workflow execute \
  --type ToolsWorkflow \
  --task-queue claude-agent-sdk-tools \
  --workflow-id claude-agent-sdk-tools \
  --input '"Count the r letters in strawberry, then get the weather in Paris."'
```

Offline, the result is:

```text
"There are 3 r's in strawberry. It is 21 C and sunny in Paris."
```

## See the boundary

In the Temporal UI (`http://localhost:8233`) or with `temporal workflow show --workflow-id claude-agent-sdk-tools`, the history contains one `fetch_weather` Activity for the weather call. `count_letter` has no Activity of its own; it ran inside Workflow tasks. The other Activities are the integration's `claude-code-*` transport Activities.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/tools_test.py
```

The test scripts the model to call both tools, checks the final reply and the tool results Claude received, asserts that exactly one `fetch_weather` Activity was scheduled and none for `count_letter`, and replays the history.

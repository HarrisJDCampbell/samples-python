# MCP

Claude Code calls a tool served by a local stdio MCP server that it launches itself. The Workflow only passes the server's command in `ClaudeAgentOptions.mcp_servers` and pre-approves its tool with `allowed_tools`.

## What this shows

- Claude Code starts `echo_mcp_server.py` as a separate process and talks to it over stdio, so the MCP traffic never touches Workflow code. It happens inside the Claude Code process, which the transport's Activities launch and feed on the Worker. Nothing in the Workflow history except Claude Code's messages records the call.
- The command is resolved on the Worker, not in the Workflow. The server script is an absolute path derived from the Workflow module's `__file__` with string operations, so it does not depend on the current directory. `python` is found on the Worker's `PATH`, which `uv run` points at the project environment. Claude Code inherits the Worker's environment.
- `strict_mcp_config=True` and `setting_sources=[]` keep MCP servers and settings from your own Claude Code configuration out of the sample. `tools=[]` removes the built-in tools so the MCP tool is the only one offered.
- This is a stateless server: each Claude Code process owns its server process, which exits when Claude Code does. Use [Custom Tools](../tools/README.md) when the tool should run as Workflow code and call Activities.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

### Live

Export `ANTHROPIC_API_KEY` in the environment of the Worker, then start it:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/mcp/run_worker.py
```

### Offline

Scripted model, no credentials. The same Worker, plugin, Workflow, and Claude Code subprocess run:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/mcp/run_worker.py
```

### Start the Workflow

```bash
temporal workflow execute \
  --type McpWorkflow \
  --task-queue claude-agent-sdk-mcp \
  --workflow-id claude-agent-sdk-mcp \
  --input '"Use the echo tool on the message: hello from MCP"'
```

Offline, the result is `"The MCP server echoed: hello from MCP"`. Live, the wording is Claude's. In the Temporal UI, the history shows the transport's Activities that carry Claude Code's tool call and the server's reply.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/mcp_test.py
```

The test scripts the model to call `mcp__echo__echo`, checks that the real server's reply reaches the next model request and the final result, and replays the history.

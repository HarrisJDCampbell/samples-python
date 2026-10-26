# Claude Agent SDK Samples

⚠️ **Pre-release**: this integration and its interfaces may change before General Availability.

These samples demonstrate the [Temporal Claude Agent SDK integration](https://github.com/temporalio/ai-integrations/tree/main/python/claude_agent_sdk), which runs [Claude Code](https://code.claude.com/docs/en/agent-sdk/overview) agents as Temporal Workflows. Your Workflow uses the Claude Agent SDK's own `ClaudeSDKClient` or `query` with a `TemporalTransport`. Claude Code runs unmodified, Temporal Activities carry its input and output, and approvals, hooks, and custom tools run as Workflow code.

## Samples

| Category | Sample | What it shows |
| --- | --- | --- |
| Agent Chat | [agent_chat](agent_chat) | A multi-turn chat driven by Updates, with Continue-As-New that resumes Claude's session in the next run. Start here. |
| Tools | [tools](tools) | One custom tool computed in the Workflow and one that runs an Activity, both via `@tool` and `create_sdk_mcp_server`. |
| MCP | [mcp](mcp) | A bundled stdio MCP server that Claude Code launches and calls itself. |
| Streaming | [streaming](streaming) | Token-by-token output through a Workflow Stream, with or without a subscriber. |
| Human in the Loop | [human_in_the_loop](human_in_the_loop) | `can_use_tool` waits durably for a person's Update: approve, deny, or cancel. |
| Structured Output | [structured_output](structured_output) | A JSON-schema result validated as a Pydantic model at the Workflow boundary. |
| Multi-Agent | [multi_agent](multi_agent) | Claude Code's native subagents: a coordinator delegating to a researcher and a writer. |
| Sandboxes | [sandbox](sandbox) | A custom transport that runs Claude Code in a Docker Sandbox (`sbx`), with the Workflow approving every tool call. |
| Plugins | [plugins](plugins) | Your own skill, passed to Claude Code as a local plugin through `ClaudeAgentOptions.plugins`. |

Observability is not covered yet. OpenTelemetry context propagation into Claude Code is planned, with a sample to follow.

Every sample except `sandbox` uses the default transport Activities, which run Claude Code in a subprocess on the Worker.

## Prerequisites

1. Install dependencies:

   ```bash
   uv sync --group claude-agent-sdk
   ```

   The `claude-agent-sdk` package bundles Claude Code, so nothing else needs installing.

2. Start a Temporal dev server:

   ```bash
   temporal server start-dev
   ```

3. Choose a mode for the Worker:

   - **Live:** set your own `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`) in the Worker's terminal. Claude Code inherits the Worker's environment, so the key never passes through Workflow history.
   - **Offline:** set `CLAUDE_OFFLINE=1` and no key. The Worker starts a scripted Anthropic API on localhost and points Claude Code at it, so each sample runs through the same Worker, plugin, Workflow, and Activities with canned answers.

Each sample's README has its Worker command and the `temporal workflow` commands to drive it.

## Tests

The tests run every sample against the scripted API and a local dev server, with no credentials:

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin
```

They're skipped on Windows, where the default transport's shell scripts don't run.

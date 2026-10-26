# Multi-Agent

Claude Code's native subagent delegation, run as a Temporal Workflow. A coordinator delegates to two subagents defined in `ClaudeAgentOptions(agents=...)`: a `researcher` that gathers facts and a `writer` that turns them into a briefing.

- `AgentDefinition` gives each role a description (when to use it), a prompt, and its own tools. A subagent's tools must also be in the top-level `tools`.
- The delegation tool is named `Agent` in this Claude Code version. It is pre-approved with `allowed_tools`, so delegation needs no person.
- Every message a subagent produces carries `parent_tool_use_id`, the `Agent` tool call that started it. The Workflow maps that id to the subagent type and returns the messages grouped by role.
- `forward_subagent_text=True` makes Claude Code forward the subagents' text, not only their tool calls.
- Claude Code runs in a subprocess on the Worker, and the Workflow reaches it through Activities. Subagents run inside that Claude Code process.

## Run it

From the repository root, start a dev server and, in another terminal, the Worker.

Live, with your own `ANTHROPIC_API_KEY` in the Worker's environment:

```bash
temporal server start-dev
uv run --group claude-agent-sdk claude_agent_sdk_plugin/multi_agent/run_worker.py
```

Offline, with a scripted Anthropic API and no credentials:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/multi_agent/run_worker.py
```

Then run the Workflow:

```bash
temporal workflow execute \
  --type MultiAgentWorkflow \
  --task-queue claude-agent-sdk-multi-agent \
  --workflow-id multi-agent \
  --input '"durable execution"'
```

## Expected behavior

The result lists the final briefing and, under `messages_by_agent`, what each of `coordinator`, `researcher`, and `writer` said. Offline, the researcher returns three facts, the writer one sentence, and the coordinator `Final briefing: Temporal keeps your code running through failures.` The Workflow also logs each message with its role.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/multi_agent_test.py
```

The test scripts the coordinator to call both subagents, asserts that requests carrying each role's prompt reached the API, checks the per-role messages and final result, and replays the Workflow history.

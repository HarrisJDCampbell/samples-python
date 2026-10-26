# Plugins

Give Claude Code your own skill by passing it a Claude Code plugin, and see Claude use it.

A Claude Code plugin is a directory that bundles skills, and can also bundle agents, slash commands, hooks, and MCP servers. This sample bundles the `haiku-writer` plugin:

```text
haiku-writer/
├── .claude-plugin/plugin.json
└── skills/haiku/SKILL.md
```

The `haiku` skill tells Claude to answer with a haiku and sign it `~ haiku-writer`.

`PluginsWorkflow` passes the plugin with `ClaudeAgentOptions(plugins=[{"type": "local", "path": PLUGIN_DIR}])`, and limits Claude Code's tools to `Skill`. Claude Code lists the plugin's skill as `haiku-writer:haiku`. When the model calls the `Skill` tool with that name, Claude Code reads `SKILL.md` and gives its instructions to the model. The skill loads even with `setting_sources=[]`, and Claude Code lets the model use it without asking for permission.

The plugin path is a path on the Worker, because Claude Code runs in a subprocess on the Worker. The Workflow builds it from the module's own location, so it works from any working directory. The path is recorded in Workflow history as part of the launch Activity's input.

## Run it

Start a local Temporal server in one terminal:

```bash
temporal server start-dev
```

Start the Worker in a second terminal. It needs `ANTHROPIC_API_KEY` in its environment:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/plugins/run_worker.py
```

Or run it with no credentials. A scripted local Anthropic API calls the skill, then answers with a fixed haiku:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/plugins/run_worker.py
```

Ask for a haiku from a third terminal:

```bash
temporal workflow execute \
  --type PluginsWorkflow \
  --task-queue claude-agent-sdk-plugins \
  --workflow-id plugins \
  --input '"Write a haiku about durable execution."'
```

## Expected behavior

The result is a haiku followed by the `~ haiku-writer` signature. Offline it is always:

```text
Workers fall and rise
history remembers all
the work carries on

~ haiku-writer
```

In the Temporal UI, the `claude-code-launch` Activity's input includes `--plugin-dir` and the plugin's path on the Worker.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/plugins_test.py
```

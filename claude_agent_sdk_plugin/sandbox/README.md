# Sandbox

Run Claude Code inside a [Docker Sandbox](https://docs.docker.com/ai/sandboxes/) instead of on the Worker, and make the Workflow the approval gate for every tool call.

The sandbox provides isolation. Inside it, everything is allowed: the network policy is open and every built-in Claude Code tool is available. The durable Workflow provides control: Claude Code runs in its `default` permission mode, so it asks `can_use_tool` before each tool call that needs permission, and the Workflow waits for a reviewer's Update before answering. A pending approval survives Worker restarts and can wait as long as it needs to.

The open network policy (`"**"`) also lets the sandbox reach every port on the Worker's host through `host.docker.internal`. Narrow it with `sbx policy` if that host runs services the agent shouldn't reach.

## What This Sample Demonstrates

- A custom transport: four Activities in `activities.py` (`launch_in_sandbox`, `write_to_sandbox`, `watch_sandbox`, `remove_sandbox`) built with `CliFiles`, `follow_lines`, and `watch_output`, grouped in `TransportActivities`, and passed as `TemporalTransport(options, SBX_ACTIVITIES)` in the Workflow and `ClaudeAgentSDKPlugin(activities=SBX_ACTIVITIES)` on the Worker.
- One sandbox per transport session, named `claude-sandbox-<session_id>`. Launch creates it unless it already exists, so a retried launch reuses it. Stop removes it, along with its scoped secret and network rule.
- Approval as Workflow state: the `pending_tool_calls` Query lists each waiting tool call with its name and input, and the `decide_tool` Update approves or denies it.

## How the API Key Reaches Claude Code

The key never goes through `ClaudeAgentOptions.env` or any Activity input, so it never appears in Workflow history. The launch Activity reads `ANTHROPIC_API_KEY` from the Worker's own environment and stores it with `sbx secret set anthropic --sandbox <name>`, passing it on stdin. Claude Code in the sandbox gets only the placeholder `sk-ant-api03-proxy-managed`. The sandbox's proxy swaps in the stored key on requests to Anthropic, so the key never enters the sandbox either.

If the Worker has no `ANTHROPIC_API_KEY`, the sandbox uses a global key you stored once with `sbx secret set anthropic`.

The Worker also forwards `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` if they're set. A loopback base URL is rewritten to `host.docker.internal`, so the sandbox can reach a gateway on the Worker's host.

## Prerequisites

- [Docker Sandboxes](https://docs.docker.com/ai/sandboxes/) (`sbx`) installed on the Worker's machine and signed in (`sbx login`). The sandboxes use `sbx`'s `claude` agent template, which includes Claude Code.
- `sbx` keeps sandboxes on the machine that runs it. If you run Workers on several machines, give the transport a `task_queue` that only one machine polls.

## Running the Sample

Start a Temporal dev server:

```bash
temporal server start-dev
```

Start the Worker with your own key (live mode):

```bash
ANTHROPIC_API_KEY=... uv run --group claude-agent-sdk claude_agent_sdk_plugin/sandbox/run_worker.py
```

Or start it without credentials (offline mode). A scripted Anthropic API on the Worker's host answers Claude Code in the sandbox, with the same Worker, plugin, Workflow, and sandbox Activities:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/sandbox/run_worker.py
```

Start the Workflow:

```bash
temporal workflow start \
  --type SandboxWorkflow \
  --task-queue claude-agent-sdk-sandbox \
  --workflow-id sandbox \
  --input '"Write the first five primes to primes.txt, then delete it."'
```

List the tool calls waiting for a decision:

```bash
temporal workflow query --workflow-id sandbox --name pending_tool_calls
```

```
QueryResult  [{"tool_input":{"command":"echo 2 3 5 7 11 > primes.txt && cat primes.txt","description":"Write the primes"},"tool_name":"Bash","tool_use_id":"toolu_write"}]
```

Approve it. Claude Code runs the command in the sandbox:

```bash
temporal workflow update execute --workflow-id sandbox --name decide_tool \
  --input '{"tool_use_id": "toolu_write", "approved": true}'
```

Query again to see the next call, then deny it:

```bash
temporal workflow update execute --workflow-id sandbox --name decide_tool \
  --input '{"tool_use_id": "toolu_delete", "approved": false}'
```

Get the result:

```bash
temporal workflow result --workflow-id sandbox
```

In offline mode, the result is `"I wrote the primes to primes.txt. You denied deleting it, so it stays."` In live mode, Claude chooses its own tool calls and IDs, so use the IDs the Query returns. While the Workflow runs, `sbx ls` shows its `claude-sandbox-...` sandbox. Once the Workflow completes, the sandbox is gone.

## Test

The test needs no Docker. It puts a fake `sbx` on `PATH` that runs each command in a temporary directory, with the Claude Code bundled with the Claude Agent SDK standing in for the sandbox's:

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/sandbox_test.py
```

## Files

| File | Description |
|------|-------------|
| `activities.py` | The four custom transport Activities that run Claude Code through `sbx` |
| `workflow.py` | `SandboxWorkflow`: `ClaudeSDKClient` with the sandbox transport and Update-driven approvals |
| `run_worker.py` | Registers `ClaudeAgentSDKPlugin(activities=SBX_ACTIVITIES)` and the offline answers |

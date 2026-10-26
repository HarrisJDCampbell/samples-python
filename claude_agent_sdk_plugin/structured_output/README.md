# Structured Output

Constrain Claude Code's final answer to a JSON schema and validate it as a typed Pydantic model at the Workflow boundary.

`TriageTicketWorkflow` builds the schema from the `SupportTicket` Pydantic model and passes it as `ClaudeAgentOptions(output_format={"type": "json_schema", "schema": ...})`. Claude Code exposes the schema to the model as a `StructuredOutput` tool, checks the model's input against it, and sends the validated value back in `ResultMessage.structured_output`. The Workflow validates that value with `SupportTicket.model_validate(...)` and returns the model. The Worker's Client uses `pydantic_data_converter` so the typed model crosses the Temporal boundary.

If the model's output does not match the schema, Claude Code returns the validation error to the model as a tool error so it can correct itself. If the model never produces a valid value, `structured_output` is `None` and the Workflow fails with a non-retryable `ApplicationError`.

## Run it

Start a local Temporal server in one terminal:

```bash
temporal server start-dev
```

Start the Worker in a second terminal. It needs `ANTHROPIC_API_KEY` in its environment:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/structured_output/run_worker.py
```

Or run it with no credentials. A scripted local Anthropic API answers with a fixed ticket:

```bash
CLAUDE_OFFLINE=1 uv run --group claude-agent-sdk claude_agent_sdk_plugin/structured_output/run_worker.py
```

Triage a message from a third terminal:

```bash
temporal workflow execute \
  --type TriageTicketWorkflow \
  --task-queue claude-agent-sdk-structured-output \
  --workflow-id structured-output \
  --input '"The app crashes every time I open the settings page."'
```

## Expected behavior

The result is the typed ticket as JSON, for example `{"category": "bug", "priority": 2, "summary": "..."}`. Offline it is always:

```json
{"category": "bug", "priority": 2, "summary": "The settings page crashes the app when opened."}
```

In the Temporal UI, the Claude Code run appears as the transport's Activities, and the Workflow result is the validated `SupportTicket`.

## Test

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin/structured_output_test.py
```

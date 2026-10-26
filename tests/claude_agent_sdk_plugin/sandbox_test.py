import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

import claude_agent_sdk
import pytest
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin, CliFiles
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import scripted_api
from claude_agent_sdk_plugin.sandbox.activities import (
    FILES_ROOT,
    PROXY_MANAGED_KEY,
    SBX_ACTIVITIES,
)
from claude_agent_sdk_plugin.sandbox.run_worker import OFFLINE_ANSWERS
from claude_agent_sdk_plugin.sandbox.workflow import (
    SandboxWorkflow,
    ToolCall,
    ToolDecision,
)

SECRET = "sk-ant-test-secret-never-in-history"

FAKE_SBX = """#!{python}
import json, os, shutil, signal, sys

ROOT = {root!r}
BIN = {bin!r}
args = sys.argv[1:]
with open(os.path.join(ROOT, "log.jsonl"), "a") as log:
    log.write(json.dumps(args) + "\\n")
sandboxes = os.path.join(ROOT, "sandboxes")
command = args[0]
if command == "ls":
    print("\\n".join(sorted(os.listdir(sandboxes))))
elif command == "create":
    name = args[args.index("--name") + 1]
    os.makedirs(os.path.join(sandboxes, name, "home/agent/workspace"))
elif command == "secret":
    name = args[args.index("--sandbox") + 1]
    with open(os.path.join(ROOT, "secrets.jsonl"), "a") as secrets:
        secrets.write(json.dumps([name, sys.stdin.read().strip()]) + "\\n")
elif command == "rm":
    sandbox = os.path.join(sandboxes, args[-1])
    with open(os.path.join(sandbox, "groups")) as groups:
        for group in groups.read().split():
            try:
                os.killpg(int(group), signal.SIGKILL)
            except ProcessLookupError:
                pass
    shutil.rmtree(sandbox)
elif command == "exec":
    rest = args[1:]
    env = {{"PATH": BIN + ":/usr/bin:/bin"}}
    workdir = "/home/agent/workspace"
    interactive = False
    while rest[0].startswith("-"):
        flag = rest.pop(0)
        if flag == "-i":
            interactive = True
        elif flag == "-e":
            key, _, value = rest.pop(0).partition("=")
            env[key] = value.replace("host.docker.internal", "127.0.0.1")
        elif flag == "-w":
            workdir = rest.pop(0)
    name, *argv = rest
    sandbox = os.path.join(sandboxes, name)
    if not os.path.isdir(sandbox):
        sys.exit("sandbox not found: " + name)
    env["HOME"] = os.path.join(sandbox, "home/agent")
    os.setsid()
    with open(os.path.join(sandbox, "groups"), "a") as groups:
        groups.write(str(os.getpid()) + "\\n")
    os.chdir(os.path.join(sandbox, workdir.lstrip("/")))
    if not interactive:
        os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    os.execvpe(argv[0], argv, env)
"""


@pytest.fixture
def fake_sbx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "sbx"
    bin = root / "bin"
    bin.mkdir(parents=True)
    (root / "sandboxes").mkdir()
    (bin / "claude").symlink_to(
        Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
    )
    script = bin / "sbx"
    script.write_text(
        FAKE_SBX.format(python=sys.executable, root=str(root), bin=str(bin))
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin}{os.pathsep}{os.environ['PATH']}")
    return root


def sbx_calls(root: Path) -> list[list[str]]:
    return [json.loads(line) for line in (root / "log.jsonl").read_text().splitlines()]


async def pending_call(handle: WorkflowHandle, tool_use_id: str) -> ToolCall:
    while True:
        for call in await handle.query(SandboxWorkflow.pending_tool_calls):
            if call.tool_use_id == tool_use_id:
                return call
        await asyncio.sleep(0.2)


async def test_workflow_approves_tool_calls_claude_code_makes_in_its_sandbox(
    client: Client, fake_sbx: Path
) -> None:
    task_queue = f"claude-agent-sdk-sandbox-{uuid.uuid4()}"
    with scripted_api(OFFLINE_ANSWERS) as api:
        os.environ["ANTHROPIC_API_KEY"] = SECRET
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SandboxWorkflow],
            plugins=[ClaudeAgentSDKPlugin(activities=SBX_ACTIVITIES)],
        ):
            handle = await client.start_workflow(
                SandboxWorkflow.run,
                "Write the first five primes to primes.txt, then delete it.",
                id=f"claude-agent-sdk-sandbox-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            write = await asyncio.wait_for(pending_call(handle, "toolu_write"), 60)
            assert write.tool_name == "Bash"
            assert write.tool_input["command"].startswith("echo 2 3 5 7 11")
            await handle.execute_update(
                SandboxWorkflow.decide_tool, ToolDecision("toolu_write", True)
            )
            await asyncio.wait_for(pending_call(handle, "toolu_delete"), 60)
            await handle.execute_update(
                SandboxWorkflow.decide_tool, ToolDecision("toolu_delete", False)
            )
            result = await asyncio.wait_for(handle.result(), 60)

    assert result == (
        "I wrote the primes to primes.txt. You denied deleting it, so it stays."
    )
    written = next(
        block
        for body in api.requests
        for message in body["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block.get("tool_use_id") == "toolu_write"
    )
    assert "2 3 5 7 11" in json.dumps(written["content"])

    calls = sbx_calls(fake_sbx)
    creates = [call for call in calls if call[0] == "create"]
    assert len(creates) == 1
    name = creates[0][creates[0].index("--name") + 1]
    assert ["policy", "allow", "network", "--sandbox", name, "**"] in calls
    assert calls[-1] == ["rm", "--force", name]
    assert not (fake_sbx / "sandboxes" / name).exists()
    launch = next(call for call in calls if call[0] == "exec" and "claude" in call)
    assert f"ANTHROPIC_API_KEY={PROXY_MANAGED_KEY}" in launch
    secrets = [json.loads(line) for line in (fake_sbx / "secrets.jsonl").open()]
    assert [name, SECRET] in secrets

    history = await handle.fetch_history()
    assert SECRET not in history.to_json()
    scheduled = {
        event.activity_task_scheduled_event_attributes.activity_type.name
        for event in history.events
        if event.HasField("activity_task_scheduled_event_attributes")
    }
    assert scheduled == {
        "launch_in_sandbox",
        "write_to_sandbox",
        "watch_sandbox",
        "remove_sandbox",
    }
    await Replayer(
        workflows=[SandboxWorkflow],
        plugins=[ClaudeAgentSDKPlugin(activities=SBX_ACTIVITIES)],
    ).replay_workflow(history)

    session_id = name.removeprefix("claude-sandbox-")
    shutil.rmtree(CliFiles(FILES_ROOT, session_id).dir, ignore_errors=True)

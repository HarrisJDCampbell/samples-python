import asyncio
import os
import re
from collections.abc import AsyncIterator, Callable

from temporalio import activity
from temporalio.claude_agent_sdk import (
    CliFiles,
    LaunchRequest,
    StdinWrite,
    StopRequest,
    TransportActivities,
    WatchRequest,
    cli_connection_error,
    follow_lines,
    heartbeating,
    watch_output,
)

FILES_ROOT = "/tmp"
WORKSPACE = "/home/agent/workspace"
PROXY_MANAGED_KEY = "sk-ant-api03-proxy-managed"
FORWARDED_ENV = ("ANTHROPIC_BASE_URL", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")


def sandbox_name(session_id: str) -> str:
    return f"claude-sandbox-{session_id}"


async def sbx(*args: str, input: bytes | None = None) -> bytes:
    process = await asyncio.create_subprocess_exec(
        "sbx",
        *args,
        stdin=asyncio.subprocess.DEVNULL if input is None else asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate(input)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    if process.returncode:
        message = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"sbx {args[0]} failed: {message}")
    return stdout


async def sandbox_exists(name: str) -> bool:
    return name in (await sbx("ls", "-q")).decode().split()


def sandbox_env(request_env: dict[str, str]) -> dict[str, str]:
    forwarded = {
        name: re.sub(r"//(127\.0\.0\.1|localhost)\b", "//host.docker.internal", value)
        for name in FORWARDED_ENV
        if (value := os.environ.get(name))
    }
    return {"ANTHROPIC_API_KEY": PROXY_MANAGED_KEY, **forwarded, **request_env}


# @@@SNIPSTART python-claude-agent-sdk-sandbox-activities
@activity.defn
async def launch_in_sandbox(request: LaunchRequest) -> str:
    async with heartbeating():
        if request.user is not None:
            raise cli_connection_error("Claude Code runs as the sandbox's agent user")
        name = sandbox_name(request.session_id)
        if not await sandbox_exists(name):
            await sbx("create", "--name", name, "--no-progress", "claude")
        await sbx("policy", "allow", "network", "--sandbox", name, "**")
        if key := os.environ.get("ANTHROPIC_API_KEY"):
            await sbx(
                "secret",
                "set",
                "anthropic",
                "--sandbox",
                name,
                "--force",
                input=key.encode(),
            )
        files = CliFiles(FILES_ROOT, request.session_id)
        env_flags = [
            flag
            for key, value in sandbox_env(request.env).items()
            for flag in ("-e", f"{key}={value}")
        ]
        await sbx(
            "exec",
            *env_flags,
            "-w",
            request.cwd or WORKSPACE,
            name,
            *files.launch_command(request.cli_path or "claude", request.args),
        )
        return name


@activity.defn
async def write_to_sandbox(write: StdinWrite) -> None:
    async with heartbeating():
        files = CliFiles(FILES_ROOT, write.session_id)
        command = files.write_stdin_command(write.number)
        await sbx("exec", "-i", write.handle, *command, input=write.text.encode())


@activity.defn
async def watch_sandbox(request: WatchRequest) -> None:
    name = request.handle
    files = CliFiles(FILES_ROOT, request.session_id)

    async def status() -> str:
        return (await sbx("exec", name, *files.status_command())).decode().strip()

    async def running() -> bool:
        return await status() == "running"

    async def exit_status() -> int | None:
        code = await status()
        return int(code) if code.isdigit() else None

    def follow(path: str) -> Callable[[int], AsyncIterator[bytes]]:
        async def read(offset: int) -> bytes:
            script = 'tail -c +"$1" "$2" | head -c 65536'
            return await sbx(
                "exec", name, "sh", "-c", script, "sh", str(offset + 1), path
            )

        return lambda offset: follow_lines(read, running, offset, poll_interval=0.5)

    await watch_output(
        request.session_id,
        stdout=follow(files.stdout),
        exit_status=exit_status,
        stderr=follow(files.stderr),
        stream_topic=request.stream_topic,
        signal_stderr=request.signal_stderr,
    )


@activity.defn
async def remove_sandbox(request: StopRequest) -> None:
    async with heartbeating():
        name = sandbox_name(request.session_id)
        if await sandbox_exists(name):
            await sbx("rm", "--force", name)


SBX_ACTIVITIES = TransportActivities(
    launch=launch_in_sandbox,
    write_stdin=write_to_sandbox,
    watch_output=watch_sandbox,
    stop=remove_sandbox,
)
# @@@SNIPEND

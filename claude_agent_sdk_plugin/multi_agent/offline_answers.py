from claude_agent_sdk_plugin.offline import Answer, tool_use

RESEARCH_NOTES = "- Workflows are durable.\n- Activities are retried.\n- Signals are delivered exactly once."
BRIEFING = "Temporal keeps your code running through failures."

ANSWERS: dict[str, Answer] = {
    "short briefing on this topic": tool_use(
        "toolu_research",
        "Agent",
        description="Research the topic",
        subagent_type="researcher",
        prompt="Collect three key facts about the topic.",
    ),
    "Collect three key facts": RESEARCH_NOTES,
    "tool_result:toolu_research": tool_use(
        "toolu_write",
        "Agent",
        description="Write the briefing",
        subagent_type="writer",
        prompt="Turn these notes into a one-sentence briefing.",
    ),
    "Turn these notes": BRIEFING,
    "tool_result:toolu_write": f"Final briefing: {BRIEFING}",
}

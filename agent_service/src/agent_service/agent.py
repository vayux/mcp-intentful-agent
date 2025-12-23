"""Agent orchestration loop with bounded steps and safe writes.

This module implements the main agent loop that:
1. Connects to an MCP server subprocess for tool execution
2. Uses a planner (LLM or rule-based) to determine next actions
3. Executes tools through MCP with automatic confirmation handling
4. Maintains conversation context across multiple turns
5. Enforces step limits to prevent infinite loops

In production, replace RuleBasedPlanner with a real LLM that outputs
the same Action schema using structured outputs.
"""
from __future__ import annotations

import logging
from typing import Any

from .llm_adapter import (
    Action,
    AskUserAction,
    FinalAction,
    RuleBasedPlanner,
    ToolAction,
)
from .mcp_client import McpConnection

log = logging.getLogger("agent")

# Maximum steps per conversation turn to prevent infinite loops
MAX_STEPS = 6


async def run_agent(
    user_message: str,
    *,
    mcp_server_script: str,
    backend_base_url: str,
    backend_access_token: str,
    scopes: list[str],
    history: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Minimal orchestration loop:
    - bounded steps
    - tool execution through MCP
    - safe write confirmation enforced by tool server

    Returns: (response_message, updated_tool_results)
    """
    planner = RuleBasedPlanner()
    tool_results = tool_results or []

    conn = McpConnection()
    tools = await conn.connect(
        server_script=mcp_server_script,
        env={
            "BACKEND_BASE_URL": backend_base_url,
            "MCP_ACCESS_TOKEN": backend_access_token,
            "MCP_SCOPES": ",".join(scopes),
        },
    )
    log.info("connected_tools=%s", [t["name"] for t in tools])

    try:
        current_user_text = user_message

        for step in range(MAX_STEPS):
            action: Action = planner.next_action(current_user_text, tool_results)
            log.info("step=%d action_type=%s", step, action.type)

            if isinstance(action, FinalAction):
                return action.message, tool_results

            if isinstance(action, AskUserAction):
                return action.question, tool_results

            if isinstance(action, ToolAction):
                log.info(
                    "step=%d action=tool tool=%s args=%s why=%s",
                    step,
                    action.tool,
                    action.args,
                    action.why,
                )

                result = await conn.call_tool(action.tool, action.args)
                tool_results.append(
                    result if isinstance(result, dict) else {"ok": True, "result": result}
                )

                # If tool server demands confirmation, let planner handle the message
                if (
                    isinstance(result, dict)
                    and result.get("error", {}).get("code") == "CONFIRMATION_REQUIRED"
                ):
                    # Run planner once more to get appropriate confirmation message
                    confirm_action = planner.next_action("", tool_results)
                    if isinstance(confirm_action, AskUserAction):
                        return confirm_action.question, tool_results
                    # Fallback if planner returns something unexpected
                    return 'I need your confirmation to proceed. Reply "Yes" to confirm.', tool_results

                # Continue loop (no new user input mid-loop)
                current_user_text = ""

        return (
            "I couldn't complete that safely within the step limit. Please try again with more details.",
            tool_results,
        )
    finally:
        await conn.close()


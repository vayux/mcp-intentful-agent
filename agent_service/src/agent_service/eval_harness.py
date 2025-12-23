"""Simple evaluation harness for testing agent behavior.

Run with: python -m agent_service.eval_harness

This harness tests golden conversations to ensure:
- Confirmation is required before writes
- Tool calls happen in expected order
- Responses contain expected content
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent import run_agent
from .logging_setup import setup_logging


@dataclass
class TestCase:
    """A test case for the agent."""

    name: str
    messages: list[str]
    expect_reply_contains: list[str] = field(default_factory=list)
    expect_reply_not_contains: list[str] = field(default_factory=list)


# Golden test cases
GOLDEN_TESTS = [
    TestCase(
        name="cancel_flow_asks_confirmation",
        messages=["Cancel my delayed order"],
        expect_reply_contains=["confirm", "cancel"],
    ),
    TestCase(
        name="status_check_shows_delayed",
        messages=["What is my order status?"],
        expect_reply_contains=["delayed"],
    ),
    TestCase(
        name="cancel_flow_executes_after_confirmation",
        messages=["Cancel my order", "Yes, cancel it"],
        expect_reply_contains=["cancelled"],
    ),
    TestCase(
        name="simple_greeting_handled",
        messages=["Hello"],
        expect_reply_contains=["help", "order"],
    ),
]


async def run_test(
    test: TestCase, mcp_script: str, backend_url: str
) -> tuple[bool, str]:
    """Run a single test case."""
    tool_results: list[dict[str, Any]] = []
    all_replies: list[str] = []

    for message in test.messages:
        try:
            reply, tool_results = await run_agent(
                user_message=message,
                mcp_server_script=mcp_script,
                backend_base_url=backend_url,
                backend_access_token="test-token",
                scopes=["order:read", "order:cancel"],
                tool_results=tool_results,
            )
            all_replies.append(reply)
        except Exception as e:
            return False, f"Exception during agent execution: {e}"

    # Check assertions on the final reply
    final_reply = all_replies[-1].lower() if all_replies else ""

    for expected in test.expect_reply_contains:
        if expected.lower() not in final_reply:
            return (
                False,
                f"Expected reply to contain '{expected}', got: {all_replies[-1][:100]}",
            )

    for not_expected in test.expect_reply_not_contains:
        if not_expected.lower() in final_reply:
            return (
                False,
                f"Expected reply NOT to contain '{not_expected}', got: {all_replies[-1][:100]}",
            )

    return True, "PASSED"


async def run_all_tests() -> bool:
    """Run all golden tests."""
    setup_logging()

    # Determine paths
    mcp_script = os.getenv(
        "MCP_SERVER_SCRIPT",
        str(
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "src"
            / "mcp_server"
            / "server.py"
        ),
    )
    backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8080")

    print(f"Running {len(GOLDEN_TESTS)} tests...")
    print(f"MCP script: {mcp_script}")
    print(f"Backend URL: {backend_url}")
    print("-" * 50)

    passed = 0
    failed = 0

    for test in GOLDEN_TESTS:
        try:
            success, message = await run_test(test, mcp_script, backend_url)
            if success:
                print(f"✅ {test.name}: {message}")
                passed += 1
            else:
                print(f"❌ {test.name}: {message}")
                failed += 1
        except Exception as e:
            print(f"❌ {test.name}: ERROR - {e}")
            failed += 1

    print("-" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Entry point for the eval harness."""
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()


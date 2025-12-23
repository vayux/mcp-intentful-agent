"""HTTP API for the agent service with session management.

This FastAPI application provides an HTTP interface to the agent:
- POST /chat: Send messages and receive agent responses
- GET /health: Health check endpoint
- GET /sessions: List active sessions (debugging)
- DELETE /sessions/{id}: Clear a specific session

Session management is handled in-memory for this POC.
In production, use Redis or a database for session storage.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import run_agent
from .logging_setup import setup_logging

# Setup logging
setup_logging()
log = logging.getLogger("agent-service")

app = FastAPI(
    title="Agent Service",
    description="AI agent for order management with MCP tools",
)

# ---- Session storage (use Redis in production) ----
sessions: dict[str, dict[str, Any]] = {}

# ---- Configuration ----
# Path to MCP server script (adjust for your setup)
MCP_SERVER_SCRIPT = os.getenv(
    "MCP_SERVER_SCRIPT",
    str(
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "src"
        / "mcp_server"
        / "server.py"
    ),
)
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8080")
BACKEND_ACCESS_TOKEN = os.getenv("BACKEND_ACCESS_TOKEN", "demo-token-12345")
DEFAULT_SCOPES = ["order:read", "order:cancel", "order:write"]


class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response with session tracking."""

    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Process a chat message and return agent response."""
    # Get or create session
    session_id = req.session_id or str(uuid.uuid4())
    session = sessions.setdefault(session_id, {"history": [], "tool_results": []})

    log.info("session_id=%s message=%s", session_id, req.message[:100])

    try:
        reply, tool_results = await run_agent(
            user_message=req.message,
            mcp_server_script=MCP_SERVER_SCRIPT,
            backend_base_url=BACKEND_BASE_URL,
            backend_access_token=BACKEND_ACCESS_TOKEN,
            scopes=DEFAULT_SCOPES,
            history=session["history"],
            tool_results=session["tool_results"],
        )

        # Update session
        session["history"].append({"role": "user", "content": req.message})
        session["history"].append({"role": "assistant", "content": reply})
        session["tool_results"] = tool_results

        log.info("session_id=%s reply=%s", session_id, reply[:100])
        return ChatResponse(reply=reply, session_id=session_id)

    except Exception as e:
        log.exception("Error processing chat: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    """Clear a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "cleared"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions")
def list_sessions():
    """List all active sessions (for debugging)."""
    return {
        "sessions": [
            {"session_id": sid, "message_count": len(s["history"])}
            for sid, s in sessions.items()
        ]
    }


def main():
    """Entry point for the agent service."""
    log.info("Starting agent service on port 3000")
    log.info("MCP server script: %s", MCP_SERVER_SCRIPT)
    log.info("Backend URL: %s", BACKEND_BASE_URL)
    uvicorn.run(app, host="0.0.0.0", port=3000)


if __name__ == "__main__":
    main()


# MCP Agent Service

> A proof-of-concept AI agent built with the Model Context Protocol (MCP) that demonstrates how to add an intelligent agent layer over existing backend APIs.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project demonstrates how to build an AI agent that wraps an existing backend API using the Model Context Protocol (MCP). The agent provides a natural language interface for users to interact with backend services while maintaining security, validation, and business logic guardrails.

### What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open protocol that standardizes how AI agents communicate with tools and data sources. It provides:

- **Standardized tool discovery and execution**
- **Multiple transport layers** (stdio, HTTP/SSE)
- **Built-in security and scope management**
- **Language-agnostic JSON-RPC protocol**

### Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│   Client    │────▶│  Agent Service  │────▶│  MCP Server │────▶│ Mock Backend │
│  (HTTP/UI)  │     │   (Port 3000)   │     │   (stdio)   │     │  (Port 8080) │
│             │◀────│   FastAPI +     │◀────│  FastMCP +  │◀────│   FastAPI    │
│             │     │   Session Mgmt  │     │   Tools     │     │   REST API   │
└─────────────┘     └─────────────────┘     └─────────────┘     └──────────────┘
```

<img width="986" height="523" alt="diagram-export-23-12-2025-14_09_21" src="https://github.com/user-attachments/assets/11d82137-9d73-4683-9075-48c8c97b1aa3" />


**Communication Patterns:**
- Client ↔ Agent Service: HTTP REST API
- Agent Service ↔ MCP Server: stdio (JSON-RPC over subprocess)
- MCP Server ↔ Backend: HTTP REST API

## Components

### 1. Mock Backend (`backend/`)
Simulates an existing production backend with order management endpoints. In a real implementation, this would be your actual backend system.

### 2. MCP Server (`mcp_server/`)
Exposes **intentful tools** that wrap backend operations with:
- Business logic and validation (Pydantic models)
- Confirmation gating for destructive operations
- Scope-based authorization
- Idempotency support
- Structured error handling

### 3. Agent Service (`agent_service/`)
Orchestrates the conversation flow:
- HTTP API for client interactions
- Session management (in-memory for POC)
- Action planning (rule-based POC, replace with LLM)
- Bounded execution loops
- Tool execution via MCP

### 4. Chat UI (`chat_ui.py`)
Streamlit-based web interface for testing and demonstration.

## Features

### Agent Capabilities

The agent can help with:
- **Check order status** - "What's my order status?"
- **View order details** - "Show my latest order"
- **Cancel delayed orders** - "Cancel my order" (with confirmation)
- **Place new orders** - "Order 2 widgets and 1 gadget"

### MCP Tools

| Tool | Description | Requires Confirmation |
|------|-------------|:---------------------:|
| `get_latest_order` | Get the most recent order for the user | No |
| `get_order_status` | Get status for a specific order | No |
| `request_order_cancellation` | Cancel an order (only delayed orders) | Yes |
| `create_order` | Place a new order with products | Yes |

**Available Products:** widget, gadget, gizmo, doohickey, thingamajig

### Key Design Principles

1. **Intentful Tools** - Tools encode business intent (e.g., "request_order_cancellation") rather than CRUD operations (e.g., "update_order")
2. **Server-side Guardrails** - MCP server enforces validation, confirmation, and authorization
3. **Idempotency** - Write operations support idempotency keys to prevent duplicate actions
4. **Bounded Execution** - Agent loop has a maximum step limit to prevent infinite loops
5. **Session Management** - Multi-turn conversations maintain context

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

**Option 1: Single Virtual Environment (Recommended)**

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

**Option 2: Separate Environments per Component**

```bash
# Backend
cd backend && pip install -e . && cd ..

# MCP Server
cd mcp_server && pip install -e . && cd ..

# Agent Service
cd agent_service && pip install -e . && cd ..

# Streamlit UI
pip install streamlit
```

### Running the Application

**Terminal 1 - Start Backend**
```bash
cd backend
python main.py
# Running on http://localhost:8080
```

**Terminal 2 - Start Agent Service**
```bash
cd agent_service/src
python -m agent_service.app
# Running on http://localhost:3000
```

**Terminal 3 - Start Chat UI (Recommended)**
```bash
streamlit run chat_ui.py
# Opens browser at http://localhost:8501
```

### Testing

**Option A: Streamlit UI**
- Navigate to http://localhost:8501
- Use quick action buttons or type messages
- Session state is maintained automatically

**Option B: Demo Script**
```bash
chmod +x run_demo.sh
./run_demo.sh
```

**Option C: cURL Commands**
```bash
# Place an order
curl -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Order 2 widgets and 1 gadget"}'

# Response: {"reply": "Ready to place order...", "session_id": "abc-123"}

# Confirm the order
curl -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes", "session_id": "abc-123"}'
```

**Option D: Run Test Suite**
```bash
cd agent_service/src
python -m agent_service.eval_harness
```

## API Reference

### Agent Service API

**POST /chat**
- Request: `{"message": str, "session_id": str?}`
- Response: `{"reply": str, "session_id": str}`

**GET /health**
- Response: `{"status": "ok"}`

**GET /sessions**
- Response: List of active sessions (debugging)

**DELETE /sessions/{id}**
- Clear a specific session

### Backend API

**GET /v1/me/orders/latest**
- Get user's most recent order

**GET /v1/orders/{id}/status**
- Get order status

**POST /v1/orders/{id}/cancel**
- Cancel an order (idempotent)

**POST /v1/orders**
- Create a new order
- Request: `{"items": [{"product_name": str, "quantity": int}]}`

## Configuration

Environment variables can be set to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_BASE_URL` | `http://localhost:8080` | Backend API URL |
| `BACKEND_ACCESS_TOKEN` | `demo-token-12345` | Auth token for backend |
| `MCP_SERVER_SCRIPT` | Auto-detected | Path to MCP server script |

## Project Structure

```
mcp-agent-service/
├── backend/                    # Mock backend service
│   ├── pyproject.toml
│   └── main.py
├── mcp_server/                 # MCP tool server
│   ├── pyproject.toml
│   └── src/mcp_server/
│       ├── server.py          # FastMCP server with tools
│       ├── backend_client.py  # HTTP client for backend
│       ├── errors.py          # Structured error types
│       └── logging_setup.py   # Logging config (stderr)
├── agent_service/              # Agent orchestration
│   ├── pyproject.toml
│   └── src/agent_service/
│       ├── app.py             # FastAPI HTTP wrapper
│       ├── agent.py           # Main orchestration loop
│       ├── llm_adapter.py     # Action schema & planner
│       ├── mcp_client.py      # MCP client (stdio)
│       ├── logging_setup.py   # Logging config (stdout)
│       └── eval_harness.py    # Test suite
├── chat_ui.py                  # Streamlit web interface
├── run_demo.sh                 # CLI demo script
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore patterns
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Add docstrings to all modules, classes, and public functions
- Format with Black (optional)

### Adding New Tools

1. Add the backend endpoint in `backend/main.py`
2. Add the HTTP client method in `mcp_server/src/mcp_server/backend_client.py`
3. Create Pydantic input model and tool function in `mcp_server/src/mcp_server/server.py`
4. Update the planner logic in `agent_service/src/agent_service/llm_adapter.py`
5. Add test cases to `agent_service/src/agent_service/eval_harness.py`

### Replacing the Rule-Based Planner with an LLM

The `RuleBasedPlanner` in `llm_adapter.py` is a deterministic rule-based system for POC purposes. To use a real LLM:

1. Replace `RuleBasedPlanner.next_action()` with an LLM call
2. Use structured outputs to return the same `Action` schema
3. Examples:
   - **OpenAI**: `response_format={"type": "json_schema", "json_schema": {...}}`
   - **Anthropic**: Use tool calling with forced tool choice
   - **Any LLM**: Use [Instructor](https://github.com/jxnl/instructor) library

## Production Considerations

This is a POC. For production deployment:

1. **Replace in-memory session store** with Redis or database
2. **Add proper JWT validation** instead of simple token check
3. **Use a real LLM** instead of RuleBasedPlanner
4. **Add rate limiting and monitoring**
5. **Implement proper logging and observability**
6. **Add comprehensive error handling**
7. **Use secrets management** for tokens and credentials
8. **Add authentication and authorization**
9. **Implement audit logging** for all write operations
10. **Deploy with proper CI/CD** and testing

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [FastMCP Library](https://github.com/jlowin/fastmcp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) for easy MCP server implementation
- Inspired by the [MCP specification](https://spec.modelcontextprotocol.io/)
- Demo UI powered by [Streamlit](https://streamlit.io/)

---

**Note:** This is a proof-of-concept for educational purposes. It demonstrates architectural patterns and is not production-ready as-is.

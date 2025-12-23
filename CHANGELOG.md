# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-23

### Added
- Initial release of MCP Agent Service POC
- Mock backend service with order management endpoints
- MCP server with intentful tools for order operations
- Agent service with HTTP API and session management
- Streamlit chat UI for interactive testing
- Support for creating, viewing, and canceling orders
- Confirmation gating for destructive operations
- Idempotency support for write operations
- Scope-based authorization
- Structured error handling
- Test suite with evaluation harness
- Demo script for quick testing
- Comprehensive documentation
- MIT License
- Contributing guidelines
- Professional README with badges and architecture diagrams

### Features

#### MCP Tools
- `get_latest_order`: Retrieve user's most recent order
- `get_order_status`: Check status of a specific order
- `request_order_cancellation`: Cancel delayed orders (requires confirmation)
- `create_order`: Place new orders with product selection (requires confirmation)

#### Agent Capabilities
- Natural language order status checking
- Order detail viewing
- Order cancellation with confirmation flow
- New order placement with confirmation
- Multi-turn conversation support
- Session state management

#### Backend Endpoints
- `GET /v1/me/orders/latest`: Get latest order
- `GET /v1/orders/{id}/status`: Get order status  
- `POST /v1/orders/{id}/cancel`: Cancel order (idempotent)
- `POST /v1/orders`: Create new order
- `GET /health`: Health check

### Technical Details

#### Architecture
- Agent Service: FastAPI + session management (Port 3000)
- MCP Server: FastMCP with stdio transport (subprocess)
- Mock Backend: FastAPI REST API (Port 8080)
- Communication: HTTP (client ↔ agent), stdio/JSON-RPC (agent ↔ MCP), HTTP (MCP ↔ backend)

#### Code Quality
- Type hints throughout
- Comprehensive docstrings
- Structured logging
- Error handling with custom exceptions
- Pydantic validation for all inputs
- Clean separation of concerns

#### Testing
- Evaluation harness with test cases
- Demo script for manual testing
- Streamlit UI for interactive testing
- Health check endpoints

### Documentation
- Professional README with quick start guide
- Architecture diagrams
- API reference
- Configuration guide
- Production considerations
- Contributing guidelines
- Code examples and usage patterns

### Development
- Python 3.10+ support
- Virtual environment setup
- Consolidated requirements.txt
- Separate pyproject.toml per component
- .gitignore for common patterns
- Clean project structure

## [Unreleased]

### Planned Features
- Real LLM integration (replacing RuleBasedPlanner)
- Redis-based session storage
- Enhanced error recovery
- Rate limiting
- Metrics and monitoring
- Docker containerization
- CI/CD pipeline
- More comprehensive test coverage

---

For more details on any release, see the git log or GitHub releases page.


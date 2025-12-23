# Contributing to MCP Agent Service

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/mcp-agent-service.git
cd mcp-agent-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
cd backend && pip install -e . && cd ..
cd mcp_server && pip install -e . && cd ..
cd agent_service && pip install -e . && cd ..
```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for all function signatures
- Add docstrings to all modules, classes, and public functions
- Keep functions focused and single-purpose
- Write self-documenting code with clear variable names

### Example

```python
"""Module docstring explaining the purpose."""
from __future__ import annotations

from typing import Any

def process_order(order_id: str, confirm: bool = False) -> dict[str, Any]:
    """Process an order with optional confirmation.
    
    Args:
        order_id: Unique order identifier
        confirm: Whether to confirm the processing
        
    Returns:
        Dictionary containing order processing result
        
    Raises:
        ValueError: If order_id is invalid
    """
    # Implementation...
    pass
```

## Testing

Before submitting a pull request, ensure:

1. All existing tests pass
2. New features include tests
3. Code has been manually tested with the demo

```bash
# Run the test suite
cd agent_service/src
python -m agent_service.eval_harness

# Manual testing
./run_demo.sh
```

## Commit Messages

Use clear, descriptive commit messages:

- Start with a verb in present tense (Add, Fix, Update, Remove)
- Keep the first line under 50 characters
- Add a detailed description if needed

```bash
# Good
git commit -m "Add support for order refunds"

# Better
git commit -m "Add support for order refunds

Implements a new MCP tool 'request_order_refund' that allows
users to request refunds for completed orders. Includes:
- Backend endpoint for refund processing
- MCP tool with confirmation gating
- Updated planner logic
- Test cases"
```

## Pull Request Process

1. **Update Documentation**: Ensure README.md reflects any changes
2. **Add Tests**: Include tests for new features
3. **Update CHANGELOG**: Add entry describing your changes
4. **One Feature Per PR**: Keep pull requests focused on a single feature or fix
5. **Respond to Feedback**: Address review comments promptly

### PR Title Format

```
[Type] Brief description

Types:
- Feature: New functionality
- Fix: Bug fix
- Docs: Documentation changes
- Refactor: Code refactoring
- Test: Test improvements
- Chore: Maintenance tasks
```

## Adding New MCP Tools

When adding a new tool, update all layers:

1. **Backend** (`backend/main.py`): Add REST endpoint
2. **Backend Client** (`mcp_server/src/mcp_server/backend_client.py`): Add HTTP client method
3. **MCP Server** (`mcp_server/src/mcp_server/server.py`):
   - Create Pydantic input model
   - Implement tool function with `@mcp.tool()` decorator
   - Add appropriate validation and error handling
4. **Planner** (`agent_service/src/agent_service/llm_adapter.py`): Update intent detection and action logic
5. **Tests** (`agent_service/src/agent_service/eval_harness.py`): Add test cases
6. **Documentation**: Update README with new tool description

## Code Review Checklist

Before submitting, verify:

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New code has tests
- [ ] Documentation is updated
- [ ] No unnecessary dependencies added
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate
- [ ] Type hints are used consistently
- [ ] No security vulnerabilities introduced
- [ ] Comments explain "why", not "what"

## Reporting Issues

When reporting bugs or issues:

1. Check if the issue already exists
2. Provide a clear title and description
3. Include steps to reproduce
4. Specify your environment (OS, Python version)
5. Include relevant logs or error messages

### Issue Template

```markdown
**Description:**
Clear description of the issue

**Steps to Reproduce:**
1. Start the services
2. Send request: `curl ...`
3. Observe error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: macOS 14.0
- Python: 3.10.5
- MCP version: 1.0.0

**Logs:**
```
Relevant log output
```
```

## Feature Requests

For new features:

1. Check if similar feature exists or was requested
2. Describe the use case and benefit
3. Provide examples of how it would work
4. Consider backward compatibility

## Questions?

Feel free to open an issue with the "question" label if you need help or clarification.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help make this project better for everyone

## License

By contributing, you agree that your contributions will be licensed under the MIT License.


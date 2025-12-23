#!/bin/bash
# Demo script to test the MCP Agent Service POC

set -e

echo "=== MCP Agent POC Demo ==="
echo ""

# Check if backend is running
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "[ERROR] Backend not running. Start it with:"
    echo "   cd backend && python main.py"
    exit 1
fi
echo "[OK] Backend is running on port 8080"

# Check if agent service is running
if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "[ERROR] Agent service not running. Start it with:"
    echo "   cd agent_service/src && python -m agent_service.app"
    exit 1
fi
echo "[OK] Agent service is running on port 3000"

echo ""
echo "=== Testing conversation flow ==="
echo ""

# First message
echo "User: Cancel my delayed order"
RESPONSE=$(curl -s -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Cancel my delayed order"}')

REPLY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['reply'])")
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo "Agent: $REPLY"
echo "   (session_id: $SESSION_ID)"
echo ""

# Second message (confirmation)
echo "User: Yes, cancel it"
RESPONSE=$(curl -s -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Yes, cancel it\", \"session_id\": \"$SESSION_ID\"}")

REPLY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['reply'])")
echo "Agent: $REPLY"
echo ""

echo "=== Demo complete ==="
echo ""
echo "Try more commands:"
echo "  curl -X POST http://localhost:3000/chat -H 'Content-Type: application/json' -d '{\"message\": \"What is my order status?\"}'"

"""MCP server exposing intentful tools over the existing backend.

This server implements the Model Context Protocol (MCP) to expose
business-intentful tools that encapsulate domain logic, validation,
and security guardrails over an existing REST API.

Key features:
- Tool discovery via MCP protocol
- Input validation with Pydantic
- Confirmation gating for destructive operations
- Scope-based authorization
- Idempotent operations
- Structured error handling
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from mcp_server.backend_client import ExistingBackendClient
from mcp_server.errors import ToolError, structured_error
from mcp_server.logging_setup import setup_logging

log = logging.getLogger("orders-mcp")

# ---- Configuration from environment (set by agent-service) ----
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8080")
ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "")
SCOPES = set(s.strip() for s in os.getenv("MCP_SCOPES", "").split(",") if s.strip())


def require_scope(scopes: set[str], required: str) -> None:
    """Check if required scope is present."""
    if required not in scopes:
        raise ToolError("FORBIDDEN", f"Missing scope: {required}")


# Demo idempotency store (use Redis/DynamoDB in production)
_idempotency_cache: dict[str, Any] = {}

# Initialize FastMCP server
mcp = FastMCP("orders-mcp")

# Backend client (initialized in main)
backend: ExistingBackendClient | None = None


# ---- Pydantic models for input validation ----
class GetOrderStatusInput(BaseModel):
    """Input for get_order_status tool."""

    order_id: str = Field(
        ..., min_length=6, max_length=64, description="Order identifier"
    )


class RequestCancelInput(BaseModel):
    """Input for request_order_cancellation tool."""

    order_id: str = Field(..., min_length=6, max_length=64)
    confirmed: bool = Field(..., description="Must be true to execute cancellation")
    idempotency_key: str | None = Field(None, min_length=8, max_length=128)


class OrderItemInput(BaseModel):
    """Single item in an order."""

    product_name: str = Field(..., min_length=1, max_length=100, description="Name of the product")
    quantity: int = Field(1, ge=1, le=100, description="Quantity to order")


class CreateOrderInput(BaseModel):
    """Input for create_order tool."""

    items: list[OrderItemInput] = Field(..., min_length=1, max_length=10)
    confirmed: bool = Field(..., description="Must be true to place the order")


# ---- Tools (async, return JSON strings) ----
@mcp.tool()
async def get_latest_order() -> str:
    """Get the most recent order for the authenticated user."""
    try:
        require_scope(SCOPES, "order:read")
        assert backend is not None
        order = await backend.get_latest_order()
        log.info("tool=get_latest_order order_id=%s", order.get("orderId"))
        return json.dumps({"ok": True, "order": order})
    except Exception as e:
        log.warning("tool=get_latest_order err=%s", repr(e))
        return json.dumps(structured_error(e))


@mcp.tool()
async def get_order_status(order_id: str) -> str:
    """Get status for a specific order by order_id."""
    try:
        require_scope(SCOPES, "order:read")
        inp = GetOrderStatusInput(order_id=order_id)
        assert backend is not None
        status = await backend.get_order_status(inp.order_id)
        log.info(
            "tool=get_order_status order_id=%s status=%s",
            inp.order_id,
            status.get("status"),
        )
        return json.dumps({"ok": True, "status": status})
    except Exception as e:
        log.warning("tool=get_order_status order_id=%s err=%s", order_id, repr(e))
        return json.dumps(structured_error(e))


@mcp.tool()
async def request_order_cancellation(
    order_id: str, confirmed: bool, idempotency_key: str | None = None
) -> str:
    """Request cancellation for an order. Requires confirmed=True. Idempotent."""
    try:
        require_scope(SCOPES, "order:cancel")
        inp = RequestCancelInput(
            order_id=order_id, confirmed=confirmed, idempotency_key=idempotency_key
        )

        # Gate: require explicit confirmation
        if not inp.confirmed:
            raise ToolError(
                "CONFIRMATION_REQUIRED",
                "Cancellation requires explicit confirmation.",
                {"order_id": inp.order_id, "required": {"confirmed": True}},
            )

        key = inp.idempotency_key or str(uuid.uuid4())
        cache_key = f"cancel:{inp.order_id}:{key}"

        # Idempotency check
        if cache_key in _idempotency_cache:
            log.info(
                "audit=true tool=request_order_cancellation cache_hit=true order_id=%s key=%s",
                inp.order_id,
                key,
            )
            return json.dumps(
                {
                    "ok": True,
                    "result": _idempotency_cache[cache_key],
                    "idempotency_key": key,
                }
            )

        assert backend is not None
        result = await backend.request_cancellation(inp.order_id, key)

        # Audit log for writes
        log.info(
            "audit=true tool=request_order_cancellation order_id=%s key=%s result=%s",
            inp.order_id,
            key,
            result,
        )

        _idempotency_cache[cache_key] = result
        return json.dumps({"ok": True, "result": result, "idempotency_key": key})
    except Exception as e:
        log.warning(
            "tool=request_order_cancellation order_id=%s err=%s", order_id, repr(e)
        )
        return json.dumps(structured_error(e))


@mcp.tool()
async def create_order(items: list[dict], confirmed: bool) -> str:
    """Create a new order with the specified products. Available products: widget, gadget, gizmo, doohickey, thingamajig. Requires confirmed=True."""
    try:
        require_scope(SCOPES, "order:write")

        # Validate input
        validated_items = [OrderItemInput(**item) for item in items]
        inp = CreateOrderInput(items=validated_items, confirmed=confirmed)

        # Gate: require explicit confirmation for writes
        if not inp.confirmed:
            items_summary = ", ".join(
                f"{item.quantity}x {item.product_name}" for item in inp.items
            )
            raise ToolError(
                "CONFIRMATION_REQUIRED",
                f"Please confirm you want to place an order for: {items_summary}",
                {
                    "items": [{"product_name": i.product_name, "quantity": i.quantity} for i in inp.items],
                    "required": {"confirmed": True},
                },
            )

        assert backend is not None
        result = await backend.create_order(
            [{"product_name": item.product_name, "quantity": item.quantity} for item in inp.items]
        )

        log.info(
            "audit=true tool=create_order order_id=%s items=%d total=%s",
            result.get("orderId"),
            len(inp.items),
            result.get("total"),
        )

        return json.dumps({"ok": True, "order": result})
    except Exception as e:
        log.warning("tool=create_order err=%s", repr(e))
        return json.dumps(structured_error(e))


def main() -> None:
    """Entry point for the MCP server."""
    setup_logging()

    global backend
    if not ACCESS_TOKEN:
        raise RuntimeError("Missing MCP_ACCESS_TOKEN (agent-service must provide it)")

    backend = ExistingBackendClient(BACKEND_BASE_URL, ACCESS_TOKEN)

    log.info("Starting orders-mcp server over stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

